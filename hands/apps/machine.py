"""WHAT THIS COMPUTER IS."""

import getpass
import os
import platform
import shutil
import sys
from pathlib import Path

WINDOWS = "win32"

GIGABYTE = 1024**3


def facts():
    """THE MACHINE IN A HANDFUL OF LINES."""
    total, _, free = shutil.disk_usage(Path.home())

    return "\n".join(
        [
            f"Operating system: {platform.system()} {platform.release()}",
            f"Architecture: {platform.machine()}",
            f"CPU cores: {os.cpu_count() or 'unknown'}",
            f"Memory: {gigabytes(memory_bytes())}",
            f"Disk: {gigabytes(free)} free of {gigabytes(total)}",
            f"Hostname: {platform.node()}",
            f"User: {getpass.getuser()}",
        ]
    )


def memory_bytes():
    """TOTAL RAM, OR None WHERE WE CANNOT ASK CHEAPLY."""
    if sys.platform == WINDOWS:
        return windows_memory()

    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        return None


def windows_memory():
    import ctypes

    class Status(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = Status()
    status.dwLength = ctypes.sizeof(Status)

    try:
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    except (AttributeError, OSError):
        return None

    return status.ullTotalPhys


def gigabytes(count):
    return f"{count / GIGABYTE:.0f} GB" if count else "unknown"
