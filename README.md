# kbsync

Daily one-way sync from a Zendesk Help Center into a Gemini File Search store, so an
assistant can answer support questions from the current docs and cite them. Re-runs upload
only what changed.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env     # fill in ZENDESK_HOST and GEMINI_API_KEY
python main.py --create-store kbsync   # once; paste the name into .env
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

Static chunks of **800 tokens with 200 overlap**, set per file through `chunkingConfig`
on the upload call rather than left to the service default.

Help Center articles are short procedures — a few hundred to a couple of thousand tokens —
so 800 keeps a whole numbered procedure, with its heading, inside one chunk. The 200-token
overlap carries the end of one section into the next so a step sequence split across a
boundary stays answerable, without doubling the stored copy of every article the way a 50%
overlap would. Both are configurable in `.env`.

Each file leads with its title and an `Article URL:` line, repeated outside the YAML front
matter, so whichever chunk a search returns still carries the citation.

Every run logs the file count and the chunk count embedded.

## Daily job

_TODO: host, schedule, link to logs._

Each run logs `added / updated / skipped`. New and changed articles are detected by
comparing a content hash against the previous run, so an unchanged Help Center costs no
uploads.

## Notes

- **Gemini rather than OpenAI.** Both are permitted. Gemini File Search gives a vector store
  with free storage and free query-time embeddings, and its API covers everything the job
  needs: `customMetadata` per document carries the content hash that drives the delta, and
  `chunkingConfig` sets the chunking strategy explicitly.
- **Delta state lives in the store, not on disk.** Each document carries its article id and
  body hash as metadata, so a run lists the store, compares hashes and uploads only what
  differs. The container needs no volume and loses nothing when it exits.
- **Uploads are plain REST calls**, not a dashboard drag-and-drop: start a resumable upload,
  finalise it, wait for the import operation, delete the document it replaced.
- The fetched Markdown is **not committed**. `articles/` is gitignored: the content belongs
  to the Help Center it came from, and every run regenerates it. Counts are in the run log.
- The source Help Center is configuration (`ZENDESK_HOST`), not a constant, so this repo
  carries no vendor-specific strings.

## Tests

```bash
pytest -q
```
