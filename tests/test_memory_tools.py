from SPROUT.core.llm import Response
from SPROUT.tools.workspace import create_native_code_tools


class FakeRetriever:
    def __init__(self):
        self.documents = []

    def add_document(self, fact: str) -> None:
        self.documents.append(fact)

    def delete_document(self, fact: str) -> int:
        before = len(self.documents)
        self.documents = [item for item in self.documents if item != fact]
        return before - len(self.documents)

    def delete_document_by_id(self, document_id: int) -> int:
        if 1 <= document_id <= len(self.documents):
            del self.documents[document_id - 1]
            return 1
        return 0


def call_tool(tools, name: str, fact: str) -> str:
    response = Response(
        tool_call={"tool": name, "kwargs": {"fact": fact}}
    )
    return tools.execute(response)


def test_remember_fact_requires_approval(monkeypatch):
    retriever = FakeRetriever()
    tools = create_native_code_tools(retriever=retriever)
    monkeypatch.setattr("builtins.input", lambda _: "n")

    result = call_tool(tools, "remember_fact", "My name is Ada.")

    assert "denied" in result
    assert retriever.documents == []


def test_approved_remember_and_forget_fact(monkeypatch):
    retriever = FakeRetriever()
    tools = create_native_code_tools(retriever=retriever)
    approvals = iter(["y", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(approvals))

    fact = "My name is Ada."
    assert "Saved" in call_tool(tools, "remember_fact", fact)
    assert retriever.documents == [fact]

    assert "Deleted 1" in call_tool(tools, "forget_fact", fact)
    assert retriever.documents == []

def test_forget_fact_by_id_requires_approval(monkeypatch):
    retriever = FakeRetriever()
    retriever.add_document("My name is Ada.")
    tools = create_native_code_tools(retriever=retriever)
    response = Response(
        tool_call={
            "tool": "forget_fact_by_id",
            "kwargs": {"document_id": 1},
        }
    )

    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert "denied" in tools.execute(response)
    assert retriever.documents == ["My name is Ada."]

    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert tools.execute(response) == "Deleted saved fact 1."
    assert retriever.documents == []