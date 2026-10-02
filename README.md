# kbsync

Daily one-way sync from a Zendesk Help Center into a Gemini File Search store, so an
assistant answers support questions from the current docs and cites them. Each run uploads
only what changed.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.sample .env                    # ZENDESK_HOST, GEMINI_API_KEY
python main.py --create-store kbsync   # once; paste the name into .env
```

## Run locally

```bash
python main.py                      # full sync; --limit N for a quick pass
python main.py --no-upload          # Markdown only, no API key needed
python main.py --ask "How do I add a YouTube video?"
pytest -q                           # 49 offline tests
pytest -m eval                      # 6-case eval set; hits the API
```

With Docker, which is what the scheduled job runs:

```bash
docker build -t kbsync .
docker run --rm --env-file .env kbsync      # or: ... kbsync main.py
```

Runs once and exits 0; exits 1 with one line if required settings are missing.

## Chunking strategy

**512 tokens per chunk, 128 overlap**, set per file through `chunkingConfig` rather than left
to the service default. 512 is the service maximum, so the real decision was the overlap:
articles are short procedures with headed sections, and 512 tokens usually holds one section
whole. The 128-token overlap (25%) carries the end of one section into the next so a numbered
sequence split across a boundary stays answerable, without storing a quarter of the corpus
twice as a 50% overlap would. Both are configurable; a value over 512 is rejected locally
rather than by the API.

Every file repeats its `Article URL:` outside the YAML front matter. That is load-bearing: a
File Search citation hands back the matched **chunk text**, not a link, so the URL has to be
in the body for an answer to cite it. Each run logs files written and chunks embedded.

## Daily job

`fly.toml` plus `deploy-fly.sh` create a Fly Machine with `--schedule daily`: it wakes, runs
`main.py` once, and stops. Deploy once with `./deploy-fly.sh` after
`fly secrets set ZENDESK_HOST=... GEMINI_API_KEY=... GEMINI_FILE_SEARCH_STORE=...`.

**Logs:** `fly logs -a kbsync`, or https://fly.io/apps/kbsync/monitoring — that page needs
account access, so a transcript of a real scheduled run is in [`docs/run-log.md`](docs/run-log.md).
Every run logs `added / updated / skipped`.

Delta detection compares a sha256 of each converted body against the hash stored on the
document in the store, so an unchanged Help Center costs no uploads: a second pass over 416
articles takes about a second.

## Screenshot

_TODO: `--ask "How do I add a YouTube video?"` showing the answer and its Article URL._

## Notes

- **Gemini rather than OpenAI** — both are allowed. File Search storage and query-time
  embeddings are free, so a daily job costs nothing.
- **Uploads are plain REST calls**, never the dashboard: resumable start, finalise, wait for
  the import, delete the document it replaced.
- **State lives in the store**, not on disk. Nothing to mount, nothing lost when the
  container exits.
- **`articles/` is not committed.** It is regenerated every run, and the content belongs to
  the Help Center it came from.
- `GEMINI_MODEL` defaults to `gemini-flash-latest`; pinned versions returned
  `503 service_unavailable` on the free tier.
