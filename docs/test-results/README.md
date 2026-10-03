# Test results

Captured runs, so the numbers in the README can be checked without a key.

| File | Suite | Result |
|---|---|---|
| [`offline-20261003.txt`](offline-20261003.txt) | `pytest -q` — 63 tests, no network | 63 passed in 0.30s |
| [`eval-live-20261003.txt`](eval-live-20261003.txt) | `pytest -m eval` — 6 tests against the live store | 6 passed in 61s |

The offline suite covers the cleaning rules (what survives HTML conversion and what must not),
slugs and front matter, the body hash that drives the delta, the upload calls with the HTTP
layer stubbed, retry behaviour including a quota-sized `Retry-After`, and that one failed
upload does not end a run.

The eval set is six questions drawn from real conversations with the production bot. The one
worth reading is `test_unsupported_hardware_invents_no_article_url`: it asks about "SmartBridge",
a player that does not exist, and asserts that every article-shaped URL in the reply appears in
`articles/manifest.json`. Asked the same question without retrieval, the model fabricates
citations that return HTTP 404 — see [`../retrieval-check.md`](../retrieval-check.md).

Reproduce:

```bash
pytest -q          # offline
pytest -m eval     # needs GEMINI_API_KEY and a populated store
```
