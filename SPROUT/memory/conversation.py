from SPROUT.core.llm import LLM

class Memory:
    """Base conversation-history interface."""

    def __init__(self):
        self.messages = []

    def add(
        self, role: str, content: str, tool_call: dict | None = None, **kwargs
    ) -> None:
        message = {"role": role, "content": content}
        if tool_call is not None:
            message["tool_calls"] = [tool_call]
        self.messages.append(message)

    def get_messages(self) -> list[dict]:
        return self.messages


class TrimmingMemory(Memory):
    """Keep system instructions and the most recent complete user turns."""

    def __init__(self, max_turns: int = 2):
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1.")
        super().__init__()
        self.max_turns = max_turns

    def add(self, role: str, content: str, **kwargs) -> None:
        super().add(role, content, **kwargs)

        system = [m for m in self.messages if m["role"] == "system"]
        conversation = [m for m in self.messages if m["role"] != "system"]
        user_starts = [
            index for index, message in enumerate(conversation)
            if message["role"] == "user"
        ]

        if len(user_starts) > self.max_turns:
            conversation = conversation[user_starts[-self.max_turns]:]

        self.messages = system + conversation


class SummarizationMemory(Memory):
    """Memory that compresses past turns into a running summary via an LLM."""

    def __init__(self, llm: LLM):
        super().__init__()
        self.llm = llm

    def add(self, role: str, content: str, **kwargs) -> None:
        # Add the new message first using the parent class (Memory)
        super().add(role, content, **kwargs)

        # After each completed turn, update the running summary
        if role == "assistant":
            # Split the existing summary from the new conversation turns
            summary = ""
            conversation = ""
            for message in self.messages:
                if message["role"] == "system":
                    summary = message["content"]
                else:
                    conversation += f"{message['role']}: {message['content']}\n"

            # Ask the LLM to extend the summary with the new conversation
            prompt = f"""Update the summary with the new conversation.

Summary: {summary}

Conversation:
{conversation}
Output the updated summary only."""
            response = self.llm.generate([{"role": "user", "content": prompt}])
            self.messages = [{"role": "system", "content": response.content}]


class MultimodalMemory(Memory):
    """Simple memory module to store conversation history."""

    def add(
        self,
        role: str,
        content: str,
        tool_call: dict | None = None,
        image_data: str | None = None,
        **kwargs,
    ) -> None:
        if image_data:
            url = (
                image_data
                if image_data.startswith(("http://", "https://"))
                else f"data:image/jpeg;base64,{image_data}"
            )
            content = [
                {"type": "image_url", "image_url": {"url": url}},
                {"type": "text", "text": content},
            ]

        super().add(role, content, tool_call=tool_call, **kwargs)