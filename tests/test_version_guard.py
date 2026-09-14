"""Tests for the CNX Home Assistant compatibility policy."""
from custom_components.cnx_smart_villa.version_guard import evaluate_version


def test_validated_stable_series_is_tested() -> None:
    info = evaluate_version(major=2026, minor=9, patch=2, version="2026.9.2")
    assert info.tested is True
    assert info.status == "tested"


def test_future_series_is_fail_open_but_unvalidated() -> None:
    info = evaluate_version(major=2026, minor=10, patch=0, version="2026.10.0")
    assert info.tested is False
    assert info.status == "untested_newer"


def test_development_build_is_never_production_validated() -> None:
    info = evaluate_version(
        major=2026,
        minor=9,
        patch="0b1",
        version="2026.9.0b1",
    )
    assert info.tested is False
    assert info.status == "development"


def test_older_than_minimum_is_unsupported() -> None:
    info = evaluate_version(major=2026, minor=8, patch=4, version="2026.8.4")
    assert info.tested is False
    assert info.status == "unsupported_older"
