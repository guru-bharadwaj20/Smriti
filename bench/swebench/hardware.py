"""Hardware and sampled process-memory metadata for reproducible CPU runs."""

from __future__ import annotations

import ctypes
import os
import platform
from typing import Any


def hardware_metadata() -> dict[str, Any]:
    result: dict[str, Any] = {
        'cpu': platform.processor(),
        'logical_cpus': os.cpu_count(),
        'os': platform.platform(),
        'python': platform.python_version(),
        'ram_bytes': None,
    }
    if os.name == 'nt':

        class MemoryStatus(ctypes.Structure):
            _fields_ = [('length', ctypes.c_uint32), ('load', ctypes.c_uint32)] + [
                (name, ctypes.c_uint64)
                for name in [
                    'total_phys',
                    'avail_phys',
                    'total_page',
                    'avail_page',
                    'total_virtual',
                    'avail_virtual',
                    'avail_extended',
                ]
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            result['ram_bytes'] = status.total_phys
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0'
        ) as key:
            result['cpu'] = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
    elif os.path.exists('/proc/meminfo'):
        with open('/proc/meminfo', encoding='ascii') as file:
            for line in file:
                if line.startswith('MemTotal:'):
                    result['ram_bytes'] = int(line.split()[1]) * 1024
                    break
    return result


def process_rss_bytes() -> int | None:
    if os.name == 'nt':

        class ProcessMemory(ctypes.Structure):
            _fields_ = [('size', ctypes.c_uint32), ('faults', ctypes.c_uint32)] + [
                (name, ctypes.c_size_t)
                for name in [
                    'peak_rss',
                    'rss',
                    'peak_paged',
                    'paged',
                    'peak_nonpaged',
                    'nonpaged',
                    'pagefile',
                    'peak_pagefile',
                ]
            ]

        status = ProcessMemory()
        status.size = ctypes.sizeof(status)
        current_process = ctypes.windll.kernel32.GetCurrentProcess
        current_process.restype = ctypes.c_void_p
        read_memory = ctypes.windll.psapi.GetProcessMemoryInfo
        read_memory.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessMemory), ctypes.c_uint32]
        read_memory.restype = ctypes.c_bool
        process = current_process()
        if read_memory(process, ctypes.byref(status), status.size):
            return int(status.rss)
        return None
    if os.path.exists('/proc/self/statm'):
        with open('/proc/self/statm', encoding='ascii') as file:
            return int(file.read().split()[1]) * os.sysconf('SC_PAGE_SIZE')
    return None
