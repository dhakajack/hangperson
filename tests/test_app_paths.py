from __future__ import annotations

from pathlib import Path

import app_paths


def test_repo_root_matches_project_root() -> None:
    assert app_paths.repo_root() == Path(__file__).resolve().parents[1]


def test_resource_path_uses_repo_root_when_not_frozen(monkeypatch) -> None:
    monkeypatch.delattr(app_paths.sys, "_MEIPASS", raising=False)

    path = app_paths.resource_path("data", "words_en.txt")

    assert path == app_paths.repo_root() / "data" / "words_en.txt"


def test_resource_path_uses_bundle_root_when_frozen(monkeypatch) -> None:
    monkeypatch.setattr(app_paths.sys, "_MEIPASS", "/tmp/hangperson-bundle", raising=False)

    path = app_paths.resource_path("assets", "images")

    assert path == Path("/tmp/hangperson-bundle") / "assets" / "images"
