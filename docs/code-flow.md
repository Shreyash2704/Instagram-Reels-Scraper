# Backend code flow (routes → services → integrations)

How a request moves through **FastAPI routes**, **services**, **external integrations**, and back to the **client**. File names point to the real code.

---

## 1. Big picture: client ↔ API ↔ work ↔ client

```mermaid
flowchart LR
  subgraph Client["Browser / SPA"]
    UI[React app]
  end

  subgraph Routes["FastAPI routes"]
    RSrc["routes_sources.py"]
    RRun["routes_runs.py"]
    RPrx["routes_proxy_image.py"]
  end

  subgraph Async["Out-of-band work"]
    BT["BackgroundTasks\nor RQ worker"]
  end

  subgraph Service["Services"]
    Pipe["pipeline_service.execute_run"]
    Dest["destination_client.post_payload"]
    Media["media_storage.attach_stored_media"]
  end

  subgraph Integ["Integrations / external"]
    Apify["ApifyClient + aimscrape_provider"]
    Norm["normalize.py"]
    ExtHttp["httpx → DESTINATION_URL"]
    CDN["httpx → CDN image URL"]
  end

  DB[(SQLite via SQLAlchemy)]

  UI -->|POST /sources, POST .../run\nGET /runs, GET /sources| RSrc
  UI --> RRun
  UI --> RPrx

  RSrc --> DB
  RRun --> DB
  RSrc -->|schedule job| BT
  BT --> Pipe
  Pipe --> Apify
  Apify -->|dataset items| Pipe
  Pipe --> Norm
  Pipe --> Media
  Media -->|optional disk/S3| Pipe
  Pipe --> Dest
  Dest --> ExtHttp
  Pipe --> DB

  RPrx --> CDN
  RPrx -->|image bytes| UI

  RRun -->|JSON run row| UI
  RSrc -->|JSON| UI
```

---

## 2. Start a run: `POST /sources/{id}/run` (vertical detail)

Numbers match the general order of operations inside `execute_run`.

```mermaid
flowchart TB
  C[Client: POST /sources/source_id/run]

  subgraph Step1["① Route layer"]
    RS[run_source in routes_sources.py]
    RS -->|create Run pending| DB1[(Database)]
    RS -->|Redis on?| RQ{RQ?}
    RQ -->|yes| EQ[enqueue_run → process_run in worker]
    RQ -->|no| BT[BackgroundTasks → _run_pipeline_task]
  end

  subgraph Step2["② Same process / worker"]
    ER[execute_run in pipeline_service.py]
  end

  subgraph Step3["③ Integration — Apify"]
    PRV[AimscrapeInstagramProvider.build_run_input]
    AC[ApifyClient.actor.call + dataset.iterate_items]
    PRV --> AC
  end

  subgraph Step4["④ Back in pipeline service"]
    NORM[normalize_item per row]
    DED[doptional dedupe filter]
    NORM --> DED
  end

  subgraph Step5["⑤ Service — media"]
    ASM[attach_stored_media in media_storage.py]
  end

  subgraph Step6["⑥ Service — destination"]
    PP[post_payload in destination_client.py]
    PP --> EXT[External HTTP POST to DESTINATION_URL]
  end

  subgraph Step7["⑦ Persist & finish"]
    DB2[(Database: status, payload_preview,\ncounts, destination_status_code)]
  end

  C --> RS
  EQ --> ER
  BT --> ER
  ER --> PRV
  AC --> ER
  ER --> NORM
  DED --> ASM
  ASM --> ER
  ER --> PP
  EXT --> ER
  ER --> DB2

  POLL[Client: GET /runs/run_id on a timer]
  POLL --> GRR[get_run in routes_runs.py]
  GRR --> DB2
  GRR -->|RunRead JSON| C
```

---

## 3. Read-only routes (no pipeline)

```mermaid
flowchart LR
  C[Client]
  C -->|GET /sources| LS[list_sources]
  C -->|GET /sources/id| GS[get_source]
  C -->|GET /runs| LR[list_runs]
  C -->|GET /runs/id| GR[get_run]
  LS --> DB[(DB)]
  GS --> DB
  LR --> DB
  GR --> DB
  DB -->|Pydantic response| C
```

---

## 4. Thumbnail proxy: `GET /proxy/cdn-image`

```mermaid
flowchart LR
  C[Client img src]
  R[routes_proxy_image.proxy_cdn_image]
  H[httpx GET to allowlisted CDN URL]
  C --> R
  R --> H
  H -->|bytes| R
  R -->|image/* response| C
```

---

## File cheat sheet

| Layer | Files |
|--------|--------|
| **Routes** | `app/api/routes_sources.py`, `routes_runs.py`, `routes_proxy_image.py` |
| **Orchestration** | `app/services/pipeline_service.py` (`execute_run`) |
| **HTTP side effects** | `app/services/destination_client.py`, `app/services/media_storage.py` |
| **Apify wiring** | `app/integrations/apify/aimscrape_provider.py`, `normalize.py` |
| **Async entry** | `routes_sources._run_pipeline_task` / `app/jobs/tasks.process_run` + `jobs/queue.enqueue_run` |

For product-level architecture (optional queue, storage, trust), see [system-design.md](./system-design.md).
