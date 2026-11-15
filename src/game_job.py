"""Emit and search a moderation event from a game backend job."""
from dataclasses import asdict, dataclass
from typing import Any

from .infrai_client import InfraiClient


@dataclass(frozen=True)
class PlayerAsset:
    asset_id: str
    player_id: str
    asset_type: str
    moderation_status: str


def moderation_queue(assets: list[PlayerAsset]) -> list[PlayerAsset]:
    """Choose the assets that need human review next."""
    return [asset for asset in assets if asset.moderation_status == "queued"]


def publish_asset(client: InfraiClient, asset: PlayerAsset) -> dict[str, Any]:
    event = {
        "message": "player asset moderation state",
        "level": "info",
        "context": asdict(asset),
        "idempotency_key": asset.asset_id,
    }
    return client.ingest_log(event)


def run_job(client: InfraiClient, assets: list[PlayerAsset]) -> dict[str, Any]:
    for asset in assets:
        publish_asset(client, asset)
    queued = client.search_logs('moderation_status:"queued"')
    identity = client.whoami()
    return {"queued": queued, "identity": identity}


if __name__ == "__main__":
    assets = [PlayerAsset("asset-204", "player-17", "skin", "queued")]
    result = run_job(InfraiClient(), assets)
    print(result)
