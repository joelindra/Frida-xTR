"""
Frida-Xtr UI Package
Provides both the classic ANSI CLI interface (ui.console) and the modern Textual TUI (ui.tui).
"""

from .colors import Colors
from .console import run_cli
from .tui import run_tui

__all__ = [
    "Colors",
    "run_cli",
    "run_tui",
]
