"""One run of the pipeline: fetch, convert, write, report."""

import logging

from .config import Settings
from .documents import build_all
from .helpcenter import HelpCenter
from .manifest import Manifest
from .models import Article, SyncReport
from .store import ArticleStore

log = logging.getLogger(__name__)


def sync(settings: Settings, limit: int | None = None) -> SyncReport:
    client = HelpCenter(settings.zendesk_host, settings.locale)
    sections = client.fetch_sections()
    payloads = client.fetch_articles(limit=limit or settings.max_articles)

    articles = [Article.from_api(payload, sections) for payload in payloads]
    documents = build_all(articles)

    store = ArticleStore(settings.out_dir)
    store.prepare()
    manifest = Manifest.load(settings.out_dir)
    report = SyncReport()

    for document in documents:
        report.record(manifest.status(document), document.slug)
        manifest.record(document)
        # Every document is written so a fresh checkout holds the whole corpus;
        # the status only decides what a later step has to re-upload.
        store.write(document)

    manifest.save(settings.out_dir)
    report.stale = store.stale_files({document.slug for document in documents})

    if report.stale:
        log.info("%d file(s) no longer published: %s", len(report.stale), ", ".join(report.stale))

    return report
