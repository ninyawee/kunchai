"""Thai transliteration using vLLM/OpenAI-compatible API."""

import re
import time
from openai import OpenAI

from examples import get_system_prompt


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks from Qwen3 output."""
    # Remove everything between <think> and </think>
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Also handle unclosed <think> tags (streaming)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()


class ThaiTransliterator:
    """Transliterate English phonetic input to Thai using LLM."""

    def __init__(
        self,
        base_url: str = "http://vedas:8000/v1",
        model: str = "Qwen/Qwen3-0.6B",
        api_key: str = "not-needed",
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.system_prompt = get_system_prompt()

    def transliterate(self, english_input: str) -> tuple[list[str], float]:
        """
        Transliterate English phonetic input to Thai.

        Returns:
            Tuple of (list of Thai suggestions, response time in seconds)
        """
        start_time = time.perf_counter()

        # Append /no_think for Qwen3 to disable thinking mode
        prompt = f"{english_input} /no_think"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=50,
            temperature=0.3,
        )

        elapsed = time.perf_counter() - start_time

        content = response.choices[0].message.content or ""
        # Strip thinking tags if present
        content = strip_thinking(content)
        # Parse suggestions (one per line)
        suggestions = [line.strip() for line in content.strip().split("\n") if line.strip()]

        return suggestions, elapsed


if __name__ == "__main__":
    # Quick test
    trans = ThaiTransliterator()
    suggestions, elapsed = trans.transliterate("sawatdee")
    print(f"Input: sawatdee")
    print(f"Suggestions: {suggestions}")
    print(f"Time: {elapsed:.3f}s")
