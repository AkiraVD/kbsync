"""What the delta is measured against."""

from typing import Protocol

from .models import Document, Status
from .vectorstore import RemoteFile


class StateStore(Protocol):
    def status(self, document: Document) -> Status: ...

    def record(self, document: Document) -> None: ...


class VectorStoreState:
    """Delta read from the vector store's own file attributes.

    Keeps the daily job stateless: no volume to mount and nothing to lose when
    the container goes away.
    """

    def __init__(self, remote: dict[str, RemoteFile]):
        self.remote = remote

    def status(self, document: Document) -> Status:
        previous = self.existing(document)
        if previous is None:
            return Status.ADDED
        if previous.content_hash != document.content_hash:
            return Status.UPDATED
        return Status.SKIPPED

    def existing(self, document: Document) -> RemoteFile | None:
        return self.remote.get(str(document.article.id))

    def record(self, document: Document) -> None:
        return None
