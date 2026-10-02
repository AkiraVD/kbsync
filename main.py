"""Sync a Zendesk Help Center into a vector store. Runs once and exits."""

import argparse
import logging
import sys

from src.assistant import Assistant
from src.config import Settings
from src.sync import sync
from src.vectorstore import create_store


def main() -> int:
    _setup_logging()
    args = _parse_args()
    settings = Settings.from_env()
    log = logging.getLogger("kbsync")

    if args.ask:
        return _ask(settings, args.ask, log)

    if args.create_store:
        name = create_store(
            settings.api_key,
            args.create_store,
            base_url=settings.base_url,
            embedding_model=settings.embedding_model,
        )
        log.info("created %s - put it in GEMINI_FILE_SEARCH_STORE", name)
        return 0

    log.info(
        "syncing %s (%s) into %s", settings.zendesk_host, settings.locale, settings.out_dir
    )
    report = sync(settings, limit=args.limit, upload=not args.no_upload)

    if not report.total:
        log.error("the API returned no published articles")
        return 1

    log.info("wrote %d Markdown files to %s", report.total, settings.out_dir)
    log.info("%s", report.summary())
    if report.uploaded:
        log.info(
            "embedded %d file(s), ~%d chunks at %d tokens with %d overlap",
            report.uploaded,
            report.chunks,
            settings.chunking.max_tokens,
            settings.chunking.overlap_tokens,
        )
    return 0


def _ask(settings: Settings, question: str, log: logging.Logger) -> int:
    if not settings.uploads_enabled:
        log.error("asking needs GEMINI_API_KEY and GEMINI_FILE_SEARCH_STORE")
        return 1

    assistant = Assistant(
        settings.api_key, settings.store_name, settings.model, base_url=settings.base_url
    )
    answer = assistant.ask(question)

    print(f"\nQ: {question}\n")
    print(answer.text or "(no answer)")
    if answer.citations:
        print("\nRetrieved from:")
        for citation in answer.citations:
            print(f"  {citation}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, help="stop after N articles (default: every published one)"
    )
    parser.add_argument(
        "--no-upload", action="store_true", help="write Markdown without uploading"
    )
    parser.add_argument(
        "--create-store", metavar="NAME", help="create a File Search store, then exit"
    )
    parser.add_argument(
        "--ask", metavar="QUESTION", help="ask the store a question, then exit"
    )
    return parser.parse_args()


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


if __name__ == "__main__":
    sys.exit(main())
