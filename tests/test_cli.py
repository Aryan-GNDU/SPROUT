from types import SimpleNamespace

from SPROUT import cli


def test_memories_command_displays_saved_fact_ids(monkeypatch):
    output = []

    class FakeConsole:
        def print(self, *args, **kwargs):
            output.extend(args)

    monkeypatch.setattr(cli, "console", FakeConsole())
    agent = SimpleNamespace(
        retriever=SimpleNamespace(
            list_documents=lambda: [(7, "My name is Ada.")]
        )
    )

    cli.handle_command("/memories", agent)

    assert output == ["  7: My name is Ada."]