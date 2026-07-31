from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str = "base_provider"

    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> str:
        """messages: list of {"role": "user"|"assistant", "content": str}, oldest first.

        Returns the assistant's reply as plain text.
        """
        raise NotImplementedError