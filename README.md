# opensky-pipeline

A pipeline that polls the OpenSky Network API on a schedule and turns live aircraft snapshots into a time series stored in Postgres.

## What this does

OpenSky's `/states/all` endpoint returns the current state of every aircraft its receiver network can see right now — position, altitude, velocity, and so on. It's a snapshot, not a history. There's no endpoint that hands you "this aircraft's track over the last six hours."

This pipeline builds that history itself: it polls `/states/all` at a fixed interval, writes each poll's results as rows in Postgres, and lets the accumulated snapshots become the dataset. The interesting part isn't fetching the data — it's generating a usable time series out of something that's inherently just a point-in-time view.

## Architecture

Planned flow, orchestrated by Airflow and containerized with Docker:

```
OpenSky /states/all API
        |
        v
   collect (poll on a schedule)
        |
        v
   parse state vectors -> rows
        |
        v
   store in Postgres (aircraft_data)
        |
        v
   transform / downstream layers
   - traffic analytics (SQL)
   - anomaly detection (rule-based + unsupervised)
```

**Current state of the repo:** only the Postgres schema ([sql/create_tables.sql](sql/create_tables.sql)) exists so far. The ingestion script, Airflow DAGs, Docker Compose stack, and the analytics/anomaly-detection layers are planned but not yet written. `docker-compose.yml`, `requirements.txt`, and `.env.example` are currently placeholder files.

## The data

One row in `aircraft_data` is one aircraft's state as reported in a single poll — not one row per aircraft. The same aircraft (`icao24`) will have many rows over time as the pipeline keeps polling it.

```sql
CREATE TABLE aircraft_data(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    icao24 TEXT NOT NULL,
    callsign TEXT,
    origin_country TEXT NOT NULL,
    time_position TIMESTAMPTZ,
    last_contact TIMESTAMPTZ NOT NULL,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    baro_altitude DOUBLE PRECISION,
    on_ground BOOLEAN NOT NULL,
    velocity DOUBLE PRECISION,
    true_track DOUBLE PRECISION,
    vertical_rate DOUBLE PRECISION,
    geo_altitude DOUBLE PRECISION,
    squawk TEXT,
    position_source SMALLINT NOT NULL,
    poll_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_observation UNIQUE (icao24, last_contact)
)
```

Key columns:

- `icao24` — the aircraft's 24-bit ICAO transponder address, the closest thing to a stable aircraft ID in this data.
- `last_contact`, `time_position` — timestamps reported by OpenSky itself: when the aircraft was last heard from, and when its position was last updated. These describe the aircraft's state, not the pipeline's behavior.
- `poll_time`, `ingested_at` — timestamps owned by the pipeline: when this polling run started, and when the row was actually written to Postgres. These describe the collection process, not the aircraft.
- `on_ground`, `velocity`, `baro_altitude`, `geo_altitude`, `vertical_rate`, `true_track` — flight state at the time of the report.
- `position_source` — which system supplied the position (ADS-B, ASTERIX, MLAT, etc., per OpenSky's encoding).

The two timestamp pairs matter because they answer different questions: "when did this happen to the aircraft" vs. "when did we observe/record it." A stale `last_contact` with a fresh `poll_time` tells you the aircraft hasn't updated, not that the pipeline failed.

**Dedup:** `/states/all` will often return the same aircraft state across consecutive polls if nothing has changed. `UNIQUE (icao24, last_contact)` plus `ON CONFLICT DO NOTHING` on insert means a repeated (icao24, last_contact) pair is silently skipped, so the same real-world observation isn't stored twice just because it showed up in more than one poll.

## Setup

Not yet runnable end-to-end — this documents the intended configuration.

**Environment variables** (`.env`, based on `.env.example`):

OpenSky's API requires OAuth2 client credentials, obtained from an OpenSky account:

```
OPENSKY_CLIENT_ID=
OPENSKY_CLIENT_SECRET=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
```

`.env` is gitignored; `.env.example` is meant to be the checked-in template with the variable names but no values.

**Running it** (once the Docker Compose stack is written):

```
docker compose up -d
```

This should bring up Postgres, Airflow, and the poller as services, with the DAG handling the polling schedule.

## Analytics and anomaly detection

Downstream of ingestion, the plan is two layers on top of `aircraft_data`:

- **Traffic analytics** — SQL queries/views over the accumulated observations (traffic volume, route/position patterns, altitude and velocity distributions, etc.).
- **Anomaly detection** — a rule-based layer (e.g. implausible speed/altitude/position jumps) plus an unsupervised model (e.g. clustering or outlier detection over flight state) to flag unusual behavior.

Neither layer is implemented yet.

## Limitations

- The raw table retains position-less contacts — rows where OpenSky only has a Mode-S detection with no position fix (`longitude`/`latitude` null). These aren't filtered at ingest; anything that consumes `aircraft_data` needs to handle nulls.
- Redundant sightings aren't fully eliminated by the `UNIQUE(icao24, last_contact)` constraint. If an aircraft's position hasn't changed but `last_contact` has advanced, that's a new, distinct row by design (a new observation was made), even though the position is unchanged from the previous row. Collapsing those into "the aircraft was stationary at X from time A to time B" is left to downstream queries, not done at ingest.
- Coverage is a single-region bounding box, not global. Whatever region is configured for the poller is the only traffic this dataset can ever see.
- Temporal resolution is capped by the poll interval. Anything that happens between two polls (a climb, a turn, a full pass through the region) isn't captured — the pipeline reconstructs a time series from samples, not a continuous track.
- OpenSky's free tier has rate and daily credit limits on API calls. The poll interval and bounding box size are constrained by that budget, not just by what would be analytically ideal.
