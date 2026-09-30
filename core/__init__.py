"""
Frida-Xtr Core Package
Contains core logic for ADB interaction, Frida engine, Device rooting, and Script injection.
"""

from .adb import (
    DeviceInfo,
    run_command,
    detect_devices,
    auto_connect_emulators,
    auto_detect_and_connect_emulators,
    auto_connect_ldplayer,
    probe_port,
    probe_ports_parallel,
    probe_tcp_port,
    EMULATOR_PORT_MAP,
    EMULATOR_PORT_PRESETS,
    get_device_architecture,
    get_device_type,
    get_device_properties,
    check_root_access,
    setup_port_forward,
    remove_port_forward,
    remove_all_port_forwards,
    get_active_port_forwards,
    allocate_device_port,
    load_port_mappings,
    save_port_mappings,
    get_project_root,
)

from .frida_engine import (
    DEFAULT_FRIDA_PORT,
    check_host_frida_environment,
    check_frida_server_file,
    get_available_frida_server_files,
    get_frida_server_file_for_architecture,
    get_frida_server_architecture,
    check_architecture_compatibility,
    is_frida_server_running,
    set_frida_server_cached_status,
    invalidate_frida_server_cache,
    test_frida_connection,
    setup_frida_server,
    start_frida_server,
    stop_frida_server,
    view_device_processes,
)

from .root import (
    get_root_guidance,
    resolve_android_home,
    find_ramdisk_path,
    execute_rootavd,
)

from .injector import (
    CODESHARE_PRESETS,
    get_scripts_from_folder,
    get_package_list,
    build_frida_command,
    launch_frida_session,
)

__all__ = [
    # ADB
    "DeviceInfo",
    "run_command",
    "detect_devices",
    "auto_connect_emulators",
    "auto_detect_and_connect_emulators",
    "auto_connect_ldplayer",
    "probe_port",
    "probe_ports_parallel",
    "probe_tcp_port",
    "EMULATOR_PORT_MAP",
    "EMULATOR_PORT_PRESETS",
    "get_device_architecture",
    "get_device_type",
    "get_device_properties",
    "check_root_access",
    "setup_port_forward",
    "remove_port_forward",
    "remove_all_port_forwards",
    "get_active_port_forwards",
    "allocate_device_port",
    "load_port_mappings",
    "save_port_mappings",
    "get_project_root",
    # Frida Engine
    "DEFAULT_FRIDA_PORT",
    "check_host_frida_environment",
    "check_frida_server_file",
    "get_available_frida_server_files",
    "get_frida_server_file_for_architecture",
    "get_frida_server_architecture",
    "check_architecture_compatibility",
    "is_frida_server_running",
    "set_frida_server_cached_status",
    "invalidate_frida_server_cache",
    "test_frida_connection",
    "setup_frida_server",
    "start_frida_server",
    "stop_frida_server",
    "view_device_processes",
    # Root
    "get_root_guidance",
    "resolve_android_home",
    "find_ramdisk_path",
    "execute_rootavd",
    # Injector
    "CODESHARE_PRESETS",
    "get_scripts_from_folder",
    "get_package_list",
    "build_frida_command",
    "launch_frida_session",
]
