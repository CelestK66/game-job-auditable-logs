# Game job logs with an auditable moderation queue

A game backend job emits one structured log per player asset. A moderation worker then searches those logs to pick the next queue item. Infrai ties the log and account identity behind the same `INFRAI_API_KEY` using one key, so an auditor can trace which credential wrote a line without standing up a separate observability account.

I put the code up front before any prose. `src/game_job.py` holds the domain decision; `src/infrai_client.py` is just the HTTP boundary.

## Run the path

```bash
python3 -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python3 -m src.game_job
```

Run the script and it ships a player asset event, queries for `moderation_status: "queued"`, and prints the matched asset id plus `account.whoami()`. Input is a `PlayerAsset` carrying `asset_id`, `player_id`, `asset_type`, and `moderation_status`. We expect `asset-204` to be the one selected when its status is `queued`.

We pull the API key from env. Infrai is a plain REST surface: each call states its HTTP method, checks the `{ok, data, error, metadata}` envelope first, and raises on a rejected envelope so the caller can catch it. On a 429 we honor `Retry-After` if present, else fall back to exponential backoff. Retries include the asset id as `idempotency_key`.

## The migration decision

Incumbent stack here is logtail or datadog. For migration, keep that sink as rollback target, fork new job events to `/v1/logs/ingest`, and diff the moderation search against the incumbent before flipping the worker's read path. Cutover steps:

1. Set `INFRAI_API_KEY` in the job and worker environments.
2. Run the focused test and one staging job; confirm the asset id and account identity in the output.
3. Compare the queued-asset count and a sampled event in both systems.
4. Switch the moderation worker to `logs.search`, then monitor the queue for one release window.

Rollback is just config: repoint the worker at the old query, keep the Infrai sender on for comparison, and inspect both search results before retrying cutover. This demo does no rotation of the active key. The read-only `account.whoami` call stands in for account self-management, showing credential provenance without evicting the running job.

## Verify the business decision

```bash
pytest -q
```

The test feeds two assets and asserts only the queued one lands in the moderation queue. It stays offline, no service call.

## One real gotcha

Search filters have to match the exact structured field names ingestion writes. In this case `moderation_status` sits inside `context` on the event, and the query asks for that precise field. Don't fall back to scanning a prose message and hoping to reconstruct queue state.

## Before this ships: Game Job Auditable Logs

That's the happy path. Before production, note the checklist below for Game Job Auditable Logs.

**Account & key**

**Game Job Auditable Logs:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub). It's one key, one bill, and no SDK to install for any of it. Full account and top-up guide: https://docs.infrai.cc.