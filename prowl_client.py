from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import requests

PROWL_ENDPOINT = "https://api.prowlapp.com/publicapi/add"


@dataclass
class ProwlConfig:
    api_key: str
    application: str = "Windows Prowl Agent"
    device: str = ""


class ProwlClient:
    def __init__(self, config: ProwlConfig, timeout_seconds: int = 10) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds

    def send(self, event: str, description: str, priority: int = 0) -> None:
        if not self.config.api_key:
            raise RuntimeError("Prowl API key is missing.")

        payload = {
            "apikey": self.config.api_key,
            "application": self.config.application,
            "event": event[:1000],
            "description": description[:10000],
            "priority": priority,
        }
        if self.config.device:
            payload["device"] = self.config.device

        response = requests.post(PROWL_ENDPOINT, data=payload, timeout=self.timeout_seconds)
        response.raise_for_status()


def resolve_api_key(config_value: str) -> str:
    env_key = os.getenv("PROWL_API_KEY", "").strip()
    return env_key or config_value


def backoff_sleep(base_seconds: float, attempt: int) -> None:
    time.sleep(min(base_seconds * (2 ** attempt), 30))
