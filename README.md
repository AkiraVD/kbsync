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

**Logs:** https://fly.io/apps/kbsync/monitoring, or `fly logs -a kbsync`. That page needs a Fly
account, so the last-run artefact is committed as [`docs/run-log.md`](docs/run-log.md) — the
transcript of a real scheduled run, readable by anyone. Every run logs `added / updated /
skipped`.

Delta detection compares a sha256 of each converted body against the hash stored on the
document in the store, so an unchanged Help Center costs no uploads: a second pass over 416
articles takes about a second.

## Screenshot

![The brief's question answered with citations in AI Studio](docs/screenshot-aistudio.jpg)

Gemini's File Search has no Playground surface — AI Studio offers Search grounding, code
execution and function calling, but no way to attach a store — so the capture above runs the
same verbatim prompt against the generated Markdown, with every other tool switched off.
Five bullets, the prompt's cap, and two real article URLs.

The assistant proper is exercised through the API, and that transcript is in
[`docs/screenshot-ask.txt`](docs/screenshot-ask.txt): same question, answered out of the
vector store, with the `Article URL:` line the prompt asks for.

## Notes

- **Gemini rather than OpenAI** — both are allowed. File Search storage and query-time
  embeddings are free, so a daily job costs nothing.
- **Uploads are plain REST calls**, never the dashboard: resumable start, finalise, wait for
  the import, delete the document it replaced.
- **State lives in the store**, not on disk. Nothing to mount, nothing lost when the
  container exits.
- **`articles/` is not committed.** It is regenerated every run, and the content belongs to
  the Help Center it came from.
- **`GEMINI_MODEL` defaults to `gemini-flash-lite-latest`.** The free tier caps requests per
  model per day, and `gemini-flash-latest` (which resolves to `gemini-3.8-flash`) allows 20 —
  enough to exhaust on one eval run. Pinned versions also answered `503` under load. Quota
  replies carry a `Retry-After` measured in hours, so the HTTP layer refuses any wait over a
  minute instead of sleeping until tomorrow.
- **Indexing is the slow part**, not answering: about 10s per document, so a first full index
  of 416 articles takes roughly 70 minutes. Every run after that is a second.
