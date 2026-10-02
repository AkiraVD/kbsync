"""Fetch a Zendesk Help Center into clean Markdown.

Runs once and exits: `python main.py`. Later steps (vector store upload) hang off
the same manifest this writes.
"""

import argparse
import logging
import sys

from src.config import load_config
from src.helpcenter import HelpCenter
from src.store import write_articles


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="stop after N articles (default: every published article)",
    )
    return parser.parse_args()


def main() -> int:
    setup_logging()
    args = parse_args()
    config = load_config()
    log = logging.getLogger("kbsync")

    log.info("syncing %s (%s) into %s", config.zendesk_host, config.locale, config.out_dir)

    client = HelpCenter(config.zendesk_host, config.locale)
    sections = client.section_names()
    articles = client.articles(max_articles=args.limit or config.max_articles)

    if not articles:
        log.error("the API returned no published articles")
        return 1

    result = write_articles(articles, sections, config.out_dir)
    log.info("wrote %d Markdown files to %s", len(result.manifest), config.out_dir)
    log.info("%s", result.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
