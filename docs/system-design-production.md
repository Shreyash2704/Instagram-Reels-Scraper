# Production system design — architecture & scaling

End-to-end view of this application as a **production-style** deployment: how the **client**, **API**, **database**, **Redis**, **workers**, **object storage**, and **external services** connect, and how you **scale** when load grows.

For day-to-day pipeline behavior and failure modes, see [system-design.md](./system-design.md). For code-level paths, see [code-flow.md](./code-flow.md).

---

## 1. Logical architecture (all major pieces)

```mermaid
flowchart TB
  subgraph Users["Users"]
    B[Browser]
  end

  subgraph Edge["Edge & static"]
    CDN_FE[CDN / object storage\nfor SPA static files]
    LB[Load balancer\noptional TLS termination]
  end

  subgraph AppTier["Application tier"]
    API1[FastAPI instance 1]
    API2[FastAPI instance N]
  end

  subgraph DataTier["Data & async"]
    PG[(PostgreSQL\nor Aurora)]
    REDIS[(Redis)]
    S3[(Amazon S3\nor compatible)]
  end

  subgraph WorkerTier["Job workers"]
    W1[RQ worker 1]
    W2[RQ worker M]
  end

  subgraph External["External services"]
    APIFY[Apify platform]
    DEST[Customer webhook\nDESTINATION_URL]
    IGIMG[Instagram / Meta\nimage hosts\nproxied for thumbnails]
  end

  B --> CDN_FE
  B -->|HTTPS API + polling| LB
  LB --> API1
  LB --> API2

  API1 --> PG
  API2 --> PG
  API1 --> REDIS
  API2 --> REDIS

  REDIS --> W1
  REDIS --> W2
  W1 --> PG
  W2 --> PG
  W1 --> APIFY
  W2 --> APIFY
  W1 --> S3
  W2 --> S3
  W1 --> DEST
  W2 --> DEST

  API1 --> IGIMG
  API2 --> IGIMG
  B -->|GET /proxy/cdn-image| LB
```

**Legend**

| Box | In this repo today | Typical production shape |
|-----|--------------------|---------------------------|
| **Browser** | Vite dev server or `npm run build` static files | SPA behind CDN; calls **one public API URL** |
| **Load balancer** | Often skipped locally | ALB / nginx / Cloud Run / k8s Ingress |
| **FastAPI** | Single `uvicorn` process | **Multiple replicas** (stateless HTTP) |
| **PostgreSQL** | **SQLite** file (`DATABASE_URL`) | Managed Postgres — **required** for concurrent writes & HA |
| **Redis** | Optional (`REDIS_URL` empty → `BackgroundTasks`) | **Required at scale** — queue + decouple API from long runs |
| **RQ workers** | Same code, `rq worker` | **Separate fleet** — scale count independently from API |
| **S3** | Optional `MEDIA_STORAGE=s3` | **Preferred** for media — shared across all API/worker instances |
| **Apify** | Always (scraping) | Same; respect rate limits & billing |
| **Webhook** | Optional `DESTINATION_URL` | Customer-owned HTTPS endpoint |
| **Image proxy** | `GET /proxy/cdn-image` | Stays on API tier (or move behind CDN with care) |

---

## 2. Request flow: one “run” from client to completion

```mermaid
sequenceDiagram
  participant C as Client SPA
  participant LB as Load balancer
  participant API as FastAPI
  participant DB as Database
  participant Q as Redis queue
  participant W as RQ worker
  participant A as Apify
  participant S3 as S3
  participant D as Destination webhook

  C->>LB: POST /sources then POST /sources/id/run
  LB->>API: forward
  API->>DB: insert run pending
  API->>Q: enqueue job run_id
  API-->>C: 200 run_id

  loop Poll until terminal state
    C->>LB: GET /runs/run_id
    LB->>API: forward
    API->>DB: read run
    API-->>C: status running / completed / failed
  end

  Q->>W: dequeue run_id
  W->>DB: mark running
  W->>A: actor run + read dataset
  A-->>W: items
  W->>W: normalize, dedupe
  opt MEDIA_STORAGE=s3
    W->>S3: put objects
  end
  W->>DB: payload_preview, counts
  opt DESTINATION_URL set
    W->>D: POST JSON array
  end
  W->>DB: completed or failed
```

With **no Redis**, steps **enqueue → worker** collapse into **FastAPI `BackgroundTasks`** on the **same** process that handled the HTTP request (fine for dev, poor for scale).

---

## 3. How components talk (connections)

```mermaid
flowchart LR
  subgraph Client
    SPA[SPA]
  end

  subgraph Backend
    API[FastAPI]
    WRK[Workers]
  end

  DB[(DB)]
  R[(Redis)]
  OB[(S3)]

  SPA -->|REST JSON| API
  API --> DB
  API --> R
  R --> WRK
  WRK --> DB
  WRK --> OB
  API --> OB
  WRK -->|HTTPS| EXT1[Apify]
  WRK -->|HTTPS| EXT2[Webhook]
  API -->|HTTPS| EXT3[Thumbnail proxy fetch]
  SPA -->|img src| API
```

- **Client ↔ API:** JSON over HTTPS (CORS configured via `CORS_ORIGINS`).
- **API ↔ DB:** SQLAlchemy — every instance and worker needs the **same** `DATABASE_URL` in production (not local SQLite files per machine).
- **API ↔ Redis:** enqueue only (`LPUSH` / RQ).
- **Workers ↔ Redis:** dequeue; workers do **not** need to serve HTTP.
- **Workers ↔ S3:** boto3 uploads when `MEDIA_STORAGE=s3`; all workers share one bucket/prefix.
- **Workers ↔ Apify / webhook:** outbound HTTPS from worker network (allow egress in firewall / VPC).

---

## 4. Scaling when traffic increases

### Principles

1. **Stateless API** — Any replica can handle `GET /runs` and `POST /sources/.../run`. Session stickiness is **not** required for this API design.
2. **Heavy work off the request thread** — Use **Redis + many workers** so HTTP handlers stay fast under burst.
3. **One writer truth** — **PostgreSQL** (or compatible) replaces SQLite so many API replicas and workers don’t fight over a single file lock.
4. **Shared blob store** — **S3** (not local disk on one container) so every worker can read/write media and the API can serve or redirect consistently.
5. **Bottlenecks to watch** — **Apify** concurrency and account limits, **destination** webhook rate limits, **DB** connection pool size, **Redis** memory, **S3** request rates.

### Scaling diagram

```mermaid
flowchart TB
  subgraph LowTraffic["Low traffic / dev"]
    d1[1× API\nBackgroundTasks]
    d2[(SQLite file)]
    d1 --> d2
  end

  subgraph HighTraffic["Higher traffic / production"]
    LB2[Load balancer]
    a1[API × K]
    a2[(Postgres)]
    r2[(Redis)]
    wpool[Workers × M]
    s2[(S3)]

    LB2 --> a1
    a1 --> a2
    a1 --> r2
    r2 --> wpool
    wpool --> a2
    wpool --> s2
  end

  LowTraffic -.->|evolve| HighTraffic
```

| Knob | What to do |
|------|------------|
| More **concurrent users** reading status | Scale **API replicas** + connection pool to Postgres |
| More **runs per minute** | Scale **RQ workers**; ensure **Redis** is sized; watch Apify limits |
| **Media-heavy** workloads | Scale workers + **S3**; avoid `MEDIA_STORAGE=local` multi-host |
| **Global users** | Put SPA on **CDN**; run API in region(s) close to DB or use regional read replicas later |
| **Reliability** | Managed Redis/Postgres with failover; health checks on API; dead-letter / retry policy for failed jobs |

---

## 5. Checklist: dev → production

- [ ] Replace **SQLite** with **PostgreSQL** and run migrations / `create_all` once per environment.
- [ ] Set **REDIS_URL** and run **multiple `rq worker`** processes or containers.
- [ ] Run **at least as many API processes** as needed for p95 latency (e.g. gunicorn+uvicorn workers or k8s replicas).
- [ ] Use **S3** for `MEDIA_STORAGE` if more than one API/worker host.
- [ ] Store **secrets** (`APIFY_TOKEN`, DB, AWS) in a secret manager, not in git.
- [ ] Lock down **CORS** to real frontend origins.
- [ ] Add **TLS** at load balancer; restrict **security groups** (workers need egress to Apify, S3, webhook).
- [ ] Optional: **rate limiting** and auth on public API before wide exposure.

---

## Related docs

- [system-design.md](./system-design.md) — behavior, failure modes, workflows  
- [code-flow.md](./code-flow.md) — routes → services → integrations  
