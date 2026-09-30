#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.frida_engine - Frida Server Lifecycle & Daemon Operations
Handles binary validation, ELF parsing, push/chmod, daemon management,
connection health checking, and process enumeration.
"""

import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import frida
except ImportError:
    frida = None

from .adb import (
    check_root_access,
    get_device_architecture,
    get_project_root,
    probe_port,
    run_command,
    setup_port_forward,
)

DEFAULT_FRIDA_PORT: int = 27042

ARCH_TO_FILE: Dict[str, str] = {
    "x86": "frida-server-x86",
    "x86_64": "frida-server-x86_64",
    "arm64-v8a": "frida-server-arm64",
    "armeabi-v7a": "frida-server-arm",
}

COMPATIBILITY_MAP: Dict[str, List[str]] = {
    "x86_64": ["x86_64", "x86-64"],
    "x86": ["x86"],
    "arm64-v8a": ["arm64", "aarch64", "arm64-v8a"],
    "armeabi-v7a": ["arm", "armeabi-v7a"],
}


def check_host_frida_environment() -> Tuple[bool, bool, str]:
    """
    Check if frida-tools CLI and Python frida package are available on host system.
    Returns: (has_frida_tools, has_frida_lib, warning_message)
    """
    has_frida_tools = shutil.which("frida-ps") is not None
    has_frida_lib = frida is not None
    msg = ""
    if not has_frida_tools and not has_frida_lib:
        msg = "frida & frida-tools are not installed. Run: pip install -r requirements.txt"
    elif not has_frida_tools:
        msg = "frida-tools CLI (frida-ps) was not found in PATH. Run: pip install frida-tools"
    elif not has_frida_lib:
        msg = "Python package 'frida' is not installed. Run: pip install frida"
    return has_frida_tools, has_frida_lib, msg


def check_frida_server_file(base_dir: Optional[Path] = None) -> bool:
    """Check if any frida-server binary is present in server/ or project root."""
    return len(get_available_frida_server_files(base_dir)) > 0


def get_available_frida_server_files(base_dir: Optional[Path] = None) -> List[Path]:
    """Get list of available frida-server files found in server/ and project root."""
    if base_dir is None:
        base_dir = get_project_root()
    server_dir = base_dir / "server"

    search_dirs = [server_dir, base_dir]
    possible_names = [
        "frida-server",
        "frida-server-x86",
        "frida-server-x86_64",
        "frida-server-arm64",
        "frida-server-arm",
    ]

    found_files: List[Path] = []
    seen_names = set()

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for name in possible_names:
            candidate = s_dir / name
            if candidate.exists() and candidate.is_file() and name not in seen_names:
                found_files.append(candidate)
                seen_names.add(name)

    return found_files


def get_frida_server_file_for_architecture(
    device_abi: str, base_dir: Optional[Path] = None
) -> Optional[Path]:
    """Locate the matching frida-server binary for the specified device ABI."""
    if base_dir is None:
        base_dir = get_project_root()
    server_dir = base_dir / "server"

    file_name = ARCH_TO_FILE.get(device_abi)
    search_dirs = [server_dir, base_dir]

    if file_name:
        for s_dir in search_dirs:
            candidate = s_dir / file_name
            if candidate.exists() and candidate.is_file():
                return candidate

    # Fallback: check for generic 'frida-server'
    for s_dir in search_dirs:
        generic = s_dir / "frida-server"
        if generic.exists() and generic.is_file():
            return generic

    return None


def get_frida_server_architecture(file_path: Optional[Path] = None) -> Optional[str]:
    """
    Detect frida-server architecture by reading the ELF header e_machine field.
    0x03 -> x86 (EM_386)
    0x3E -> x86_64 (EM_X86_64)
    0x28 -> armeabi-v7a (EM_ARM)
    0xB7 -> arm64-v8a (EM_AARCH64)
    """
    if file_path is None:
        files = get_available_frida_server_files()
        if not files:
            return None
        file_path = files[0]

    if not file_path.exists():
        return None

    try:
        with open(file_path, "rb") as f:
            header = f.read(20)
            if len(header) >= 20 and header[0:4] == b"\x7fELF":
                machine = int.from_bytes(header[18:20], byteorder="little")
                if machine == 0x3E:
                    return "x86_64"
                elif machine == 0x03:
                    return "x86"
                elif machine == 0xB7:
                    return "arm64-v8a"
                elif machine == 0x28:
                    return "armeabi-v7a"
    except Exception:
        pass

    # Fallback to file command on Unix/macOS
    if os.name != "nt":
        rc, output, _ = run_command(["file", str(file_path)])
        if rc == 0:
            out_lower = output.lower()
            if "x86-64" in out_lower or "x86_64" in out_lower or "amd64" in out_lower:
                return "x86_64"
            elif "x86" in out_lower and "x86-64" not in out_lower:
                return "x86"
            elif "arm64" in out_lower or "aarch64" in out_lower:
                return "arm64-v8a"
            elif "arm" in out_lower:
                return "armeabi-v7a"

    return None


def check_architecture_compatibility(
    device_abi: str, frida_arch: Optional[str]
) -> Tuple[bool, str]:
    """Verify if the device ABI matches the frida-server binary architecture."""
    if not frida_arch or not device_abi:
        return True, "unknown"

    device_arch = device_abi.lower()
    frida_arch_lower = frida_arch.lower()

    if device_arch in COMPATIBILITY_MAP:
        for arch in COMPATIBILITY_MAP[device_arch]:
            if arch in frida_arch_lower:
                return True, frida_arch

    if device_arch == "x86_64" and frida_arch_lower == "x86":
        return False, f"Device is {device_arch} but frida-server is {frida_arch} (incompatible)"

    if device_arch == "x86" and ("x86_64" in frida_arch_lower or "x86-64" in frida_arch_lower):
        return False, f"Device is {device_arch} (32-bit) but frida-server is {frida_arch} (64-bit) - ARCHITECTURE MISMATCH"

    return False, f"Device architecture {device_arch} is not compatible with frida-server {frida_arch}"


# In-memory status cache to avoid blocking UI rendering
_FRIDA_STATUS_CACHE: Dict[str, Tuple[bool, float]] = {}
FRIDA_STATUS_CACHE_TTL: float = 10.0  # seconds


def set_frida_server_cached_status(device_id: str, is_running: bool) -> None:
    """Manually update the cached status for a device."""
    _FRIDA_STATUS_CACHE[device_id] = (is_running, time.time())


def invalidate_frida_server_cache(device_id: Optional[str] = None) -> None:
    """Clear cached Frida server status."""
    if device_id:
        _FRIDA_STATUS_CACHE.pop(device_id, None)
    else:
        _FRIDA_STATUS_CACHE.clear()


def is_frida_server_running(device_id: str, use_cache: bool = True) -> bool:
    """
    Check if frida-server daemon is active on device using fast pidof or ps check.
    Uses memory cache when use_cache=True for instantaneous, non-blocking UI updates.
    """
    now = time.time()
    if use_cache and device_id in _FRIDA_STATUS_CACHE:
        val, ts = _FRIDA_STATUS_CACHE[device_id]
        return val

    # Fast check via pidof
    rc, out, _ = run_command(["adb", "-s", device_id, "shell", "pidof frida-server"], timeout=0.8)
    if rc == 0 and out.strip():
        _FRIDA_STATUS_CACHE[device_id] = (True, now)
        return True

    # Fast ps check without hanging
    rc, out, _ = run_command(
        ["adb", "-s", device_id, "shell", "ps -A | grep frida-server || ps | grep frida-server"],
        timeout=1.0,
    )
    is_running = (rc == 0 and "frida-server" in out)
    _FRIDA_STATUS_CACHE[device_id] = (is_running, now)
    return is_running


def test_frida_connection(target: str, is_host_port: bool = True, timeout: float = 1.5) -> Tuple[bool, str]:
    """
    Test active connectivity to frida-server with dual-engine fallback (CLI + Python API).
    Pre-probes TCP socket to avoid long timeouts on closed ports.
    """
    host_target = target
    if is_host_port:
        if ":" not in host_target:
            host_target = f"127.0.0.1:{host_target}"
        host, _, port_str = host_target.partition(":")
        try:
            p = int(port_str)
            if not probe_port(p, host=host or "127.0.0.1", timeout=0.08):
                return False, "Port closed"
        except (ValueError, TypeError):
            pass

    # Method 1: frida-ps CLI
    if shutil.which("frida-ps"):
        cmd = ["frida-ps", "-H", host_target] if is_host_port else ["frida-ps", "-D", target, "-a"]
        rc, _, _ = run_command(cmd, capture_output=True, timeout=timeout)
        if rc == 0:
            return True, "frida-ps CLI"

    # Method 2: Python frida API
    if frida is not None:
        try:
            if is_host_port:
                mgr = frida.get_device_manager()
                dev = mgr.add_remote_device(host_target)
                dev.enumerate_processes()
                return True, "Python frida API"
            else:
                dev = frida.get_device(target)
                dev.enumerate_processes()
                return True, "Python frida API"
        except Exception as e:
            return False, str(e)

    return False, "frida-tools and Python frida API could not be reached"


def setup_frida_server(
    device_id: str,
    device_abi: Optional[str] = None,
    server_file: Optional[Path] = None,
    use_root: Optional[bool] = None,
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Tuple[bool, str]:
    """
    Deploys frida-server binary to /data/local/tmp/frida-server with safe chmod.
    """
    def log(step: str, status: str):
        if progress_callback:
            progress_callback(step, status)

    if not device_abi:
        device_abi = get_device_architecture(device_id) or "unknown"
        log("ARCH", f"Detected device ABI: {device_abi}")

    if server_file is None:
        server_file = get_frida_server_file_for_architecture(device_abi)

    if not server_file or not server_file.exists():
        err_msg = f"frida-server binary for ABI {device_abi} was not found"
        log("ERROR", err_msg)
        return False, err_msg

    if use_root is None:
        use_root = check_root_access(device_id)
    log("ROOT", f"Root access: {'Yes' if use_root else 'No'}")

    # Stop existing instance to avoid 'Text file busy'
    log("STOP", "Stopping running frida-server...")
    if use_root:
        run_command(["adb", "-s", device_id, "shell", "su", "-c", "pkill -9 frida-server"])
    run_command(["adb", "-s", device_id, "shell", "pkill -9 frida-server"])
    time.sleep(0.5)

    # Push to temp file
    temp_name = f"frida-server-temp-{device_abi}"
    log("PUSH", f"Pushing {server_file.name} to /data/local/tmp/{temp_name}...")
    rc, out, err = run_command(
        ["adb", "-s", device_id, "push", str(server_file), f"/data/local/tmp/{temp_name}"]
    )
    if rc != 0:
        err_msg = f"Push failed: {err or out}"
        log("ERROR", err_msg)
        return False, err_msg

    # Remove old binary
    log("CLEAN", "Removing old /data/local/tmp/frida-server...")
    rm_cmd = "rm -f /data/local/tmp/frida-server"
    if use_root:
        run_command(["adb", "-s", device_id, "shell", "su", "-c", rm_cmd])
    else:
        run_command(["adb", "-s", device_id, "shell", rm_cmd])

    # Rename temp to target
    log("RENAME", "Moving to /data/local/tmp/frida-server...")
    mv_cmd = f"mv /data/local/tmp/{temp_name} /data/local/tmp/frida-server"
    if use_root:
        rc, _, _ = run_command(["adb", "-s", device_id, "shell", "su", "-c", mv_cmd])
    else:
        rc, _, _ = run_command(["adb", "-s", device_id, "shell", mv_cmd])

    if rc != 0:
        cp_cmd = f"cp -f /data/local/tmp/{temp_name} /data/local/tmp/frida-server && rm /data/local/tmp/{temp_name}"
        if use_root:
            run_command(["adb", "-s", device_id, "shell", "su", "-c", cp_cmd])
        else:
            run_command(["adb", "-s", device_id, "shell", cp_cmd])

    # Set permissions 755
    log("CHMOD", "Applying chmod 755...")
    chmod_cmd = "chmod 755 /data/local/tmp/frida-server"
    if use_root:
        run_command(["adb", "-s", device_id, "shell", "su", "-c", chmod_cmd])
    else:
        run_command(["adb", "-s", device_id, "shell", chmod_cmd])

    # Verify presence
    rc, out, _ = run_command(
        ["adb", "-s", device_id, "shell", "test -f /data/local/tmp/frida-server && echo 'exists' || echo 'not found'"]
    )
    if "exists" in out:
        log("SUCCESS", "Frida Server binary setup completed successfully.")
        return True, "Setup success"

    log("ERROR", "Binary verification failed after push.")
    return False, "Verification failed"


def start_frida_server(
    device_id: str,
    local_port: int = DEFAULT_FRIDA_PORT,
    use_root: Optional[bool] = None,
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Tuple[bool, str]:
    """
    Start Frida server daemon on device, establish port forwarding, and verify handshake.
    """
    def log(step: str, status: str):
        if progress_callback:
            progress_callback(step, status)

    # Verify presence on device
    rc, out, _ = run_command(
        ["adb", "-s", device_id, "shell", "test -f /data/local/tmp/frida-server && echo 'exists' || echo 'not found'"]
    )
    if "exists" not in out:
        log("ERROR", "frida-server not found on device. Run setup first.")
        return False, "frida-server file not found on device"

    if use_root is None:
        use_root = check_root_access(device_id)

    # Kill old instances
    log("STOP", "Stopping previous frida-server...")
    if use_root:
        run_command(["adb", "-s", device_id, "shell", "su", "-c", "pkill -9 frida-server"])
        run_command(["adb", "-s", device_id, "shell", "su", "-c", "setenforce 0"])
    run_command(["adb", "-s", device_id, "shell", "pkill -9 frida-server"])
    time.sleep(0.5)

    # Spawn daemon via nohup
    log("SPAWN", "Spawning frida-server daemon...")
    start_cmd = "nohup /data/local/tmp/frida-server -l 0.0.0.0 >/dev/null 2>&1 &"
    if use_root:
        run_command(["adb", "-s", device_id, "shell", "su", "-c", start_cmd])
    else:
        run_command(["adb", "-s", device_id, "shell", start_cmd])

    # Wait for process to spawn
    log("WAIT", "Waiting for daemon to initialize...")
    is_running = False
    for _ in range(5):
        time.sleep(1.0)
        if is_frida_server_running(device_id):
            is_running = True
            break

    if not is_running:
        log("RETRY", "Trying alternative background launcher...")
        alt_cmd = "/data/local/tmp/frida-server -l 0.0.0.0 &"
        if use_root:
            run_command(["adb", "-s", device_id, "shell", "su", "-c", alt_cmd])
        else:
            run_command(["adb", "-s", device_id, "shell", alt_cmd])
        time.sleep(2.0)
        if is_frida_server_running(device_id):
            is_running = True

    if not is_running:
        log("ERROR", "Frida server process failed to spawn.")
        return False, "Failed to start frida-server daemon"

    # Setup port forwarding
    log("PORT", f"Forwarding localhost:{local_port} -> device:27042...")
    fwd_ok, fwd_msg = setup_port_forward(device_id, local_port, 27042)
    if not fwd_ok:
        log("WARNING", f"Port forwarding notice: {fwd_msg}")

    time.sleep(1.0)

    # Test connection
    log("PROBE", "Verifying connection handshake...")
    connected = False
    conn_engine = ""
    for _ in range(3):
        ok, engine = test_frida_connection(f"127.0.0.1:{local_port}", is_host_port=True)
        if ok:
            connected = True
            conn_engine = engine
            break
        time.sleep(1.0)

    if connected:
        set_frida_server_cached_status(device_id, True)
        log("SUCCESS", f"Connected via {conn_engine} on localhost:{local_port}")
        return True, f"Online on port {local_port} [{conn_engine}]"

    # Test direct USB connection fallback
    usb_ok, usb_engine = test_frida_connection(device_id, is_host_port=False)
    if usb_ok:
        set_frida_server_cached_status(device_id, True)
        log("SUCCESS", f"Connected directly via USB [{usb_engine}]")
        return True, f"Online via USB [{usb_engine}]"

    has_tools, has_lib, host_warn = check_host_frida_environment()
    err_detail = host_warn if host_warn else "Unable to establish handshake with daemon"
    log("ERROR", err_detail)
    return False, err_detail


def stop_frida_server(
    device_id: str,
    local_port: Optional[int] = None,
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Tuple[bool, str]:
    """
    Stop frida-server daemon on target device and remove associated port forwards.
    """
    def log(step: str, status: str):
        if progress_callback:
            progress_callback(step, status)

    log("STOP", f"Stopping frida-server on {device_id}...")
    run_command(["adb", "-s", device_id, "shell", "su", "-c", "pkill -9 frida-server"])
    run_command(["adb", "-s", device_id, "shell", "pkill -9 frida-server"])

    log("PORT", f"Removing port forwards for {device_id}...")
    run_command(["adb", "-s", device_id, "forward", "--remove-all"])

    set_frida_server_cached_status(device_id, False)
    log("SUCCESS", f"Frida server stopped on {device_id}")
    return True, "Stopped successfully"


def view_device_processes(
    target: str, is_host_port: bool = True
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Fetch running process list from Frida server target.
    Returns: (success, process_list, error_message)
    """
    host_target = target
    if is_host_port and ":" not in host_target:
        host_target = f"127.0.0.1:{host_target}"

    procs: List[Dict[str, Any]] = []

    # Try Python API first
    if frida is not None:
        try:
            if is_host_port:
                mgr = frida.get_device_manager()
                dev = mgr.add_remote_device(host_target)
            else:
                dev = frida.get_device(target)
            for p in dev.enumerate_processes():
                procs.append({"pid": p.pid, "name": p.name})
            procs.sort(key=lambda x: x["name"].lower())
            return True, procs, ""
        except Exception as e:
            pass

    # Fallback to frida-ps CLI
    if shutil.which("frida-ps"):
        cmd = ["frida-ps", "-H", host_target] if is_host_port else ["frida-ps", "-D", target]
        rc, out, err = run_command(cmd)
        if rc == 0:
            lines = out.strip().split("\n")
            for line in lines:
                line_clean = line.strip()
                if not line_clean or any(h in line_clean.lower() for h in ["pid", "name", "---", "==="]):
                    continue
                parts = line_clean.split(maxsplit=1)
                if len(parts) == 2 and parts[0].isdigit():
                    procs.append({"pid": int(parts[0]), "name": parts[1].strip()})
            procs.sort(key=lambda x: x["name"].lower())
            return True, procs, ""

    return False, [], "Failed to enumerate processes via Frida"
