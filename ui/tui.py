#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui.tui - Modern Interactive Textual Terminal User Interface for Frida-Xtr
Asynchronous multi-device dashboard with reactive controls, real-time logging,
live-filtering package browser, process explorer, script inspector, and background auto-discovery.
"""

import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from core import (
    CODESHARE_PRESETS,
    DEFAULT_FRIDA_PORT,
    DeviceInfo,
    allocate_device_port,
    auto_connect_emulators,
    auto_connect_ldplayer,
    build_frida_command,
    check_architecture_compatibility,
    check_host_frida_environment,
    check_root_access,
    detect_devices,
    execute_rootavd,
    find_ramdisk_path,
    get_active_port_forwards,
    get_available_frida_server_files,
    get_device_architecture,
    get_device_properties,
    get_frida_server_architecture,
    get_frida_server_file_for_architecture,
    get_package_list,
    get_project_root,
    get_root_guidance,
    get_scripts_from_folder,
    invalidate_frida_server_cache,
    is_frida_server_running,
    launch_frida_session,
    load_port_mappings,
    remove_all_port_forwards,
    save_port_mappings,
    set_frida_server_cached_status,
    setup_frida_server,
    setup_port_forward,
    start_frida_server,
    stop_frida_server,
    test_frida_connection,
    view_device_processes,
)

TUI_CSS = """
Screen {
    background: #0d1117;
    color: #e6edf3;
}

Header {
    background: #161b22;
    color: #38bdf8;
    text-style: bold;
    border-bottom: solid #38bdf8;
    height: 1;
}

Footer {
    background: #161b22;
    color: #8b949e;
    height: 1;
}

#stats-banner {
    height: 1;
    background: #161b22;
    border-bottom: solid #21262d;
    padding: 0 1;
    content-align: center middle;
    text-style: bold;
}

#main-container {
    height: 1fr;
    layout: horizontal;
}

#sidebar {
    width: 32;
    background: #12161f;
    border-right: solid #21262d;
    padding: 0 1;
}

#sidebar-header-box {
    height: auto;
    padding: 0;
    border-bottom: solid #21262d;
    margin-bottom: 1;
}

#sidebar-title {
    text-align: center;
    color: #38bdf8;
    text-style: bold;
}

#sidebar-subtitle {
    text-align: center;
    color: #10b981;
    text-style: italic;
}

#device-list {
    height: 1fr;
    background: #12161f;
    border: none;
    margin-bottom: 1;
}

.device-item {
    padding: 0 1;
    background: #161b22;
    margin-bottom: 1;
    border-left: solid #30363d;
    height: auto;
}

.device-item:hover {
    background: #1f293d;
    border-left: solid #38bdf8;
}

/* Luminous Highlight & Color Overlay for Active Target Android/Emulator */
.device-item.active-target {
    background: #092c42;
    border-left: wide #10b981;
    border-right: solid #0284c7;
    border-top: solid #0284c7;
    border-bottom: solid #0284c7;
    color: #ffffff;
}

.device-item.active-target:hover {
    background: #0e3b57;
    border-left: wide #34d399;
}

#device-list:focus > .device-item.--highlight {
    background: #1e3a5f;
    border-left: wide #38bdf8;
}

.device-item.--highlight {
    background: #1e3a5f;
    border-left: wide #38bdf8;
}

.device-item.--highlight.active-target {
    background: #0b3e5f;
    border-left: wide #10b981;
    border-right: solid #38bdf8;
    border-top: solid #38bdf8;
    border-bottom: solid #38bdf8;
}

.sidebar-buttons {
    layout: vertical;
    margin-top: 1;
    height: auto;
}

Button {
    height: 1;
    min-height: 1;
    border: none;
    padding: 0 1;
    text-style: bold;
}

Button:hover {
    text-style: bold underline;
}

Button:focus {
    text-style: bold underline;
    border: none;
}

Button.-primary {
    background: #0284c7;
    color: #ffffff;
}

Button.-primary:hover {
    background: #0ea5e9;
}

Button.-success {
    background: #059669;
    color: #ffffff;
}

Button.-success:hover {
    background: #10b981;
}

Button.-warning {
    background: #d97706;
    color: #ffffff;
}

Button.-warning:hover {
    background: #f59e0b;
}

Button.-error {
    background: #dc2626;
    color: #ffffff;
}

Button.-error:hover {
    background: #ef4444;
}

Button.-default {
    background: #21262d;
    color: #c9d1d9;
}

Button.-default:hover {
    background: #30363d;
}

.sidebar-buttons Button {
    margin-bottom: 1;
    width: 100%;
    height: 1;
    min-height: 1;
    border: none;
    padding: 0 1;
}

#workspace {
    width: 1fr;
    background: #0d1117;
    padding: 0 1;
}

TabbedContent {
    height: 1fr;
}

TabPane {
    padding: 0 1;
    background: #11141c;
}

.section-card {
    background: #161b22;
    border: round #30363d;
    padding: 0 1;
    margin-bottom: 1;
}

#inject-layout {
    layout: horizontal;
    height: 1fr;
    margin: 0;
}

#inject-left-card {
    width: 48%;
    height: 1fr;
    margin-right: 1;
    scrollbar-size-vertical: 1;
}

#inject-right-card {
    width: 52%;
    height: 1fr;
}

.card-title {
    color: #38bdf8;
    text-style: bold;
    margin-bottom: 0;
}

.action-row {
    layout: horizontal;
    height: auto;
    margin: 1 0;
}

.action-row Button {
    margin-right: 1;
    height: 1;
    min-height: 1;
    border: none;
    padding: 0 1;
}

#preview-box {
    background: #090d13;
    border: round #21262d;
    padding: 0 1;
    margin-top: 1;
    margin-bottom: 1;
}

.preview-title {
    color: #c084fc;
    text-style: bold;
    margin-bottom: 0;
}

#command-preview-box {
    background: #090d13;
    border: round #38bdf8;
    padding: 0 1;
    margin-top: 1;
    margin-bottom: 1;
}

#log-container {
    height: 8;
    background: #12161f;
    border-top: solid #21262d;
    padding: 0 1;
}

#log-header {
    layout: horizontal;
    height: 1;
    padding: 0;
}

#log-header Button {
    height: 1;
    min-height: 1;
    border: none;
    padding: 0 1;
}

#log-title {
    color: #38bdf8;
    text-style: bold;
    width: 1fr;
}

#event-log {
    height: 6;
    background: #0a0d14;
    border: round #21262d;
    padding: 0 1;
}

.filter-input {
    margin-bottom: 0;
    border: solid #38bdf8;
    background: #161b22;
    height: 1;
    min-height: 1;
    padding: 0 1;
}

.filter-counter {
    color: #8b949e;
    text-align: right;
    margin: 0;
}

.select-dropdown {
    margin-bottom: 1;
    background: #161b22;
}

DataTable {
    background: #0d1117;
    border: round #30363d;
    height: 1fr;
}

.selected-target-card {
    background: #1c2128;
    border: solid #38bdf8;
    padding: 0 1;
    margin-bottom: 1;
}

/* Color Accents */
.badge-online {
    color: #10b981;
    text-style: bold;
}

.badge-offline {
    color: #f43f5e;
    text-style: bold;
}

.badge-root {
    color: #a855f7;
    text-style: bold;
}
"""


class FridaXTRApp(App):
    """Frida-Xtr Modern Terminal Dashboard with Multi-Emulator Auto-Discovery & Live Filtering."""

    TITLE = "Frida-XTr v2.0"
    SUB_TITLE = "Created By Anonre"
    CSS = TUI_CSS

    BINDINGS = [
        Binding("q", "quit_app", "Quit", priority=True),
        Binding("r", "refresh_devices", "Scan/Auto-Detect"),
        Binding("s", "start_frida_action", "Start Frida"),
        Binding("x", "stop_frida_action", "Stop Frida"),
        Binding("u", "setup_frida_action", "Setup Frida"),
        Binding("e", "launch_injection", "Execute Frida (e)"),
        Binding("d", "focus_dashboard_tab", "Dashboard"),
        Binding("p", "focus_process_tab", "Processes"),
        Binding("i", "focus_inject_tab", "Inject"),
        Binding("c", "focus_ports_tab", "Ports"),
        Binding("l", "clear_logs", "Clear Logs"),
    ]

    # Reactive Application State
    devices: reactive[List[DeviceInfo]] = reactive([])
    selected_device_id: reactive[Optional[str]] = reactive(None)
    selected_device_info: reactive[Optional[DeviceInfo]] = reactive(None)
    selected_package: reactive[str] = reactive("")
    is_busy: reactive[bool] = reactive(False)
    total_frida_online: reactive[int] = reactive(0)
    total_forwards: reactive[int] = reactive(0)

    # In-memory caches for instant search filtering and lag-free device switching
    _all_processes: List[Dict[str, Any]] = []
    _all_packages: List[Dict[str, str]] = []
    _device_processes: Dict[str, List[Dict[str, Any]]] = {}
    _device_packages: Dict[str, List[Dict[str, str]]] = {}
    _device_ports_cache: Dict[str, int] = {}
    _device_port_status_cache: Dict[str, str] = {}
    _adb_lock = threading.Lock()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # Top Metrics Status Banner (Sleek 1-Line Status)
        yield Static(
            "⚡ [bold #10b981]MULTI-DEVICE MANAGER[/bold #10b981] │ "
            "📱 [bold #38bdf8]DEVICES:[/bold #38bdf8] 0 │ "
            "🔥 [bold #f59e0b]FRIDA:[/bold #f59e0b] 0 │ "
            "🔌 [bold #c084fc]FORWARDS:[/bold #c084fc] 0 │ "
            "🎯 [bold #fbbf24]TARGET:[/bold #fbbf24] None │ "
            "💻 [bold #10b981]ENGINE:[/bold #10b981] Ready",
            id="stats-banner",
        )

        with Container(id="main-container"):
            # Left Sidebar
            with Container(id="sidebar"):
                with Container(id="sidebar-header-box"):
                    yield Static("Frida-XTr", id="sidebar-title")
                    yield Static("Created By Anonre", id="sidebar-subtitle")

                yield ListView(
                    id="device-list"
                )

                with Vertical(classes="sidebar-buttons"):
                    yield Button("🔄 Auto-Scan (r)", id="btn-refresh", variant="primary")
                    yield Button("▶ Start Frida (s)", id="btn-sidebar-start", variant="success")
                    yield Button("⏹ Stop Frida (x)", id="btn-sidebar-stop", variant="warning")
                    yield Button("🛑 Stop All Daemons", id="btn-stop-all", variant="error")

            # Main Workspace Area
            with Container(id="workspace"):
                with TabbedContent(id="tabs"):
                    # Tab 1: Dashboard & Device Info
                    with TabPane("📊 Dashboard (d)", id="tab-dashboard"):
                        with VerticalScroll():
                            with Container(classes="section-card"):
                                yield Static("TARGET DEVICE SPECIFICATION", classes="card-title")
                                yield Static("Select a device from the left sidebar...", id="target-summary-text")

                            with Container(classes="section-card"):
                                yield Static("DEVICE & SERVER CONTROLS", classes="card-title")
                                with Horizontal(classes="action-row"):
                                    yield Button("📥 Setup Binary (u)", id="btn-setup", variant="warning")
                                    yield Button("▶ Start Server (s)", id="btn-start", variant="success")
                                    yield Button("⏹ Stop Server (x)", id="btn-stop", variant="error")
                                with Horizontal(classes="action-row"):
                                    yield Button("🛡️ Auto Root AVD", id="btn-autoroot", variant="primary")
                                    yield Button("🔍 Deep Status Probe", id="btn-status-check", variant="default")
                                    yield Button("💉 Jump to Inject (i)", id="btn-jump-inject", variant="default")

                    # Tab 2: Process Explorer with Live Search
                    with TabPane("🔍 Processes (p)", id="tab-processes"):
                        yield Static("Target: [dim]No device selected[/dim]", id="process-target-badge", classes="selected-target-card")
                        yield Input(
                            placeholder="🔍 Filter processes by name or PID (instant filter)...",
                            id="process-filter",
                            classes="filter-input",
                        )
                        yield Static("0 processes loaded", id="process-counter", classes="filter-counter")
                        with Horizontal(classes="action-row"):
                            yield Button("🔄 Refresh Processes", id="btn-load-processes", variant="primary")
                            yield Button("💉 Use Selected in Inject", id="btn-use-proc-inject", variant="success")
                        yield DataTable(id="process-table")

                    # Tab 3: Package Injector with Live Search & Script Inspector
                    with TabPane("💉 Inject Script (i)", id="tab-inject"):
                        with Horizontal(id="inject-layout"):
                            # Left Card: Script & Launch Configuration
                            with VerticalScroll(classes="section-card", id="inject-left-card"):
                                yield Static("SCRIPT CONFIGURATION", classes="card-title")
                                yield Label("Script Source Type:")
                                yield Select(
                                    [
                                        ("Local Script (.js in scripts/ folder)", "local"),
                                        ("Codeshare Preset (Bypass SSL / Root)", "codeshare"),
                                    ],
                                    id="script-source-select",
                                    value="local",
                                    classes="select-dropdown",
                                )
                                yield Label("Script Selection:")
                                yield Select([], id="script-item-select", classes="select-dropdown")

                                # Script Inspector Preview Card
                                with Container(id="preview-box"):
                                    yield Static("SCRIPT INSPECTOR & METADATA", classes="preview-title")
                                    yield Static("Loading script details...", id="script-preview-text")

                                yield Label("Execution Mode:")
                                yield Select(
                                    [
                                        ("Spawn (-f, fresh restart & early hook)", "spawn"),
                                        ("Attach (-n, attach to active process)", "attach"),
                                    ],
                                    id="mode-select",
                                    value="spawn",
                                    classes="select-dropdown",
                                )

                                # Generated Command Box
                                with Container(id="command-preview-box"):
                                    yield Static("COMMAND PREVIEW", classes="preview-title")
                                    yield Static("frida ...", id="command-preview-text")

                            # Right Card: Target Applications
                            with Vertical(classes="section-card", id="inject-right-card"):
                                yield Static("TARGET APPLICATIONS", classes="card-title")
                                yield Static("Target: [dim]No package selected[/dim]", id="selected-package-badge", classes="selected-target-card")
                                yield Input(
                                    placeholder="🔍 Filter applications by name or package (instant filter)...",
                                    id="package-filter",
                                    classes="filter-input",
                                )
                                yield Static("0 packages loaded", id="package-counter", classes="filter-counter")
                                with Horizontal(classes="action-row"):
                                    yield Button("📥 Load Applications", id="btn-load-packages", variant="primary")
                                    yield Button("🚀 Execute Frida (e)", id="btn-launch-inject", variant="success")
                                yield DataTable(id="package-table")

                    # Tab 4: Port Management
                    with TabPane("🔌 Port Management (c)", id="tab-ports"):
                        yield Static("Target: [dim]No device selected[/dim]", id="ports-target-badge", classes="selected-target-card")
                        with Horizontal(classes="action-row"):
                            yield Button("🔄 Refresh Mappings", id="btn-refresh-ports", variant="primary")
                            yield Button("🗑 Clear All Forwards", id="btn-clear-ports", variant="error")
                        yield DataTable(id="ports-table")

        # Bottom Log Viewer
        with Container(id="log-container"):
            with Horizontal(id="log-header"):
                yield Static("📜 ACTIVITY & AUDIT STREAM", id="log-title")
                yield Button("Clear (l)", id="btn-clear-logs", variant="default")
            yield RichLog(id="event-log", wrap=True, highlight=True, markup=True)

        yield Footer()

    def on_mount(self) -> None:
        """Initialize tables, populate dropdowns, and schedule background polling."""
        self.init_tables()
        self.populate_scripts_dropdown()
        self.log_message("[bold cyan][INIT][/bold cyan] Frida-XTr v2.0 active. Created By Anonre.")
        self.check_environment()
        self.action_refresh_devices()

        # Non-blocking background poller for seamless connection tracking (every 4 seconds)
        self.set_interval(4.0, self.background_status_poll)

    def init_tables(self) -> None:
        """Setup column headers for DataTables."""
        # Process Table
        pt = self.query_one("#process-table", DataTable)
        pt.cursor_type = "row"
        pt.add_columns("PID", "Process Identifier")

        # Package Table
        pkt = self.query_one("#package-table", DataTable)
        pkt.cursor_type = "row"
        pkt.add_columns("Application Label", "Package Identifier")

        # Ports Table
        port_tbl = self.query_one("#ports-table", DataTable)
        port_tbl.cursor_type = "row"
        port_tbl.add_columns("Device ID", "Local Host Port", "Device Port", "Status")

    def log_message(self, message: str) -> None:
        """Append timestamped message to the RichLog pane safely across threads."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[dim cyan][{timestamp}][/dim cyan] {message}"
        try:
            log_widget = self.query_one("#event-log", RichLog)
            self.app.call_from_thread(log_widget.write, formatted)
        except Exception:
            pass

    def update_stats_banner(self) -> None:
        """Refresh top statistics banner metrics."""
        dev_count = len(self.devices)
        active_frida = self.total_frida_online
        forwards = self.total_forwards
        target = self.selected_device_id or "None"
        target_extra = ""
        if self.selected_device_info:
            port = self.selected_device_info.port or allocate_device_port(self.selected_device_info.id)
            target_extra = f"(:{port})"

        try:
            banner = self.query_one("#stats-banner", Static)
            banner.update(
                f"⚡ [bold #10b981]MULTI-DEVICE MANAGER[/bold #10b981] │ "
                f"📱 [bold #38bdf8]DEV:[/bold #38bdf8] {dev_count} │ "
                f"🔥 [bold #f59e0b]FRIDA:[/bold #f59e0b] {active_frida} │ "
                f"🔌 [bold #c084fc]FORWARD:[/bold #c084fc] {forwards} │ "
                f"🎯 [bold #fbbf24]TARGET:[/bold #fbbf24] {target} {target_extra} │ "
                f"💻 [bold #10b981]ENGINE:[/bold #10b981] Ready"
            )
        except Exception:
            pass

    @work(thread=True)
    def check_environment(self) -> None:
        """Inspect host machine for frida and frida-ps CLI."""
        has_tools, has_lib, warn = check_host_frida_environment()
        if warn:
            self.log_message(f"[bold yellow][WARN][/bold yellow] {warn}")
        else:
            self.log_message("[bold green][READY][/bold green] Host environment ready: frida-tools CLI & Python library available.")

    @work(thread=True)
    def background_status_poll(self) -> None:
        """Non-blocking background polling to maintain up-to-date device and daemon state."""
        if not self._adb_lock.acquire(blocking=False):
            return
        try:
            # Auto-connect listening emulators and detect devices
            devs = detect_devices(hydrate_properties=False, auto_connect=True)
            active_frida = 0
            for d in devs:
                if is_frida_server_running(d.id, use_cache=False):
                    active_frida += 1

            forwards = len(get_active_port_forwards())
            self.app.call_from_thread(self._update_poll_state, devs, active_frida, forwards)
        except Exception:
            pass
        finally:
            self._adb_lock.release()

    def _update_poll_state(self, devs: List[DeviceInfo], active_frida: int, forwards: int) -> None:
        self.total_frida_online = active_frida
        self.total_forwards = forwards
        self.update_stats_banner()

        # Check if device topology changed
        old_ids = [d.id for d in self.devices]
        new_ids = [d.id for d in devs]
        if old_ids != new_ids:
            # Re-enumerate and hydrate properties when devices change
            self.action_refresh_devices()
        else:
            self._update_device_list_visuals()

    @work(thread=True)
    def action_refresh_devices(self) -> None:
        """Perform automated discovery of emulators and USB devices."""
        with self._adb_lock:
            try:
                self.log_message("[bold #38bdf8][ADB][/bold #38bdf8] Auto-scanning and detecting emulators/devices...")
                newly_connected = auto_connect_emulators()
                if newly_connected:
                    self.log_message(f"[bold green][CONNECT][/bold green] Successfully auto-connected emulators: {', '.join(newly_connected)}")

                devs = detect_devices(hydrate_properties=True, auto_connect=False)
                for d in devs:
                    is_frida_server_running(d.id, use_cache=False)
                self.app.call_from_thread(self._update_device_list, devs)
            except Exception as e:
                self.log_message(f"[bold red][ERROR][/bold red] Device scan failed: {e}")

    def _update_device_list(self, devs: List[DeviceInfo]) -> None:
        self.devices = devs
        device_list_view = self.query_one("#device-list", ListView)
        device_list_view.clear()

        online_count = 0
        if not devs:
            self.log_message("[yellow][ADB] No devices or emulators connected.[/yellow]")
            device_list_view.extend([ListItem(Static("[dim]No active devices[/dim]"), classes="device-item")])
            self.selected_device_id = None
            self.selected_device_info = None
            self.total_frida_online = 0
            self.update_stats_banner()
            self.update_dashboard()
            self.update_process_view()
            self.update_package_view()
            self.update_ports_view()
            self._render_ports_table_fast()
            return

        # Determine target device first
        target_dev = None
        if self.selected_device_id:
            target_dev = next((d for d in devs if d.id == self.selected_device_id), None)
        if not target_dev and devs:
            target_dev = devs[0]

        if target_dev:
            prev_id = self.selected_device_id
            self.selected_device_id = target_dev.id
            self.selected_device_info = target_dev
            if prev_id != target_dev.id:
                self.log_message(f"[bold cyan][DEVICE][/bold cyan] Active target: {target_dev.id} ({target_dev.device_label})")

        new_items: List[ListItem] = []
        for dev in devs:
            is_running = is_frida_server_running(dev.id, use_cache=True)
            if is_running:
                online_count += 1
            status_text = "[bold #10b981]● ONLINE[/bold #10b981]" if is_running else "[dim #f43f5e]○ OFFLINE[/dim #f43f5e]"
            root_text = "[bold #a855f7][ROOT][/bold #a855f7]" if dev.has_root else "[dim #64748b][USER][/dim #64748b]"
            port_text = f" [cyan]:{dev.port}[/cyan]" if dev.port else ""

            lbl = dev.model or dev.device_label
            if len(lbl) > 16:
                lbl = lbl[:15] + "…"

            is_active = (target_dev is not None and dev.id == target_dev.id)
            if is_active:
                item_text = (
                    f"[bold #38bdf8]▶ {dev.id}[/bold #38bdf8]{port_text}  {root_text}\n"
                    f"{status_text}  [bold #10b981]★ ACTIVE TARGET[/bold #10b981]"
                )
                item = ListItem(
                    Static(item_text),
                    classes="device-item active-target",
                )
            else:
                item_text = (
                    f"[bold white]{dev.id}[/bold white]{port_text}  {root_text}\n"
                    f"{status_text}  [dim]{lbl}[/dim]"
                )
                item = ListItem(
                    Static(item_text),
                    classes="device-item",
                )
            item.device_id = dev.id
            new_items.append(item)

        device_list_view.extend(new_items)
        self.total_frida_online = online_count
        self.update_stats_banner()

        if target_dev:
            try:
                target_idx = next((i for i, d in enumerate(devs) if d.id == target_dev.id), 0)
                device_list_view.index = target_idx
            except Exception:
                pass

        self.update_dashboard()
        self.update_process_view()
        self.update_package_view()
        self.update_ports_view()
        self._render_ports_table_fast()
        self.update_command_preview()
        self.action_refresh_ports()

    def _update_device_list_visuals(self) -> None:
        """
        Instantly refresh visual color overlay and badges for all device items in sidebar.
        Applies glowing emerald-cyan border framing and bold active badge to the selected emulator.
        """
        try:
            device_list_view = self.query_one("#device-list", ListView)
        except Exception:
            return

        for item in device_list_view.children:
            if not isinstance(item, ListItem):
                continue
            dev_id = getattr(item, "device_id", None)
            if not dev_id:
                continue

            matched = next((d for d in self.devices if d.id == dev_id), None)
            is_active = (dev_id == self.selected_device_id)

            if is_active:
                item.add_class("active-target")
            else:
                item.remove_class("active-target")

            try:
                static_widget = item.query_one(Static)
                is_running = is_frida_server_running(dev_id, use_cache=True)
                status_text = "[bold #10b981]● ONLINE[/bold #10b981]" if is_running else "[dim #f43f5e]○ OFFLINE[/dim #f43f5e]"
                root_text = "[bold #a855f7][ROOT][/bold #a855f7]" if (matched and matched.has_root) else "[dim #64748b][USER][/dim #64748b]"
                port = matched.port if matched else None
                port_text = f" [cyan]:{port}[/cyan]" if port else ""

                lbl = (matched.model or matched.device_label) if matched else dev_id
                if len(lbl) > 16:
                    lbl = lbl[:15] + "…"

                if is_active:
                    item_text = (
                        f"[bold #38bdf8]▶ {dev_id}[/bold #38bdf8]{port_text}  {root_text}\n"
                        f"{status_text}  [bold #10b981]★ ACTIVE TARGET[/bold #10b981]"
                    )
                else:
                    item_text = (
                        f"[bold white]{dev_id}[/bold white]{port_text}  {root_text}\n"
                        f"{status_text}  [dim]{lbl}[/dim]"
                    )
                static_widget.update(item_text)
            except Exception:
                pass

    def _render_ports_table_fast(self) -> None:
        """
        Instant in-memory rendering of the port forwardings table.
        Highlights the selected active device with zero network delays.
        """
        try:
            tbl = self.query_one("#ports-table", DataTable)
        except Exception:
            return

        combined: Dict[str, int] = dict(self._device_ports_cache)
        for d in self.devices:
            if d.id not in combined:
                port = d.port or allocate_device_port(d.id)
                combined[d.id] = port
                self._device_ports_cache[d.id] = port

        tbl.clear()
        for dev_id, port in combined.items():
            status = self._device_port_status_cache.get(dev_id)
            if not status:
                is_running = is_frida_server_running(dev_id, use_cache=True)
                status = "[bold yellow]● Running (Port Ready)[/bold yellow]" if is_running else "[dim #64748b]○ Standby / Ready[/dim #64748b]"

            is_active = (dev_id == self.selected_device_id)
            if is_active:
                dev_col = f"[bold white]{dev_id}[/bold white] [bold #10b981]★ ACTIVE TARGET[/bold #10b981]"
                port_col = f"[bold #38bdf8]{port}[/bold #38bdf8]"
            else:
                dev_col = f"[dim white]{dev_id}[/dim white]"
                port_col = f"[dim]{port}[/dim]"

            tbl.add_row(dev_col, port_col, "27042", status)

    def _get_or_select_device(self) -> Optional[DeviceInfo]:
        """
        Return the currently selected device, or auto-select the first device in self.devices.
        If no devices are connected, notifies the user and returns None.
        """
        if self.selected_device_info:
            return self.selected_device_info
        if self.devices:
            self.selected_device_info = self.devices[0]
            self.selected_device_id = self.devices[0].id
            self._update_device_list_visuals()
            self.update_stats_banner()
            self.update_dashboard()
            self.update_process_view()
            self.update_package_view()
            self.update_ports_view()
            self._render_ports_table_fast()
            self.update_command_preview()
            return self.selected_device_info
        self.notify("No active device found. Please connect or launch an emulator.", severity="warning")
        self.log_message("[yellow][WARN] No target device selected. Click [🔄 Auto-Scan (r)] or start an emulator.[/yellow]")
        return None

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle device selection from sidebar."""
        self._select_device_from_item(event.item)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle keyboard or cursor highlight in device list."""
        if event.item:
            self._select_device_from_item(event.item)

    def _select_device_from_item(self, item: ListItem) -> None:
        """Helper to switch active device focus cleanly and instantly across all tabs."""
        dev_id = getattr(item, "device_id", None) or getattr(item, "name", None)
        if not dev_id:
            return

        if dev_id == self.selected_device_id and self.selected_device_info is not None:
            self._update_device_list_visuals()
            return

        matched = next((d for d in self.devices if d.id == dev_id), None)
        if matched:
            prev_id = self.selected_device_id
            self.selected_device_id = matched.id
            self.selected_device_info = matched
            if prev_id != matched.id:
                self.log_message(f"[bold cyan][SELECT][/bold cyan] Switched active device to: {matched.id} ({matched.device_label})")

            # Instant UI updates with zero subprocess latency
            self._update_device_list_visuals()
            self.update_stats_banner()
            self.update_dashboard()
            self.update_process_view()
            self.update_package_view()
            self.update_ports_view()
            self._render_ports_table_fast()
            self.update_command_preview()

    def update_dashboard(self) -> None:
        """Update dashboard card with current device properties."""
        summary = self.query_one("#target-summary-text", Static)
        dev = self.selected_device_info or (self.devices[0] if self.devices else None)
        if not dev:
            summary.update("[dim yellow]No device selected. Connect an emulator or physical Android device.[/dim yellow]")
            return
        is_running = is_frida_server_running(dev.id, use_cache=True)
        status_badge = "[bold #10b981]ONLINE (Daemon Active)[/bold #10b981]" if is_running else "[bold #f43f5e]OFFLINE (Daemon Inactive)[/bold #f43f5e]"
        root_badge = "[bold #10b981]Rooted (su binary active)[/bold #10b981]" if dev.has_root else "[yellow]Unrooted (Normal User)[/yellow]"
        port = dev.port or allocate_device_port(dev.id)

        content = (
            f"• [bold #38bdf8]Device Identifier:[/bold #38bdf8] [bold white]{dev.id}[/bold white]\n"
            f"• [bold #38bdf8]Platform & Type:[/bold #38bdf8] {dev.device_label} ({dev.device_type})\n"
            f"• [bold #38bdf8]Model & Hardware:[/bold #38bdf8] {dev.model or 'Unknown'} / {dev.product or 'Unknown'}\n"
            f"• [bold #38bdf8]Architecture (ABI):[/bold #38bdf8] [bold yellow]{dev.abi or 'Unknown'}[/bold yellow]\n"
            f"• [bold #38bdf8]Android Version:[/bold #38bdf8] {dev.version or 'Unknown'} (SDK API {dev.api or '?'})\n"
            f"• [bold #38bdf8]Root Access:[/bold #38bdf8] {root_badge}\n"
            f"• [bold #38bdf8]Frida Daemon:[/bold #38bdf8] {status_badge}\n"
            f"• [bold #38bdf8]Port Forwarding:[/bold #38bdf8] [bold blue]localhost:{port}[/bold blue] ➔ [bold blue]device:27042[/bold blue]"
        )
        summary.update(content)

    def update_process_view(self) -> None:
        """Synchronize Process Explorer view with the currently selected device."""
        dev = self.selected_device_info or (self.devices[0] if self.devices else None)
        dev_id = dev.id if dev else "None"

        try:
            badge = self.query_one("#process-target-badge", Static)
            if dev:
                is_running = is_frida_server_running(dev.id, use_cache=True)
                status_badge = "[bold #10b981]ONLINE[/bold #10b981]" if is_running else "[dim #f43f5e]OFFLINE[/dim #f43f5e]"
                port = dev.port or allocate_device_port(dev.id)
                badge.update(
                    f"🎯 Target Device: [bold #38bdf8]{dev.id}[/bold #38bdf8] ({dev.device_label}) │ "
                    f"Port: [cyan]localhost:{port}[/cyan] │ "
                    f"Daemon: {status_badge}"
                )
            else:
                badge.update("🎯 Target Device: [dim yellow]No device selected[/dim yellow]")
        except Exception:
            pass

        # Clear process filter input when switching device
        try:
            filter_input = self.query_one("#process-filter", Input)
            filter_input.value = ""
        except Exception:
            pass

        # Render cached processes for this device or clear table
        if dev and dev.id in self._device_processes:
            self._all_processes = self._device_processes[dev.id]
            self._render_filtered_processes("")
        else:
            self._all_processes = []
            try:
                tbl = self.query_one("#process-table", DataTable)
                tbl.clear()
                counter = self.query_one("#process-counter", Static)
                counter.update(f"[dim]No processes cached for {dev_id}. Click [🔄 Refresh Processes] to load from this device.[/dim]")
            except Exception:
                pass

    def update_package_view(self) -> None:
        """Synchronize Application Package Injector with the currently selected device."""
        dev = self.selected_device_info or (self.devices[0] if self.devices else None)
        dev_id = dev.id if dev else "None"
        port = str(dev.port or allocate_device_port(dev_id)) if dev else "27042"

        try:
            badge = self.query_one("#selected-package-badge", Static)
            if self.selected_package:
                badge.update(
                    f"🎯 Target: [bold #38bdf8]{dev_id}[/bold #38bdf8] (: {port}) │ "
                    f"App: [bold #10b981]{self.selected_package}[/bold #10b981] ➔ [bold green]Ready! Press [e] / click 🚀 Execute Frida[/bold green]"
                )
            elif dev:
                badge.update(
                    f"🎯 Target: [bold #38bdf8]{dev_id}[/bold #38bdf8] (: {port}) │ "
                    f"[dim]No package selected (Pick from list below or enter manually)[/dim]"
                )
            else:
                badge.update("🎯 Target: [dim yellow]No device selected[/dim yellow]")
        except Exception:
            pass

        # Clear package filter input when switching device
        try:
            pkg_input = self.query_one("#package-filter", Input)
            pkg_input.value = ""
        except Exception:
            pass

        # Render cached packages for this device or clear table
        if dev and dev.id in self._device_packages:
            self._all_packages = self._device_packages[dev.id]
            self._render_filtered_packages("")
        else:
            self._all_packages = []
            try:
                tbl = self.query_one("#package-table", DataTable)
                tbl.clear()
                counter = self.query_one("#package-counter", Static)
                counter.update(f"[dim]No applications cached for {dev_id}. Click [📥 Load Applications] to load from this device.[/dim]")
            except Exception:
                pass

    def update_ports_view(self) -> None:
        """Synchronize Port Management badge with the currently selected device."""
        dev = self.selected_device_info or (self.devices[0] if self.devices else None)
        try:
            badge = self.query_one("#ports-target-badge", Static)
            if dev:
                port = dev.port or allocate_device_port(dev.id)
                is_running = is_frida_server_running(dev.id, use_cache=True)
                status_badge = "[bold #10b981]ONLINE[/bold #10b981]" if is_running else "[dim #f43f5e]OFFLINE[/dim #f43f5e]"
                badge.update(
                    f"🎯 Target Device: [bold #38bdf8]{dev.id}[/bold #38bdf8] │ "
                    f"Assigned Port: [bold blue]localhost:{port}[/bold blue] ➔ [bold blue]device:27042[/bold blue] │ "
                    f"Daemon: {status_badge}"
                )
            else:
                badge.update("🎯 Target Device: [dim yellow]No device selected[/dim yellow]")
        except Exception:
            pass

    def populate_scripts_dropdown(self) -> None:
        """Populate script selection dropdown with local and codeshare options."""
        source = self.query_one("#script-source-select", Select).value
        item_select = self.query_one("#script-item-select", Select)

        if source == "local":
            scripts = get_scripts_from_folder()
            if scripts:
                options = [(s["name"], s["path"]) for s in scripts]
                item_select.set_options(options)
                item_select.value = options[0][1]
            else:
                item_select.set_options([("No scripts found in scripts/ folder", "")])
        else:
            options = [(f"{p['id']}. {p['title']}", p["name"]) for p in CODESHARE_PRESETS]
            item_select.set_options(options)
            item_select.value = options[0][1]

        self.update_script_preview()
        self.update_command_preview()

    def update_script_preview(self) -> None:
        """Update the interactive script inspector card."""
        preview_widget = self.query_one("#script-preview-text", Static)
        source = self.query_one("#script-source-select", Select).value
        script_val = self.query_one("#script-item-select", Select).value

        if not script_val:
            preview_widget.update("[dim]No script selected.[/dim]")
            return

        if source == "local":
            path = Path(script_val)
            name = path.name
            desc = "Local script from scripts/ directory"
            if "ssl" in name.lower():
                desc = "Universal TLS/SSL Pinning bypass (TrustManager, OkHttp3, CertificatePinner)."
            preview_widget.update(
                f"[bold #38bdf8]Source:[/bold #38bdf8] Local File ({name})\n"
                f"[bold #38bdf8]Path:[/bold #38bdf8] {path}\n"
                f"[bold #38bdf8]Description:[/bold #38bdf8] {desc}"
            )
        else:
            preset = next((p for p in CODESHARE_PRESETS if p["name"] == script_val), None)
            if preset:
                preview_widget.update(
                    f"[bold #c084fc]Title:[/bold #c084fc] {preset.get('title', preset['name'])}\n"
                    f"[bold #38bdf8]Author:[/bold #38bdf8] @{preset.get('author', 'community')}\n"
                    f"[bold #38bdf8]Target Hook:[/bold #38bdf8] {preset.get('description', '')}\n"
                    f"[bold #38bdf8]Codeshare ID:[/bold #38bdf8] {preset['name']}"
                )
            else:
                preview_widget.update(f"[bold #c084fc]Codeshare Target:[/bold #c084fc] {script_val}")

    def update_command_preview(self) -> None:
        """Update generated command preview."""
        cmd_box = self.query_one("#command-preview-text", Static)
        dev = self.selected_device_info or (self.devices[0] if self.devices else None)
        if not dev:
            cmd_box.update("[dim]Select device and target application first[/dim]")
            return

        dev_id = dev.id
        port = str(dev.port or allocate_device_port(dev_id))
        pkg = self.selected_package or self.query_one("#package-filter", Input).value.strip() or "<target.package>"
        source = self.query_one("#script-source-select", Select).value
        script_val = self.query_one("#script-item-select", Select).value
        mode_val = self.query_one("#mode-select", Select).value

        if source == "local":
            script_part = f"-l {Path(script_val).name}" if script_val else "-l <script.js>"
        else:
            script_part = f"--codeshare {script_val}" if script_val else "--codeshare <id>"

        mode_part = "-f" if mode_val == "spawn" else "-n"
        cmd = f"frida -H 127.0.0.1:{port} {mode_part} {pkg} {script_part}"
        cmd_box.update(f"[bold #38bdf8]{cmd}[/bold #38bdf8]")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle dropdown selection changes."""
        if event.select.id == "script-source-select":
            self.populate_scripts_dropdown()
        elif event.select.id in ("script-item-select", "mode-select"):
            self.update_script_preview()
            self.update_command_preview()

    # Button Event Handlers
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-refresh":
            self.action_refresh_devices()
        elif btn_id in ("btn-setup", "btn-sidebar-setup"):
            self.action_setup_frida()
        elif btn_id in ("btn-start", "btn-sidebar-start"):
            self.action_start_frida()
        elif btn_id in ("btn-stop", "btn-sidebar-stop"):
            self.action_stop_frida()
        elif btn_id == "btn-stop-all":
            self.action_stop_all_servers()
        elif btn_id == "btn-autoroot":
            self.action_autoroot()
        elif btn_id == "btn-status-check":
            self.action_check_status()
        elif btn_id == "btn-load-processes":
            self.action_load_processes()
        elif btn_id == "btn-use-proc-inject":
            self.action_use_selected_process_for_inject()
        elif btn_id == "btn-load-packages":
            self.action_load_packages()
        elif btn_id == "btn-launch-inject":
            self.action_launch_injection()
        elif btn_id == "btn-jump-inject":
            self.action_focus_inject_tab()
        elif btn_id == "btn-refresh-ports":
            self.action_refresh_ports()
        elif btn_id == "btn-clear-ports":
            self.action_clear_ports()
        elif btn_id == "btn-clear-logs":
            self.action_clear_logs()

    @work(thread=True)
    def action_setup_frida(self) -> None:
        """Deploy frida-server binary to target device."""
        dev = self._get_or_select_device()
        if not dev:
            return

        dev_id = dev.id
        abi = dev.abi or get_device_architecture(dev_id) or "unknown"
        self.log_message(f"[bold #f59e0b][SETUP][/bold #f59e0b] Target: {dev_id} (ABI: {abi})...")

        server_file = get_frida_server_file_for_architecture(abi)
        if not server_file:
            self.log_message(f"[bold red][SETUP FAIL][/bold red] frida-server binary for ABI {abi} not found in server/!")
            self.notify("frida-server binary not found", severity="error")
            return

        success, msg = setup_frida_server(
            dev_id,
            device_abi=abi,
            server_file=server_file,
            progress_callback=lambda step, desc: self.log_message(f"[{step}] {desc}"),
        )
        if success:
            self.log_message(f"[bold green][SETUP OK][/bold green] Frida Server setup completed on {dev_id}!")
            self.notify(f"Setup successful on {dev_id}", severity="information")
        else:
            self.log_message(f"[bold red][SETUP FAIL][/bold red] Setup failed: {msg}")
            self.notify(f"Setup failed: {msg}", severity="error")

    @work(thread=True)
    def action_start_frida(self) -> None:
        """Start Frida Server on target device."""
        dev = self._get_or_select_device()
        if not dev:
            return

        dev_id = dev.id
        port = dev.port or allocate_device_port(dev_id)
        dev.port = port
        self.log_message(f"[bold #10b981][START][/bold #10b981] Starting Frida Server on {dev_id} (Port: {port})...")

        success, msg = start_frida_server(
            dev_id,
            local_port=port,
            progress_callback=lambda step, desc: self.log_message(f"[{step}] {desc}"),
        )

        if success:
            self.log_message(f"[bold green][START OK][/bold green] Frida Server ONLINE on {dev_id} (localhost:{port})")
            self.notify(f"Frida Server active on {dev_id}", severity="information")
            mappings = load_port_mappings()
            mappings[dev_id] = port
            save_port_mappings(mappings)
            self.action_refresh_devices()
        else:
            self.log_message(f"[bold red][START FAIL][/bold red] Failed to start Frida Server: {msg}")
            self.notify(f"Failed to start Frida Server: {msg}", severity="error")

    @work(thread=True)
    def action_stop_frida(self) -> None:
        """Stop Frida Server on target device."""
        dev = self._get_or_select_device()
        if not dev:
            return

        dev_id = dev.id
        self.log_message(f"[bold #f43f5e][STOP][/bold #f43f5e] Stopping Frida Server on {dev_id}...")
        success, msg = stop_frida_server(
            dev_id,
            progress_callback=lambda step, desc: self.log_message(f"[{step}] {desc}"),
        )
        if success:
            self.log_message(f"[bold green][STOP OK][/bold green] Frida Server stopped on {dev_id}")
            self.notify(f"Frida Server stopped on {dev_id}", severity="information")
            self.action_refresh_devices()

    @work(thread=True)
    def action_stop_all_servers(self) -> None:
        """Stop Frida Server on all connected devices and remove port forwards."""
        self.log_message("[bold red][STOP ALL][/bold red] Stopping Frida Server on all devices...")
        devs = detect_devices(hydrate_properties=False, auto_connect=False)
        for d in devs:
            stop_frida_server(d.id)
            self.log_message(f"• Stopped on {d.id}")

        remove_all_port_forwards()
        port_file = get_project_root() / "port_mapping.txt"
        if port_file.exists():
            port_file.unlink()

        self.log_message("[bold green][STOP ALL OK][/bold green] All Frida Servers & port forwardings stopped.")
        self.notify("All servers stopped", severity="information")
        self.action_refresh_devices()

    @work(thread=True)
    def action_autoroot(self) -> None:
        """Automated rooting check and rootAVD execution."""
        dev = self._get_or_select_device()
        if not dev:
            return

        guidance = get_root_guidance(dev.device_type, dev.device_label)
        if not guidance["supported"]:
            self.log_message(f"[bold yellow][ROOT NOTICE][/bold yellow] {guidance['title']}:\n{guidance['message']}")
            self.notify(guidance["title"], severity="warning")
            return

        api = dev.api or ""
        abi = dev.abi or ""
        self.log_message(f"[bold cyan][ROOT][/bold cyan] Searching ramdisk for {dev.id} (API: {api}, ABI: {abi})...")
        ramdisk = find_ramdisk_path(api, abi)
        if not ramdisk:
            self.log_message(f"[bold red][ROOT FAIL][/bold red] ramdisk.img not found for API {api} and ABI {abi}")
            self.notify("Ramdisk image not found", severity="error")
            return

        self.log_message(f"[bold green][ROOT][/bold green] Ramdisk image found: {ramdisk}")
        self.log_message("Starting rootAVD process (may take several minutes)...")

        success, msg = execute_rootavd(
            dev.id,
            ramdisk,
            output_callback=lambda line: self.log_message(f"[dim]{line}[/dim]"),
        )
        if success:
            self.log_message(f"[bold green][ROOT OK][/bold green] Autoroot on {dev.id} complete! Please cold-boot the AVD.")
            self.notify("Autoroot completed!", severity="information")
        else:
            self.log_message(f"[bold yellow][ROOT][/bold yellow] rootAVD notification: {msg}")

    @work(thread=True)
    def action_check_status(self) -> None:
        """Verify status of all devices and active ports."""
        self.log_message("[bold cyan][STATUS][/bold cyan] Checking status of all devices...")
        self.action_refresh_devices()

    # Process Explorer with Live Search
    @work(thread=True)
    def action_load_processes(self) -> None:
        """Fetch running process list via Frida for selected device."""
        dev = self._get_or_select_device()
        if not dev:
            return

        dev_id = dev.id
        port = dev.port or allocate_device_port(dev_id)
        self.log_message(f"[bold #38bdf8][PROCS][/bold #38bdf8] Fetching process list from {dev_id} (localhost:{port})...")

        target = f"127.0.0.1:{port}"
        success, procs, err = view_device_processes(target, is_host_port=True)
        if not success:
            # Fallback direct USB
            success, procs, err = view_device_processes(dev_id, is_host_port=False)

        if success:
            self._device_processes[dev_id] = procs
            if self.selected_device_id == dev_id:
                self._all_processes = procs
                self.app.call_from_thread(self._render_filtered_processes, None)
            self.log_message(f"[bold green][PROCS OK][/bold green] Successfully loaded {len(procs)} active processes on {dev_id}.")
            self.notify(f"Loaded {len(procs)} processes on {dev_id}", severity="information")
        else:
            self.log_message(f"[bold red][PROCS FAIL][/bold red] Failed to load processes on {dev_id}: {err}")
            self.notify(f"Failed to load processes on {dev_id}", severity="error")

    def _render_filtered_processes(self, query: Optional[str] = None) -> None:
        """Instantly filter processes in memory and update table."""
        if query is None:
            try:
                query = self.query_one("#process-filter", Input).value
            except Exception:
                query = ""
        tbl = self.query_one("#process-table", DataTable)
        tbl.clear()
        query = query.lower().strip()

        matched = [
            p for p in self._all_processes
            if not query or query in str(p.get("pid", "")).lower() or query in p.get("name", "").lower()
        ]

        if matched:
            tbl.add_rows([(str(p["pid"]), p["name"]) for p in matched])

        counter = self.query_one("#process-counter", Static)
        dev_id = self.selected_device_id or "Unknown"
        counter.update(f"Target: [bold cyan]{dev_id}[/bold cyan] │ Showing {len(matched)} of {len(self._all_processes)} total processes")

    def action_use_selected_process_for_inject(self) -> None:
        """Take selected process from process table and use in Inject tab."""
        pt = self.query_one("#process-table", DataTable)
        if pt.cursor_row is not None and pt.cursor_row < pt.row_count:
            try:
                row_data = pt.get_row_at(pt.cursor_row)
                proc_name = str(row_data[1])
                pid = str(row_data[0])
                self.selected_package = proc_name
                dev = self.selected_device_info or (self.devices[0] if self.devices else None)
                dev_id = dev.id if dev else "Unknown"
                port = str(dev.port or allocate_device_port(dev_id)) if dev else "27042"

                badge = self.query_one("#selected-package-badge", Static)
                badge.update(f"Target Device: [bold #38bdf8]{dev_id}[/bold #38bdf8] (: {port}) │ Process: [bold #10b981]{proc_name}[/bold #10b981] (PID: {pid}) ➔ [bold green]Attach Ready![/bold green]")

                # Set mode to attach
                mode_select = self.query_one("#mode-select", Select)
                mode_select.value = "attach"

                self.update_command_preview()
                self.action_focus_inject_tab()
                self.log_message(f"[bold cyan][PROCESS SELECTED][/bold cyan] Device: {dev_id} ➔ Target set to process: {proc_name}")
                self.notify(f"Selected process: {proc_name} on {dev_id}")
            except Exception as e:
                self.log_message(f"[yellow][WARN][/yellow] Failed to select process: {e}")

    # Package Explorer with Live Search
    @work(thread=True)
    def action_load_packages(self) -> None:
        """Fetch installed packages from selected device via 3-tier cascade."""
        dev = self._get_or_select_device()
        if not dev:
            return

        dev_id = dev.id
        port = str(dev.port or allocate_device_port(dev_id))
        self.log_message(f"[bold #38bdf8][APPS][/bold #38bdf8] Fetching application list from {dev_id}...")

        packages = get_package_list(dev_id, port)
        if packages:
            self._device_packages[dev_id] = packages
            if self.selected_device_id == dev_id:
                self._all_packages = packages
                self.app.call_from_thread(self._render_filtered_packages, None)
            self.log_message(f"[bold green][APPS OK][/bold green] Successfully found {len(packages)} applications on {dev_id}.")
            self.notify(f"Loaded {len(packages)} applications on {dev_id}", severity="information")
        else:
            self.log_message(f"[yellow][APPS] No applications found on {dev_id}. Ensure Frida Server or ADB is active.[/yellow]")
            self.notify(f"No applications found on {dev_id}", severity="warning")

    def _render_filtered_packages(self, query: Optional[str] = None) -> None:
        """Instantly filter packages in memory and update table."""
        if query is None:
            try:
                query = self.query_one("#package-filter", Input).value
            except Exception:
                query = ""
        tbl = self.query_one("#package-table", DataTable)
        tbl.clear()
        query = query.lower().strip()

        matched = [
            p for p in self._all_packages
            if not query or query in p.get("name", "").lower() or query in p.get("package", "").lower()
        ]

        if matched:
            tbl.add_rows([(p.get("name", p["package"]), p["package"]) for p in matched])

        counter = self.query_one("#package-counter", Static)
        dev_id = self.selected_device_id or "Unknown"
        counter.update(f"Target: [bold cyan]{dev_id}[/bold cyan] │ Showing {len(matched)} of {len(self._all_packages)} total applications")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Instant live search filtering as the user types."""
        if event.input.id == "process-filter":
            self._render_filtered_processes(event.value)
        elif event.input.id == "package-filter":
            val = event.value.strip()
            if self.selected_package and val and val != self.selected_package:
                self.selected_package = ""
                try:
                    dev = self.selected_device_info or (self.devices[0] if self.devices else None)
                    dev_id = dev.id if dev else "Unknown"
                    badge = self.query_one("#selected-package-badge", Static)
                    badge.update(f"Target Device: [bold cyan]{dev_id}[/bold cyan] │ Manual: [bold #38bdf8]{val}[/bold #38bdf8]")
                except Exception:
                    pass
            self._render_filtered_packages(val)
            self.update_command_preview()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Clicking a row in tables updates active context."""
        if event.data_table.id == "package-table":
            row_data = event.data_table.get_row(event.row_key)
            if row_data and len(row_data) >= 2:
                pkg_id = row_data[1]
                app_name = row_data[0]
                self.selected_package = pkg_id

                dev = self.selected_device_info or (self.devices[0] if self.devices else None)
                dev_id = dev.id if dev else "Unknown"
                port = str(dev.port or allocate_device_port(dev_id)) if dev else "27042"

                badge = self.query_one("#selected-package-badge", Static)
                badge.update(
                    f"🎯 Target: [bold #38bdf8]{dev_id}[/bold #38bdf8] (: {port}) │ "
                    f"App: [bold #10b981]{pkg_id}[/bold #10b981] ({app_name}) ➔ [bold green]Ready! Press [e] / click 🚀 Execute Frida[/bold green]"
                )

                self.update_command_preview()
                self.log_message(f"[bold cyan][TARGET APP][/bold cyan] Device: {dev_id} ➔ Selected package: {pkg_id} ({app_name})")
                self.notify(f"Selected: {pkg_id}. Press [e] or click '🚀 Execute Frida'!", severity="information")

        elif event.data_table.id == "process-table":
            row_data = event.data_table.get_row(event.row_key)
            if row_data and len(row_data) >= 2:
                proc_name = str(row_data[1])
                pid = str(row_data[0])
                self.selected_package = proc_name
                dev = self.selected_device_info or (self.devices[0] if self.devices else None)
                dev_id = dev.id if dev else "Unknown"
                port = str(dev.port or allocate_device_port(dev_id)) if dev else "27042"

                badge = self.query_one("#selected-package-badge", Static)
                badge.update(
                    f"🎯 Target: [bold #38bdf8]{dev_id}[/bold #38bdf8] (: {port}) │ "
                    f"Process: [bold #10b981]{proc_name}[/bold #10b981] (PID: {pid}) ➔ [bold green]Attach Ready![/bold green]"
                )

                # Set mode to attach
                mode_select = self.query_one("#mode-select", Select)
                mode_select.value = "attach"

                self.update_command_preview()
                self.action_focus_inject_tab()
                self.log_message(f"[bold cyan][TARGET PROC][/bold cyan] Device: {dev_id} ➔ Selected process: {proc_name} (PID: {pid})")
                self.notify(f"Selected process: {proc_name}")

        elif event.data_table.id == "ports-table":
            row_data = event.data_table.get_row(event.row_key)
            if row_data and len(row_data) >= 1:
                target_raw = str(row_data[0])
                matched = next((d for d in self.devices if d.id in target_raw), None)
                if matched and matched.id != self.selected_device_id:
                    self.selected_device_id = matched.id
                    self.selected_device_info = matched
                    self.log_message(f"[bold cyan][SELECT][/bold cyan] Switched active device to: {matched.id} ({matched.device_label})")
                    try:
                        dev_list = self.query_one("#device-list", ListView)
                        idx = next((i for i, d in enumerate(self.devices) if d.id == matched.id), 0)
                        dev_list.index = idx
                    except Exception:
                        pass
                    self._update_device_list_visuals()
                    self.update_stats_banner()
                    self.update_dashboard()
                    self.update_process_view()
                    self.update_package_view()
                    self.update_ports_view()
                    self._render_ports_table_fast()
                    self.update_command_preview()

    def action_launch_injection(self) -> None:
        """Launch interactive Frida terminal session in a new window."""
        dev = self._get_or_select_device()
        if not dev:
            return

        dev_id = dev.id
        port = str(dev.port or allocate_device_port(dev_id))

        # Get target package
        selected_pkg = self.selected_package
        if not selected_pkg:
            # Check package table cursor or filter input
            pkg_tbl = self.query_one("#package-table", DataTable)
            if pkg_tbl.cursor_row is not None and pkg_tbl.cursor_row < pkg_tbl.row_count:
                try:
                    row_data = pkg_tbl.get_row_at(pkg_tbl.cursor_row)
                    selected_pkg = str(row_data[1])
                    self.selected_package = selected_pkg
                except Exception:
                    pass

        if not selected_pkg:
            manual_input = self.query_one("#package-filter", Input).value.strip()
            if manual_input:
                selected_pkg = manual_input
                self.selected_package = selected_pkg
            else:
                self.notify("Please select or enter a package name first", severity="warning")
                return

        # Get script
        script_source = self.query_one("#script-source-select", Select).value
        script_val = self.query_one("#script-item-select", Select).value
        mode_val = self.query_one("#mode-select", Select).value

        if not script_val:
            self.notify("Please select a script first", severity="warning")
            return

        if script_source == "local":
            script_args = ["-l", str(script_val)]
            script_display = Path(script_val).name
        else:
            script_args = ["--codeshare", str(script_val)]
            script_display = f"codeshare:{script_val}"

        spawn_mode = (mode_val == "spawn")
        target_host_port = f"127.0.0.1:{port}"

        self.log_message(f"[bold #c084fc][INJECT][/bold #c084fc] Launching Frida: {selected_pkg} ({script_display}) on {dev_id} (localhost:{port})...")
        frida_cmd = build_frida_command(target_host_port, selected_pkg, script_args, spawn_mode=spawn_mode)
        success, msg = launch_frida_session(dev_id, port, selected_pkg, script_display, frida_cmd, in_new_window=True)

        if success:
            self.log_message(f"[bold green][INJECT OK][/bold green] Frida session window opened on {dev_id}: {msg}")
            self.notify(f"Frida window opened for {dev_id}!", severity="information")
        else:
            self.log_message(f"[bold red][INJECT FAIL][/bold red] Failed to launch Frida on {dev_id}: {msg}")
            self.notify(f"Failed: {msg}", severity="error")

    @work(thread=True)
    def action_refresh_ports(self) -> None:
        """Refresh port table entries, probe sockets in background, and update cache."""
        cached = load_port_mappings()
        active = get_active_port_forwards()
        combined = {**cached, **active}

        # Ensure all detected devices are included
        for d in self.devices:
            if d.id not in combined:
                combined[d.id] = d.port or allocate_device_port(d.id)

        self._device_ports_cache.update(combined)

        for dev_id, port in combined.items():
            ok, _ = test_frida_connection(f"127.0.0.1:{port}", is_host_port=True)
            if ok:
                status = "[bold green]● Connected (Active)[/bold green]"
            elif is_frida_server_running(dev_id, use_cache=True):
                status = "[bold yellow]● Running (Port Ready)[/bold yellow]"
            else:
                status = "[dim #64748b]○ Standby / Ready[/dim #64748b]"
            self._device_port_status_cache[dev_id] = status

        self.app.call_from_thread(self._render_ports_table_fast)
        self.app.call_from_thread(self.update_ports_view)

    def _update_ports_table(self, rows: Optional[List[Tuple[str, str, str, str]]] = None) -> None:
        self._render_ports_table_fast()
        self.update_ports_view()

    @work(thread=True)
    def action_clear_ports(self) -> None:
        """Clear all active ADB port forwardings."""
        remove_all_port_forwards()
        port_file = get_project_root() / "port_mapping.txt"
        if port_file.exists():
            port_file.unlink()
        self.log_message("[bold green][PORTS][/bold green] All port forwardings cleared successfully.")
        self.notify("All port forwards cleared", severity="information")
        self.action_refresh_ports()

    # Keyboard Action Bindings
    def action_quit_app(self) -> None:
        self.exit()

    def action_start_frida_action(self) -> None:
        self.action_start_frida()

    def action_stop_frida_action(self) -> None:
        self.action_stop_frida()

    def action_setup_frida_action(self) -> None:
        self.action_setup_frida()

    def action_focus_dashboard_tab(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "tab-dashboard"

    def action_focus_process_tab(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "tab-processes"

    def action_focus_inject_tab(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "tab-inject"

    def action_focus_ports_tab(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "tab-ports"

    def action_clear_logs(self) -> None:
        log_widget = self.query_one("#event-log", RichLog)
        log_widget.clear()


def run_tui() -> None:
    """Entry point for the interactive Textual dashboard."""
    app = FridaXTRApp()
    app.run()


if __name__ == "__main__":
    run_tui()
