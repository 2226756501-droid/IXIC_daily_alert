from unittest.mock import patch, MagicMock

import requests

from modules.yahoo_client import fetch_chart
from modules.storage import (
    load_history, save_history,
    load_config, save_config, load_market_state, save_market_state,
    load_memory, save_memory,
)
from modules.types import Record


@patch("modules.yahoo_client.requests.get")
def test_fetch_yahoo_chart_success(mock_get) -> None:
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"chart": {"result": [{"meta": {"regularMarketPrice": 15000}}]}},
        raise_for_status=lambda: None,
    )
    result = fetch_chart("1d")
    assert result["chart"]["result"][0]["meta"]["regularMarketPrice"] == 15000


@patch("modules.yahoo_client.requests.get")
def test_fetch_yahoo_chart_network_error(mock_get) -> None:
    mock_get.side_effect = requests.ConnectionError("网络连接失败")
    result = fetch_chart("1d")
    assert result == {}


@patch("modules.yahoo_client.requests.get")
def test_fetch_yahoo_chart_http_error(mock_get) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP 404")
    mock_get.return_value = mock_response
    result = fetch_chart("1d")
    assert result == {}


def test_save_and_load_history(monkeypatch, tmp_path) -> None:
    temp_file = tmp_path / "history.csv"
    monkeypatch.setattr("modules.storage.HISTORY_FILE", str(temp_file))
    records = [Record("2026-06-14", 15000.0, 100.0, 0.67, 0.5, 15010.0, 15100.0, 14900.0, 123456789.0, "2026-06-14 12:00 UTC")]
    save_history(records)
    loaded = load_history()
    assert len(loaded) == 1
    assert loaded[0].date == "2026-06-14"
    assert loaded[0].close == 15000.0


def test_load_history_missing(monkeypatch) -> None:
    monkeypatch.setattr("modules.storage.HISTORY_FILE", "nonexistent.csv")
    assert load_history() == []


def test_load_config_default(monkeypatch) -> None:
    monkeypatch.setattr("modules.storage.CONFIG_FILE", "nonexistent.json")
    config = load_config()
    assert config["sensitivity_multiplier"] == 1.0


def test_save_and_load_config(monkeypatch, tmp_path) -> None:
    temp_file = tmp_path / "config.json"
    monkeypatch.setattr("modules.storage.CONFIG_FILE", str(temp_file))
    save_config({"sensitivity_multiplier": 2.5})
    loaded = load_config()
    assert loaded["sensitivity_multiplier"] == 2.5


def test_save_and_load_market_state(monkeypatch, tmp_path) -> None:
    temp_file = tmp_path / "state.json"
    monkeypatch.setattr("modules.storage.STATE_FILE", str(temp_file))
    save_market_state({"state": "abnormal", "consecutive_drops": 3})
    loaded = load_market_state()
    assert loaded["state"] == "abnormal"
    assert loaded["consecutive_drops"] == 3


def test_load_market_state_default(monkeypatch) -> None:
    monkeypatch.setattr("modules.storage.STATE_FILE", "nonexistent.json")
    state = load_market_state()
    assert state["state"] == "normal"
    assert state["consecutive_drops"] == 0


def test_save_and_load_memory(monkeypatch, tmp_path) -> None:
    temp_file = tmp_path / "memory.json"
    monkeypatch.setattr("modules.storage.MEMORY_FILE", str(temp_file))
    save_memory({"events": [{"id": 1}], "next_id": 2})
    loaded = load_memory()
    assert loaded["next_id"] == 2
    assert len(loaded["events"]) == 1
