from __future__ import annotations

import asyncio
import os
import time

from config_io import AppSettings
from monitors import MonitorConfig, StateStore, SystemMonitors, Thresholds
from prowl_client import ProwlClient, ProwlConfig


class MonitorService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._stop = asyncio.Event()

    async def run(self) -> None:
        if not self.settings.api_key:
            raise RuntimeError("Prowl API key not set.")

        client = ProwlClient(
            ProwlConfig(
                api_key=self.settings.api_key,
                application=self.settings.application,
                device=self.settings.device,
            )
        )

        state = StateStore(os.path.join("data", "state.json"))
        monitor_config = MonitorConfig(
            cooldown_seconds=self.settings.cooldown_seconds,
            thresholds=Thresholds(
                battery_percent=self.settings.battery_threshold_percent,
                cpu_percent=self.settings.cpu_threshold_percent,
                memory_percent=self.settings.memory_threshold_percent,
                disk_percent=self.settings.disk_threshold_percent,
            ),
            port_cooldown_seconds=self.settings.ports_cooldown_seconds,
        )
        monitors = SystemMonitors(monitor_config, state)

        last_port_check = 0.0

        while not self._stop.is_set():
            try:
                if self.settings.battery_low:
                    msg = monitors.check_battery_low()
                    if msg:
                        client.send("Battery Low", msg, priority=1)

                if self.settings.power_change:
                    msg = monitors.check_power_change()
                    if msg:
                        client.send("Power Status", msg)

                if self.settings.cpu_high:
                    msg = monitors.check_cpu_high()
                    if msg:
                        client.send("CPU High", msg)

                if self.settings.memory_high:
                    msg = monitors.check_memory_high()
                    if msg:
                        client.send("Memory High", msg)

                if self.settings.disk_low:
                    msg = monitors.check_disk_low("C:\\")
                    if msg:
                        client.send("Disk Low", msg, priority=1)

                if self.settings.network_change:
                    msg = monitors.check_network_change()
                    if msg:
                        client.send("Network Status", msg)

                if self.settings.ports_monitor:
                    now = time.time()
                    if (now - last_port_check) >= self.settings.ports_poll_interval_seconds:
                        last_port_check = now
                        ports_filter = self.settings.ports_list or None
                        for msg in monitors.check_port_changes(ports_filter):
                            client.send("Port Change", msg)

                state.save()
            except Exception as exc:
                print(f"Error in monitor loop: {exc}")

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.settings.poll_interval_seconds)
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        self._stop.set()
