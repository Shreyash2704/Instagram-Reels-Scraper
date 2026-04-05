# Architecture — Instagram video downloader pipeline

## Problem context

Prototype pipeline for Videoselz-style assessment: discover public Instagram videos via Apify, normalize metadata and CDN URLs, persist runs in SQLite, and optionally deliver a JSON payload to a configurable webhook URL. Operators use a Vite SPA; scheduled jobs call the API (cron/CI).

## Components

| Component | Role |
|-----------|------|
| **Vite SPA** | Create/list sources, trigger runs, inspect run status and errors. |
| **FastAPI** | REST API, dependency-injected DB and Apify client; enqueues jobs or uses in-process background tasks. |
| **Redis + RQ** (optional) | Durable queue when `REDIS_URL` is set; `rq worker` runs `process_run(run_id)`. |
| **SQLite** | Sources, runs, optional dedupe of delivered media per source, `run_media_items` for downloads. |
| **Apify** | `aimscrape/instagram-scraper` (primary) — queries → dataset items (posts/reels). |
| **Local disk / S3** (optional) | When `MEDIA_STORAGE` is `local` or `s3`, videos are downloaded (and uploaded to S3 when configured). |
| **Destination** | HTTP POST receives JSON array of normalized video records (no auth in v1). |

## Trust boundaries

- **Secrets:** `APIFY_TOKEN` only on the server; never exposed to the browser.
- **Public IG only:** No Instagram login; private or restricted profiles may return empty or partial data.
- **Destination:** Optional `DESTINATION_URL`; empty skips POST; otherwise trusted webhook.

## Architecture and Data flow (single run)

![alt text](<Instagram content scraper (1).jpg>)

1. Client calls `POST /sources/{id}/run`.
2. API creates a `Run` row (`pending`), enqueues to **Redis/RQ** or schedules **`BackgroundTasks`**, returns `run_id`.
3. Worker sets `running`, builds Apify `queries` from `Source.type` + `value`, calls actor with `maxResultsPerQuery`.
4. Dataset items are **normalized** to the delivery schema; only rows with `is_video` (or usable `video_url`) are included unless only images exist (then empty array policy applies).
5. Optional **dedupe:** skip items already recorded for this `source_id`.
6. Optional **media:** if `MEDIA_STORAGE` is `local` or `s3`, download each `video_url`, write `run_media_items`, set `stored_path` / `stored_url` on payload items; on errors and `PIPELINE_FAIL_CLOSED`, fail the run before delivery.
7. **POST** JSON array to `DESTINATION_URL` (or skip if URL empty — log only).
8. Worker sets `completed` or `failed`, stores short error message and optional payload summary.

## Related

- [system-design-production.md](./system-design-production.md) — production deployment diagram, Redis/S3/Postgres, and scaling.

## Failure modes

| Failure | Behavior |
|---------|----------|
| Invalid source value | `4xx` on create/update; run not started. |
| Apify error / timeout | Run `failed`; message stored; partial delivery per `PIPELINE_FAIL_CLOSED` env. |
| Destination unreachable | Retries per `DESTINATION_RETRIES`; run may `failed` or `completed_with_errors` (implementation: mark failed after retries exhausted). |
| Empty video set | POST empty JSON array `[]` to destination (documented). |
| Media download / S3 error | With `PIPELINE_FAIL_CLOSED`, run `failed` and destination skipped; rows in `run_media_items` may contain `error` text. |
| Redis down with `REDIS_URL` set | Enqueue fails at runtime — operational concern; use health checks or unset `REDIS_URL` for single-process dev. |

## User workflows

### Operator (UI)

1. Open SPA → **Sources** → create source (hashtag / profile / post URL / profile tagged).
2. Click **Run** on a source (or use API).
3. Open **Runs** → select run → view status, error text, counts, JSON preview of delivered payload.

### Scheduled (cron / GitHub Actions)

1. Obtain `source_id` (from UI or `GET /sources`).
2. `curl -X POST https://host/sources/{id}/run` on schedule.
3. Monitor `GET /runs` or logs.

### Failure path

1. Run shows `failed` in UI and API.
2. Check logs for `apify`, `normalize`, `destination` prefixes.
3. Fix source or config; trigger new run.
