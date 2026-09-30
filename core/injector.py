#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.injector - Application Package Enumeration & Frida Script Runner
Discovers local JS hook scripts, Codeshare presets, installed Android packages,
and launches Frida injection sessions in interactive terminal windows.
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import frida
except ImportError:
    frida = None

from .adb import get_project_root, run_command

CODESHARE_PRESETS: List[Dict[str, str]] = [
    {
        "id": "1",
        "title": "Universal SSL Pinning Bypass 2",
        "author": "sowdust",
        "name": "sowdust/universal-android-ssl-pinning-bypass-2",
        "description": "Standard universal TLS/SSL certificate pinning bypass.",
    },
    {
        "id": "2",
        "title": "Universal SSL Pinning Bypass with Frida",
        "author": "pcipolloni",
        "name": "pcipolloni/universal-android-ssl-pinning-bypass-with-frida",
        "description": "Comprehensive trust manager and OkHttp bypass.",
    },
    {
        "id": "3",
        "title": "Frida Multiple Bypass",
        "author": "fdciabdul",
        "name": "fdciabdul/frida-multiple-bypass",
        "description": "Root & SSL pinning multi-target bypass.",
    },
    {
        "id": "4",
        "title": "Fridantiroot",
        "author": "dzonerzy",
        "name": "dzonerzy/fridantiroot",
        "description": "Root detection evasion hooks.",
    },
    {
        "id": "5",
        "title": "Who Does It Call",
        "author": "oleavr",
        "name": "oleavr/who-does-it-call",
        "description": "Live method call tracing helper.",
    },
]


def get_scripts_from_folder(scripts_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """Scan scripts/ directory for available .js files."""
    if scripts_dir is None:
        scripts_dir = get_project_root() / "scripts"

    scripts: List[Dict[str, str]] = []
    if not scripts_dir.exists():
        return scripts

    for file_path in scripts_dir.glob("*.js"):
        if file_path.is_file():
            scripts.append(
                {
                    "name": file_path.name,
                    "path": str(file_path),
                    "relative_path": str(file_path.relative_to(get_project_root())),
                }
            )

    scripts.sort(key=lambda x: x["name"].lower())
    return scripts


def get_package_list(device_id: str, port: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Get installed applications/packages from device using 3-tier cascade:
    1. Python frida library (enumerate_applications)
    2. frida-ps CLI (-ai flag)
    3. ADB fallback (pm list packages)
    """
    packages: List[Dict[str, str]] = []
    seen = set()

    # Method 1: Python frida library
    if frida is not None:
        try:
            dev = None
            if port:
                try:
                    mgr = frida.get_device_manager()
                    dev = mgr.add_remote_device(f"127.0.0.1:{port}")
                except Exception:
                    pass
            if not dev and device_id:
                try:
                    dev = frida.get_device(device_id)
                except Exception:
                    pass

            if dev:
                for app in dev.enumerate_applications():
                    if app.identifier not in seen:
                        seen.add(app.identifier)
                        packages.append(
                            {
                                "line": f"{app.name:<25} {app.identifier}",
                                "package": app.identifier,
                                "name": app.name,
                            }
                        )
                if packages:
                    packages.sort(key=lambda x: x["package"].lower())
                    return packages
        except Exception:
            pass

    # Method 2: frida-ps CLI
    if shutil.which("frida-ps"):
        cmd = ["frida-ps", "-H", f"127.0.0.1:{port}", "-ai"] if port else ["frida-ps", "-D", device_id, "-ai"]
        returncode, output, _ = run_command(cmd)

        if returncode != 0 and device_id:
            returncode, output, _ = run_command(["frida-ps", "-D", device_id, "-ai"])

        if returncode == 0:
            lines = output.strip().split("\n")
            for line in lines:
                line_clean = line.strip()
                if not line_clean or any(
                    header in line_clean.lower()
                    for header in ["pid", "name", "identifier", "---", "==="]
                ):
                    continue

                parts = line_clean.split()
                if parts:
                    pkg = parts[-1]
                    if pkg.startswith(("com.", "org.", "net.", "io.", "id.", "app.")) or (
                        len(parts) > 1 and parts[0].isdigit()
                    ):
                        if pkg not in seen:
                            seen.add(pkg)
                            app_name = " ".join(parts[1:-1]) if len(parts) > 2 else pkg
                            packages.append(
                                {
                                    "line": line_clean,
                                    "package": pkg,
                                    "name": app_name,
                                }
                            )
            if packages:
                packages.sort(key=lambda x: x["package"].lower())
                return packages

    # Method 3: ADB fallback (pm list packages)
    if device_id:
        returncode, output, _ = run_command(
            ["adb", "-s", device_id, "shell", "pm list packages -3 || pm list packages"]
        )
        if returncode == 0:
            for line in output.strip().split("\n"):
                line_clean = line.strip()
                if line_clean.startswith("package:"):
                    pkg = line_clean.replace("package:", "").strip()
                    if pkg and pkg not in seen:
                        seen.add(pkg)
                        packages.append({"line": pkg, "package": pkg, "name": pkg})
            packages.sort(key=lambda x: x["package"].lower())

    return packages


def build_frida_command(
    target_host_port: str,
    package_name: str,
    script_args: List[str],
    spawn_mode: bool = True,
) -> List[str]:
    """Constructs the Frida CLI arguments list."""
    cmd = ["frida", "-H", target_host_port]
    if spawn_mode:
        cmd.extend(["-f", package_name])
    else:
        cmd.extend(["-n", package_name])
    cmd.extend(script_args)
    return cmd


def launch_frida_session(
    device_id: str,
    port: str,
    package_name: str,
    script_name: str,
    frida_cmd: List[str],
    in_new_window: bool = True,
) -> Tuple[bool, str]:
    """
    Spawns an interactive terminal window executing Frida injection.
    """
    try:
        if os.name == "nt":
            temp_bat = tempfile.NamedTemporaryFile(mode="w", suffix=".bat", delete=False)
            temp_bat.write("@echo off\n")
            temp_bat.write(f"title Frida-Xtr - {package_name}\n")
            temp_bat.write("color 0A\n")
            temp_bat.write("echo.\n")
            temp_bat.write("echo ====================================================================\n")
            temp_bat.write(f"echo   Frida-Xtr INJECTION - {package_name}\n")
            temp_bat.write("echo ====================================================================\n")
            temp_bat.write("echo.\n")
            temp_bat.write(f"echo Device: {device_id}\n")
            temp_bat.write(f"echo Port: {port}\n")
            temp_bat.write(f"echo Script: {script_name}\n")
            temp_bat.write("echo.\n")
            temp_bat.write("echo [INFO] Starting Frida session...\n")
            temp_bat.write("echo [INFO] Press Ctrl+C to terminate\n")
            temp_bat.write("echo.\n")
            cmd_line = subprocess.list2cmdline(frida_cmd)
            temp_bat.write(cmd_line + "\n")
            temp_bat.write("echo.\n")
            temp_bat.write("if errorlevel 1 (\n")
            temp_bat.write("    echo.\n")
            temp_bat.write("    echo [ERROR] Failed to execute Frida session!\n")
            temp_bat.write("    echo.\n")
            temp_bat.write("    echo Possible causes:\n")
            temp_bat.write("      - Package name is invalid or not installed\n")
            temp_bat.write("      - Target application not found on device\n")
            temp_bat.write("      - Frida Server is not running properly\n")
            temp_bat.write("    echo.\n")
            temp_bat.write("    pause\n")
            temp_bat.write(")\n")
            temp_bat.write("pause\n")
            temp_bat.close()

            subprocess.Popen(
                [
                    "cmd",
                    "/c",
                    "start",
                    f"Frida-Xtr - {package_name}",
                    "cmd",
                    "/c",
                    temp_bat.name,
                ]
            )
            return True, "Launched in new Windows command prompt"
        else:
            # Unix / macOS window spawning
            try:
                subprocess.Popen(["xterm", "-e"] + frida_cmd + [";", "read"])
                return True, "Launched in xterm"
            except Exception:
                try:
                    subprocess.Popen(["gnome-terminal", "--"] + frida_cmd)
                    return True, "Launched in gnome-terminal"
                except Exception:
                    subprocess.Popen(frida_cmd)
                    return True, "Launched in background process"
    except Exception as e:
        return False, f"Failed to launch Frida window: {str(e)}"
