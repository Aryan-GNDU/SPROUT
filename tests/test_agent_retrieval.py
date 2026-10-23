from SPROUT.core.agent import SproutAgent
from SPROUT.core.llm import Response
from SPROUT.core.planning import NativeReAct
from SPROUT.memory.conversation import Memory
from SPROUT.memory.retrieval import DocumentRetriever
from SPROUT.tools.registry import Tools


class FakeEmbeddingModel:
    def embed(self, text: str) -> list[float]:
        return [float(len(text)), float(sum(map(ord, text)) % 997)]


class FakeLLM:
    def generate(self, messages, tools=None):
        self.messages = messages
        return Response(content="Your name is Ada.")


class NoOpDisplay:
    def __call__(self, event, data=None):
        pass


def test_retrieved_context_reaches_llm_but_not_conversation(tmp_path):
    retriever = DocumentRetriever(
        FakeEmbeddingModel(),
        str(tmp_path / "retrieval.sqlite3"),
    )
    retriever.add_document("The user's preferred name is Ada.")

    llm = FakeLLM()
    memory = Memory()
    agent = SproutAgent(
        llm=llm,
        memory=memory,
        tools=Tools(),
        planner=NativeReAct(max_steps=1),
        display=NoOpDisplay(),
        retriever=retriever,
    )

    assert agent.run("What is my preferred name?") == "Your name is Ada."
    assert any(
        message["role"] == "system"
        and "preferred name is Ada" in message["content"]
        for message in llm.messages
    )
    assert len([m for m in memory.messages if m["role"] == "user"]) == 1
    assert all("preferred name is Ada" not in str(m["content"]) for m in memory.messages)