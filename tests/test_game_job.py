from src.game_job import PlayerAsset, moderation_queue


def test_only_queued_assets_enter_moderation_queue():
    assets = [
        PlayerAsset("asset-204", "player-17", "skin", "queued"),
        PlayerAsset("asset-205", "player-18", "banner", "approved"),
    ]

    assert [asset.asset_id for asset in moderation_queue(assets)] == ["asset-204"]
