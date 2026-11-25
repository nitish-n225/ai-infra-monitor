"""
Native Windows Service Wrapper (pywin32 ServiceFramework) for the Monitoring Agent.
Allows enterprise deployment as a LocalSystem Windows Service that runs continuously
even before any user signs in and natively holds SeSecurityPrivilege for Security Event Logs.

Usage (Administrator PowerShell):
    python -m agent.win_service install
    python -m agent.win_service start
    python -m agent.win_service stop
    python -m agent.win_service remove
"""
import os
import sys
import threading
from pathlib import Path

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
    HAS_WIN32_SERVICE = True
except ImportError:
    HAS_WIN32_SERVICE = False

from agent.config import AgentConfig, DEFAULT_CONFIG_PATH, DEFAULT_STATE_PATH
from agent.main import WindowsMonitoringAgent, setup_logging


if HAS_WIN32_SERVICE:
    class EnterpriseAIMonitorService(win32serviceutil.ServiceFramework):
        _svc_name_ = "EnterpriseAIMonitorService"
        _svc_display_name_ = "Enterprise Autonomous AI Infrastructure Monitor Agent"
        _svc_description_ = (
            "Collects authorized Windows Event Viewer logs, hardware telemetry, "
            "and configured application logs for central AI monitoring."
        )

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.agent: WindowsMonitoringAgent | None = None
            self.worker_thread: threading.Thread | None = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self.agent:
                self.agent.stop()
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            cfg_path = Path(os.environ.get("AGENT_CONFIG_PATH", str(DEFAULT_CONFIG_PATH)))
            state_path = Path(os.environ.get("AGENT_STATE_PATH", str(DEFAULT_STATE_PATH)))
            cfg = AgentConfig.load(cfg_path)
            setup_logging(cfg.agent_log_path or str(cfg_path.parent / "agent_service.log"))
            if not cfg.backend_url or not cfg.consent_accepted:
                servicemanager.LogErrorMsg("EnterpriseAIMonitorService missing backend_url or explicit consent_accepted=true.")
                return

            self.agent = WindowsMonitoringAgent(cfg, state_path=state_path)
            self.worker_thread = threading.Thread(target=self.agent.run_forever, daemon=True)
            self.worker_thread.start()
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)


if __name__ == "__main__":
    if not HAS_WIN32_SERVICE:
        print("pywin32 ServiceFramework is required on Windows.")
        sys.exit(1)
    win32serviceutil.HandleCommandLine(EnterpriseAIMonitorService)

