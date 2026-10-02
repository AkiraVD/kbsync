# Does the bot actually reach the store?

A probe worth more than a demo question: ask for values that exist only in the corpus. The
Weather Radar article was updated on 2026-09-29, so no model knows it from training, and the
answer is four exact facts rather than prose a reader has to judge.

> In the Weather Radar app, list the exact Playback Speed values and the exact Forecast Time
> options, say which one is the default for each, and state which countries the app covers.
> Then give the Article URL.

Same model, same verbatim system prompt, asked twice.

## Against the store — `python main.py --ask ...`

```
* Playback Speed values: 0.5x, 1x (default), and 2x
* Forecast Time options: 20, 40, or 60 min (default is 60 min)
* Country coverage: The United States only

Article URL: https://support.optisigns.com/hc/en-us/articles/55906396437523-How-to-Use-the-Weather-Radar-App

Retrieved from:
  how-to-use-the-weather-radar-app.md  https://support.optisigns.com/hc/en-us/articles/55906396437523-How-to-Use-the-Weather-Radar-App
```

## Without retrieval — same question in AI Studio, nothing attached

```
* Playback Speed values: Slow, Medium (Default), and Fast.
* Forecast Time options: None (Default), 30 mins, 1 hour, 1.5 hours, and 2 hours.
* Country Coverage: The app covers the US, Canada, Europe, and Australia.

Article URL: https://support.optisigns.com/hc/en-us/articles/1500004944802-How-to-Use-the-Weather-Radar-App
```

## Scored against the article

| | Without retrieval | Against the store | Correct |
|---|---|---|---|
| Playback Speed | Slow / Medium / Fast | **0.5x, 1x (default), 2x** | 0.5x, 1x (default), 2x |
| Forecast Time | None / 30min / 1h / 1.5h / 2h | **20, 40, 60 min (60 default)** | 20, 40, 60 min (60 default) |
| Coverage | US, Canada, Europe, Australia | **United States only** | United States only |
| Article URL | `…/1500004944802-…` → **HTTP 404** | `…/55906396437523-…` → **HTTP 200** | 55906396437523 |

Four of four, including each default. Guessing `0.5x/1x/2x` is possible; also landing
`20/40/60` with 60 as the default, the single-country restriction *and* a URL that resolves
is not.

The failure mode is the interesting half. The prompt orders the bot to cite, so a model with
nothing to cite manufactures something shaped like a citation — twice, in two different
Zendesk id formats (`360018861614` on an earlier run, `1500004944802` here), both HTTP 404.
Answering "the app covers Europe" to a customer in Europe, with a citation, is worse than
answering nothing.

Verify any citation the same way:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' "<the article url>"
```

`tests/test_eval.py` automates exactly this check: every article-shaped URL in an answer must
appear in `articles/manifest.json`.
