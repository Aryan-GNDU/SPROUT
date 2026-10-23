from SPROUT.core.llm import Response
from SPROUT.memory.conversation import SummarizationMemory


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate(self, messages, tools=None):
        self.calls.append(messages)
        return Response(content=f"summary-{len(self.calls)}")


def test_summarization_preserves_system_and_recent_turns():
    llm = FakeLLM()
    memory = SummarizationMemory(llm, max_recent_turns=2)
    system_prompt = "Follow the user's instructions."

    memory.add("system", system_prompt)

    for turn in range(1, 4):
        memory.add("user", f"question-{turn}")
        memory.add("assistant", f"answer-{turn}")

    messages = memory.get_messages()

    assert len(llm.calls) == 1
    assert memory.summary == "summary-1"
    assert messages[0] == {"role": "system", "content": system_prompt}
    assert messages[1]["role"] == "system"
    assert "summary-1" in messages[1]["content"]
    assert [message["content"] for message in messages[2:]] == [
        "question-2",
        "answer-2",
        "question-3",
        "answer-3",
    ]


def test_summarization_waits_until_tool_call_turn_finishes():
    llm = FakeLLM()
    memory = SummarizationMemory(llm, max_recent_turns=2)

    memory.add("system", "System instructions.")
    for turn in range(1, 3):
        memory.add("user", f"question-{turn}")
        memory.add("assistant", f"answer-{turn}")

    memory.add("user", "question-3")
    memory.add(
        "assistant",
        "",
        tool_call={"id": "call-1", "type": "function"},
    )

    assert llm.calls == []

    memory.add("tool", "tool result")
    memory.add("assistant", "final answer")

    assert len(llm.calls) == 1
    assert memory.summary == "summary-1"
    assert memory.get_messages()[-1]["content"] == "final answer"