"""Helpers for resolving runtime paths in source and frozen builds."""

from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    """Return the project root when running from a source checkout."""
    return Path(__file__).resolve().parent


def app_root() -> Path:
    """Return the active runtime root for source or frozen app execution."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return repo_root()


def resource_path(*parts: str) -> Path:
    """Resolve a resource relative to the active runtime root."""
    return app_root().joinpath(*parts)


def data_path(*parts: str) -> Path:
    """Resolve a path within the bundled data directory."""
    return resource_path("data", *parts)


def assets_images_path(*parts: str) -> Path:
    """Resolve a path within the bundled image assets directory."""
    return resource_path("assets", "images", *parts)
