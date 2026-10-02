"""Ask the File Search store a question.

SYSTEM_PROMPT is the brief's prompt, copied byte for byte including the bullet
characters and the `Article URL:` citation lines. The live bot cites differently
(a markdown link); that difference is noted in the README and not corrected here.
"""

import logging
from dataclasses import dataclass

from .http import Client
from .vectorstore import DEFAULT_BASE_URL

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""


@dataclass(frozen=True)
class Answer:
    text: str
    citations: tuple[str, ...]


class Assistant:
    def __init__(
        self,
        api_key: str,
        store_name: str,
        model: str,
        base_url: str = DEFAULT_BASE_URL,
    ):
        self.store = store_name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = Client({"x-goog-api-key": api_key}, timeout=120)

    def ask(self, question: str) -> Answer:
        payload = self.client.post(
            f"{self.base_url}/interactions",
            json={
                "model": self.model,
                "input": question,
                "system_instruction": SYSTEM_PROMPT,
                "tools": [
                    {
                        "type": "file_search",
                        "file_search_store_names": [self.store],
                    }
                ],
            },
        )
        return parse_answer(payload)


def parse_answer(payload: dict) -> Answer:
    interaction = payload.get("interaction", payload)
    parts: list[str] = []
    citations: list[str] = []

    for step in interaction.get("steps", []):
        for block in step.get("content", []) or []:
            text = block.get("text")
            if text:
                parts.append(text)
            for annotation in block.get("annotations") or []:
                source = annotation.get("source") or annotation.get("file_name")
                if source and source not in citations:
                    citations.append(source)

    return Answer(text="\n".join(parts).strip(), citations=tuple(citations))
