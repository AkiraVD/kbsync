"""One run of the pipeline: fetch, convert, write, upload the delta, report."""

import logging

from .config import Settings
from .documents import build_all
from .helpcenter import HelpCenter
from .manifest import Manifest
from .models import Article, Document, Status, SyncReport
from .state import StateStore, VectorStoreState
from .store import ArticleStore
from .vectorstore import UploadError, VectorStore

log = logging.getLogger(__name__)


def sync(settings: Settings, limit: int | None = None, upload: bool = True) -> SyncReport:
    cap = limit if limit is not None else settings.max_articles
    documents = _collect(settings, cap)
    store = ArticleStore(settings.out_dir)
    store.prepare()

    manifest = Manifest.load(settings.out_dir)
    uploader = _uploader(settings) if upload else None
    state: StateStore = (
        VectorStoreState(uploader.fetch_files()) if uploader else manifest
    )

    report = SyncReport()
    for document in documents:
        status = state.status(document)
        store.write(document)
        report.written += 1

        if uploader and status is not Status.SKIPPED:
            try:
                _upload(uploader, state, document, report)
            except UploadError as exc:
                # A daily job that loses 400 good articles to one bad upload is
                # worse than one that reports the gap and exits non-zero.
                log.warning("%s", exc)
                report.failed.append(document.slug)
                continue

        manifest.record(document)
        report.record(status, document.slug)

    manifest.save(settings.out_dir, prune=not cap)

    # Only a full run can tell an unpublished article from one we never asked for.
    if not cap:
        report.stale = store.stale_files({document.slug for document in documents})
        _log_stale(report.stale)

    return report


def _log_stale(stale: list[str], examples: int = 5) -> None:
    if not stale:
        return
    shown = ", ".join(stale[:examples])
    more = f" (+{len(stale) - examples} more)" if len(stale) > examples else ""
    log.info("%d file(s) no longer published: %s%s", len(stale), shown, more)


def _collect(settings: Settings, limit: int | None) -> list[Document]:
    client = HelpCenter(settings.zendesk_host, settings.locale)
    sections = client.fetch_sections()
    payloads = client.fetch_articles(limit=limit)
    return build_all(Article.from_api(payload, sections) for payload in payloads)


def _uploader(settings: Settings) -> VectorStore | None:
    if not settings.uploads_enabled:
        log.info("no File Search credentials, writing Markdown only")
        return None
    return VectorStore(
        settings.api_key,
        settings.store_name,
        settings.chunking,
        base_url=settings.base_url,
    )


def _upload(
    uploader: VectorStore, state: StateStore, document: Document, report: SyncReport
) -> None:
    replacing = state.existing(document) if isinstance(state, VectorStoreState) else None
    uploader.put(document, replacing=replacing)
    report.uploaded += 1
    report.chunks += uploader.chunking.estimate_chunks(document.text)
    log.info("uploaded %s", document.filename)
