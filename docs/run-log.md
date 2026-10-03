# A real scheduled run on Fly

Output of the Machine that `./deploy-fly.sh` creates. It wakes on its daily schedule, runs
`main.py` once, exits 0 and stops. Live at https://fly.io/apps/kbsync/monitoring or through
`fly logs -a kbsync`; that page needs a Fly account, so the transcript is reproduced here.

This run caught genuine upstream edits: the Help Center had gone from 416 published articles
to 415 overnight, with four rewritten.

```
    2026-10-03T01:51:21Z app[2872127c431278] sin [info] INFO Preparing to run: `python main.py` as kbsync
    2026-10-03T01:51:22Z app[2872127c431278] sin [info]2026-10-03T01:51:22 INFO    syncing support.optisigns.com (en-us) into articles
    2026-10-03T01:51:24Z app[2872127c431278] sin [info]2026-10-03T01:51:24 INFO    fetched 74 section names
    2026-10-03T01:51:27Z app[2872127c431278] sin [info]2026-10-03T01:51:27 INFO    fetched 415 articles from the Help Center API
    2026-10-03T01:51:45Z app[2872127c431278] sin [info]2026-10-03T01:51:45 INFO    store holds 416 documents with known article ids
    2026-10-03T01:52:00Z app[2872127c431278] sin [info]2026-10-03T01:52:00 INFO    uploaded how-to-use-the-monday-com-app.md
    2026-10-03T01:52:14Z app[2872127c431278] sin [info]2026-10-03T01:52:14 INFO    uploaded how-to-use-airtable-with-optisigns.md
    2026-10-03T01:52:28Z app[2872127c431278] sin [info]2026-10-03T01:52:28 INFO    uploaded how-to-use-the-mindmeister-app.md
    2026-10-03T01:52:41Z app[2872127c431278] sin [info]2026-10-03T01:52:41 INFO    uploaded how-to-best-use-canva-with-optisigns.md
    2026-10-03T01:52:41Z app[2872127c431278] sin [info]2026-10-03T01:52:41 INFO    wrote 415 Markdown files to articles
    2026-10-03T01:52:41Z app[2872127c431278] sin [info]2026-10-03T01:52:41 INFO    added=0 updated=4 skipped=411
    2026-10-03T01:52:41Z app[2872127c431278] sin [info]2026-10-03T01:52:41 INFO    embedded 4 file(s), ~11 chunks at 512 tokens with 128 overlap
    2026-10-03T01:52:42Z app[2872127c431278] sin [info] INFO Main child exited normally with code: 0
    2026-10-03T01:52:42Z runner[2872127c431278] sin [info]machine restart policy set to 'no', not restarting
```

Machine config, abridged:

```json
{ "schedule": "daily", "restart": { "policy": "no" }, "guest": { "cpus": 1, "memory_mb": 256 } }
```

Four lines carry the requirements:

- `store holds 416 documents with known article ids` — delta state read back out of the vector
  store, which is why the container needs no volume.
- `uploaded …` four times, naming each file — only what changed was sent.
- `added=0 updated=4 skipped=411` and `embedded 4 file(s), ~11 chunks at 512 tokens with 128
  overlap` — the counts the brief asks to be logged.
- `machine restart policy set to 'no', not restarting` — a job that finishes is not mistaken
  for a crash.

Two articles were unpublished upstream and are reported rather than deleted; pruning the
store is on the cut list. The slow case is the first index of an empty store, not this one:
416 documents over about 70 minutes, including a crash at 322 that re-uploaded nothing on
resume.
