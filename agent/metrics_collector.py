"""
Real Windows System Metrics & Service Status Collector.
Uses psutil and Windows Service Control Manager APIs to collect genuine hardware & OS metrics
including multi-volume disk utilization, CPU, RAM, Network IO, top processes, and Windows services.
"""
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import psutil


class SystemMetricsCollector:
    """Collects real CPU, RAM, multi-drive Disk, Network, Process, and Windows Service telemetry."""

    def __init__(self, system_drive: Optional[str] = None):
        self.system_drive = system_drive or os.environ.get("SystemDrive", "C:") + "\\"
        self._last_net = psutil.net_io_counters()
        self._last_net_ts = time.monotonic()
        psutil.cpu_percent(interval=None)

    def _collect_disk_volumes(self) -> tuple[float, float, float, List[Dict[str, Any]]]:
        volumes: List[Dict[str, Any]] = []
        primary_pct = 0.0
        primary_used = 0.0
        primary_total = 0.0

        try:
            for part in psutil.disk_partitions(all=False):
                if "cdrom" in part.opts.lower() or not part.fstype:
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    vol = {
                        "mount": part.mountpoint,
                        "fstype": part.fstype,
                        "percent": round(float(usage.percent), 1),
                        "used_gb": round(float(usage.used) / (1024 ** 3), 2),
                        "total_gb": round(float(usage.total) / (1024 ** 3), 2),
                    }
                    volumes.append(vol)
                    if part.mountpoint.upper().startswith(self.system_drive[:2].upper()):
                        primary_pct = vol["percent"]
                        primary_used = vol["used_gb"]
                        primary_total = vol["total_gb"]
                except Exception:
                    continue
        except Exception:
            pass

        if not volumes:
            try:
                du = psutil.disk_usage(self.system_drive)
                primary_pct = round(float(du.percent), 1)
                primary_used = round(float(du.used) / (1024 ** 3), 2)
                primary_total = round(float(du.total) / (1024 ** 3), 2)
                volumes.append({
                    "mount": self.system_drive,
                    "fstype": "NTFS",
                    "percent": primary_pct,
                    "used_gb": primary_used,
                    "total_gb": primary_total,
                })
            except Exception:
                pass
        elif primary_total == 0.0:
            primary_pct = volumes[0]["percent"]
            primary_used = volumes[0]["used_gb"]
            primary_total = volumes[0]["total_gb"]

        return primary_pct, primary_used, primary_total, volumes

    def collect(self) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()

        cpu_percent = round(float(psutil.cpu_percent(interval=0.2)), 1)
        cpu_cores = psutil.cpu_count(logical=True) or 1

        vm = psutil.virtual_memory()
        ram_percent = round(float(vm.percent), 1)
        ram_used_gb = round(float(vm.used) / (1024 ** 3), 2)
        ram_total_gb = round(float(vm.total) / (1024 ** 3), 2)

        disk_percent, disk_used_gb, disk_total_gb, disk_volumes = self._collect_disk_volumes()

        net = psutil.net_io_counters()
        now_mono = time.monotonic()
        elapsed = max(0.1, now_mono - self._last_net_ts)
        delta_sent = max(0, net.bytes_sent - self._last_net.bytes_sent)
        delta_recv = max(0, net.bytes_recv - self._last_net.bytes_recv)
        net_sent_kbps = round((delta_sent / 1024.0) / elapsed, 2)
        net_recv_kbps = round((delta_recv / 1024.0) / elapsed, 2)
        self._last_net = net
        self._last_net_ts = now_mono

        processes: List[Dict[str, Any]] = []
        proc_count = 0
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            proc_count += 1
            try:
                info = proc.info
                processes.append({
                    "pid": info.get("pid"),
                    "name": info.get("name") or "unknown",
                    "cpu_percent": round(float(info.get("cpu_percent") or 0.0), 1),
                    "memory_percent": round(float(info.get("memory_percent") or 0.0), 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda p: (p["memory_percent"], p["cpu_percent"]), reverse=True)
        top_processes = processes[:10]

        services_list: List[Dict[str, Any]] = []
        if hasattr(psutil, "win_service_iter"):
            try:
                for svc in psutil.win_service_iter():
                    try:
                        s_info = svc.as_dict()
                        start_type = s_info.get("start_type", "")
                        status = s_info.get("status", "")
                        if start_type == "automatic" or len(services_list) < 25:
                            services_list.append({
                                "name": s_info.get("name"),
                                "display_name": s_info.get("display_name"),
                                "status": status,
                                "start_type": start_type,
                            })
                    except Exception:
                        continue
            except Exception:
                pass

        services_list.sort(key=lambda s: (0 if (s["start_type"] == "automatic" and s["status"] != "running") else 1, s["name"] or ""))
        uptime_seconds = round(max(0.0, time.time() - psutil.boot_time()), 1)

        return {
            "timestamp": now_iso,
            "cpu_percent": cpu_percent,
            "cpu_cores": cpu_cores,
            "ram_percent": ram_percent,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "disk_percent": disk_percent,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "disk_volumes": disk_volumes,
            "net_bytes_sent": int(net.bytes_sent),
            "net_bytes_recv": int(net.bytes_recv),
            "net_sent_kbps": net_sent_kbps,
            "net_recv_kbps": net_recv_kbps,
            "process_count": proc_count,
            "top_processes": top_processes,
            "services": services_list[:30],
            "uptime_seconds": uptime_seconds,
        }
