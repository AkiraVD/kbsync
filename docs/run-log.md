# A real scheduled run on Fly

Output of the Machine that `./deploy-fly.sh` creates. It wakes on its daily schedule, runs
`main.py` once, exits 0 and stops. This pass found nothing new, which is the normal case: all
416 articles were already in the store, so nothing was re-uploaded.

Live at https://fly.io/apps/kbsync/monitoring, or `fly logs -a kbsync`. That page needs
account access, so the transcript is reproduced here.

```
    2026-10-02T11:13:21Z app[185d097f797038] sin [info] INFO Preparing to run: `python main.py` as kbsync
    2026-10-02T11:13:21Z app[185d097f797038] sin [info]2026-10-02T11:13:21 INFO    syncing support.optisigns.com (en-us) into articles
    2026-10-02T11:13:23Z app[185d097f797038] sin [info]2026-10-02T11:13:23 INFO    fetched 74 section names
    2026-10-02T11:13:26Z app[185d097f797038] sin [info]2026-10-02T11:13:26 INFO    fetched 416 articles from the Help Center API
    2026-10-02T11:13:44Z app[185d097f797038] sin [info]2026-10-02T11:13:44 INFO    store holds 416 documents with known article ids
    2026-10-02T11:13:44Z app[185d097f797038] sin [info]2026-10-02T11:13:44 INFO    wrote 416 Markdown files to articles
    2026-10-02T11:13:44Z app[185d097f797038] sin [info]2026-10-02T11:13:44 INFO    added=0 updated=0 skipped=416
    2026-10-02T11:13:45Z app[185d097f797038] sin [info] INFO Main child exited normally with code: 0
    2026-10-02T11:13:45Z runner[185d097f797038] sin [info]machine restart policy set to 'no', not restarting
```

Machine config, abridged:

```json
{ "schedule": "daily", "restart": { "policy": "no" }, "guest": { "cpus": 1, "memory_mb": 256 } }
```

Three lines carry the requirements. `store holds 416 documents` is the delta check reading
state back out of the vector store. `added=0 updated=0 skipped=416` is the delta itself: a
hash per article compared against what the store held, and nothing re-uploaded. And
`machine restart policy set to 'no', not restarting` is why a job that finishes is not
mistaken for a crash and run again.

The slow case is the first index of an empty store, not this one: 416 documents over about
70 minutes, including a recovery from a crash at 322 that re-uploaded nothing.
