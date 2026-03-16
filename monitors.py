from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import psutil


@dataclass
class Thresholds:
    battery_percent: int
    cpu_percent: int
    memory_percent: int
    disk_percent: int


@dataclass
class MonitorConfig:
    cooldown_seconds: int
    thresholds: Thresholds
    port_cooldown_seconds: int


class StateStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self.state: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self.state = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.state = json.load(f)
        except (json.JSONDecodeError, OSError):
            self.state = {}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, sort_keys=True)

    def last_triggered(self, key: str) -> float:
        value = self.state.get(key, 0.0)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def set_triggered(self, key: str, timestamp: float) -> None:
        self.state[key] = timestamp

    def get_value(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set_value(self, key: str, value: Any) -> None:
        self.state[key] = value


class SystemMonitors:
    def __init__(self, config: MonitorConfig, state: StateStore) -> None:
        self.config = config
        self.state = state

    def _can_notify(self, key: str, now: float, cooldown: Optional[int] = None) -> bool:
        last = self.state.last_triggered(key)
        cooldown_seconds = cooldown if cooldown is not None else self.config.cooldown_seconds
        return (now - last) >= cooldown_seconds

    def check_battery_low(self) -> Optional[str]:
        battery = psutil.sensors_battery()
        if battery is None:
            return None

        if battery.power_plugged:
            return None

        if battery.percent > self.config.thresholds.battery_percent:
            return None

        now = time.time()
        if not self._can_notify("battery_low", now):
            return None

        self.state.set_triggered("battery_low", now)
        return f"Battery is at {battery.percent:.0f}%. Plug in soon."

    def check_power_change(self) -> Optional[str]:
        battery = psutil.sensors_battery()
        if battery is None:
            return None

        current = bool(battery.power_plugged)
        last = self.state.get_value("power_plugged")
        if last is None:
            self.state.set_value("power_plugged", current)
            return None

        if current == last:
            return None

        now = time.time()
        if not self._can_notify("power_change", now):
            return None

        self.state.set_triggered("power_change", now)
        self.state.set_value("power_plugged", current)
        return "Power adapter connected." if current else "Power adapter disconnected."

    def check_cpu_high(self) -> Optional[str]:
        cpu = psutil.cpu_percent(interval=1)
        if cpu < self.config.thresholds.cpu_percent:
            return None

        now = time.time()
        if not self._can_notify("cpu_high", now):
            return None

        self.state.set_triggered("cpu_high", now)
        return f"CPU usage is {cpu:.0f}%."

    def check_memory_high(self) -> Optional[str]:
        memory = psutil.virtual_memory()
        if memory.percent < self.config.thresholds.memory_percent:
            return None

        now = time.time()
        if not self._can_notify("memory_high", now):
            return None

        self.state.set_triggered("memory_high", now)
        return f"Memory usage is {memory.percent:.0f}%."

    def check_disk_low(self, path: str = "C:\\") -> Optional[str]:
        disk = psutil.disk_usage(path)
        free_percent = 100 - disk.percent
        if free_percent > self.config.thresholds.disk_percent:
            return None

        now = time.time()
        if not self._can_notify("disk_low", now):
            return None

        self.state.set_triggered("disk_low", now)
        return f"Disk free space is {free_percent:.0f}% on {path}."

    def check_network_change(self) -> Optional[str]:
        stats = psutil.net_if_stats()
        up = False
        for name, info in stats.items():
            if name.lower().startswith("loopback"):
                continue
            if info.isup:
                up = True
                break

        last = self.state.get_value("network_up")
        if last is None:
            self.state.set_value("network_up", up)
            return None

        if up == last:
            return None

        now = time.time()
        if not self._can_notify("network_change", now):
            return None

        self.state.set_triggered("network_change", now)
        self.state.set_value("network_up", up)
        return "Network connectivity restored." if up else "Network connectivity lost."

    def check_port_changes(self, ports_filter: Optional[Iterable[int]] = None) -> List[str]:
        try:
            connections = psutil.net_connections(kind="inet")
        except Exception:
            return []

        current: Set[Tuple[str, int]] = set()
        for conn in connections:
            if conn.status != psutil.CONN_LISTEN:
                continue
            if not conn.laddr:
                continue
            port = int(conn.laddr.port)
            if ports_filter is not None and port not in ports_filter:
                continue
            current.add(("tcp", port))

        last_ports = self.state.get_value("listening_ports", [])
        try:
            last_set = {(p[0], int(p[1])) for p in last_ports}
        except Exception:
            last_set = set()

        opened = current - last_set
        closed = last_set - current

        if opened or closed:
            self.state.set_value("listening_ports", [(p, port) for p, port in current])

        now = time.time()
        messages: List[str] = []
        if opened and self._can_notify("ports_open", now, cooldown=self.config.port_cooldown_seconds):
            self.state.set_triggered("ports_open", now)
            ports_text = ", ".join([f"{proto.upper()} {port}" for proto, port in sorted(opened)])
            messages.append(f"Ports opened: {ports_text}.")

        if closed and self._can_notify("ports_closed", now, cooldown=self.config.port_cooldown_seconds):
            self.state.set_triggered("ports_closed", now)
            ports_text = ", ".join([f"{proto.upper()} {port}" for proto, port in sorted(closed)])
            messages.append(f"Ports closed: {ports_text}.")

        return messages
