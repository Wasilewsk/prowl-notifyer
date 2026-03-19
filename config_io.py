from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List


def _config_dir() -> str:
    base = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(base, "prowl-notifyer-config")


CONFIG_DIR = _config_dir()
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.toml")


@dataclass
class AppSettings:
    api_key: str
    application: str
    device: str
    poll_interval_seconds: int
    cooldown_seconds: int
    battery_low: bool
    battery_threshold_percent: int
    cpu_high: bool
    cpu_threshold_percent: int
    memory_high: bool
    memory_threshold_percent: int
    disk_low: bool
    disk_threshold_percent: int
    power_change: bool
    network_change: bool
    ports_monitor: bool
    ports_list: List[int]
    ports_poll_interval_seconds: int
    ports_cooldown_seconds: int
    file_watch_enabled: bool
    file_watch_paths: List[str]
    file_watch_poll_interval_seconds: int
    start_in_tray: bool
    start_monitoring_on_launch: bool
    auto_check_updates: bool


DEFAULTS = AppSettings(
    api_key="",
    application="Windows Prowl Agent",
    device="",
    poll_interval_seconds=30,
    cooldown_seconds=600,
    battery_low=True,
    battery_threshold_percent=20,
    cpu_high=True,
    cpu_threshold_percent=90,
    memory_high=True,
    memory_threshold_percent=90,
    disk_low=True,
    disk_threshold_percent=10,
    power_change=True,
    network_change=True,
    ports_monitor=False,
    ports_list=[],
    ports_poll_interval_seconds=15,
    ports_cooldown_seconds=60,
    file_watch_enabled=False,
    file_watch_paths=[],
    file_watch_poll_interval_seconds=30,
    start_in_tray=True,
    start_monitoring_on_launch=True,
    auto_check_updates=True,
)


def _load_toml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib  # type: ignore[import-not-found]

    with open(path, "rb") as f:
        return tomllib.load(f)


def config_exists() -> bool:
    return os.path.exists(CONFIG_PATH)


def _parse_ports(value: Any) -> List[int]:
    if value is None:
        return []
    if isinstance(value, list):
        ports = []
        for item in value:
            try:
                ports.append(int(item))
            except (TypeError, ValueError):
                continue
        return ports
    if isinstance(value, str):
        ports = []
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ports.append(int(part))
            except ValueError:
                continue
        return ports
    return []


def load_settings() -> AppSettings:
    data = _load_toml(CONFIG_PATH)
    prowl_data = data.get("prowl", {})
    general = data.get("general", {})
    events = data.get("events", {})
    features = data.get("features", {})
    ports = data.get("ports", {})
    files = data.get("files", {})
    ui = data.get("ui", {})

    return AppSettings(
        api_key=str(prowl_data.get("api_key", DEFAULTS.api_key)),
        application=str(prowl_data.get("application", DEFAULTS.application)),
        device=str(general.get("device", DEFAULTS.device)),
        poll_interval_seconds=int(general.get("poll_interval_seconds", DEFAULTS.poll_interval_seconds)),
        cooldown_seconds=int(general.get("cooldown_seconds", DEFAULTS.cooldown_seconds)),
        battery_low=bool(events.get("battery_low", DEFAULTS.battery_low)),
        battery_threshold_percent=int(
            events.get("battery_threshold_percent", DEFAULTS.battery_threshold_percent)
        ),
        cpu_high=bool(events.get("cpu_high", DEFAULTS.cpu_high)),
        cpu_threshold_percent=int(events.get("cpu_threshold_percent", DEFAULTS.cpu_threshold_percent)),
        memory_high=bool(events.get("memory_high", DEFAULTS.memory_high)),
        memory_threshold_percent=int(
            events.get("memory_threshold_percent", DEFAULTS.memory_threshold_percent)
        ),
        disk_low=bool(events.get("disk_low", DEFAULTS.disk_low)),
        disk_threshold_percent=int(events.get("disk_threshold_percent", DEFAULTS.disk_threshold_percent)),
        power_change=bool(features.get("power_change", DEFAULTS.power_change)),
        network_change=bool(features.get("network_change", DEFAULTS.network_change)),
        ports_monitor=bool(ports.get("monitor", DEFAULTS.ports_monitor)),
        ports_list=_parse_ports(ports.get("ports", DEFAULTS.ports_list)),
        ports_poll_interval_seconds=int(
            ports.get("poll_interval_seconds", DEFAULTS.ports_poll_interval_seconds)
        ),
        ports_cooldown_seconds=int(ports.get("cooldown_seconds", DEFAULTS.ports_cooldown_seconds)),
        file_watch_enabled=bool(files.get("enabled", DEFAULTS.file_watch_enabled)),
        file_watch_paths=list(files.get("paths", DEFAULTS.file_watch_paths)),
        file_watch_poll_interval_seconds=int(
            files.get("poll_interval_seconds", DEFAULTS.file_watch_poll_interval_seconds)
        ),
        start_in_tray=bool(ui.get("start_in_tray", DEFAULTS.start_in_tray)),
        start_monitoring_on_launch=bool(
            ui.get("start_monitoring_on_launch", DEFAULTS.start_monitoring_on_launch)
        ),
        auto_check_updates=bool(ui.get("auto_check_updates", DEFAULTS.auto_check_updates)),
    )


def save_settings(settings: AppSettings) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)

    lines = []
    lines.append("[prowl]")
    lines.append(f"api_key = \"{settings.api_key}\"")
    lines.append(f"application = \"{settings.application}\"")
    lines.append("")

    lines.append("[general]")
    lines.append(f"poll_interval_seconds = {settings.poll_interval_seconds}")
    lines.append(f"cooldown_seconds = {settings.cooldown_seconds}")
    lines.append("")
    lines.append(f"device = \"{settings.device}\"")
    lines.append("")

    lines.append("[events]")
    lines.append(f"battery_low = {str(settings.battery_low).lower()}")
    lines.append(f"battery_threshold_percent = {settings.battery_threshold_percent}")
    lines.append(f"cpu_high = {str(settings.cpu_high).lower()}")
    lines.append(f"cpu_threshold_percent = {settings.cpu_threshold_percent}")
    lines.append(f"memory_high = {str(settings.memory_high).lower()}")
    lines.append(f"memory_threshold_percent = {settings.memory_threshold_percent}")
    lines.append(f"disk_low = {str(settings.disk_low).lower()}")
    lines.append(f"disk_threshold_percent = {settings.disk_threshold_percent}")
    lines.append("")

    lines.append("[features]")
    lines.append(f"power_change = {str(settings.power_change).lower()}")
    lines.append(f"network_change = {str(settings.network_change).lower()}")
    lines.append("")

    lines.append("[ports]")
    lines.append(f"monitor = {str(settings.ports_monitor).lower()}")
    lines.append(f"poll_interval_seconds = {settings.ports_poll_interval_seconds}")
    lines.append(f"cooldown_seconds = {settings.ports_cooldown_seconds}")
    ports_list = ", ".join([str(p) for p in settings.ports_list])
    lines.append(f"ports = [{ports_list}]")
    lines.append("")

    lines.append("[files]")
    lines.append(f"enabled = {str(settings.file_watch_enabled).lower()}")
    lines.append(f"poll_interval_seconds = {settings.file_watch_poll_interval_seconds}")
    file_paths = ", ".join([f\"\\\"{p}\\\"\" for p in settings.file_watch_paths])
    lines.append(f"paths = [{file_paths}]")
    lines.append("")

    lines.append("[ui]")
    lines.append(f"start_in_tray = {str(settings.start_in_tray).lower()}")
    lines.append(
        f"start_monitoring_on_launch = {str(settings.start_monitoring_on_launch).lower()}"
    )
    lines.append(f"auto_check_updates = {str(settings.auto_check_updates).lower()}")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
