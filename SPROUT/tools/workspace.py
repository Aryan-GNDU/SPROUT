import ast
import csv
import datetime
import json
import random
import re
import subprocess
import sys
from pathlib import Path
from SPROUT.tools.registry import Skills
from SPROUT.memory.retrieval import DocumentRetriever

def get_weather(location: str) -> str:
    temperature = random.randint(10, 30)
    status = random.choice(["Sunny", "Cloudy", "Rainy"])
    return f"Weather in {location}: {status}, {temperature}℃"


def calculator(a: str, b: str) -> float:
    """Add two numbers."""
    return float(a) + float(b)


def add(a: str, b: str) -> float:
    """Add two numbers."""
    return float(a) + float(b)


def subtract(a: str, b: str) -> float:
    """Subtract two numbers."""
    return float(a) - float(b)


def multiply(a: str, b: str) -> float:
    """Multiply two numbers."""
    return float(a) * float(b)


def today() -> str:
    """Return today's date (YYYY-MM-DD)."""
    return datetime.date.today().isoformat()


def days_between(a: str, b: str) -> int:
    """Days between two ISO dates."""
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


# --- Code Tools (workspace-scoped) ---

# Directories that are noise for exploration, search, and linting.
_EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
}

_MAX_READ_CHARS = 20000
_MAX_OUTPUT_CHARS = 12000

# Git revisions: letters, digits and a few separators. Must not start with "-"
# so a model can never smuggle an option into a git command.
_REVISION_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.~^/@{}-]*$")


def _build_code_tools(workspace: str = ".") -> dict:
    """Build code tool functions scoped to a workspace. Returns {name: (func, description)}."""
    root = Path(workspace).resolve()

    def _safe_path(path: str) -> Path:
        """Resolve path within workspace, reject traversal."""
        resolved = (root / path).resolve()
        # is_relative_to avoids the prefix bug where '/work-evil' passes a
        # string check against '/work'.
        if not resolved.is_relative_to(root):
            raise ValueError(f"Path '{path}' is outside the workspace.")
        return resolved

    def _git(args: list, timeout: int = 10) -> str:
        """Run a git command in the workspace and return trimmed output or an error string."""
        name = args[0]
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )
            output = result.stdout.strip()
            if len(output) > _MAX_OUTPUT_CHARS:
                output = output[:_MAX_OUTPUT_CHARS] + "\n\n[Output truncated.]"
            return output
        except subprocess.TimeoutExpired:
            return f"Error: git {name} timed out."
        except FileNotFoundError:
            return "Error: Git is not installed or not on PATH."
        except subprocess.CalledProcessError as error:
            return (
                error.stderr.strip()
                or error.stdout.strip()
                or f"git {name} failed ({error.returncode})."
            )

    # ---------- Reading ----------

    def read_file(path: str) -> str:
        """Read a file's contents."""
        target = _safe_path(path)
        if not target.exists():
            return f"Error: '{path}' not found."
        text = target.read_text(encoding="utf-8")
        if len(text) > _MAX_READ_CHARS:
            return (
                text[:_MAX_READ_CHARS]
                + f"\n\n[Truncated at {_MAX_READ_CHARS} characters. "
                "Use read_lines to read specific sections.]"
            )
        return text

    def read_lines(path: str, start: str = "1", end: str = "50") -> str:
        """Read specific lines from a file (1-indexed, inclusive)."""
        target = _safe_path(path)
        if not target.exists():
            return f"Error: '{path}' not found."
        start, end = int(start), int(end)
        lines = target.read_text(encoding="utf-8").splitlines()
        selected = lines[max(0, start - 1) : end]
        numbered = [
            f"{i}: {line}" for i, line in enumerate(selected, start=max(1, start))
        ]
        return "\n".join(numbered) or "(empty range)"

    def list_files(directory: str = ".") -> str:
        """List files in a directory."""
        target = _safe_path(directory)
        if not target.is_dir():
            return f"Error: '{directory}' is not a directory."
        entries = sorted(target.iterdir())
        return (
            "\n".join(p.name + ("/" if p.is_dir() else "") for p in entries)
            or "(empty)"
        )

    def tree(directory: str = ".", depth: str = "2") -> str:
        """Show a recursive directory tree, skipping noise like .git and .venv."""
        target = _safe_path(directory)
        if not target.is_dir():
            return f"Error: '{directory}' is not a directory."
        max_depth = max(1, min(int(depth), 6))
        max_entries = 200
        lines = []

        def walk(folder: Path, level: int) -> None:
            entries = sorted(
                folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            )
            for entry in entries:
                if entry.name in _EXCLUDED_DIRS:
                    continue
                if len(lines) >= max_entries:
                    return
                is_dir = entry.is_dir() and not entry.is_symlink()
                lines.append("  " * level + entry.name + ("/" if is_dir else ""))
                if is_dir and level + 1 < max_depth:
                    walk(entry, level + 1)

        walk(target, 0)
        if not lines:
            return "(empty)"
        if len(lines) >= max_entries:
            lines.append(f"[Showing the first {max_entries} entries.]")
        return "\n".join(lines)

    def find_files(pattern: str) -> str:
        """Find files matching a glob pattern (e.g., '*.py')."""
        matches = sorted(p for p in root.rglob(pattern) if p.is_file())
        results = [
            str(p.relative_to(root))
            for p in matches
            if p.resolve().is_relative_to(root)
            and not any(part in _EXCLUDED_DIRS for part in p.relative_to(root).parts)
        ]
        return "\n".join(results[:30]) or "No files found."

    def search_file(query: str, path: str) -> str:
        """Search for text in a file, returning matching lines."""
        target = _safe_path(path)
        if not target.is_file():
            return f"Error: '{path}' is not a file."
        matches = []
        try:
            for i, line in enumerate(
                target.read_text(encoding="utf-8").splitlines(), 1
            ):
                if query in line:
                    matches.append(f"{i}: {line.strip()}")
                    if len(matches) >= 20:
                        return "\n".join(matches) + "\n(truncated)"
        except (UnicodeDecodeError, PermissionError) as e:
            return f"Error reading '{path}': {e}"
        return "\n".join(matches) or "No matches found."

    def search_code(query: str) -> str:
        """Search project files for matching text."""
        if not query.strip():
            return "Search query cannot be empty."

        matches = []
        query_folded = query.casefold()

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in _EXCLUDED_DIRS for part in path.relative_to(root).parts):
                continue
            # A symlink inside the workspace can point outside it; skip those.
            if not path.resolve().is_relative_to(root):
                continue

            try:
                if path.stat().st_size > 1_000_000:
                    continue
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue

            for line_number, line in enumerate(lines, start=1):
                if query_folded in line.casefold():
                    relative_path = path.relative_to(root)
                    matches.append(
                        f"{relative_path}:{line_number}: {line.strip()[:300]}"
                    )
                    if len(matches) >= 30:
                        return "\n".join(matches) + "\n[Results limited to 30 matches.]"

        return "\n".join(matches) or "No matches found."

    def python_outline(path: str) -> str:
        """List the classes and functions in a Python file with line numbers."""
        target = _safe_path(path)
        if not target.is_file():
            return f"Error: '{path}' is not a file."
        try:
            tree_ = ast.parse(target.read_text(encoding="utf-8"), filename=path)
        except SyntaxError as error:
            return f"Syntax error at line {error.lineno}: {error.msg}"
        except (OSError, UnicodeDecodeError) as error:
            return f"Error reading '{path}': {error}"

        def signature(node) -> str:
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            args = ", ".join(a.arg for a in node.args.args)
            return f"{prefix} {node.name}({args}) (line {node.lineno})"

        lines = []
        for node in tree_.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lines.append(signature(node))
            elif isinstance(node, ast.ClassDef):
                lines.append(f"class {node.name} (line {node.lineno})")
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        lines.append("  " + signature(child))
        return "\n".join(lines) or "No classes or functions found."

    def read_json(path: str) -> str:
        """Parse and pretty-print a JSON file in the workspace."""
        target = _safe_path(path)
        if not target.is_file():
            return f"Error: '{path}' is not a file."

        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            return f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        except (OSError, UnicodeDecodeError) as error:
            return f"Error reading '{path}': {error}"

        formatted = json.dumps(data, indent=2, ensure_ascii=False)
        if len(formatted) > _MAX_OUTPUT_CHARS:
            return formatted[:_MAX_OUTPUT_CHARS] + "\n[Output truncated.]"
        return formatted

    def read_csv(path: str) -> str:
        """Read CSV rows and return them as formatted JSON."""
        target = _safe_path(path)
        if not target.is_file():
            return f"Error: '{path}' is not a file."

        try:
            with target.open(encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                rows = []
                has_more = False

                for index, row in enumerate(reader):
                    if index >= 100:
                        has_more = True
                        break
                    rows.append(row)
        except (OSError, UnicodeDecodeError, csv.Error) as error:
            return f"Error reading CSV '{path}': {error}"

        if not rows:
            return "CSV contains no data rows."

        output = json.dumps(rows, indent=2, ensure_ascii=False)
        if has_more:
            output += "\n[Showing the first 100 rows.]"
        return output

    # ---------- Writing and file management ----------

    def write_file(path: str, content: str) -> str:
        """Write content to a file."""
        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Written to '{path}'."

    def edit_file(path: str, old_str: str, new_str: str) -> str:
        """Replace one exact, unique piece of text in a file."""
        target = _safe_path(path)
        if not target.is_file():
            return f"Error: '{path}' is not a file."
        if not old_str:
            return "Error: old_str cannot be empty."
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            return f"Error reading '{path}': {error}"

        count = text.count(old_str)
        if count == 0:
            return "Error: old_str was not found. Check whitespace and indentation."
        if count > 1:
            return (
                f"Error: old_str appears {count} times. "
                "Include more surrounding lines so it matches exactly once."
            )

        line_number = text[: text.index(old_str)].count("\n") + 1
        target.write_text(text.replace(old_str, new_str, 1), encoding="utf-8")
        return f"Edited '{path}' at line {line_number}."

    def append_file(path: str, content: str) -> str:
        """Append content to the end of a file (creates it if missing)."""
        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as file:
            file.write(content)
        return f"Appended to '{path}'."

    def make_dir(path: str) -> str:
        """Create a directory (and any missing parents)."""
        target = _safe_path(path)
        target.mkdir(parents=True, exist_ok=True)
        return f"Directory '{path}' is ready."

    def delete_file(path: str) -> str:
        """Delete a single file (directories are refused)."""
        target = _safe_path(path)
        if not target.exists():
            return f"Error: '{path}' not found."
        if not target.is_file():
            return f"Error: '{path}' is not a file. Directories cannot be deleted."
        target.unlink()
        return f"Deleted '{path}'."

    def move_file(src: str, dst: str) -> str:
        """Move or rename a file inside the workspace (won't overwrite)."""
        source = _safe_path(src)
        dest = _safe_path(dst)
        if not source.is_file():
            return f"Error: '{src}' is not a file."
        if dest.exists():
            return f"Error: '{dst}' already exists."
        dest.parent.mkdir(parents=True, exist_ok=True)
        source.rename(dest)
        return f"Moved '{src}' to '{dst}'."

    # ---------- Running code ----------

    def execute_python(code: str) -> str:
        """Execute Python code and return output."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(root),
            )
            if result.returncode != 0:
                return f"Exit code {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}".strip()
            return result.stdout.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Code execution timed out (30s limit)."

    def run_tests() -> str:
        """Run the workspace's pytest suite."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = "\n".join(
                part for part in (result.stdout.strip(), result.stderr.strip()) if part
            )
            if result.returncode == 0:
                return output or "Tests passed."
            return f"pytest exited with code {result.returncode}.\n{output}"
        except subprocess.TimeoutExpired:
            return "Error: pytest timed out after 120 seconds."

    def run_linter(path: str = ".") -> str:
        """Check Python code for problems (uses ruff if installed, else syntax check)."""
        target = _safe_path(path)
        if not target.exists():
            return f"Error: '{path}' not found."
        relative = str(target.relative_to(root)) or "."

        try:
            result = subprocess.run(
                [sys.executable, "-m", "ruff", "check", relative],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if "No module named ruff" not in result.stderr:
                output = "\n".join(
                    part
                    for part in (result.stdout.strip(), result.stderr.strip())
                    if part
                )
                if len(output) > _MAX_OUTPUT_CHARS:
                    output = output[:_MAX_OUTPUT_CHARS] + "\n[Output truncated.]"
                return output or "ruff: no problems found."
        except subprocess.TimeoutExpired:
            return "Error: ruff timed out after 60 seconds."

        # Fallback: syntax-check every Python file with the standard library.
        files = [target] if target.is_file() else sorted(target.rglob("*.py"))
        problems = []
        checked = 0
        for file in files:
            if file.suffix != ".py":
                continue
            if any(part in _EXCLUDED_DIRS for part in file.relative_to(root).parts):
                continue
            if not file.resolve().is_relative_to(root):
                continue
            checked += 1
            try:
                ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
            except SyntaxError as error:
                problems.append(
                    f"{file.relative_to(root)}:{error.lineno}: {error.msg}"
                )
            except (OSError, UnicodeDecodeError) as error:
                problems.append(f"{file.relative_to(root)}: {error}")
        if problems:
            return "ruff is not installed; syntax check found:\n" + "\n".join(problems)
        return f"ruff is not installed; syntax check passed for {checked} file(s)."

    # ---------- Git ----------

    def git_status() -> str:
        """Show changed files in the workspace's Git repository."""
        return _git(["status", "--short"]) or "Working tree clean."

    def git_diff() -> str:
        """Show tracked changes compared with the latest commit."""
        return _git(["diff", "HEAD", "--"]) or "No tracked changes compared with HEAD."

    def git_log(limit: str = "10") -> str:
        """Show recent commits in the workspace's Git repository."""
        try:
            count = int(limit)
        except (TypeError, ValueError):
            return "Choose a commit limit from 1 to 30."
        if count < 1 or count > 30:
            return "Choose a commit limit from 1 to 30."
        return _git(["log", f"-{count}", "--oneline", "--decorate"]) or "No commits found."

    def git_show(commit: str = "HEAD") -> str:
        """Show a commit's message and changes."""
        if not _REVISION_RE.match(commit):
            return "Error: invalid commit reference."
        return _git(["show", "--stat", "--patch", commit, "--"])

    def git_blame(path: str, start: str = "1", end: str = "50") -> str:
        """Show who last changed each line in a range of a file."""
        target = _safe_path(path)
        if not target.is_file():
            return f"Error: '{path}' is not a file."
        try:
            first, last = int(start), int(end)
        except (TypeError, ValueError):
            return "Error: start and end must be line numbers."
        if first < 1 or last < first or last - first > 200:
            return "Error: choose a range of 1 to 200 lines, starting at line 1 or later."
        relative = str(target.relative_to(root))
        return _git(["blame", "-L", f"{first},{last}", "--", relative])

    def git_add(path: str = ".") -> str:
        """Stage a file or directory for commit."""
        target = _safe_path(path)
        if not target.exists():
            return f"Error: '{path}' not found."
        relative = str(target.relative_to(root)) or "."
        error = _git(["add", "--", relative])
        return error or f"Staged '{path}'."

    def git_commit(message: str) -> str:
        """Commit the currently staged changes with a message."""
        if not message.strip():
            return "Error: commit message cannot be empty."
        return _git(["commit", "-m", message]) or "Commit created successfully."

    return {
        # Reading and exploring
        "read_file": (read_file, "Read a file: read_file(path: str)"),
        "read_lines": (
            read_lines,
            "Read line range: read_lines(path: str, start: int, end: int)",
        ),
        "list_files": (list_files, "List files: list_files(directory: str)"),
        "tree": (
            tree,
            "Show a directory tree: tree(directory: str = '.', depth: int = 2)",
        ),
        "find_files": (
            find_files,
            "Find files by pattern: find_files(pattern: str)",
        ),
        "search_file": (
            search_file,
            "Search for text in a file: search_file(query: str, path: str)",
        ),
        "search_code": (
            search_code,
            "Search project files for matching text: search_code(query: str)",
        ),
        "python_outline": (
            python_outline,
            "List classes and functions in a Python file: python_outline(path: str)",
        ),
        "read_json": (
            read_json,
            "Parse and pretty-print a JSON file: read_json(path: str)",
        ),
        "read_csv": (
            read_csv,
            "Read CSV rows as formatted JSON: read_csv(path: str)",
        ),
        # Writing and file management
        "write_file": (
            write_file,
            "Write a file: write_file(path: str, content: str)",
        ),
        "edit_file": (
            edit_file,
            "Replace exact text in a file once: edit_file(path: str, old_str: str, new_str: str)",
        ),
        "append_file": (
            append_file,
            "Append text to a file: append_file(path: str, content: str)",
        ),
        "make_dir": (make_dir, "Create a directory: make_dir(path: str)"),
        "delete_file": (delete_file, "Delete a file: delete_file(path: str)"),
        "move_file": (
            move_file,
            "Move or rename a file: move_file(src: str, dst: str)",
        ),
        # Running code
        "execute_python": (
            execute_python,
            "Run Python code: execute_python(code: str)",
        ),
        "run_tests": (
            run_tests,
            "Run the workspace's pytest suite.",
        ),
        "run_linter": (
            run_linter,
            "Check Python code for problems: run_linter(path: str = '.')",
        ),
        # Git
        "git_status": (
            git_status,
            "Show changed files in the workspace's Git repository.",
        ),
        "git_diff": (
            git_diff,
            "Show tracked changes compared with the latest commit.",
        ),
        "git_log": (
            git_log,
            "Show recent commits: git_log(limit: int = 10)",
        ),
        "git_show": (
            git_show,
            "Show a commit's message and changes: git_show(commit: str = 'HEAD')",
        ),
        "git_blame": (
            git_blame,
            "Show who last changed lines: git_blame(path: str, start: int, end: int)",
        ),
        "git_add": (git_add, "Stage changes for commit: git_add(path: str = '.')"),
        "git_commit": (
            git_commit,
            "Commit staged changes: git_commit(message: str)",
        ),
    }


# Tools that change files, run code, or alter Git history ask for confirmation.
_APPROVAL_REQUIRED = {
    "execute_python",
    "write_file",
    "edit_file",
    "append_file",
    "delete_file",
    "move_file",
    "make_dir",
    "run_tests",
    "git_add",
    "git_commit",
}


def create_native_code_tools(workspace: str = ".",
                              retriever: DocumentRetriever | None = None,
                              ) -> Skills:
    """Create coding tools with native function calling (schemas auto-generated)."""
    tools = Skills(requires_approval=set(_APPROVAL_REQUIRED))
    for name, (func, desc) in _build_code_tools(workspace).items():
        tools.add_tool(name, func, desc)
    if retriever is not None:
        def forget_fact(fact: str) -> str:
            """Delete a saved fact by its exact text."""
            fact = fact.strip()
            if not fact:
                return "No fact provided."

            deleted = retriever.delete_document(fact)
            if deleted == 0:
                return "No exact matching saved fact found."
            return f"Deleted {deleted} matching saved fact(s)."

        tools.add_tool(
            "forget_fact",
            forget_fact,
            "Delete a saved fact using its exact stored text.",
        )
        tools.requires_approval.add("forget_fact")

        def forget_fact_by_id(document_id: int) -> str:
            """Delete a saved fact by its ID."""
            deleted = retriever.delete_document_by_id(document_id)
            if deleted == 0:
                return f"No saved fact found with ID {document_id}."
            return f"Deleted saved fact {document_id}."

        tools.add_tool(
            "forget_fact_by_id",
            forget_fact_by_id,
            "Delete a saved fact using its ID from the saved-facts list.",
        )
        tools.requires_approval.add("forget_fact_by_id")

        def remember_fact(fact: str) -> str:
            """Save a user-approved fact to persistent memory."""
            fact = fact.strip()
            if not fact:
                return "Nothing to save."
            retriever.add_document(fact)
            return "Saved that fact to persistent memory."

        tools.add_tool(
            "remember_fact",
            remember_fact,
            "Save a fact the user explicitly asked SPROUT to remember.",
        )
        tools.requires_approval.add("remember_fact")
    return tools