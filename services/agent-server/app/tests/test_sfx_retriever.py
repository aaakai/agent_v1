from __future__ import annotations

from audio_runtime import MockSFXRetriever, SFXAsset, SFXAssetQuery, SFXEvent


def test_retrieve_door_knock_by_event() -> None:
    retriever = MockSFXRetriever()

    asset = retriever.retrieve(SFXAssetQuery(tags=[]), event="door_knock")

    assert asset.asset_id == "door_knock_001"


def test_retrieve_by_knock_tag() -> None:
    retriever = MockSFXRetriever()

    asset = retriever.retrieve({"tags": ["knock"]})

    assert asset.asset_id == "door_knock_001"


def test_duration_filter_limits_results() -> None:
    retriever = MockSFXRetriever()

    asset = retriever.retrieve(
        {"tags": ["knock"], "duration_ms": [1000, 1200]},
    )

    assert asset is None


def test_unknown_query_returns_none() -> None:
    retriever = MockSFXRetriever()

    assert retriever.retrieve({"tags": ["dragon"]}) is None


def test_add_asset_makes_it_retrievable() -> None:
    retriever = MockSFXRetriever()
    retriever.add_asset(
        SFXAsset(
            asset_id="bell_001",
            event="bell",
            path="mock://sfx/bell.wav",
            duration_ms=700,
            tags=["bell"],
        )
    )

    assert retriever.retrieve({"tags": ["bell"]}).asset_id == "bell_001"


def test_retrieve_for_event_uses_sfx_event() -> None:
    retriever = MockSFXRetriever()
    event = SFXEvent(
        event="door_knock",
        asset_query=SFXAssetQuery(tags=["door"], duration_ms=(300, 1200)),
    )

    assert retriever.retrieve_for_event(event).asset_id == "door_knock_001"
