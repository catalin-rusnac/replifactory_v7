import logging
import os
import socket
import sys

import servicemanager
import win32event
import win32service
import win32serviceutil
from server import create_app
from waitress import serve


bundle_dir = os.path.abspath(os.path.dirname(__file__))
logging.basicConfig(
    level=logging.INFO,
    format="[flaskapp] %(levelname)-7.7s %(message)s"
)
path_to_database = os.path.join(bundle_dir, "data/replifactory.db")
os.environ["DATABASE_URI"] = f"sqlite:///{path_to_database}"


class FlaskSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "Replifactory"
    _svc_display_name_ = "Replifactory"
    _svc_description_ = "Controll replifactory machine"

    def __init__(self, *args):
        win32serviceutil.ServiceFramework.__init__(self, *args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(5)
        self.stop_requested = False

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        logging.info("Stopped service.")
        self.stop_requested = True

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        logging.info("Starting service...")
        app = create_app()
        serve(app, host="0.0.0.0", port=5000, threads=1)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FlaskSvc)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FlaskSvc)
