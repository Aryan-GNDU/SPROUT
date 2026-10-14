from Tinyagent.llm import LLM

class Memory:
    """Simple memory module to store conversation history."""

    def __init__(self):
        self.messages = []

    def add(
        self, role: str, content: str, tool_call: dict | None = None, **kwargs
    ) -> None:
        """Add a message to memory."""
        message = {"role": role, "content": content}

        # Tool call
        if tool_call:
            message["tool_calls"] = [tool_call]

        # Append message to memory
        self.messages.append(message)

    def get_messages(self) -> list[dict]:
        """Get all messages."""
        return self.messages

class TrimmingMemory(Memory):
    """Memory that keeps only the last two user/assistant turns."""

    def add(self, role: str, content: str, **kwargs) -> None:
        # Add the new message first using the parent class (Memory)
        super().add(role, content)

        # Then, keep system message plus the most recent two turns (4 messages)
        system = [
            message for message in self.messages if message["role"] == "system"
        ]
        turns = [
            message for message in self.messages if message["role"] != "system"
        ]
        self.messages = system + turns[-4:]

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
        tool_call: dict = None,
        image_data: str = None,
    ):
        """Add a message to memory."""
        # Image
        if image_data:
            is_url = image_data.startswith(("http://", "https://"))
            url = image_data if is_url else f"data:image/jpeg;base64,{image_data}"
            content = [
                {"type": "image_url", "image_url": {"url": url}},
                {"type": "text", "text": content},
            ]

        # Main message
        message = {"role": role, "content": content}

        # Tool call
        if tool_call:
            message["tool_calls"] = [tool_call]

        # Append message to memory
        self.messages.append(message)


class MultiModalMemory(Memory):
    def add(
        self,
        role: str,
        content: str,
        tool_call: dict = None,
        image_data: str = None,
    ):
        """Add a message to memory."""
        if image_data:
            is_url = image_data.startswith(("http://", "https://"))
            url = image_data if is_url else f"data:image/jpeg;base64,{image_data}"
            content = [
                {"type": "image_url", "image_url": {"url": url}},
                {"type": "text", "text": content},
            ]
        super().add(role, content, tool_call=tool_call)