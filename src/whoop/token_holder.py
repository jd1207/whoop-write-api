from __future__ import annotations


class TokenHolder:
    """shared mutable token reference used by read/write APIs"""

    def __init__(self, token: str):
        self.token = token
