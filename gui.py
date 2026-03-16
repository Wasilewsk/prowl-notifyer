from __future__ import annotations

import asyncio
import threading
from dataclasses import replace

import wx
import wx.adv

from config_io import AppSettings, DEFAULTS, load_settings, save_settings
from prowl_client import ProwlClient, ProwlConfig
from service import MonitorService


class ServiceRunner:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.service: MonitorService | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return

        def target() -> None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.service = MonitorService(self.settings)
            try:
                self.loop.run_until_complete(self.service.run())
            finally:
                self.loop.close()

        self.thread = threading.Thread(target=target, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.loop and self.service:
            self.loop.call_soon_threadsafe(self.service.stop)

    def is_running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()


class SettingsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, settings: AppSettings) -> None:
        super().__init__(parent, title="Settings", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.settings = settings

        sizer = wx.BoxSizer(wx.VERTICAL)
        notebook = wx.Notebook(self)

        self.page_prowl = self._build_prowl_page(notebook)
        self.page_events = self._build_events_page(notebook)
        self.page_features = self._build_features_page(notebook)
        self.page_ports = self._build_ports_page(notebook)
        self.page_ui = self._build_ui_page(notebook)

        notebook.AddPage(self.page_prowl, "Prowl")
        notebook.AddPage(self.page_events, "Events")
        notebook.AddPage(self.page_features, "Features")
        notebook.AddPage(self.page_ports, "Ports")
        notebook.AddPage(self.page_ui, "UI")

        sizer.Add(notebook, 1, wx.ALL | wx.EXPAND, 10)

        btn_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizerAndFit(sizer)

    def _build_prowl_page(self, parent: wx.Window) -> wx.Panel:
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        api_label = wx.StaticText(panel, label="&API key")
        self.api_key_ctrl = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self.api_key_ctrl.SetValue(self.settings.api_key)
        grid.Add(api_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.api_key_ctrl, 1, wx.EXPAND)

        app_label = wx.StaticText(panel, label="&Application name")
        self.app_ctrl = wx.TextCtrl(panel)
        self.app_ctrl.SetValue(self.settings.application)
        grid.Add(app_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.app_ctrl, 1, wx.EXPAND)

        device_label = wx.StaticText(panel, label="&Device (optional)")
        self.device_ctrl = wx.TextCtrl(panel)
        self.device_ctrl.SetValue(self.settings.device)
        grid.Add(device_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.device_ctrl, 1, wx.EXPAND)

        sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 10)

        test_btn = wx.Button(panel, label="Send &Test Notification")
        test_btn.Bind(wx.EVT_BUTTON, self.on_test)
        sizer.Add(test_btn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        return panel

    def _build_events_page(self, parent: wx.Window) -> wx.Panel:
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(0, 3, 8, 8)
        grid.AddGrowableCol(2, 1)

        self.battery_check = wx.CheckBox(panel, label="&Battery low")
        self.battery_check.SetValue(self.settings.battery_low)
        self.battery_spin = wx.SpinCtrl(panel, min=1, max=100, initial=self.settings.battery_threshold_percent)
        grid.Add(self.battery_check, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="Threshold (%)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.battery_spin, 0)

        self.cpu_check = wx.CheckBox(panel, label="&CPU high")
        self.cpu_check.SetValue(self.settings.cpu_high)
        self.cpu_spin = wx.SpinCtrl(panel, min=1, max=100, initial=self.settings.cpu_threshold_percent)
        grid.Add(self.cpu_check, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="Threshold (%)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.cpu_spin, 0)

        self.memory_check = wx.CheckBox(panel, label="&Memory high")
        self.memory_check.SetValue(self.settings.memory_high)
        self.memory_spin = wx.SpinCtrl(panel, min=1, max=100, initial=self.settings.memory_threshold_percent)
        grid.Add(self.memory_check, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="Threshold (%)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.memory_spin, 0)

        self.disk_check = wx.CheckBox(panel, label="&Disk low")
        self.disk_check.SetValue(self.settings.disk_low)
        self.disk_spin = wx.SpinCtrl(panel, min=1, max=100, initial=self.settings.disk_threshold_percent)
        grid.Add(self.disk_check, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="Free space threshold (%)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.disk_spin, 0)

        sizer.Add(grid, 0, wx.ALL, 10)

        poll_sizer = wx.FlexGridSizer(0, 2, 8, 8)
        poll_sizer.AddGrowableCol(1, 1)

        poll_label = wx.StaticText(panel, label="Polling interval (seconds)")
        self.poll_ctrl = wx.SpinCtrl(panel, min=5, max=3600, initial=self.settings.poll_interval_seconds)
        poll_sizer.Add(poll_label, 0, wx.ALIGN_CENTER_VERTICAL)
        poll_sizer.Add(self.poll_ctrl, 0)

        cooldown_label = wx.StaticText(panel, label="Cooldown (seconds between alerts)")
        self.cooldown_ctrl = wx.SpinCtrl(panel, min=60, max=86400, initial=self.settings.cooldown_seconds)
        poll_sizer.Add(cooldown_label, 0, wx.ALIGN_CENTER_VERTICAL)
        poll_sizer.Add(self.cooldown_ctrl, 0)

        sizer.Add(poll_sizer, 0, wx.ALL, 10)
        panel.SetSizer(sizer)
        return panel

    def _build_features_page(self, parent: wx.Window) -> wx.Panel:
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.power_check = wx.CheckBox(panel, label="&Notify when power adapter is plugged/unplugged")
        self.power_check.SetValue(self.settings.power_change)
        sizer.Add(self.power_check, 0, wx.ALL, 10)

        self.network_check = wx.CheckBox(panel, label="&Notify when network connectivity changes")
        self.network_check.SetValue(self.settings.network_change)
        sizer.Add(self.network_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        return panel

    def _build_ports_page(self, parent: wx.Window) -> wx.Panel:
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.ports_enable_check = wx.CheckBox(panel, label="&Monitor ports opening/closing")
        self.ports_enable_check.SetValue(self.settings.ports_monitor)
        sizer.Add(self.ports_enable_check, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        ports_label = wx.StaticText(panel, label="Ports (comma-separated, empty = all)")
        self.ports_ctrl = wx.TextCtrl(panel)
        if self.settings.ports_list:
            self.ports_ctrl.SetValue(", ".join([str(p) for p in self.settings.ports_list]))
        grid.Add(ports_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.ports_ctrl, 1, wx.EXPAND)

        poll_label = wx.StaticText(panel, label="Port polling interval (seconds)")
        self.ports_poll_ctrl = wx.SpinCtrl(panel, min=5, max=3600, initial=self.settings.ports_poll_interval_seconds)
        grid.Add(poll_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.ports_poll_ctrl, 0)

        cooldown_label = wx.StaticText(panel, label="Port alert cooldown (seconds)")
        self.ports_cooldown_ctrl = wx.SpinCtrl(panel, min=30, max=86400, initial=self.settings.ports_cooldown_seconds)
        grid.Add(cooldown_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.ports_cooldown_ctrl, 0)

        sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 10)
        panel.SetSizer(sizer)
        return panel

    def _build_ui_page(self, parent: wx.Window) -> wx.Panel:
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.start_in_tray_check = wx.CheckBox(panel, label="&Start hidden in system tray")
        self.start_in_tray_check.SetValue(self.settings.start_in_tray)
        sizer.Add(self.start_in_tray_check, 0, wx.ALL, 10)

        self.start_monitoring_check = wx.CheckBox(panel, label="&Start monitoring on launch")
        self.start_monitoring_check.SetValue(self.settings.start_monitoring_on_launch)
        sizer.Add(self.start_monitoring_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        return panel

    def on_test(self, _event: wx.Event) -> None:
        api_key = self.api_key_ctrl.GetValue().strip()
        if not api_key:
            wx.MessageBox("Please enter your API key first.", "Missing API Key")
            return

        client = ProwlClient(ProwlConfig(api_key=api_key, application="Prowl Notifier Setup"))
        try:
            client.send("Test Notification", "Prowl notifier is working.")
            wx.MessageBox("Test notification sent.", "Success")
        except Exception as exc:
            wx.MessageBox(f"Failed to send test notification: {exc}", "Error")

    def get_settings(self) -> AppSettings:
        ports_list = []
        for part in self.ports_ctrl.GetValue().split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ports_list.append(int(part))
            except ValueError:
                continue

        return replace(
            DEFAULTS,
            api_key=self.api_key_ctrl.GetValue().strip(),
            application=self.app_ctrl.GetValue().strip() or DEFAULTS.application,
            device=self.device_ctrl.GetValue().strip(),
            poll_interval_seconds=int(self.poll_ctrl.GetValue()),
            cooldown_seconds=int(self.cooldown_ctrl.GetValue()),
            battery_low=self.battery_check.GetValue(),
            battery_threshold_percent=int(self.battery_spin.GetValue()),
            cpu_high=self.cpu_check.GetValue(),
            cpu_threshold_percent=int(self.cpu_spin.GetValue()),
            memory_high=self.memory_check.GetValue(),
            memory_threshold_percent=int(self.memory_spin.GetValue()),
            disk_low=self.disk_check.GetValue(),
            disk_threshold_percent=int(self.disk_spin.GetValue()),
            power_change=self.power_check.GetValue(),
            network_change=self.network_check.GetValue(),
            ports_monitor=self.ports_enable_check.GetValue(),
            ports_list=ports_list,
            ports_poll_interval_seconds=int(self.ports_poll_ctrl.GetValue()),
            ports_cooldown_seconds=int(self.ports_cooldown_ctrl.GetValue()),
            start_in_tray=self.start_in_tray_check.GetValue(),
            start_monitoring_on_launch=self.start_monitoring_check.GetValue(),
        )


class TrayIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame: "MainFrame") -> None:
        super().__init__()
        self.frame = frame
        icon = wx.ArtProvider.GetIcon(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))
        self.SetIcon(icon, "Prowl Notifier")
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.on_open)

    def CreatePopupMenu(self) -> wx.Menu:
        menu = wx.Menu()
        open_item = menu.Append(wx.ID_ANY, "Open")
        settings_item = menu.Append(wx.ID_ANY, "Settings")
        if self.frame.runner.is_running():
            toggle_item = menu.Append(wx.ID_ANY, "Stop Monitoring")
        else:
            toggle_item = menu.Append(wx.ID_ANY, "Start Monitoring")
        menu.AppendSeparator()
        exit_item = menu.Append(wx.ID_EXIT, "Exit")

        self.Bind(wx.EVT_MENU, self.on_open, open_item)
        self.Bind(wx.EVT_MENU, self.on_settings, settings_item)
        self.Bind(wx.EVT_MENU, self.on_toggle, toggle_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        return menu

    def on_open(self, _event: wx.Event) -> None:
        self.frame.show_window()

    def on_settings(self, _event: wx.Event) -> None:
        self.frame.open_settings()

    def on_toggle(self, _event: wx.Event) -> None:
        self.frame.toggle_monitoring()

    def on_exit(self, _event: wx.Event) -> None:
        self.frame.force_exit()


class MainFrame(wx.Frame):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__(None, title="Prowl Notifier", size=(540, 260))
        self.settings = settings
        self.runner = ServiceRunner(settings)
        self.tray = TrayIcon(self)
        self.force_quit = False

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Prowl Notifier")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL, 10)

        self.status = wx.StaticText(panel, label="Monitoring is stopped.")
        sizer.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.toggle_btn = wx.Button(panel, label="&Start Monitoring")
        self.toggle_btn.Bind(wx.EVT_BUTTON, self.on_toggle)
        btn_sizer.Add(self.toggle_btn, 0, wx.RIGHT, 8)

        settings_btn = wx.Button(panel, label="&Settings")
        settings_btn.Bind(wx.EVT_BUTTON, self.on_settings)
        btn_sizer.Add(settings_btn, 0, wx.RIGHT, 8)

        hide_btn = wx.Button(panel, label="&Hide to Tray")
        hide_btn.Bind(wx.EVT_BUTTON, self.on_hide)
        btn_sizer.Add(hide_btn, 0, wx.RIGHT, 8)

        exit_btn = wx.Button(panel, label="E&xit")
        exit_btn.Bind(wx.EVT_BUTTON, self.on_exit)
        btn_sizer.Add(exit_btn, 0)

        sizer.Add(btn_sizer, 0, wx.ALL, 10)
        panel.SetSizer(sizer)

        self.Bind(wx.EVT_CLOSE, self.on_close)

        if self.settings.start_monitoring_on_launch:
            self.runner.start()
            self.update_status()

        if self.settings.start_in_tray:
            self.Hide()

    def update_status(self) -> None:
        if self.runner.is_running():
            self.status.SetLabel("Monitoring is running.")
            self.toggle_btn.SetLabel("S&top Monitoring")
        else:
            self.status.SetLabel("Monitoring is stopped.")
            self.toggle_btn.SetLabel("&Start Monitoring")

    def toggle_monitoring(self) -> None:
        if self.runner.is_running():
            self.runner.stop()
        else:
            self.runner = ServiceRunner(self.settings)
            self.runner.start()
        self.update_status()

    def on_toggle(self, _event: wx.Event) -> None:
        self.toggle_monitoring()

    def on_settings(self, _event: wx.Event) -> None:
        self.open_settings()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self, self.settings)
        if dialog.ShowModal() == wx.ID_OK:
            self.settings = dialog.get_settings()
            save_settings(self.settings)

            was_running = self.runner.is_running()
            self.runner.stop()
            if was_running or self.settings.start_monitoring_on_launch:
                self.runner = ServiceRunner(self.settings)
                self.runner.start()
            self.update_status()
        dialog.Destroy()

    def on_hide(self, _event: wx.Event) -> None:
        self.Hide()

    def on_exit(self, _event: wx.Event) -> None:
        self.force_exit()

    def on_close(self, _event: wx.Event) -> None:
        if self.force_quit:
            self.runner.stop()
            self.tray.Destroy()
            self.Destroy()
            return
        self.Hide()

    def show_window(self) -> None:
        self.Show()
        self.Raise()

    def force_exit(self) -> None:
        self.force_quit = True
        self.Close()


class WelcomePage(wx.adv.WizardPageSimple):
    def __init__(self, parent: wx.adv.Wizard) -> None:
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Welcome to Prowl Notifier")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL, 10)

        body = (
            "This wizard will help you configure Prowl notifications for your Windows PC. "
            "You can choose which events to monitor."
        )
        sizer.Add(wx.StaticText(self, label=body), 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(sizer)


class ProwlPage(wx.adv.WizardPageSimple):
    def __init__(self, parent: wx.adv.Wizard) -> None:
        super().__init__(parent)
        settings = load_settings()
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Prowl Account")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        api_label = wx.StaticText(self, label="&API key")
        self.api_key_ctrl = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.api_key_ctrl.SetValue(settings.api_key)
        grid.Add(api_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.api_key_ctrl, 1, wx.EXPAND)

        app_label = wx.StaticText(self, label="&Application name")
        self.app_ctrl = wx.TextCtrl(self)
        self.app_ctrl.SetValue(settings.application)
        grid.Add(app_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.app_ctrl, 1, wx.EXPAND)

        device_label = wx.StaticText(self, label="&Device (optional)")
        self.device_ctrl = wx.TextCtrl(self)
        self.device_ctrl.SetValue(settings.device)
        grid.Add(device_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.device_ctrl, 1, wx.EXPAND)

        sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 10)

        test_btn = wx.Button(self, label="Send &Test Notification")
        test_btn.Bind(wx.EVT_BUTTON, self.on_test)
        sizer.Add(test_btn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(sizer)

    def on_test(self, _event: wx.Event) -> None:
        api_key = self.api_key_ctrl.GetValue().strip()
        if not api_key:
            wx.MessageBox("Please enter your API key first.", "Missing API Key")
            return

        client = ProwlClient(ProwlConfig(api_key=api_key, application="Prowl Notifier Setup"))
        try:
            client.send("Test Notification", "Prowl notifier is working.")
            wx.MessageBox("Test notification sent.", "Success")
        except Exception as exc:
            wx.MessageBox(f"Failed to send test notification: {exc}", "Error")


class EventsPage(wx.adv.WizardPageSimple):
    def __init__(self, parent: wx.adv.Wizard) -> None:
        super().__init__(parent)
        settings = load_settings()

        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.StaticText(self, label="System Events")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(0, 3, 8, 8)
        grid.AddGrowableCol(2, 1)

        self.battery_check = wx.CheckBox(self, label="&Battery low")
        self.battery_check.SetValue(settings.battery_low)
        self.battery_spin = wx.SpinCtrl(self, min=1, max=100, initial=settings.battery_threshold_percent)
        grid.Add(self.battery_check, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(self, label="Threshold (%)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.battery_spin, 0)

        self.cpu_check = wx.CheckBox(self, label="&CPU high")
        self.cpu_check.SetValue(settings.cpu_high)
        self.cpu_spin = wx.SpinCtrl(self, min=1, max=100, initial=settings.cpu_threshold_percent)
        grid.Add(self.cpu_check, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(self, label="Threshold (%)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.cpu_spin, 0)

        self.memory_check = wx.CheckBox(self, label="&Memory high")
        self.memory_check.SetValue(settings.memory_high)
        self.memory_spin = wx.SpinCtrl(self, min=1, max=100, initial=settings.memory_threshold_percent)
        grid.Add(self.memory_check, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(self, label="Threshold (%)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.memory_spin, 0)

        self.disk_check = wx.CheckBox(self, label="&Disk low")
        self.disk_check.SetValue(settings.disk_low)
        self.disk_spin = wx.SpinCtrl(self, min=1, max=100, initial=settings.disk_threshold_percent)
        grid.Add(self.disk_check, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(self, label="Free space threshold (%)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.disk_spin, 0)

        sizer.Add(grid, 0, wx.ALL, 10)

        poll_sizer = wx.FlexGridSizer(0, 2, 8, 8)
        poll_sizer.AddGrowableCol(1, 1)

        poll_label = wx.StaticText(self, label="Polling interval (seconds)")
        self.poll_ctrl = wx.SpinCtrl(self, min=5, max=3600, initial=settings.poll_interval_seconds)
        poll_sizer.Add(poll_label, 0, wx.ALIGN_CENTER_VERTICAL)
        poll_sizer.Add(self.poll_ctrl, 0)

        cooldown_label = wx.StaticText(self, label="Cooldown (seconds between alerts)")
        self.cooldown_ctrl = wx.SpinCtrl(self, min=60, max=86400, initial=settings.cooldown_seconds)
        poll_sizer.Add(cooldown_label, 0, wx.ALIGN_CENTER_VERTICAL)
        poll_sizer.Add(self.cooldown_ctrl, 0)

        sizer.Add(poll_sizer, 0, wx.ALL, 10)
        self.SetSizer(sizer)


class FinishPage(wx.adv.WizardPageSimple):
    def __init__(self, parent: wx.adv.Wizard) -> None:
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Finish")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL, 10)

        body = (
            "Click Finish to save your configuration. You can start monitoring immediately after finishing."
        )
        sizer.Add(wx.StaticText(self, label=body), 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.start_now = wx.CheckBox(self, label="&Start monitoring now")
        self.start_now.SetValue(True)
        sizer.Add(self.start_now, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(sizer)


class ProwlWizard(wx.adv.Wizard):
    def __init__(self, parent: wx.Window | None) -> None:
        super().__init__(parent, title="Prowl Notifier Setup")
        self.settings = load_settings()

        self.page_welcome = WelcomePage(self)
        self.page_prowl = ProwlPage(self)
        self.page_events = EventsPage(self)
        self.page_finish = FinishPage(self)

        wx.adv.WizardPageSimple.Chain(self.page_welcome, self.page_prowl)
        wx.adv.WizardPageSimple.Chain(self.page_prowl, self.page_events)
        wx.adv.WizardPageSimple.Chain(self.page_events, self.page_finish)

        self.Bind(wx.adv.EVT_WIZARD_PAGE_CHANGING, self.on_page_changing)
        self.Bind(wx.adv.EVT_WIZARD_FINISHED, self.on_finished)

    def on_page_changing(self, event: wx.adv.WizardEvent) -> None:
        if event.GetPage() == self.page_prowl and event.GetDirection():
            if not self.page_prowl.api_key_ctrl.GetValue().strip():
                wx.MessageBox("Please enter your Prowl API key to continue.", "Missing API Key")
                event.Veto()

    def on_finished(self, _event: wx.adv.WizardEvent) -> None:
        settings = replace(
            DEFAULTS,
            api_key=self.page_prowl.api_key_ctrl.GetValue().strip(),
            application=self.page_prowl.app_ctrl.GetValue().strip() or DEFAULTS.application,
            device=self.page_prowl.device_ctrl.GetValue().strip(),
            poll_interval_seconds=int(self.page_events.poll_ctrl.GetValue()),
            cooldown_seconds=int(self.page_events.cooldown_ctrl.GetValue()),
            battery_low=self.page_events.battery_check.GetValue(),
            battery_threshold_percent=int(self.page_events.battery_spin.GetValue()),
            cpu_high=self.page_events.cpu_check.GetValue(),
            cpu_threshold_percent=int(self.page_events.cpu_spin.GetValue()),
            memory_high=self.page_events.memory_check.GetValue(),
            memory_threshold_percent=int(self.page_events.memory_spin.GetValue()),
            disk_low=self.page_events.disk_check.GetValue(),
            disk_threshold_percent=int(self.page_events.disk_spin.GetValue()),
            start_monitoring_on_launch=self.page_finish.start_now.GetValue(),
        )

        save_settings(settings)
        frame = MainFrame(settings)
        frame.Show()


def run_app() -> None:
    app = wx.App(False)
    settings = load_settings()
    frame = MainFrame(settings)
    frame.Show()
    app.MainLoop()


def run_wizard() -> None:
    app = wx.App(False)
    wizard = ProwlWizard(None)
    wizard.RunWizard(wizard.page_welcome)
    wizard.Destroy()
    app.MainLoop()
