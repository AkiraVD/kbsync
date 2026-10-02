"""Ask the File Search store a question.

SYSTEM_PROMPT is the brief's prompt, copied byte for byte including the bullet
characters and the `Article URL:` citation lines. The live bot cites differently
(a markdown link); that difference is noted in the README and not corrected here.
"""

import logging
import re
from dataclasses import dataclass

from .http import Client
from .vectorstore import DEFAULT_BASE_URL

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""


ARTICLE_URL = re.compile(r"^Article URL: (\S+)", re.MULTILINE)


@dataclass(frozen=True)
class Citation:
    file_name: str
    url: str


@dataclass(frozen=True)
class Answer:
    text: str
    citations: tuple[Citation, ...]


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
    """`source` on an annotation is the retrieved chunk, not a link.

    The article URL therefore comes out of the chunk text, which is why every
    file written by this pipeline repeats it on an `Article URL:` line.
    """
    interaction = payload.get("interaction", payload)
    parts: list[str] = []
    found: dict[str, Citation] = {}

    for step in interaction.get("steps", []):
        for block in step.get("content") or []:
            text = block.get("text")
            if text:
                parts.append(text)
            for annotation in block.get("annotations") or []:
                citation = _citation(annotation)
                if not citation:
                    continue
                key = citation.file_name or citation.url
                # Several chunks come from one file; only some carry the URL line.
                if citation.url or key not in found:
                    found[key] = citation if citation.url else found.get(key, citation)

    return Answer(text="\n".join(parts).strip(), citations=tuple(found.values()))


def _citation(annotation: dict) -> Citation | None:
    file_name = annotation.get("file_name") or ""
    found = ARTICLE_URL.search(annotation.get("source") or "")
    url = found.group(1) if found else ""
    return Citation(file_name=file_name, url=url) if file_name or url else None
