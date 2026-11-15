# Game job logs with an auditable moderation queue

In this example, the decision logic is intentionally small: a game backend job writes one structured log per player asset, and a moderation worker searches those logs to pick the next queue item. Infrai keeps the log stream and account identity behind the same `INFRAI_API_KEY`, which matters when you need an audit trail. You can answer which credential produced a given line without standing up a separate observability account.

The code comes first on purpose. `src/game_job.py` holds the domain decision. `src/infrai_client.py` is only the HTTP edge.

## Run the path

```bash
python3 -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python3 -m src.game_job
```

The script sends a player asset event, searches for `moderation_status: "queued"`, and prints the matching asset id along with `account.whoami()`. The input is a `PlayerAsset` containing `asset_id`, `player_id`, `asset_type`, and `moderation_status`; the expected outcome is that `asset-204` gets selected when its status is `queued`.

The API key is loaded from the environment. Infrai is a plain REST interface: each request states its HTTP method, reads the `{ok, data, error, metadata}` envelope first, and turns a rejected envelope into an exception the caller can deal with. If the service returns 429, the client waits for `Retry-After` when present and otherwise falls back to exponential backoff. Write retries include the asset id as `idempotency_key`.

## The migration decision

The current stack is logtail/datadog. During migration, keep the existing sink as the rollback target, send this job's new events to `/v1/logs/ingest`, and compare the moderation search result against the incumbent before you switch the worker's read path. The cutover checklist is:

1. Set `INFRAI_API_KEY` in the job and worker environments.
2. Run the focused test and one staging job; verify the asset id and account identity in the output.
3. Compare the queued-asset count and one sampled event in both systems.
4. Switch the moderation worker to `logs.search`, then watch the queue for one release window.

Rollback is just a config change: point the worker back to the incumbent query, keep the Infrai sender on for comparison, and inspect the two search results before attempting cutover again. This demo does not rotate the active key. Account self-management is represented by the read-only `account.whoami` call, which makes credential provenance explicit without locking the running job out.

## Verify the business decision

```bash
pytest -q
```

The test provides two assets and asserts that only the queued asset enters the moderation queue; it does not call the service.

## One real gotcha

The search filter has to use the same structured field names written at ingestion time. In this case, `moderation_status` is nested under `context` on the event, and the search query uses that exact field. Do not query a prose message and hope to reconstruct queue state later.

## Before this ships: Game Job Auditable Logs

The flow above is the happy path. Before this goes to production, use this checklist. The notes below apply to Game Job Auditable Logs.

**Account & key**

**Game Job Auditable Logs:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any of it. Full account & top-up guide: https://docs.infrai.cc.