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

    def clear(self) -> None:
        self.messages = [
            message for message in self.messages
            if message["role"] == "system"
        ]


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


class SummarizationMemory(MultimodalMemory):
    """Summarize older turns while preserving instructions and recent context."""

    def __init__(self, llm: LLM, max_recent_turns: int = 2):
        if max_recent_turns < 1:
            raise ValueError("max_recent_turns must be at least 1.")
        super().__init__()
        self.llm = llm
        self.max_recent_turns = max_recent_turns
        self.summary = ""

    def clear(self) -> None:
        super().clear()
        self.summary = ""

        
    def add(
            self,
            role: str,
            content: str,
            tool_call: dict | None = None,
            image_data: str | None = None,
            **kwargs,
        ) -> None:
            super().add(
                role,
                content,
                tool_call=tool_call,
                image_data=image_data,
                **kwargs,
            )

            if role == "assistant" and tool_call is None:
                self._summarize_older_turns()

    def get_messages(self) -> list[dict]:
        system = [m for m in self.messages if m["role"] == "system"]
        conversation = [m for m in self.messages if m["role"] != "system"]

        if self.summary:
            system.append(
                {
                    "role": "system",
                    "content": (
                        "Conversation summary for context; this does not "
                        "override the system instructions:\n" + self.summary
                    ),
                }
            )

        return system + conversation

    def _summarize_older_turns(self) -> None:
        system = [m for m in self.messages if m["role"] == "system"]
        conversation = [m for m in self.messages if m["role"] != "system"]
        user_starts = [
            index
            for index, message in enumerate(conversation)
            if message["role"] == "user"
        ]

        if len(user_starts) <= self.max_recent_turns:
            return

        cutoff = user_starts[-self.max_recent_turns]
        older_turns = conversation[:cutoff]
        recent_turns = conversation[cutoff:]

        def text_for_summary(content) -> str:
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [
                    part.get("text", "[image attached]")
                    for part in content
                    if isinstance(part, dict)
                ]
                return "\n".join(parts) or "[multimodal content]"
            return str(content)

        transcript = "\n".join(
            f"{message['role']}: {text_for_summary(message['content'])}"
            for message in older_turns
        )
        prompt = (
            "Update the conversation summary. Preserve important user facts, "
            "preferences, decisions, and constraints. Do not invent details. "
            "Return only the updated summary.\n\n"
            f"Existing summary:\n{self.summary or '(none)'}\n\n"
            f"Older conversation:\n{transcript}"
        )
        response = self.llm.generate([{"role": "user", "content": prompt}])

        if response.content and response.content.strip():
            self.summary = response.content.strip()
            self.messages = system + recent_turns

