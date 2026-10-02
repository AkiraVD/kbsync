# kbsync

Daily one-way sync from a Zendesk Help Center into an OpenAI vector store, so an assistant
can answer support questions from the current docs and cite them. Re-runs upload only what
changed.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env     # fill in OPENAI_API_KEY, OPENAI_VECTOR_STORE_ID, ZENDESK_HOST
```

## Run locally

```bash
python main.py          # fetch → Markdown → upload delta → print counts
```

## Run in Docker

```bash
docker build -t kbsync .
docker run --rm --env-file .env kbsync
```

Runs once and exits 0.

## Chunking strategy

_TODO: size, overlap, and why — plus files and chunks embedded per run._

## Daily job

_TODO: host, schedule, link to logs._

Each run logs `added / updated / skipped`. New and changed articles are detected by
comparing a content hash against the previous run, so an unchanged Help Center costs no
uploads.

## Notes

- The fetched Markdown is **not committed**. `articles/` is gitignored: the content belongs
  to the Help Center it came from, and every run regenerates it. Counts are in the run log.
- The source Help Center is configuration (`ZENDESK_HOST`), not a constant, so this repo
  carries no vendor-specific strings.

## Tests

```bash
pytest -q
```
