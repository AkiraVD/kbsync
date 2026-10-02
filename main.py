"""Sync a Zendesk Help Center into clean Markdown. Runs once and exits."""

import argparse
import logging
import sys

from src.config import Settings
from src.sync import sync


def main() -> int:
    _setup_logging()
    args = _parse_args()
    settings = Settings.from_env()
    log = logging.getLogger("kbsync")

    log.info(
        "syncing %s (%s) into %s", settings.zendesk_host, settings.locale, settings.out_dir
    )
    report = sync(settings, limit=args.limit)

    if not report.total:
        log.error("the API returned no published articles")
        return 1

    log.info("wrote %d Markdown files to %s", report.total, settings.out_dir)
    log.info("%s", report.summary())
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, help="stop after N articles (default: every published one)"
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
