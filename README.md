# HydrantWorks

A hydrant maintenance service for Trumbull County, Ohio: the county's 7,126
fire hydrants, their inspections, the work orders raised against them, and
which ones are out of service right now. Fire departments, water departments
and dispatchers would be its users.

HydrantWorks is the codebase students inherit in **Agentic Software
Engineering** (https://mikecostarella.github.io/CS_AgenticSoftwareEngineering/).
Every lab in that course is a change to this repository, made the way a new
engineer on a team would make it: an issue, a branch, a pull request, a green
CI run, a review.

Created by Mike Costarella, Costarella Innovations, LLC.

> **What is real and what is not.** The hydrant inventory in
> `data/hydrants.csv` is the Trumbull County Auditor's hydrant export, as
> published in the [Trumbull County Hydrants map](https://mikecostarella.github.io/TrumbullCountyHydrants/),
> unchanged — quirks included. Everything else — inspections, work orders,
> out-of-service notices, crew field notes, and the fire department list — is
> **synthetic sample data**. It is not a record of any real inspection or
> repair, and no county agency or fire department uses this service.

## Quick start (Windows, PowerShell)

You need Python 3.11 or newer and Git.

First make your own copy: on GitHub, open this repository and choose
**Use this template → Create a new repository**. Then clone your copy:

```powershell
cd $HOME\agentic-se
git clone https://github.com/<you>/HydrantWorks.git
cd HydrantWorks
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn hydrantworks.main:app --reload
```

The first start builds `hydrantworks.db` (a few seconds). Then open
http://127.0.0.1:8000/docs — the interactive API docs — click **Authorize**,
and paste the read key from `.env`.

Run the tests and the linter the same way CI does (PowerShell, in the
`HydrantWorks` folder with the virtual environment active):

```powershell
ruff check .
pytest
```

On macOS or Linux, use `source .venv/bin/activate` and `cp .env.example .env`.

To rebuild the database from scratch, stop the server and run
`python -m hydrantworks.seed`.

## API at a glance

Every request except `/health` needs an `X-API-Key` header.

| Method and path | Key | What it does |
|---|---|---|
| `GET /health` | none | Liveness, version, chaos settings |
| `GET /jurisdictions` | read | Each jurisdiction with hydrant and out-of-service counts |
| `GET /hydrants` | read | Search by `jurisdiction`, `street`, `status`; paged (`page`, `size`) |
| `GET /hydrants/overdue` | read | Hydrants with no inspection in the last 365 days |
| `GET /hydrants/{id}` | read | One hydrant, with its last inspection time |
| `GET /hydrants/{id}/inspections` | read | Inspection history, newest first |
| `POST /inspections` | write | Record a field inspection |
| `GET /work-orders` | read | Filter by `status`, `hydrant_id`; newest first |
| `GET /work-orders/{id}` | read | One work order |
| `POST /work-orders` | write | Open a work order |
| `PATCH /work-orders/{id}` | write | Assign, re-prioritize, or close |
| `POST /hydrants/{id}/out-of-service` | write | Take a hydrant out of service (needs a reason) |
| `POST /hydrants/{id}/in-service` | write | Return it to service (needs a reason) |
| `GET /audit` | write | Every write: who, what, before and after, trace id |

The two keys come from `.env` (`HW_READ_KEY`, `HW_WRITE_KEY`). The read key
can only read; the write key can do everything. Give an agent the read key
until it has earned the write key.

### Domain rules

- **Overdue**: a hydrant is overdue when it has no inspection in the last 365
  days. A hydrant that has never been inspected is overdue.
- **Out of service** is the flag fire departments care about most: an
  out-of-service hydrant is one an engine company should not hook up to.
  Changing it always requires a reason and is always audited.
- **Times** are stored in UTC. Clients should send a time-zone offset
  (`2026-09-14T15:05:00-04:00`).
- **Every write is audited** with the caller's role and the request's trace id.

## Built-in tools for the labs

**Chaos mode** makes reads unreliable on purpose, so you can harden a client
against a misbehaving service. Set `HW_CHAOS` in `.env` and restart:

```
HW_CHAOS=latency=2.0,error_rate=0.2,empty_rate=0.1
HW_CHAOS_SEED=7
```

See `hydrantworks/chaos.py` for every option. Writes and `/health` are never
affected.

**Tracing.** Send `X-Trace-Id: <your id>` with a request and the service echoes
it back, logs it, and stores it with any audit entry the request creates. Set
`HW_REQUEST_LOG=logs/requests.jsonl` to also write the request log to a file.
One id per agent run lets you follow a run across your agent's trace, the
service's log, and the audit table.

## Data files

| File | What it is |
|---|---|
| `data/hydrants.csv` | The real county inventory, 7,126 hydrants |
| `data/field_notes.jsonl` | Synthetic free-text notes from inspection crews |
| `data/sample_fire_department_list.csv` | A synthetic fire department hydrant list that does not fully agree with the county's |

`scripts/make_sample_data.py` regenerates the two synthetic files.

## Project layout

```
hydrantworks/
  main.py          app factory, middleware, routers
  config.py        settings from environment variables and .env
  db.py            SQLite schema and connection helpers
  seed.py          loads the inventory, generates the synthetic history
  models.py        Pydantic request/response models: the API contract
  repository.py    every SQL query
  auth.py          read and write API keys
  tracing.py       trace ids and the request log
  chaos.py         chaos mode
  routers/         one module per resource
tests/             pytest suite; tests/fixtures holds a 36-hydrant sample
data/              the inventory and the synthetic lab data
.github/workflows  CI: ruff and pytest on every push and pull request
```

## Working on it

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch and pull-request flow,
and [BACKLOG.md](BACKLOG.md) for known issues and requested features.

## License

Code: MIT. Documentation and the synthetic data: CC BY-NC-SA 4.0. The hydrant
inventory is a public record of Trumbull County, Ohio. See
[LICENSE.md](LICENSE.md).
