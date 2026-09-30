#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui.colors - Vibrant ANSI Gradient Palette & Text Formatting
"""


class Colors:
    """Vibrant gradient color palette (pink → purple → blue) with ANSI terminal formatting."""
    # Core colors
    PINK = "\033[38;5;213m"      # Bright pink
    PURPLE = "\033[38;5;141m"   # Vibrant purple
    BLUE = "\033[38;5;39m"      # Bright blue
    CYAN = "\033[38;5;51m"      # Cyan
    GREEN = "\033[38;5;46m"     # Bright green
    YELLOW = "\033[38;5;226m"   # Bright yellow
    RED = "\033[38;5;196m"      # Bright red
    MAGENTA = "\033[38;5;201m"  # Magenta

    # Status colors
    SUCCESS = GREEN
    ERROR = RED
    WARNING = YELLOW
    INFO = CYAN

    # Text styles
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"

    @staticmethod
    def gradient(text: str, start: str = PINK, mid: str = PURPLE, end: str = BLUE) -> str:
        """Create smooth multi-stop gradient effect on text."""
        chars = list(text)
        if len(chars) == 0:
            return text
        result = []
        for i, char in enumerate(chars):
            if char == " ":
                result.append(char)
                continue
            ratio = i / max(len(chars) - 1, 1)
            if ratio < 0.5:
                color = start
            elif ratio < 0.75:
                color = mid
            else:
                color = end
            result.append(f"{color}{char}{Colors.RESET}")
        return "".join(result)
