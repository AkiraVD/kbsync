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

Static chunks of **512 tokens with 128 overlap**, set per file through `chunkingConfig` on
the upload call rather than left to the service default.

512 is the service maximum — File Search rejects anything larger — so the real decision was
the overlap. Help Center articles are short procedures with headed sections, and a 512-token
chunk usually holds one section whole. The 128-token overlap (25%) carries the end of one
section into the start of the next, so a numbered sequence split across a boundary stays
answerable, without storing half the corpus twice as a 50% overlap would. Both are
configurable in `.env`, and a value over 512 is rejected locally rather than by the API.

Each file leads with its title and an `Article URL:` line, repeated outside the YAML front
matter. This is load-bearing: a File Search citation returns the matched **chunk text**, not
a link, so the URL has to be in the body for the answer to cite it.

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
pytest -q              # 49 offline tests, no key needed
pytest -m eval         # the 6-case eval set; hits the API, needs a populated store
```

The eval set comes from real conversations with the live bot. One case asks about
unsupported "SmartBridge" hardware and asserts no article URL is invented: anything the
answer cites is checked against the manifest.

## Notes on the model

`GEMINI_MODEL` defaults to `gemini-flash-latest`. Pinned versions returned
`503 service_unavailable` ("experiencing high demand") on the free tier while
`gemini-flash-latest` answered, and the HTTP layer retries 429/503 honouring `Retry-After`.
