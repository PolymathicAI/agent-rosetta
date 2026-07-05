from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, overload

from .typing import Message

if TYPE_CHECKING:
    from .typing import MessageRole


class History(Sequence[Message]):
    def __init__(self, messages: list[dict[str, str]]):
        self._messages: list[Message] = [Message(**message) for message in messages]

    def __len__(self):
        return len(self._messages)

    @overload
    def __getitem__(self, idx: int) -> Message: ...

    @overload
    def __getitem__(self, idx: slice) -> list[Message]: ...

    def __getitem__(self, idx: slice | int) -> list[Message] | Message:
        return self._messages[idx]

    def append(self, message: Message):
        self._messages.append(message)

    def add(self, role: MessageRole = None, reasoning: str = None, content: str = None):
        message = Message(role=role, reasoning=reasoning, content=content)
        self.append(message)

    def get_query(self, context_window: int = None) -> list[dict]:
        last_message = self[-1]
        if last_message.role != "user":
            raise ValueError(
                f"Last message must be from user. Got role='{last_message.role}'"
            )

        if context_window is None:
            query = [{"role": item.role, "content": item.content} for item in self]
            return query

        head = self[:2]

        if last_message.tag == "failure":
            for message_idx in range(len(self) - 2, -1, -1):
                message = self[message_idx]
                if message.role == "user" and message.tag != "failure":
                    break
            last_successful_action_idx = message_idx - 1

            error_sequence = self[last_successful_action_idx:]
            error_head = error_sequence[:2]
            error_tail = error_sequence[2:][-2 * (context_window - 1) :]
            tail = error_head + error_tail
        else:
            tail = self[2:][-2 * context_window :]

        query = head + tail
        query = [{"role": item.role, "content": item.content} for item in query]
        return query
