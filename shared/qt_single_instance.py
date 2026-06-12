"""Qt local-socket single-instance guard (client, desktop server UI, etc.)."""

from PyQt6.QtCore import QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication


class QtSingleInstanceGuard:
    def __init__(self, server_name: str, on_activate=None):
        self.server_name = server_name
        self.on_activate = on_activate
        self._server = None

    def try_acquire(self) -> bool:
        """Return True if this process should continue as the primary instance."""
        if self._notify_running_instance():
            return False

        self._server = QLocalServer()
        QLocalServer.removeServer(self.server_name)
        if not self._server.listen(self.server_name):
            return not self._notify_running_instance()

        self._server.newConnection.connect(self._on_new_connection)
        return True

    def ping_running_instance(self) -> bool:
        return self._notify_running_instance()

    def _notify_running_instance(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if not socket.waitForConnected(500):
            return False

        socket.write(b"activate")
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        return True

    def _on_new_connection(self):
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        conn.readyRead.connect(lambda c=conn: self._handle_activate(c))

    def _handle_activate(self, conn):
        conn.readAll()
        conn.disconnectFromServer()
        if self.on_activate:
            QTimer.singleShot(0, self.on_activate)


def activate_application_window(attr: str = "main_window"):
    """Raise the primary window for a running Qt application."""
    app = QApplication.instance()
    if app is None:
        return

    win = getattr(app, attr, None)
    if win is None:
        return

    if hasattr(win, "showNormal"):
        win.showNormal()
    elif hasattr(win, "show"):
        win.show()

    win.raise_()
    win.activateWindow()
