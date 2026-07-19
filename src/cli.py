"""Minimal CLI placeholder; later sessions add workflow commands."""

from __future__ import annotations

from .store import DEFAULT_DB_PATH, VaultStore


def main() -> int:
    store = VaultStore(DEFAULT_DB_PATH)
    store.close()
    print(f"Privilege vault ready: {DEFAULT_DB_PATH}")
    return 0
