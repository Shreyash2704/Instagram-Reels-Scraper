# Instagram video downloader pipeline

Prototype pipeline: define **sources** (hashtag, profile, post URL, profile tagged tab), run an **Apify** scrape, optionally **download videos** to disk or **S3**, normalize metadata, and **POST** a JSON array to a destination URL. **SQLite** stores sources, runs, dedupe keys, and per-run media rows.

## Why this Apify actor

**Primary:** [`aimscrape/instagram-scraper`](https://apify.com/aimscrape/instagram-scraper) — one actor covers profile `/reels/`, `/tagged/`, hashtag explore URLs, and direct post/reel links via a `queries` + `maxResultsPerQuery` input. Pay-per-result pricing is documented on the store page.

**Alternatives considered**

- **automation-lab/instagram-scraper** — Broad modes and OpenAPI; pricing/model differs; fine as a swap behind `APIFY_ACTOR_ID` if input mapping is adjusted.
- **instagram-scraper/instagram-profile-reels-scraper** — Narrower (profile reels); cheaper for that slice but does not cover all source types without a second integration.
- **scraper-engine/instagram-hashtag-scraper** — Hashtag-focused; useful as a secondary actor if the primary underperforms on tags only.

## Why RQ (not Celery)

The pipeline is **synchronous** today (SQLAlchemy sync session, blocking Apify client). **RQ** + **Redis** adds a durable queue and separate worker processes with minimal moving parts. Celery is stronger for complex schedules and many queues; it is heavier to operate for this assessment scope.

## Architecture (high level)

- **FastAPI** — CRUD sources/runs, `POST /sources/{id}/run`, mock destination `POST /destination/mock`.
- **Job execution** — If `REDIS_URL` is set, the API **enqueues** `process_run(run_id)` on Redis/RQ. If `REDIS_URL` is empty, **FastAPI `BackgroundTasks`** runs the same function in-process (dev convenience).
- **Worker** — `rq worker` pulls jobs, runs `execute_run` (Apify → normalize → optional media download → dedupe → destination POST → update `Run`).
- **Media** — `MEDIA_STORAGE=local` writes under `MEDIA_LOCAL_ROOT/{run_id}/`. `MEDIA_STORAGE=s3` downloads then uploads via **boto3**; payload includes `stored_url` like `s3://bucket/key`. Rows in `run_media_items` capture paths, sizes, and errors.
- **Client** — Poll `GET /runs` and `GET /runs/{id}` (no WebSocket in this repo).

See [docs/system-design.md](docs/system-design.md) for diagrams and failure modes.

## Prerequisites

- Python **3.11+**
- Optional: **Redis** (Docker: `docker compose up -d redis`)
- **Apify** account and API token for real scrapes

## Setup

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # or place .env in backend/ — see pydantic env_file
```

Set at least `APIFY_TOKEN`. For the mock destination on the same app:

```env
DESTINATION_URL=http://127.0.0.1:8000/destination/mock
```

### Run API

```bash
cd backend
set PYTHONPATH=.    # Windows CMD
# $env:PYTHONPATH="."  # PowerShell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI: <http://127.0.0.1:8000/docs>

### Frontend (Vite + React + Tailwind)

Requires **Node.js** (LTS). The UI calls the API using `VITE_API_BASE_URL`.

```bash
cd frontend
cp .env.example .env   # set VITE_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Open <http://localhost:5173>. Start the API on port **8000** first (or change the env URL).

- **Find by** tabs map to `post_url`, `profile`, `profile_tagged`, and `hashtag`.
- **Find media** creates a source, starts a run, and polls until completion.
- **History** lists sources and runs (newest first). Pick a source, then a run, to view the same video cards as Find media from `payload_preview`. The API returns at most **200 runs** per list request; use `GET /runs?source_id=<id>` to filter by source.
- **Production build:** `npm run build` → static files in `frontend/dist/`.

### Run worker (when using Redis)

```bash
docker compose up -d redis
export REDIS_URL=redis://127.0.0.1:6379/0
export RQ_QUEUE_NAME=pipeline   # must match app default
cd backend && export PYTHONPATH=.
./scripts/run_worker.sh
```

Windows PowerShell: `backend\scripts\run_worker.ps1`

If `REDIS_URL` is **unset**, you do **not** need a worker; the API process runs jobs inline after the response is sent.

## Environment matrix

| `REDIS_URL` | Behavior |
|-------------|----------|
| Empty | `BackgroundTasks` in API process |
| Set | Jobs go to Redis; **must** run `rq worker` |

| `MEDIA_STORAGE` | Behavior |
|-----------------|----------|
| `none` | Only Instagram CDN URLs in JSON (default) |
| `local` | Download videos under `MEDIA_LOCAL_ROOT`; **`video_url` in JSON becomes** `{MEDIA_PUBLIC_BASE_URL}/media/{stored_path}` (short); original CDN is **`cdn_video_url`**. Files are served at **`GET /media/...`**. |
| `s3` | Download to temp path under `MEDIA_LOCAL_ROOT`, upload to `S3_BUCKET` |

## API quick reference

- `POST /sources` — body: `{ "type": "hashtag|profile|post_url|profile_tagged", "value": "..." }`
- `POST /sources/{id}/run` — returns `{ "run_id", "status" }`
- `GET /runs`, `GET /runs/{id}` (optional `?source_id=` on list)
- `GET /proxy/cdn-image?url=...` — fetches an image from allowlisted Meta CDN hosts (`*.cdninstagram.com`, `*.fbcdn.net`, `*.instagram.com`) for UI thumbnails when the browser blocks direct `<img>` loads
- `POST /destination/mock` — test receiver (JSON array)

## Cron example

```bash
curl -s -X POST "http://127.0.0.1:8000/sources/1/run"
```

## Tests

```bash
cd backend
set PYTHONPATH=.
pytest tests -q
ruff check app tests
ruff format app tests
```

## Windows + RQ

RQ **2.x** pulls in a scheduler that uses `multiprocessing` **fork**, which **does not exist on Windows**, so importing RQ can crash the API. This repo pins **`rq>=1.16.2,<2`**. If you still see import errors, leave **`REDIS_URL` empty** so the API uses **`BackgroundTasks`** only, or run Redis + worker under **WSL**.

## Limits and edge cases

- **Public Instagram only** for typical no-login actors; private or restricted sources may return empty datasets.
- **SQLite + multiple RQ workers** can contend on locks; use **one worker** or migrate to Postgres for heavy concurrency.
- **Apify cost** scales with `MAX_RESULTS_PER_QUERY` and actor pricing — monitor usage in the Apify console.
- **`PAYLOAD_PREVIEW_MAX_CHARS`** (default 1M) caps JSON stored in `Run.payload_preview`. If it is too small, the string is truncated mid-JSON and the **UI cannot parse** it; raise the env var and **re-run** (old rows stay truncated).
- **Download failures** when `PIPELINE_FAIL_CLOSED=true` and `MEDIA_STORAGE` is `local` or `s3`: run is marked **failed** and the destination is not called.

## License / compliance

Assessment prototype only. Production use should follow Meta-approved APIs and applicable law.
