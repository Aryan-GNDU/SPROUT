"""Terminal display utilities for the SPROUT agent development harness.

Rich is used when installed; the ANSI Display remains available as a fallback.
"""

import random
import re
import time
import threading

from SPROUT.llm import Response


# --- ANSI escape codes (used by the pure-Python Display) ---
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
RESET = "\033[0m"
ORANGE = "\033[38;5;208m"
CYAN = "\033[36m"
MINT = "\033[38;5;121m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
PURPLE = "\033[35m"


# --- Optional Rich imports (used by RichDisplay) ---
try:
    from rich.console import Console
    from rich.live import Live
    from rich.text import Text
    from rich.rule import Rule

    console = Console()
except ImportError:
    Console = Live = Text = Rule = console = None


# SPROUT wordmark. Kept separate so it can also be used in plain terminals.
NAME = r"""
 ███████╗██████╗ ██████╗  ██████╗ ██╗   ██╗████████╗
 ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╗   ██║╚══██╔══╝
 ███████╗██████╔╝██████╔╝██║   ██║██║   ██║   ██║
 ╚════██║██╔═══╝ ██╔══██╗██║   ██║██║   ██║   ██║
 ███████║██║     ██║  ██║╚██████╔╝╚██████╔╝   ██║
 ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚═════╝    ╚═╝
"""

# --- SPROUT palette ---
_SPROUT_DARK = "#167c80"
_SPROUT_MID = "#20c9b2"
_SPROUT_LIGHT = "#9af7c7"
_SPROUT_CYAN = "#48dcff"
_SPROUT_SOIL = "#527789"

# Short aliases used by the logo art below.
_DK = _SPROUT_DARK
_DM = _SPROUT_MID
_DL = _SPROUT_LIGHT

# --- SPROUT mascot ---
LOGO_ART = f"""
                                  [bold {_DL}]▒▒[/][bold {_DK}]▓▓[/]
[bold {_DK}]▓▓▓[/][bold {_DM}]▒▒▒▒▒▒▒[/]                  [bold {_DL}]▒▒▒▒▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒[/]
 [bold {_DL}]▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒▒▒▒▒▒▒▒▒[/]          [bold {_DL}]▒▒▒▒▒▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒▒[/]
  [bold {_DL}]▒▒▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒▒▒▒▒▒▒▒[/]      [bold {_DL}]▒▒▒▒▒▒▒[/][bold {_DK}]▓▓[/][bold {_DM}]▒▒▒▒[/]
   [bold {_DL}]▒▒▒▒▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒▒▒▒▒▒▒[/]   [bold {_DL}]▒▒▒▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒▒▒▒▒[/]
     [bold {_DL}]▒▒▒▒▒▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒▒▒▒▒▒[/][bold {_DL}]▒▒▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒▒▒▒▒▒[/]
       [bold {_DL}]▒▒▒▒▒▒▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒▒[/][bold {_DL}]▒▒▒[/][bold {_DK}]▓▓▓[/][bold {_DM}]▒▒▒▒▒▒[/]
          [bold {_DL}]▒▒▒▒▒▒▒▒[/][bold {_DK}]▓▓██▓[/][bold {_DM}]▒▒▒▒▒▒▒[/]
              [bold {_DL}]▒▒▒▒▒[/][bold {_DK}]▓██▓[/][bold {_DM}]▒▒[/]
                   [bold {_DK}]▓██▓[/]
                   [bold {_DK}]▓█▓▓[/]
                   [bold {_DK}]▓█▓▓[/]
                   [bold {_DK}]▓█▓[/]
                  [bold {_DK}]▓█▓▓[/]
                  [bold {_DK}]▓█▓[/]
                  [bold {_DK}]▓▓▓[/]
                  [bold {_DK}]▓▓[/]
"""

_BLOCK_WIDTH = 38
_TITLE = "S P R O U T"
_SUBTITLE = "AGENT DEVELOPMENT HARNESS"
_TAGLINE = "Where agents begin to grow."

LOGO = (
    LOGO_ART
    + f"\n[bold {_SPROUT_LIGHT}]{_TITLE.center(_BLOCK_WIDTH)}[/]"
    + f"\n[dim]{_SUBTITLE.center(_BLOCK_WIDTH)}[/]"
    + f"\n[bold {_SPROUT_MID}]{_TAGLINE.center(_BLOCK_WIDTH)}[/]\n"
)

# Retained as an alias for callers that used the old logo constant.
FLAMINGO_LOGO = LOGO


def label(name: str, style: str) -> str:
    """Format a fixed-width label for step output (Rich markup)."""
    return f"[bold {style}]{name:<13}[/]"


THINKING_FRAMES = [
    "   ·     ",
    "   ·  ✦  ",
    "  ╱·╲    ",
    " ╱ · ╲ ✦ ",
    "   ·  ╲  ",
    "  ✦     ·",
    "   ·     ",
]

THINKING_MESSAGES = [
    "Sprouting an idea...",
    "Growing a plan...",
    "Connecting the roots...",
    "Reaching for an answer...",
    "Branching through possibilities...",
    "Wiring up the next step...",
    "Nurturing a thought...",
    "Exploring new branches...",
    "Putting down roots...",
    "Growing through the problem...",
    "Gathering the right tools...",
    "Following a new lead...",
    "Turning a seed into a solution...",
]


def _plain_logo() -> str:
    """Return the SPROUT logo with Rich markup stripped, for plain terminals."""
    return re.sub(r"\[/?[^\]]*\]", "", LOGO)


# --- Display handler ---

class Display:
    """Handles agent events with ANSI-styled terminal output."""

    def __init__(self, pink: bool = False):
        # `pink` is retained for backwards compatibility with existing callers.
        self._pink = pink

    def __call__(self, event: str, data: str | Response = None) -> None:
        if event == "thinking":
            print(f"  {DIM}🌱 Sprouting an idea...{RESET}\n")

        elif event == "response":
            print(f"{BOLD}{GREEN}{'▒▒ THOUGHT ▒▒':<13}{RESET}")
            print(f"{data.reasoning}{RESET}\n")
            if data.content:
                print(f"{BOLD}{PURPLE}{'▒▒ ANSWER ▒▒':<13}{RESET}")
                print(f"{data.content}{RESET}\n")

        elif event == "tool_call" and data:
            tool = data.tool_call["tool"]
            kwargs = data.tool_call["kwargs"]
            print(f"{BOLD}{RED}{'▒▒ ACTION ▒▒':<13}{RESET}")
            print(f"{tool}({kwargs}){RESET}\n")

        elif event == "observation":
            print(f"{BOLD}{YELLOW}{'▒▒ OBSERVATION ▒▒':<13}{RESET}")
            print(f"{data}{RESET}\n")
            print(f"{DIM}{'─' * 80}{RESET}\n")


class RichDisplay:
    """Handles agent events with Rich formatting. Requires `pip install rich`."""

    def __init__(self, pink: bool = False):
        if Console is None:
            raise ImportError(
                "RichDisplay requires `rich`. Install it with: pip install rich"
            )
        # `pink` is retained for backwards compatibility with existing callers.
        self._pink = pink
        self._live = None
        self._animating = False
        self._thinking_msg = "Sprouting an idea..."

    def __call__(self, event: str, data: str | Response = None) -> None:
        if event == "thinking":
            self._stop_thinking()
            self._animating = True
            self._live = Live(console=console, refresh_per_second=8, transient=True)
            self._live.start()
            self._thinking_msg = random.choice(THINKING_MESSAGES)
            threading.Thread(target=self._animate_thinking, daemon=True).start()

        elif event == "response":
            self._stop_thinking()
            if data.reasoning:
                console.print(
                    f"  [bold dark_orange]{'THOUGHT':<13}[/][dim italic]{data.reasoning}[/]"
                )
            if data.content:
                console.print(
                    f"\n  🌱 [bold bright_cyan]ANSWER[/]    {data.content}\n"
                )

        elif event == "tool_call" and data:
            tool = data.tool_call["tool"]
            kwargs = data.tool_call["kwargs"]
            console.print(
                f"  {label('ACTION', 'yellow')}[yellow]{tool}({kwargs})[/]"
            )

        elif event == "observation":
            console.print(f"  {label('OBSERVATION', 'green')}{data}\n")
            console.print(Rule(style="dim"), end="\n\n")

    def _animate_thinking(self) -> None:
        """Animate a tiny sprout-like growth motif while the agent thinks."""
        i = 0
        while self._animating and self._live:
            frame = THINKING_FRAMES[i % len(THINKING_FRAMES)]
            self._live.update(
                Text(f"  🌱 {self._thinking_msg}  {frame}", style="bright_cyan")
            )
            time.sleep(0.15)
            i += 1

    def _stop_thinking(self) -> None:
        """Stop the thinking animation and clean up the live display."""
        self._animating = False
        if self._live:
            self._live.stop()
            self._live = None