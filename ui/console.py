#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui.console - Classic ANSI Gradient Terminal Interface
Preserves the full CLI interactive menu, modals, tables, and exit animations
while delegating all logic to the core package.
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core import (
    CODESHARE_PRESETS,
    DEFAULT_FRIDA_PORT,
    allocate_device_port,
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
    is_frida_server_running,
    launch_frida_session,
    load_port_mappings,
    remove_all_port_forwards,
    run_command,
    save_port_mappings,
    setup_frida_server,
    setup_port_forward,
    start_frida_server,
    stop_frida_server,
    test_frida_connection,
    view_device_processes,
)
from ui.colors import Colors


def clear_screen():
    """Clear terminal screen"""
    os.system("cls" if os.name == "nt" else "clear")


def print_modal(title: str, content: str = "", width: int = 70):
    """Print minimalist modal with clean borders"""
    print()
    border = f"{Colors.DIM}╭{'─' * (min(len(title), width) + 2)}╮{Colors.RESET}"
    title_line = f"{Colors.DIM}│{Colors.RESET} {Colors.BOLD}{Colors.PURPLE}{title}{Colors.RESET} {Colors.DIM}│{Colors.RESET}"
    print(border)
    print(title_line)
    if content:
        for line in content.split("\n"):
            if line.strip():
                print(f"{Colors.DIM}│{Colors.RESET}  {line}")
    print(f"{Colors.DIM}╰{'─' * (min(len(title), width) + 2)}╯{Colors.RESET}")
    print()


def print_info(msg: str):
    """Print info message with colored dot"""
    print(f"  {Colors.INFO}●{Colors.RESET} {msg}")


def print_ok(msg: str):
    """Print success message with checkmark"""
    print(f"  {Colors.SUCCESS}✓{Colors.RESET} {msg}")


def print_warning(msg: str):
    """Print warning message"""
    print(f"  {Colors.WARNING}●{Colors.RESET} {msg}")


def print_error(msg: str):
    """Print error message with X"""
    print(f"  {Colors.ERROR}✗{Colors.RESET} {msg}")


def print_table(headers: List[str], rows: List[List[str]], widths: Optional[List[int]] = None):
    """Print compact elegant table with minimal separators"""
    if not rows:
        return

    if widths is None:
        widths = [
            max(len(str(h)), max(len(str(r[i])) for r in rows))
            for i, h in enumerate(headers)
        ]

    widths = [w + 1 for w in widths]

    header_line = " ".join(
        f"{Colors.DIM}{Colors.BOLD}{h:<{w}}{Colors.RESET}"
        for h, w in zip(headers, widths)
    )
    print(f"  {header_line}")

    separator = f"{Colors.DIM}  {' '.join('─' * w for w in widths)}{Colors.RESET}"
    print(separator)

    for row in rows:
        row_line = " ".join(f"{str(cell):<{w}}" for cell, w in zip(row, widths))
        prefix = f"{Colors.DIM}→{Colors.RESET}"
        print(f"  {prefix} {row_line}")

    print()


def pause():
    """Wait for user input"""
    print()
    input(f"  {Colors.PURPLE}►{Colors.RESET} {Colors.DIM}Press Enter...{Colors.RESET}")


def animate_loading(text: str, duration: float = 1.0):
    """Modern spinner with braille patterns"""
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        color = Colors.PURPLE if i % 2 == 0 else Colors.BLUE
        print(f"\r  {color}{spinner[i % len(spinner)]}{Colors.RESET} {text}", end="", flush=True)
        time.sleep(0.1)
        i += 1
    print(f"\r  {Colors.SUCCESS}✓{Colors.RESET} {text}     ")


def animate_exit():
    """Polished exit sequence with smooth transitions"""
    clear_screen()
    print()

    thank_you = "Thank you for using"
    width = 70
    padding = (width - len(thank_you)) // 2
    centered = " " * padding + thank_you

    colors_fade = [Colors.DIM, Colors.PURPLE, Colors.BLUE, Colors.CYAN, Colors.BOLD + Colors.CYAN]
    for color in colors_fade:
        print(f"\r{color}{centered}{Colors.RESET}", end="", flush=True)
        time.sleep(0.15)
    print()
    time.sleep(0.2)

    ascii_lines = [
        f"{Colors.PINK}███████╗██████╗ ██╗██████╗  █████╗      ██╗  ██╗████████╗██████╗ {Colors.RESET}",
        f"{Colors.PURPLE}██╔════╝██╔══██╗██║██╔══██╗██╔══██╗     ╚██╗██╔╝╚══██╔══╝██╔══██╗{Colors.RESET}",
        f"{Colors.BLUE}█████╗  ██████╔╝██║██║  ██║███████║      ╚███╔╝    ██║   ██████╔╝{Colors.RESET}",
        f"{Colors.CYAN}██╔══╝  ██╔══██╗██║██║  ██║██╔══██║      ██╔██╗    ██║   ██╔══██╗{Colors.RESET}",
        f"{Colors.PURPLE}██║     ██║  ██║██║██████╔╝██║  ██║     ██╔╝ ██╗   ██║   ██║  ██║{Colors.RESET}",
        f"{Colors.PINK}╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝{Colors.RESET}",
    ]

    for line in ascii_lines:
        print(line)
        time.sleep(0.08)

    time.sleep(0.2)
    credit = "Frida-Xtr v2.0 | Multi-Device Manager"
    padding_credit = (width - len(credit)) // 2
    centered_credit = " " * padding_credit + credit
    print(f"{Colors.DIM}{Colors.PURPLE}{centered_credit}{Colors.RESET}")
    time.sleep(0.3)

    print()
    goodbye = "See you soon! 👋"
    padding_goodbye = (width - len(goodbye)) // 2
    centered_goodbye = " " * padding_goodbye + goodbye

    sparkles = ["✨", "⭐", "💫", "✨"]
    for sparkle in sparkles:
        print(f"\r{Colors.PURPLE}{centered_goodbye}{Colors.RESET} {sparkle}", end="", flush=True)
        time.sleep(0.15)
    print()
    time.sleep(0.4)

    print()
    closing_text = "Closing"
    padding_closing = (width - len(closing_text) - 12) // 2
    spaces = " " * padding_closing

    closing_frames = [
        f"{spaces}Closing",
        f"{spaces}Closing.",
        f"{spaces}Closing..",
        f"{spaces}Closing...",
    ]

    for _ in range(2):
        for frame in closing_frames:
            print(f"\r{Colors.DIM}{frame}{Colors.RESET}", end="", flush=True)
            time.sleep(0.12)

    final_msg = f"{spaces}{Colors.SUCCESS}✓ Closed successfully{Colors.RESET}"
    print(f"\r{final_msg}     ")
    time.sleep(0.6)


def print_ascii_header():
    """Print ASCII art header with gradient colors"""
    ascii_art = f"""
{Colors.PINK}███████╗██████╗ ██╗██████╗  █████╗      ██╗  ██╗████████╗██████╗ {Colors.RESET}
{Colors.PURPLE}██╔════╝██╔══██╗██║██╔══██╗██╔══██╗     ╚██╗██╔╝╚══██╔══╝██╔══██╗{Colors.RESET}
{Colors.BLUE}█████╗  ██████╔╝██║██║  ██║███████║      ╚███╔╝    ██║   ██████╔╝{Colors.RESET}
{Colors.CYAN}██╔══╝  ██╔══██╗██║██║  ██║██╔══██║      ██╔██╗    ██║   ██╔══██╗{Colors.RESET}
{Colors.PURPLE}██║     ██║  ██║██║██████╔╝██║  ██║     ██╔╝ ██╗   ██║   ██║  ██║{Colors.RESET}
{Colors.PINK}╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝{Colors.RESET}
"""
    print(ascii_art)
    print(f"{Colors.DIM}{Colors.PURPLE}Frida-Xtr v2.0 | Multi-Device Manager | By Anonre | Tuan Hades{Colors.RESET}")
    print()


def setup_frida():
    """Setup Frida on selected devices"""
    clear_screen()
    print_modal("SETUP FRIDA SERVER")

    available_files = get_available_frida_server_files()
    if not available_files:
        print_error("No frida-server binary found!")
        print(f"  {Colors.YELLOW}Target binaries searched in folder {Colors.CYAN}server/{Colors.YELLOW} or root directory:{Colors.RESET}")
        print(f"  {Colors.CYAN}• server/frida-server{Colors.RESET} (generic)")
        print(f"  {Colors.CYAN}• server/frida-server-x86{Colors.RESET} (for x86 devices)")
        print(f"  {Colors.CYAN}• server/frida-server-x86_64{Colors.RESET} (for x86_64 devices)")
        print(f"  {Colors.CYAN}• server/frida-server-arm64{Colors.RESET} (for arm64-v8a devices)")
        print(f"  {Colors.CYAN}• server/frida-server-arm{Colors.RESET} (for armeabi-v7a devices)")
        print()
        print(f"  {Colors.YELLOW}Download Frida Server from: {Colors.BLUE}https://github.com/frida/frida/releases{Colors.RESET}")
        pause()
        return

    devices = detect_devices()
    if not devices:
        print_error("No devices detected!")
        print_modal("INFO", "Ensure:\n  • Emulator/device is running\n  • USB Debugging is enabled\n  • ADB is installed and in PATH")
        pause()
        return

    headers = ["#", "Device ID", "Info"]
    rows = [[str(i), f"{Colors.CYAN}{d.id}{Colors.RESET}", f"{Colors.DIM}{d.info[:45]}{Colors.RESET}"] for i, d in enumerate(devices, 1)]
    print_table(headers, rows, [5, 20, 45])

    print_modal("SELECT DEVICES", f"Separate with space (e.g. {Colors.CYAN}1 3{Colors.RESET}) or type {Colors.YELLOW}'all'{Colors.RESET}")
    selected = input(f"  {Colors.PURPLE}►{Colors.RESET} Choice: ").strip()

    if selected.lower() == "all":
        selected_indices = list(range(1, len(devices) + 1))
    else:
        try:
            selected_indices = [int(x.strip()) for x in selected.split()]
        except ValueError:
            print_error("Invalid input!")
            pause()
            return

    print()
    for idx in selected_indices:
        if 1 <= idx <= len(devices):
            device = devices[idx - 1]
            device_id = device.id

            print_modal(f"DEVICE: {Colors.CYAN}{device_id}{Colors.RESET}")
            print_info("Checking device architecture...")
            device_abi = get_device_architecture(device_id) or "unknown"
            print_ok(f"Device architecture: {Colors.CYAN}{device_abi}{Colors.RESET}")

            frida_server_file = get_frida_server_file_for_architecture(device_abi)
            if not frida_server_file:
                print_error(f"frida-server binary for architecture {Colors.CYAN}{device_abi}{Colors.RESET} was not found!")
                continue

            rel_path = frida_server_file.relative_to(get_project_root())
            print_info(f"Using file: {Colors.CYAN}{rel_path}{Colors.RESET}")

            has_root = check_root_access(device_id)
            if has_root:
                print_ok("Root access available.")
            else:
                print_warning("Root access unavailable. Trying without root...")

            print_info("Executing Frida Server setup...")
            success, msg = setup_frida_server(
                device_id,
                device_abi=device_abi,
                server_file=frida_server_file,
                use_root=has_root,
                progress_callback=lambda step, desc: print_info(f"[{step}] {desc}")
            )

            if success:
                print_ok(f"Frida Server successfully setup on {Colors.CYAN}{device_id}{Colors.RESET}!")
            else:
                print_error(f"Setup failed on {device_id}: {msg}")
            print()

    pause()


def start_frida():
    """Start Frida Server on selected devices"""
    clear_screen()
    print_modal("START FRIDA SERVER")

    devices = detect_devices()
    if not devices:
        print_error("No devices detected!")
        pause()
        return

    print_info("Available devices:")
    print()
    headers = ["#", "Device ID", "Info"]
    rows = [[str(i), f"{Colors.CYAN}{d.id}{Colors.RESET}", f"{Colors.DIM}{d.info[:45]}{Colors.RESET}"] for i, d in enumerate(devices, 1)]
    print_table(headers, rows, [5, 20, 45])

    print_modal("SELECT DEVICES", f"Separate with space (e.g. {Colors.CYAN}1 2{Colors.RESET}) or type {Colors.YELLOW}'all'{Colors.RESET}")
    selected = input(f"  {Colors.PURPLE}►{Colors.RESET} Choice: ").strip()

    if selected.lower() == "all":
        selected_indices = list(range(1, len(devices) + 1))
    else:
        try:
            selected_indices = [int(x.strip()) for x in selected.split()]
        except ValueError:
            print_error("Invalid input!")
            pause()
            return

    print()
    port_base = 27042
    port_mapping = load_port_mappings()
    success_count = 0

    for idx in selected_indices:
        if 1 <= idx <= len(devices):
            device = devices[idx - 1]
            device_id = device.id
            print_modal(f"DEVICE: {Colors.CYAN}{device_id}{Colors.RESET}")

            # Check architecture compatibility
            device_abi = get_device_architecture(device_id) or "unknown"
            frida_arch = get_frida_server_architecture()
            if device_abi != "unknown" and frida_arch:
                is_comp, comp_msg = check_architecture_compatibility(device_abi, frida_arch)
                if not is_comp:
                    print_error("ARCHITECTURE MISMATCH detected!")
                    print_error(comp_msg)
                    continue

            current_port = allocate_device_port(device_id)
            success, msg = start_frida_server(
                device_id,
                local_port=current_port,
                progress_callback=lambda step, desc: print_info(f"[{step}] {desc}")
            )

            if success:
                port_mapping[device_id] = current_port
                success_count += 1
                print_ok(f"Frida Server running on {Colors.CYAN}{device_id}{Colors.RESET} ({Colors.BLUE}localhost:{current_port}{Colors.RESET})")
            else:
                print_error(f"Failed to start Frida Server: {msg}")

            print()

    save_port_mappings(port_mapping)

    if success_count > 0:
        print_modal("SUCCESS", f"Frida Server successfully started on {success_count} devices!")
    else:
        print_error("Failed to start Frida Server on all selected devices.")
    pause()


def stop_frida():
    """Stop Frida Server on selected devices"""
    clear_screen()
    print_modal("STOP FRIDA SERVER")

    devices = detect_devices()
    if not devices:
        print_error("No devices detected!")
        pause()
        return

    headers = ["#", "Device ID", "Info"]
    rows = [[str(i), f"{Colors.CYAN}{d.id}{Colors.RESET}", f"{Colors.DIM}{d.info[:45]}{Colors.RESET}"] for i, d in enumerate(devices, 1)]
    print_table(headers, rows, [5, 20, 45])

    print_modal("SELECT DEVICES", f"Separate with space (e.g. {Colors.CYAN}1 2{Colors.RESET}) or type {Colors.YELLOW}'all'{Colors.RESET}")
    selected = input(f"  {Colors.PURPLE}►{Colors.RESET} Choice: ").strip()

    if selected.lower() == "all":
        selected_indices = list(range(1, len(devices) + 1))
    else:
        try:
            selected_indices = [int(x.strip()) for x in selected.split()]
        except ValueError:
            print_error("Invalid input!")
            pause()
            return

    print()
    print_info("Stopping Frida Server...")
    print()

    for idx in selected_indices:
        if 1 <= idx <= len(devices):
            device_id = devices[idx - 1].id
            print_modal(f"DEVICE: {Colors.CYAN}{device_id}{Colors.RESET}")
            stop_frida_server(device_id)
            print_ok(f"Stopped on {Colors.CYAN}{device_id}{Colors.RESET}")
            print()

    if os.name == "nt":
        run_command(["taskkill", "/FI", "WindowTitle eq Frida-*", "/F"], capture_output=False)

    port_file = get_project_root() / "port_mapping.txt"
    if port_file.exists():
        port_file.unlink()

    print_modal("SUCCESS", "Frida Server stopped successfully!")
    pause()


def check_status():
    """Check Frida Server status on all devices"""
    clear_screen()
    print_modal("FRIDA STATUS CHECK")

    devices = detect_devices()
    if not devices:
        print_error("No devices detected!")
        pause()
        return

    print()
    port_mappings = load_port_mappings()
    active_forwards = get_active_port_forwards()

    headers = ["Device ID", "Status", "Port"]
    rows = []

    for device in devices:
        device_id = device.id
        frida_running = is_frida_server_running(device_id)

        if not frida_running:
            rows.append([
                f"{Colors.CYAN}{device_id}{Colors.RESET}",
                f"{Colors.RED}OFFLINE{Colors.RESET}",
                f"{Colors.DIM}N/A{Colors.RESET}",
            ])
        else:
            port = active_forwards.get(device_id) or port_mappings.get(device_id)
            if not port:
                for test_port in range(27042, 27052):
                    ok, _ = test_frida_connection(f"127.0.0.1:{test_port}", is_host_port=True)
                    if ok:
                        port = test_port
                        break

            if port:
                ok, _ = test_frida_connection(f"127.0.0.1:{port}", is_host_port=True)
                if ok:
                    rows.append([
                        f"{Colors.CYAN}{device_id}{Colors.RESET}",
                        f"{Colors.GREEN}ONLINE{Colors.RESET}",
                        f"{Colors.BLUE}localhost:{port}{Colors.RESET}",
                    ])
                else:
                    rows.append([
                        f"{Colors.CYAN}{device_id}{Colors.RESET}",
                        f"{Colors.GREEN}ONLINE{Colors.RESET}",
                        f"{Colors.YELLOW}localhost:{port} (connection failed){Colors.RESET}",
                    ])
            else:
                rows.append([
                    f"{Colors.CYAN}{device_id}{Colors.RESET}",
                    f"{Colors.GREEN}ONLINE (USB){Colors.RESET}",
                    f"{Colors.YELLOW}Port not found{Colors.RESET}",
                ])

    print_table(headers, rows, [20, 15, 25])
    pause()


def view_processes():
    """View processes on selected device"""
    clear_screen()
    print_modal("VIEW PROCESSES")

    port_mappings = load_port_mappings()
    active_forwards = get_active_port_forwards()
    combined_mappings = {**port_mappings, **active_forwards}

    if not combined_mappings:
        print_warning("No port mappings found. Please start Frida Server first.")
        pause()
        return

    mapping_list = [{"device": dev, "port": str(port)} for dev, port in combined_mappings.items()]
    headers = ["#", "Device ID", "Port"]
    rows = [[str(i), f"{Colors.CYAN}{m['device']}{Colors.RESET}", f"{Colors.BLUE}{m['port']}{Colors.RESET}"] for i, m in enumerate(mapping_list, 1)]
    print_table(headers, rows, [5, 25, 10])

    try:
        choice = input(f"  {Colors.PURPLE}►{Colors.RESET} Device [{Colors.YELLOW}1-{len(mapping_list)}{Colors.RESET}]: ").strip()
        idx = int(choice)
        if 1 <= idx <= len(mapping_list):
            selected = mapping_list[idx - 1]
            sel_device = selected["device"]
            sel_port = selected["port"]

            print()
            print_modal("DEVICE INFO", f"{Colors.CYAN}Device:{Colors.RESET} {Colors.YELLOW}{sel_device}{Colors.RESET}\n{Colors.CYAN}Port:{Colors.RESET} {Colors.BLUE}localhost:{sel_port}{Colors.RESET}")
            print_info(f"Displaying processes from {Colors.CYAN}{sel_device}{Colors.RESET}...")
            print()

            success, procs, err = view_device_processes(f"127.0.0.1:{sel_port}", is_host_port=True)
            if success and procs:
                proc_headers = ["PID", "Process Name"]
                proc_rows = [[str(p["pid"]), f"{Colors.CYAN}{p['name']}{Colors.RESET}"] for p in procs]
                print_table(proc_headers, proc_rows, [10, 45])
            else:
                print_error(f"Failed to display processes: {err}")
        else:
            print_error("Invalid choice!")
    except ValueError:
        print_error("Invalid input!")

    pause()


def port_management():
    """Manage port forwarding"""
    clear_screen()
    print_modal("PORT FORWARDING MANAGEMENT")
    auto_connect_ldplayer()

    port_mappings = load_port_mappings()
    active_forwards = get_active_port_forwards()
    combined_mappings = {**port_mappings, **active_forwards}

    if combined_mappings:
        headers = ["Device ID", "Local Port", "Device Port"]
        rows = [
            [
                f"{Colors.CYAN}{dev}{Colors.RESET}",
                f"{Colors.BLUE}localhost:{port}{Colors.RESET}",
                f"{Colors.YELLOW}27042{Colors.RESET}",
            ]
            for dev, port in combined_mappings.items()
        ]
        print_table(headers, rows, [25, 15, 15])
    else:
        print_info("No active port mappings.")

    print()
    port_menu_content = (
        f"{Colors.CYAN}[1]{Colors.RESET} {Colors.GREEN}Refresh Port Forwarding{Colors.RESET}\n"
        f"{Colors.CYAN}[2]{Colors.RESET} {Colors.YELLOW}Clear All Port Forwarding{Colors.RESET}\n"
        f"{Colors.CYAN}[3]{Colors.RESET} {Colors.DIM}Back to Main Menu{Colors.RESET}"
    )
    print_modal("SELECT ACTION", port_menu_content)
    choice = input(f"  {Colors.PURPLE}►{Colors.RESET} Choice [{Colors.YELLOW}1-3{Colors.RESET}]: ").strip()

    if choice == "1":
        print()
        print_info("Refreshing port forwarding...")
        devices = detect_devices()
        port_base = 27042
        new_mappings: Dict[str, int] = {}
        for dev in devices:
            setup_port_forward(dev.id, port_base, 27042)
            print_ok(f"{Colors.CYAN}{dev.id}{Colors.RESET} -> {Colors.BLUE}localhost:{port_base}{Colors.RESET}")
            new_mappings[dev.id] = port_base
            port_base += 1
        save_port_mappings(new_mappings)
        pause()
        port_management()
    elif choice == "2":
        print()
        print_info("Clearing all port forwarding...")
        remove_all_port_forwards()
        port_file = get_project_root() / "port_mapping.txt"
        if port_file.exists():
            port_file.unlink()
        print_ok("All port forwarding cleared.")
        pause()
        port_management()


def start_frida_package():
    """Start Frida injection on an application package"""
    clear_screen()
    print_modal("START FRIDA ON PACKAGE")
    auto_connect_ldplayer()

    devices = detect_devices()
    if not devices:
        print_error("No devices detected!")
        pause()
        return

    headers = ["#", "Device ID", "Info"]
    rows = [[str(i), f"{Colors.CYAN}{d.id}{Colors.RESET}", f"{Colors.DIM}{d.info[:45]}{Colors.RESET}"] for i, d in enumerate(devices, 1)]
    print_table(headers, rows, [5, 20, 45])

    try:
        choice = input(f"  {Colors.PURPLE}►{Colors.RESET} Device [{Colors.YELLOW}1-{len(devices)}{Colors.RESET}]: ").strip()
        idx = int(choice)
        if not (1 <= idx <= len(devices)):
            print_error("Invalid choice!")
            pause()
            return
    except ValueError:
        print_error("Invalid input!")
        pause()
        return

    selected_device = devices[idx - 1].id
    print_info("Checking Frida Server status...")
    if not is_frida_server_running(selected_device):
        print_warning("Frida Server is not running on this device! Please start Frida Server first.")
        pause()
        return

    active_forwards = get_active_port_forwards()
    cached_mappings = load_port_mappings()
    selected_port = str(active_forwards.get(selected_device) or cached_mappings.get(selected_device) or 27042)

    # Ensure port forward is healthy
    ok, _ = test_frida_connection(f"127.0.0.1:{selected_port}", is_host_port=True)
    if not ok:
        setup_port_forward(selected_device, int(selected_port), 27042)

    # Package input method
    print()
    input_content = (
        f"{Colors.CYAN}[1]{Colors.RESET} {Colors.YELLOW}Enter package name manually{Colors.RESET}\n"
        f"{Colors.CYAN}[2]{Colors.RESET} {Colors.GREEN}Select from installed application list (auto){Colors.RESET}"
    )
    print_modal("INPUT METHOD", input_content)
    pkg_method = input(f"  {Colors.PURPLE}►{Colors.RESET} Choice [{Colors.YELLOW}1-2{Colors.RESET}]: ").strip()

    package_name = ""
    if pkg_method == "1":
        package_name = input(f"  {Colors.CYAN}▶{Colors.RESET} Package name: ").strip()
        if not package_name:
            print_error("Package name cannot be empty!")
            pause()
            return
    elif pkg_method == "2":
        print_info("Fetching installed application list from device...")
        packages = get_package_list(selected_device, selected_port)
        if not packages:
            print_error("No applications found!")
            pause()
            return

        headers = ["#", "Package Info"]
        rows = [[str(i), f"{Colors.CYAN}{p['line'][:60]}{Colors.RESET}"] for i, p in enumerate(packages, 1)]
        print_table(headers, rows, [5, 60])

        try:
            p_choice = input(f"  {Colors.PURPLE}►{Colors.RESET} App [{Colors.YELLOW}1-{len(packages)}{Colors.RESET}]: ").strip()
            p_idx = int(p_choice)
            if 1 <= p_idx <= len(packages):
                package_name = packages[p_idx - 1]["package"]
                print_ok(f"Package: {Colors.CYAN}{package_name}{Colors.RESET}")
            else:
                print_error("Invalid choice!")
                pause()
                return
        except ValueError:
            print_error("Invalid input!")
            pause()
            return
    else:
        print_error("Invalid choice!")
        pause()
        return

    # Script selection
    print()
    script_content = (
        f"{Colors.CYAN}[1]{Colors.RESET} {Colors.MAGENTA}Use local .js hook script{Colors.RESET}\n"
        f"{Colors.CYAN}[2]{Colors.RESET} {Colors.BLUE}Use public Codeshare preset{Colors.RESET}"
    )
    print_modal("SELECT SCRIPT", script_content)
    s_choice = input(f"  {Colors.PURPLE}►{Colors.RESET} Choice [{Colors.YELLOW}1-2{Colors.RESET}]: ").strip()

    frida_script_args: List[str] = []
    script_name = ""

    if s_choice == "1":
        scripts = get_scripts_from_folder()
        if not scripts:
            print_error("No scripts found in 'scripts' directory!")
            pause()
            return
        headers = ["#", "Script Name"]
        rows = [[str(i), f"{Colors.MAGENTA}{s['name']}{Colors.RESET}"] for i, s in enumerate(scripts, 1)]
        print_table(headers, rows, [5, 60])

        try:
            s_idx = int(input(f"  {Colors.PURPLE}►{Colors.RESET} Script [{Colors.YELLOW}1-{len(scripts)}{Colors.RESET}]: ").strip())
            if 1 <= s_idx <= len(scripts):
                script_name = scripts[s_idx - 1]["name"]
                frida_script_args = ["-l", scripts[s_idx - 1]["path"]]
            else:
                print_error("Invalid choice!")
                pause()
                return
        except ValueError:
            print_error("Invalid input!")
            pause()
            return
    elif s_choice == "2":
        headers = ["#", "Codeshare Script"]
        rows = [[p["id"], f"{Colors.MAGENTA}{p['name']}{Colors.RESET}"] for p in CODESHARE_PRESETS]
        print_table(headers, rows, [5, 60])

        c_choice = input(f"  {Colors.PURPLE}►{Colors.RESET} Choice [{Colors.YELLOW}1-{len(CODESHARE_PRESETS)}{Colors.RESET}]: ").strip()
        matched = next((p for p in CODESHARE_PRESETS if p["id"] == c_choice), None)
        if matched:
            script_name = matched["name"]
            frida_script_args = ["--codeshare", matched["name"]]
        else:
            print_error("Invalid choice!")
            pause()
            return
    else:
        print_error("Invalid choice!")
        pause()
        return

    # Summary and launch
    summary = (
        f"{Colors.CYAN}Package:{Colors.RESET} {Colors.YELLOW}{package_name}{Colors.RESET}\n"
        f"{Colors.CYAN}Device:{Colors.RESET} {Colors.YELLOW}{selected_device}{Colors.RESET}\n"
        f"{Colors.CYAN}Port:{Colors.RESET} {Colors.BLUE}{selected_port}{Colors.RESET}\n"
        f"{Colors.CYAN}Script:{Colors.RESET} {Colors.MAGENTA}{script_name}{Colors.RESET}"
    )
    print_modal("SUMMARY", summary)
    print_info(f"Mode: {Colors.CYAN}Spawn{Colors.RESET} (opening in new window)...")

    frida_cmd = build_frida_command(f"127.0.0.1:{selected_port}", package_name, frida_script_args, spawn_mode=True)
    launch_frida_session(selected_device, selected_port, package_name, script_name, frida_cmd, in_new_window=True)

    print_modal("SUCCESS", "Frida session is running in a new window.")
    pause()


def autoroot():
    """Auto root compatible devices using rootAVD"""
    clear_screen()
    print_modal("AUTO ROOT DEVICES")
    auto_connect_ldplayer()

    devices = detect_devices()
    if not devices:
        print_error("No devices detected!")
        pause()
        return

    compatible_devices = []
    for device in devices:
        device_id = device.id
        print_modal(f"DEVICE: {Colors.CYAN}{device_id}{Colors.RESET}")
        props = get_device_properties(device_id)

        dev_type = props.get("device_type", "generic")
        dev_label = props.get("device_label", "Generic Device")
        api = props.get("api", "")
        abi = props.get("abi", "")
        version = props.get("version", "")
        product = props.get("product", "")

        print_ok(f"Device Type: {Colors.CYAN}{dev_label}{Colors.RESET}")
        print_ok(f"API Level: {Colors.CYAN}{api}{Colors.RESET}")
        print_ok(f"Architecture: {Colors.CYAN}{abi}{Colors.RESET}")
        print_ok(f"Android Version: {Colors.CYAN}{version}{Colors.RESET}")

        guidance = get_root_guidance(dev_type, dev_label)
        if not guidance["supported"]:
            has_root = check_root_access(device_id)
            if has_root:
                print_ok(f"Root Status: {Colors.GREEN}ACTIVE ({dev_label}){Colors.RESET}")
            else:
                print_warning(f"Root Status: {Colors.YELLOW}NOT ACTIVE on {dev_label}{Colors.RESET}")
                print_modal(guidance["title"], guidance["message"])
            continue

        ramdisk = find_ramdisk_path(api, abi)
        if not ramdisk:
            print_warning(f"ramdisk.img not found for API {api} and ABI {abi}")
            continue

        print_ok(f"ramdisk.img found: {Colors.CYAN}{ramdisk}{Colors.RESET}")
        compatible_devices.append({
            "id": device_id,
            "api": api,
            "abi": abi,
            "version": version,
            "product": product,
            "ramdisk": ramdisk,
        })

    if not compatible_devices:
        print_error("No compatible devices found for rooting via rootAVD!")
        pause()
        return

    headers = ["#", "Device ID", "API", "Arch", "Ramdisk"]
    rows = [[str(i), f"{Colors.CYAN}{d['id']}{Colors.RESET}", f"{Colors.YELLOW}{d['api']}{Colors.RESET}", f"{Colors.BLUE}{d['abi']}{Colors.RESET}", f"{Colors.DIM}{d['ramdisk'][:40]}...{Colors.RESET}"] for i, d in enumerate(compatible_devices, 1)]
    print_table(headers, rows, [5, 20, 8, 15, 45])

    print_modal("SELECT DEVICES", f"Separate with space (e.g. {Colors.CYAN}1 3{Colors.RESET}) or type {Colors.YELLOW}'all'{Colors.RESET}")
    choice = input(f"  {Colors.PURPLE}►{Colors.RESET} Choice: ").strip()

    if choice.lower() == "all":
        selected_indices = list(range(1, len(compatible_devices) + 1))
    else:
        try:
            selected_indices = [int(x.strip()) for x in choice.split()]
        except ValueError:
            print_error("Invalid input!")
            pause()
            return

    for idx in selected_indices:
        if 1 <= idx <= len(compatible_devices):
            dev = compatible_devices[idx - 1]
            print_modal(f"ROOTING DEVICE: {Colors.CYAN}{dev['id']}{Colors.RESET}")
            print_info("Executing rootAVD...")

            success, msg = execute_rootavd(
                dev["id"],
                dev["ramdisk"],
                output_callback=lambda line: print(f"  {Colors.DIM}{line}{Colors.RESET}")
            )

            if success:
                print_ok(f"Device {Colors.CYAN}{dev['id']}{Colors.RESET} successfully rooted!")
            else:
                print_warning(f"Rooting status: {msg}")

    print_modal("SUCCESS", "Autoroot process completed! Please cold-boot / restart AVD.")
    pause()


def list_devices_menu():
    """List all connected devices with detailed information"""
    clear_screen()
    print_modal("LIST CONNECTED DEVICES")
    auto_connect_ldplayer()

    devices = detect_devices()
    if not devices:
        print_error("No devices detected!")
        pause()
        return

    headers = ["#", "Device ID", "Status", "Information"]
    rows = [
        [
            str(i),
            f"{Colors.CYAN}{d.id}{Colors.RESET}",
            f"{Colors.SUCCESS}{d.status}{Colors.RESET}",
            f"{Colors.DIM}{d.info}{Colors.RESET}",
        ]
        for i, d in enumerate(devices, 1)
    ]
    print_table(headers, rows, [5, 20, 10, 40])
    print_info(f"Total devices found: {Colors.BOLD}{len(devices)}{Colors.RESET}")
    pause()


def exit_script():
    """Exit script with optional cleanup"""
    clear_screen()
    print_modal("EXIT")
    print(f"  {Colors.YELLOW}Would you like to stop all Frida Servers before exiting?{Colors.RESET}")
    print()
    print(f"  {Colors.CYAN}[1]{Colors.RESET} {Colors.GREEN}Yes, stop all and exit{Colors.RESET}")
    print(f"  {Colors.CYAN}[2]{Colors.RESET} {Colors.YELLOW}No, keep running{Colors.RESET}")
    print()
    choice = input(f"  {Colors.PURPLE}►{Colors.RESET} Choice: ").strip()

    if choice == "1":
        print()
        print_info("Stopping all Frida Servers...")
        devices = detect_devices()
        for d in devices:
            stop_frida_server(d.id)
            print(f"  {Colors.GREEN}[✓]{Colors.RESET} Stopped on {Colors.CYAN}{d.id}{Colors.RESET}")
            time.sleep(0.2)

        animate_loading("Removing port forwarding", 0.8)
        remove_all_port_forwards()

        if os.name == "nt":
            animate_loading("Closing Frida windows", 0.8)
            run_command(["taskkill", "/FI", "WindowTitle eq Frida-*", "/F"], capture_output=False)

        port_file = get_project_root() / "port_mapping.txt"
        if port_file.exists():
            port_file.unlink()

        print_ok("All Frida Servers stopped.")
        time.sleep(0.5)

    animate_exit()
    sys.exit(0)


def main_menu():
    """Classic single-column main menu loop"""
    while True:
        clear_screen()
        print_ascii_header()

        _, _, host_warn = check_host_frida_environment()
        if host_warn:
            print_warning(host_warn)
            print()

        print_modal("MAIN MENU", "")
        print(f"  {Colors.CYAN}[1]{Colors.RESET} {Colors.GREEN}Setup Frida Server{Colors.RESET}")
        print(f"  {Colors.CYAN}[2]{Colors.RESET} {Colors.BLUE}Start Frida Server{Colors.RESET}")
        print(f"  {Colors.CYAN}[3]{Colors.RESET} {Colors.RED}Stop Frida Server{Colors.RESET}")
        print(f"  {Colors.CYAN}[4]{Colors.RESET} {Colors.YELLOW}Check Status{Colors.RESET}")
        print(f"  {Colors.CYAN}[5]{Colors.RESET} {Colors.PURPLE}View Processes{Colors.RESET}")
        print(f"  {Colors.CYAN}[6]{Colors.RESET} {Colors.CYAN}Port Management{Colors.RESET}")
        print(f"  {Colors.CYAN}[7]{Colors.RESET} {Colors.MAGENTA}Start Frida on Package{Colors.RESET}")
        print(f"  {Colors.CYAN}[8]{Colors.RESET} {Colors.YELLOW}Auto Root Devices (Android Studio){Colors.RESET}")
        print(f"  {Colors.CYAN}[9]{Colors.RESET} {Colors.INFO}List Devices{Colors.RESET}")
        print(f"  {Colors.CYAN}[10]{Colors.RESET} {Colors.RED}Exit{Colors.RESET}")
        print()

        choice = input(f"  {Colors.PURPLE}►{Colors.RESET} Select [{Colors.YELLOW}1-10{Colors.RESET}]: ").strip()

        if choice == "1":
            setup_frida()
        elif choice == "2":
            start_frida()
        elif choice == "3":
            stop_frida()
        elif choice == "4":
            check_status()
        elif choice == "5":
            view_processes()
        elif choice == "6":
            port_management()
        elif choice == "7":
            start_frida_package()
        elif choice == "8":
            autoroot()
        elif choice == "9":
            list_devices_menu()
        elif choice == "10":
            exit_script()
        else:
            print_error("Invalid choice!")
            time.sleep(1)


def run_cli():
    """Top-level CLI launcher"""
    os.chdir(get_project_root())
    if os.name == "nt":
        os.system("title Frida-Xtr - Multi-Device Manager")

    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user. Exiting...{Colors.RESET}")
        sys.exit(0)


if __name__ == "__main__":
    run_cli()
