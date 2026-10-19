# Walkthrough

Submit connection requests with curl and poll for their verdicts. Start the service first with `docker compose up` (see the [README](../README.md#running-it)).

Output below is from a fresh `docker compose up`, with JSON formatted for readability and headers shortened.

Submit 30 kW of PV at the far end of the rural grid:

```sh
curl -si -X POST localhost:8080/connection-requests \
  -H 'Content-Type: application/json' \
  -d '{"grid_id": "kerber-landnetz-freileitung-1", "bus_id": 14, "p_kw": 30}'
```

```
HTTP/1.1 202 Accepted
location: /connection-requests/1

{
    "request_id": 1,
    "grid_id": "kerber-landnetz-freileitung-1",
    "bus_id": 14,
    "p_kw": 30.0,
    "status": "pending",
    "submitted_at": "2026-10-19T18:40:45.006887Z",
    "finished_at": null,
    "result": null,
    "error": null
}
```

Poll it. A moment later a worker has decided it: the voltage rises by at most 2.4 %, below the 3 % limit, so it's approved.

```sh
curl -s localhost:8080/connection-requests/1
```

```json
{
    "request_id": 1,
    "grid_id": "kerber-landnetz-freileitung-1",
    "bus_id": 14,
    "p_kw": 30.0,
    "status": "approved",
    "submitted_at": "2026-10-19T18:40:45.006887Z",
    "finished_at": "2026-10-19T18:40:45.777651Z",
    "result": {
        "metrics": {
            "vm_max_pu": 1.0242472153178517,
            "voltage_rise_max_pu": 0.024281648399097078,
            "line_loading_max_pct": 15.657848259411288,
            "trafo_loading_max_pct": 18.30612738769132
        },
        "verdict": "approved",
        "violations": [],
        "duration_ms": 147.90645799985214
    },
    "error": null
}
```

Now submit another 20 kW at the same bus. On an empty grid it would be approved, but it's checked together with the 30 kW approved before:

```sh
curl -s -X POST localhost:8080/connection-requests \
  -H 'Content-Type: application/json' \
  -d '{"grid_id": "kerber-landnetz-freileitung-1", "bus_id": 14, "p_kw": 20}'
curl -s localhost:8080/connection-requests/2
```

Together they raise the voltage by up to 4 %, so the request is rejected. The result lists every bus where the limit is exceeded:

```json
{
    "request_id": 2,
    "grid_id": "kerber-landnetz-freileitung-1",
    "bus_id": 14,
    "p_kw": 20.0,
    "status": "rejected",
    "submitted_at": "2026-10-19T18:40:47.092603Z",
    "finished_at": "2026-10-19T18:40:47.944553Z",
    "result": {
        "metrics": {
            "vm_max_pu": 1.0397733263300246,
            "voltage_rise_max_pu": 0.039807759411270016,
            "line_loading_max_pct": 25.706736705184984,
            "trafo_loading_max_pct": 30.0546274975198
        },
        "verdict": "rejected",
        "violations": [
            {"limit": 0.03, "value": 0.0314206408902975, "element": "bus 11", "criterion": "voltage_rise"},
            {"limit": 0.03, "value": 0.03421616218814183, "element": "bus 12", "criterion": "voltage_rise"},
            {"limit": 0.03, "value": 0.037011868860227226, "element": "bus 13", "criterion": "voltage_rise"},
            {"limit": 0.03, "value": 0.039807759411270016, "element": "bus 14", "criterion": "voltage_rise"}
        ],
        "duration_ms": 61.83916699956171
    },
    "error": null
}
```

A bus that isn't a connection point is rejected right away:

```sh
curl -s -X POST localhost:8080/connection-requests \
  -H 'Content-Type: application/json' \
  -d '{"grid_id": "kerber-landnetz-freileitung-1", "bus_id": 1, "p_kw": 20}'
```

```json
{"detail": "bus 1 is not a connection point of grid 'kerber-landnetz-freileitung-1'"}
```
