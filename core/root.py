#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.root - Device Rooting & rootAVD Orchestration
Manages device-type safety checks (emulators vs physical), Android SDK ramdisk lookup,
and rootAVD automation for Android Studio AVD instances.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from .adb import get_project_root, run_command


def get_root_guidance(device_type: str, device_label: str) -> Dict[str, Any]:
    """
    Returns safety guidance and rooting advice for specific device platforms.
    """
    if device_type == "ldplayer":
        return {
            "supported": False,
            "title": "LDPLAYER ROOT GUIDANCE",
            "message": (
                "LDPlayer does not use rootAVD (Android SDK ramdisk).\n"
                "LDPlayer includes built-in Root functionality:\n"
                "  1. Open LDPlayer\n"
                "  2. Click the Settings icon (⚙) in the top-right corner\n"
                "  3. Go to 'Other Settings' / 'Basic'\n"
                "  4. Find 'Root Permission' > Toggle to 'Enable'\n"
                "  5. Click 'Save' and restart LDPlayer.\n"
                "After restarting, root access will be active for Frida!"
            ),
        }
    elif device_type in ["nox", "memu", "mumu", "bluestacks"]:
        return {
            "supported": False,
            "title": f"{device_label.upper()} ROOT GUIDANCE",
            "message": (
                f"{device_label} has built-in root settings in its configuration menu.\n"
                f"Please open {device_label} Settings > enable 'Root Permission' > Save & Restart."
            ),
        }
    elif device_type == "genymotion":
        return {
            "supported": False,
            "title": "GENYMOTION ROOT GUIDANCE",
            "message": (
                "Genymotion has superuser/root access enabled by default in its system."
            ),
        }
    elif device_type == "wsa":
        return {
            "supported": False,
            "title": "WSA ROOT GUIDANCE",
            "message": (
                "Windows Subsystem for Android (WSA) requires MagiskOnWSA / WSABuilds for root functionality."
            ),
        }
    elif device_type == "physical":
        return {
            "supported": False,
            "title": "PHYSICAL DEVICE GUIDANCE",
            "message": (
                "Physical device detected. The 'rootAVD' script is specifically designed for Android Studio AVD.\n"
                "For physical devices, please use Magisk, KernelSU, or APatch via Bootloader & Fastboot."
            ),
        }
    elif device_type in ["avd", "generic"]:
        return {
            "supported": True,
            "title": "ANDROID STUDIO AVD ROOT",
            "message": "Android Studio AVD is supported for automated rooting via rootAVD.",
        }

    return {
        "supported": False,
        "title": "UNSUPPORTED DEVICE",
        "message": f"Device type {device_label} does not support automatic rooting via rootAVD.",
    }


def resolve_android_home() -> Optional[Path]:
    """Determine Android SDK directory from environment variables or standard locations."""
    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if android_home and Path(android_home).exists():
        return Path(android_home)

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidate = Path(local_app_data) / "Android" / "Sdk"
            if candidate.exists():
                return candidate
    else:
        home = Path.home()
        candidates = [
            home / "Library" / "Android" / "sdk",
            home / "Android" / "Sdk",
        ]
        for c in candidates:
            if c.exists():
                return c

    return None


def find_ramdisk_path(
    api: str, abi: str, android_home: Optional[Path] = None
) -> Optional[str]:
    """
    Search for ramdisk.img or ramdisk-qemu.img matching the API and ABI in system-images.
    Returns relative path starting with 'system-images/...'.
    """
    if android_home is None:
        android_home = resolve_android_home()

    if not android_home or not android_home.exists():
        return None

    abi_to_arch = {
        "x86": "x86",
        "x86_64": "x86_64",
        "armeabi-v7a": "armeabi-v7a",
        "arm64-v8a": "arm64-v8a",
    }
    arch = abi_to_arch.get(abi, abi)
    system_images_dir = android_home / "system-images"

    if not system_images_dir.exists():
        return None

    patterns = [
        f"android-{api}/google_apis_playstore/{arch}/ramdisk.img",
        f"android-{api}/google_apis/{arch}/ramdisk.img",
        f"android-{api}/google_apis_playstore/{arch}/ramdisk-qemu.img",
        f"android-{api}/google_apis/{arch}/ramdisk-qemu.img",
    ]

    if api == "31":
        patterns.extend(
            [
                f"android-S/google_apis_playstore/{arch}/ramdisk.img",
                f"android-S/google_apis/{arch}/ramdisk.img",
                f"android-Sv2/google_apis_playstore/{arch}/ramdisk.img",
                f"android-Sv2/google_apis/{arch}/ramdisk.img",
            ]
        )

    for pat in patterns:
        target = system_images_dir / pat
        if target.exists():
            return f"system-images/{pat}".replace("\\", "/")

    # Recursive directory walk fallback
    for root, _, files in os.walk(system_images_dir):
        matched_file = None
        if "ramdisk.img" in files:
            matched_file = "ramdisk.img"
        elif "ramdisk-qemu.img" in files:
            matched_file = "ramdisk-qemu.img"

        if matched_file:
            full_path = Path(root) / matched_file
            try:
                rel_path = full_path.relative_to(android_home)
                rel_str = str(rel_path).replace("\\", "/")
                if f"android-{api}" in rel_str and arch in rel_str:
                    return rel_str
            except ValueError:
                pass

    return None


def execute_rootavd(
    device_id: str,
    ramdisk_rel_path: str,
    rootavd_dir: Optional[Path] = None,
    android_home: Optional[Path] = None,
    output_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str]:
    """
    Run rootAVD.bat (Windows) or rootAVD.sh (Unix) targeting the specified device and ramdisk.
    """
    if rootavd_dir is None:
        rootavd_dir = get_project_root() / "rootAVD"

    if not rootavd_dir.exists():
        return (
            False,
            f"rootAVD folder not found at '{rootavd_dir}'. "
            "To use automated AVD rooting, please download rootAVD from https://github.com/newbit1/rootAVD "
            "and place the 'rootAVD' folder into the project root directory.",
        )

    if android_home is None:
        android_home = resolve_android_home()

    if not android_home or not android_home.exists():
        return False, "ANDROID_HOME path could not be resolved or does not exist"

    # Verify ramdisk file
    norm_path = ramdisk_rel_path.replace("/", os.sep).replace("\\", os.sep)
    full_ramdisk = android_home / norm_path
    if not full_ramdisk.exists():
        return False, f"Ramdisk file not found at {full_ramdisk}"

    if os.name == "nt":
        script_file = rootavd_dir / "rootAVD.bat"
        if not script_file.exists():
            return False, "rootAVD.bat not found"
        cmd = [str(script_file), ramdisk_rel_path.replace("/", "\\")]
    else:
        script_file = rootavd_dir / "rootAVD.sh"
        if not script_file.exists():
            return False, "rootAVD.sh not found"
        cmd = ["bash", str(script_file), ramdisk_rel_path]

    env = os.environ.copy()
    env["ANDROID_HOME"] = str(android_home)
    env["ANDROID_SERIAL"] = device_id

    original_dir = os.getcwd()
    try:
        os.chdir(rootavd_dir)
        if output_callback:
            output_callback(f"Executing: {' '.join(cmd)}")

        proc = subprocess.Popen(
            cmd,
            cwd=str(rootavd_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        output_lines = []
        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                line_clean = line.rstrip()
                output_lines.append(line_clean)
                if output_callback:
                    output_callback(line_clean)

        proc.wait()
        if proc.returncode == 0:
            return True, "rootAVD execution completed successfully"
        return False, f"rootAVD failed with exit code {proc.returncode}"
    except Exception as e:
        return False, f"Execution error: {str(e)}"
    finally:
        os.chdir(original_dir)
