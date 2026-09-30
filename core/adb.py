#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.adb - Android Debug Bridge (ADB) Manager
Handles device enumeration, multi-emulator auto-discovery, TCP socket probing,
deduplication, device properties, root validation, and port forwardings.
"""

import os
import re
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def get_project_root() -> Path:
    """Return the base directory of the Frida-Xtr project."""
    return Path(__file__).resolve().parent.parent


# Common emulator ADB listening ports mapped by emulator brand
EMULATOR_PORT_MAP: Dict[str, List[int]] = {
    "LDPlayer": [5555, 5557, 5559, 5561, 5563, 5565, 5567, 5569, 5571, 5573, 5575, 5577, 5579, 5581, 5583, 5585],
    "NoxPlayer": [62001, 62025, 62026, 62027, 62028, 62029, 62030, 62031, 62032],
    "MEmu": [21503, 21513, 21523, 21533, 21543],
    "MuMu": [7555, 16384, 16416, 16448, 16480, 16512],
    "BlueStacks": [5555, 5565, 5575, 5585, 5595, 5605, 5615, 5625, 5635, 5645],
    "WSA": [58526],
}


@dataclass
class DeviceInfo:
    """Container for device metadata supporting both attribute and dict-style access."""
    id: str
    status: str
    info: str = ""
    model: str = ""
    product: str = ""
    abi: Optional[str] = None
    api: Optional[str] = None
    version: Optional[str] = None
    device_type: str = "generic"
    device_label: str = "Generic Android Device"
    has_root: bool = False
    port: Optional[int] = None

    def __getitem__(self, item: str) -> Any:
        """Allow dictionary-style access device['id'] for backward compatibility."""
        return getattr(self, item)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style setting."""
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-style get method."""
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to standard dictionary."""
        return {
            "id": self.id,
            "status": self.status,
            "info": self.info,
            "model": self.model,
            "product": self.product,
            "abi": self.abi or "",
            "api": self.api or "",
            "version": self.version or "",
            "device_type": self.device_type,
            "device_label": self.device_label,
            "has_root": self.has_root,
            "port": self.port,
        }


def run_command(
    cmd: List[str],
    check: bool = False,
    capture_output: bool = True,
    cwd: Optional[Path | str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = 30.0,
) -> Tuple[int, str, str]:
    """Execute a shell command with safety timeout, capturing returncode, stdout, and stderr."""
    try:
        if cwd:
            cwd = str(cwd)
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True if capture_output else False,
            check=check,
            cwd=cwd,
            env=env,
            timeout=timeout,
        )
        stdout = result.stdout if capture_output and result.stdout else ""
        stderr = result.stderr if capture_output and result.stderr else ""
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return 127, "", f"Executable '{cmd[0]}' not found in PATH"
    except Exception as e:
        return 1, "", str(e)


def probe_port(port: int, host: str = "127.0.0.1", timeout: float = 0.05) -> bool:
    """
    Non-blocking fast TCP socket probe to check if a local port is actively listening.
    Returns True if TCP connection succeeds immediately, False otherwise.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def probe_ports_parallel(ports: List[int], host: str = "127.0.0.1", timeout: float = 0.05) -> List[int]:
    """
    Parallel TCP socket probe across candidate ports for ultra-fast response.
    Returns list of confirmed listening ports.
    """
    unique_ports = sorted(list(set(ports)))
    if not unique_ports:
        return []
    with ThreadPoolExecutor(max_workers=min(32, len(unique_ports))) as executor:
        results = executor.map(lambda p: (p, probe_port(p, host, timeout)), unique_ports)
        return [p for p, is_open in results if is_open]


# Connection cooldown cache to avoid hammering unresponsive or non-ADB ports
_FAILED_CONNECT_COOLDOWN: Dict[int, float] = {}
COOLDOWN_DURATION_SEC = 60.0


def auto_connect_emulators(timeout: float = 1.5) -> List[str]:
    """
    Automatically discover and connect to active local Android emulators.
    Probes LDPlayer, Nox, MEmu, MuMu, BlueStacks, and WSA via fast TCP socket probing.
    Only invokes 'adb connect' on ports that are actively listening and not yet connected.
    Includes a 60-second failed-port cooldown and parallel connection workers.
    Returns list of newly connected addresses (e.g. ['127.0.0.1:5555']).
    """
    now = time.time()
    # Check current devices to avoid redundant connection attempts
    rc, out, _ = run_command(["adb", "devices"], timeout=3.0)
    current_out = out if rc == 0 else ""

    already_attached_ports: Set[int] = set()
    for line in current_out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of"):
            continue
        parts = line.split()
        if not parts:
            continue
        dev_id = parts[0]
        # Match 127.0.0.1:XXXX or localhost:XXXX
        if ":" in dev_id:
            try:
                p = int(dev_id.split(":")[-1])
                already_attached_ports.add(p)
            except ValueError:
                pass
        # Match emulator-5554 -> console port is 5554, adb port is 5555
        elif dev_id.startswith("emulator-"):
            try:
                console_port = int(dev_id.replace("emulator-", ""))
                already_attached_ports.add(console_port)
                already_attached_ports.add(console_port + 1)
            except ValueError:
                pass

    # Gather candidate emulator ports
    all_candidate_ports: List[int] = []
    for ports in EMULATOR_PORT_MAP.values():
        all_candidate_ports.extend(ports)

    # Filter out ports already attached in ADB, in cooldown, or known QEMU console ports (even 5554-5586)
    ports_to_probe = [
        p for p in set(all_candidate_ports)
        if p not in already_attached_ports
        and not (5554 <= p <= 5586 and p % 2 == 0)
        and (now - _FAILED_CONNECT_COOLDOWN.get(p, 0) > COOLDOWN_DURATION_SEC)
    ]
    if not ports_to_probe:
        return []

    # Parallel socket probe
    listening_ports = probe_ports_parallel(ports_to_probe, timeout=0.05)
    if not listening_ports:
        return []

    def _attempt_connect(port: int) -> Optional[str]:
        target = f"127.0.0.1:{port}"
        rc_conn, out_conn, _ = run_command(["adb", "connect", target], timeout=timeout)
        if (
            rc_conn == 0
            and ("connected" in out_conn.lower() or "already connected" in out_conn.lower())
            and "unable" not in out_conn.lower()
        ):
            return target
        _FAILED_CONNECT_COOLDOWN[port] = time.time()
        return None

    connected: List[str] = []
    with ThreadPoolExecutor(max_workers=min(16, len(listening_ports))) as executor:
        results = executor.map(_attempt_connect, listening_ports)
        connected = [res for res in results if res is not None]

    return connected


def auto_connect_ldplayer() -> List[str]:
    """
    Backward-compatible wrapper for multi-emulator auto discovery.
    Automatically connects to LDPlayer, Nox, MEmu, MuMu, BlueStacks, etc.
    """
    return auto_connect_emulators()


# Backward compatibility aliases
EMULATOR_PORT_PRESETS = EMULATOR_PORT_MAP
probe_tcp_port = probe_port
auto_detect_and_connect_emulators = auto_connect_emulators


def detect_devices(
    hydrate_properties: bool = False,
    auto_connect: bool = True,
    auto_connect_emulators: Optional[bool] = None,
    **kwargs: Any,
) -> List[DeviceInfo]:
    """
    Detect connected Android devices with automatic emulator discovery and deduplication.
    If auto_connect is True, probes known emulator ports and auto-connects to listening instances.
    If hydrate_properties is True, queries device ABI, API, model, and root status.
    """
    should_auto_connect = auto_connect if auto_connect_emulators is None else auto_connect_emulators
    if should_auto_connect:
        try:
            auto_connect_emulators_fn = globals().get("auto_connect_emulators")
            if auto_connect_emulators_fn:
                auto_connect_emulators_fn()
        except Exception:
            pass

    returncode, output, _ = run_command(["adb", "devices", "-l"])
    if returncode != 0:
        return []

    raw_devices: List[DeviceInfo] = []
    lines = output.strip().split("\n")
    for line in lines[1:]:  # Skip header
        line = line.strip()
        if not line or line.startswith("List"):
            continue

        parts = line.split()
        if len(parts) >= 2:
            device_id = parts[0]
            status = parts[1]
            info = " ".join(parts[2:]) if len(parts) > 2 else ""

            if status == "offline" and (device_id.startswith("127.0.0.1:") or device_id.startswith("localhost:")):
                # Cleanup offline local loopback connections
                run_command(["adb", "disconnect", device_id], timeout=2.0)
                continue

            if status == "device":
                model = ""
                product = ""
                model_match = re.search(r"model:(\S+)", info)
                product_match = re.search(r"product:(\S+)", info)
                if model_match:
                    model = model_match.group(1)
                if product_match:
                    product = product_match.group(1)

                raw_devices.append(
                    DeviceInfo(
                        id=device_id,
                        status=status,
                        info=info,
                        model=model,
                        product=product,
                    )
                )

    # Deduplicate ONLY true loopback alias duplicates (e.g. 127.0.0.1:5555 when emulator-5554 is attached).
    # Never discard distinct emulator instances (such as emulator-5554 and emulator-5556)!
    emu_console_ports: Set[int] = set()
    for dev in raw_devices:
        if dev.id.startswith("emulator-"):
            try:
                p = int(dev.id.replace("emulator-", ""))
                emu_console_ports.add(p)
            except ValueError:
                pass

    unique_devices: List[DeviceInfo] = []
    seen_ids: Set[str] = set()

    for dev in raw_devices:
        is_redundant_ip = False
        if ":" in dev.id and ("127.0.0.1" in dev.id or "localhost" in dev.id):
            try:
                ip_port = int(dev.id.split(":")[-1])
                # If emulator-(ip_port - 1) is already connected natively, this IP connection is a redundant mirror
                if (ip_port - 1) in emu_console_ports:
                    is_redundant_ip = True
                    run_command(["adb", "disconnect", dev.id], timeout=2.0)
            except ValueError:
                pass

        if not is_redundant_ip and dev.id not in seen_ids:
            seen_ids.add(dev.id)
            unique_devices.append(dev)

    # Assign cached port mappings if available
    port_mappings = load_port_mappings()
    active_forwards = get_active_port_forwards()
    for dev in unique_devices:
        if dev.id in active_forwards:
            dev.port = active_forwards[dev.id]
        elif dev.id in port_mappings:
            dev.port = port_mappings[dev.id]

        if hydrate_properties:
            props = get_device_properties(dev.id)
            dev.abi = props.get("abi")
            dev.api = props.get("api")
            dev.version = props.get("version")
            dev.device_type = props.get("device_type", "generic")
            dev.device_label = props.get("device_label", "Generic Android Device")
            dev.has_root = check_root_access(dev.id)

    return unique_devices


def get_device_architecture(device_id: str) -> Optional[str]:
    """Query ro.product.cpu.abi via adb getprop."""
    returncode, output, _ = run_command(
        ["adb", "-s", device_id, "shell", "getprop", "ro.product.cpu.abi"]
    )
    if returncode == 0 and output.strip():
        return output.strip()
    return None


def get_device_type(device_id: str) -> Tuple[str, str]:
    """
    Detect the specific device/emulator type.
    Returns (type_code, display_label).
    type_code: 'avd' | 'ldplayer' | 'nox' | 'bluestacks' | 'memu' | 'mumu' | 'genymotion' | 'wsa' | 'physical' | 'generic'
    """
    returncode, output, _ = run_command(
        [
            "adb",
            "-s",
            device_id,
            "shell",
            "getprop ro.product.name; getprop ro.product.manufacturer; getprop ro.hardware; getprop ro.build.flavor; getprop ro.product.model",
        ]
    )
    if returncode != 0:
        return "generic", "Generic Android Device"

    lines = [line.strip().lower() for line in output.strip().split("\n") if line.strip()]
    props_str = " ".join(lines)

    # 1. LDPlayer
    if any(k in props_str for k in ["leidian", "ldplayer"]):
        return "ldplayer", "LDPlayer Emulator"
    rc_ld, _, _ = run_command(
        ["adb", "-s", device_id, "shell", "which ldprop || test -f /system/bin/ldprop"]
    )
    if rc_ld == 0:
        return "ldplayer", "LDPlayer Emulator"

    # 2. Nox
    if any(k in props_str for k in ["nox", "bignox"]):
        return "nox", "NoxPlayer Emulator"

    # 3. BlueStacks
    if any(k in props_str for k in ["bluestacks", "bst"]):
        return "bluestacks", "BlueStacks Emulator"

    # 4. MEmu
    if any(k in props_str for k in ["memu", "microvirt"]):
        return "memu", "MEmu Play Emulator"

    # 5. MuMu
    if any(k in props_str for k in ["mumu", "nemu", "netease"]):
        return "mumu", "MuMu Player Emulator"

    # 6. Genymotion
    if any(k in props_str for k in ["genymotion"]):
        return "genymotion", "Genymotion Emulator"

    # 7. WSA (Windows Subsystem for Android)
    if any(k in props_str for k in ["wsa", "subsystem_for_android"]):
        return "wsa", "Windows Subsystem for Android"

    # 8. Android Studio AVD
    if any(
        k in props_str
        for k in ["ranchu", "goldfish", "sdk_gphone", "google_apis", "sdk_google", "aosp_"]
    ):
        return "avd", "Android Studio AVD"
    if device_id.startswith("emulator-"):
        return "avd", "Android Studio AVD"

    # 9. Physical device (known SoC hardware keywords or popular OEMs)
    if any(
        k in props_str
        for k in [
            "qcom", "qualcomm", "mtk", "mediatek", "exynos", "kirin",
            "tensor", "hisilicon", "samsung", "xiaomi", "oppo", "vivo",
            "realme", "oneplus", "pixel", "huawei", "motorola", "honor",
        ]
    ):
        return "physical", "Physical Device"

    return "generic", "Generic Android Device"


def get_device_properties(device_id: str) -> Dict[str, str]:
    """Retrieve full dictionary of device attributes (API level, ABI, Android release, product)."""
    properties: Dict[str, str] = {}

    dev_type, dev_label = get_device_type(device_id)
    properties["device_type"] = dev_type
    properties["device_label"] = dev_label

    # API level
    rc, out, _ = run_command(["adb", "-s", device_id, "shell", "getprop", "ro.build.version.sdk"])
    if rc == 0 and out.strip():
        properties["api"] = out.strip()

    # Architecture
    rc, out, _ = run_command(["adb", "-s", device_id, "shell", "getprop", "ro.product.cpu.abi"])
    if rc == 0 and out.strip():
        properties["abi"] = out.strip()

    # Android Version
    rc, out, _ = run_command(["adb", "-s", device_id, "shell", "getprop", "ro.build.version.release"])
    if rc == 0 and out.strip():
        properties["version"] = out.strip()

    # Product name
    rc, out, _ = run_command(["adb", "-s", device_id, "shell", "getprop", "ro.product.name"])
    if rc == 0 and out.strip():
        properties["product"] = out.strip()

    return properties


def check_root_access(device_id: str) -> bool:
    """
    Verify if root / su privileges are accessible on target device.
    Uses non-disruptive shell probes to prevent restarting adbd or dropping connections.
    """
    # Method 1: check if default shell is already uid 0
    returncode, output, _ = run_command(["adb", "-s", device_id, "shell", "id"], timeout=3.0)
    if returncode == 0 and "uid=0" in output:
        return True

    # Method 2: test su binary execution
    returncode, output, _ = run_command(["adb", "-s", device_id, "shell", "su", "-c", "id"], timeout=3.0)
    if returncode == 0 and "uid=0" in output:
        return True

    # Method 3: test su binary presence in system paths
    returncode, output, _ = run_command(
        ["adb", "-s", device_id, "shell", "which su || test -f /system/bin/su || test -f /system/xbin/su && echo 'exists'"],
        timeout=3.0,
    )
    if returncode == 0 and ("su" in output or "exists" in output):
        return True

    return False


def setup_port_forward(device_id: str, local_port: int, remote_port: int = 27042) -> Tuple[bool, str]:
    """Forward a local TCP port to the device's remote frida-server port."""
    # Clear existing forward for this port first
    run_command(["adb", "-s", device_id, "forward", "--remove", f"tcp:{local_port}"])
    rc, out, err = run_command(["adb", "-s", device_id, "forward", f"tcp:{local_port}", f"tcp:{remote_port}"])
    if rc == 0:
        return True, f"localhost:{local_port} -> device:{remote_port}"
    return False, err or out or "Failed to forward port"


def remove_port_forward(device_id: str, local_port: int) -> Tuple[bool, str]:
    """Remove a specific ADB port forwarding."""
    rc, out, err = run_command(["adb", "-s", device_id, "forward", "--remove", f"tcp:{local_port}"])
    if rc == 0:
        return True, f"Removed forwarding for port {local_port}"
    return False, err or out or "Failed to remove port forward"


def remove_all_port_forwards(device_id: Optional[str] = None) -> Tuple[bool, str]:
    """Remove all port forwardings, optionally scoped to a single device."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["forward", "--remove-all"])
    rc, out, err = run_command(cmd)
    if rc == 0:
        return True, "All port forwardings removed"
    return False, err or out or "Failed to remove all port forwardings"


def get_active_port_forwards() -> Dict[str, int]:
    """
    Parse active port forwardings from `adb forward --list`.
    Returns dict mapping device_id -> local_port.
    Output format: <serial> tcp:<local_port> tcp:<remote_port>
    """
    forwards: Dict[str, int] = {}
    rc, out, _ = run_command(["adb", "forward", "--list"])
    if rc == 0 and out.strip():
        for line in out.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 2:
                dev_id = parts[0]
                local_spec = parts[1]
                if local_spec.startswith("tcp:"):
                    try:
                        port_num = int(local_spec[4:])
                        forwards[dev_id] = port_num
                    except ValueError:
                        pass
    return forwards


def allocate_device_port(device_id: str, base_port: int = 27042) -> int:
    """
    Allocate a unique, non-conflicting host port for a given device.
    Prioritizes existing active forwards or mappings for this device,
    otherwise finds the lowest available port starting at base_port.
    """
    active_forwards = get_active_port_forwards()
    if device_id in active_forwards:
        return active_forwards[device_id]

    port_mappings = load_port_mappings()
    if device_id in port_mappings:
        cached_port = port_mappings[device_id]
        # Ensure cached port is not currently occupied by ANOTHER device
        other_active_ports = {p for dev, p in active_forwards.items() if dev != device_id}
        if cached_port not in other_active_ports:
            return cached_port

    used_ports = set(active_forwards.values())
    used_ports.update(port_mappings.values())

    candidate = base_port
    while candidate in used_ports:
        candidate += 1

    return candidate


def load_port_mappings(file_path: Optional[Path] = None) -> Dict[str, int]:
    """Load cached port mappings from port_mapping.txt."""
    if file_path is None:
        file_path = get_project_root() / "port_mapping.txt"

    mappings: Dict[str, int] = {}
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if ":" in line:
                        dev_id, port_str = line.rsplit(":", 1)
                        if port_str.isdigit():
                            mappings[dev_id] = int(port_str)
        except Exception:
            pass
    return mappings


def save_port_mappings(mappings: Dict[str, int], file_path: Optional[Path] = None) -> None:
    """Save port mappings to port_mapping.txt."""
    if file_path is None:
        file_path = get_project_root() / "port_mapping.txt"

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for dev_id, port in mappings.items():
                f.write(f"{dev_id}:{port}\n")
    except Exception:
        pass
