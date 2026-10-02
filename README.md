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
docker run --rm --env-file .env kbsync            # or: ... kbsync main.py
```

Runs once and exits 0. Exits 1 with a one-line message if required settings are missing.

## Chunking strategy

Static chunks of **800 tokens with 200 overlap**, set per file through
`chunking_strategy` on the attach call rather than left to `auto` (which uses 800/400).

Help Center articles are short procedures — a few hundred to a couple of thousand tokens —
so 800 keeps a whole numbered procedure, with its heading, inside one chunk. The 200-token
overlap carries the end of one section into the next so a step sequence split across a
boundary stays answerable; `auto`'s 400 would have doubled the stored copy of every article
for no gain on documents this size. Both are configurable in `.env`.

Each file leads with its title and an `Article URL:` line, repeated outside the YAML front
matter, so whichever chunk a search returns still carries the citation.

Every run logs the file count and the chunk count embedded.

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
