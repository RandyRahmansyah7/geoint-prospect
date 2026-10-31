import pytest

from geoint_prospect.storage.keys import (
    InvalidObjectKey,
    manifest_key,
    processed_key,
    raw_key,
    safe_component,
    slug,
    tiles_key,
)


def test_key_layout_is_stable() -> None:
    assert raw_key("fixtures-observations", "0.1.0", "source.csv") == (
        "raw/fixtures-observations/0.1.0/source.csv"
    )
    assert processed_key("observations", "req-1", "out.parquet") == (
        "processed/observations/req-1/out.parquet"
    )
    assert manifest_key("req-1") == "manifests/req-1.json"
    assert tiles_key("jakarta", "2026-10-31") == "tiles/jakarta/2026-10-31.pmtiles"


def test_components_may_not_escape_their_namespace() -> None:
    for hostile in ["../etc", "a/b", "/abs", "..", "", "a" * 200, "a\nb", "a b"]:
        with pytest.raises(InvalidObjectKey):
            safe_component(hostile, field="source_id")


def test_slug_cleans_values_we_did_not_choose() -> None:
    assert slug("my file (final).csv") == "my_file__final_.csv"
    assert slug("../../etc/passwd") == "etc_passwd"
    assert slug("plain-name.csv") == "plain-name.csv"

    with pytest.raises(InvalidObjectKey):
        slug("///")


def test_keys_built_from_hostile_inputs_stay_inside_their_prefix() -> None:
    key = raw_key("fixtures-observations", "../0.1.0", "../../evil.csv")

    assert key.startswith("raw/fixtures-observations/")
    assert ".." not in key
