import sys
import platform
import subprocess
import ctypes
import psutil
import socket
import re
import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, 
    QMessageBox, QLabel, QComboBox, QHBoxLayout, QTabWidget, QTextEdit
)
from PyQt6.QtCore import QTimer, QEventLoop, QTranslator, QLocale


LOG_FILE = "syscommander.log"


def log_action(action: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {action}\n")


def is_admin():
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:
        # Linux: User muss manuell sudo nutzen, keine automatische Erhöhung hier
        return True


def get_ip_mac(interface):
    ip = "N/A"
    mac = "N/A"
    try:
        addrs = psutil.net_if_addrs()
        if interface in addrs:
            for addr in addrs[interface]:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                elif addr.family == psutil.AF_LINK or getattr(addr, 'family', None) == 17:
                    mac = addr.address
    except Exception:
        pass
    return ip, mac


def get_cpu_info():
    try:
        return platform.processor() or "Unbekannt"
    except:
        return "Unbekannt"


def get_ram_info():
    try:
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        return f"{total_gb:.2f} GB"
    except:
        return "Unbekannt"


def get_disk_info():
    try:
        disk = psutil.disk_usage('/')
        total_gb = disk.total / (1024 ** 3)
        used_gb = disk.used / (1024 ** 3)
        free_gb = disk.free / (1024 ** 3)
        return f"Gesamt: {total_gb:.2f} GB, Frei: {free_gb:.2f} GB, Belegt: {used_gb:.2f} GB"
    except:
        return "Unbekannt"


class SysCommander(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SysCommander - System Control Tool")
        self.setGeometry(300, 300, 500, 450)
        self.os_name = platform.system()
        self.translator = None
        self.current_language = "de"

        self.init_ui()
        self.load_network_interfaces()
        self.update_network_status()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_network_status)
        self.timer.start(5000)  # alle 5 Sekunden aktualisieren

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Sprache wechseln
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Sprache / Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Deutsch", "English"])
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.lang_combo)
        main_layout.addLayout(lang_layout)

        # Netzwerk Auswahl und Status
        net_layout = QHBoxLayout()
        net_layout.addWidget(QLabel("Netzwerk-Schnittstelle:"))
        self.net_combo = QComboBox()
        self.net_combo.currentTextChanged.connect(self.update_network_status)
        net_layout.addWidget(self.net_combo)
        self.net_status_label = QLabel("Status: -")
        net_layout.addWidget(self.net_status_label)
        main_layout.addLayout(net_layout)

        # Netzwerkdetails (IP & MAC)
        self.net_details_label = QLabel("IP: N/A | MAC: N/A")
        main_layout.addWidget(self.net_details_label)

        # Netzwerk Buttons
        net_btn_layout = QHBoxLayout()
        self.btn_net_offline = QPushButton("Offline (deaktivieren)")
        self.btn_net_offline.clicked.connect(self.confirm_network_offline)
        self.btn_net_online = QPushButton("Online (aktivieren)")
        self.btn_net_online.clicked.connect(self.confirm_network_online)
        net_btn_layout.addWidget(self.btn_net_offline)
        net_btn_layout.addWidget(self.btn_net_online)
        main_layout.addLayout(net_btn_layout)

        # System Aktionen Buttons
        self.btn_lock = QPushButton("Sperren")
        self.btn_lock.clicked.connect(self.confirm_lock)
        self.btn_logout = QPushButton("Abmelden")
        self.btn_logout.clicked.connect(self.confirm_logout)
        self.btn_restart = QPushButton("Neustarten")
        self.btn_restart.clicked.connect(self.confirm_restart)
        self.btn_shutdown = QPushButton("Herunterfahren")
        self.btn_shutdown.clicked.connect(self.confirm_shutdown)

        main_layout.addWidget(self.btn_lock)
        main_layout.addWidget(self.btn_logout)
        main_layout.addWidget(self.btn_restart)
        main_layout.addWidget(self.btn_shutdown)

        # Firewall Button
        self.btn_firewall = QPushButton("Firewall-Einstellungen öffnen")
        self.btn_firewall.clicked.connect(self.open_firewall)
        main_layout.addWidget(self.btn_firewall)

        # Tabs für Systeminfo und Log
        self.tabs = QTabWidget()
        self.tab_sysinfo = QWidget()
        self.tab_log = QWidget()

        self.tabs.addTab(self.tab_sysinfo, "Systeminfo")
        self.tabs.addTab(self.tab_log, "Log")

        # Systeminfo Tab
        sysinfo_layout = QVBoxLayout()
        self.lbl_cpu = QLabel()
        self.lbl_ram = QLabel()
        self.lbl_disk = QLabel()
        sysinfo_layout.addWidget(self.lbl_cpu)
        sysinfo_layout.addWidget(self.lbl_ram)
        sysinfo_layout.addWidget(self.lbl_disk)
        self.tab_sysinfo.setLayout(sysinfo_layout)

        # Log Tab
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        self.tab_log.setLayout(log_layout)

        main_layout.addWidget(self.tabs)

        self.setLayout(main_layout)
        self.update_system_info()
        self.load_log()

    def run_command(self, cmd):
        try:
            result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, self.tr("Fehler"), f"{self.tr('Befehl fehlgeschlagen')}:\n{e}")
            return ""

    def load_network_interfaces(self):
        self.net_combo.clear()
        if self.os_name == "Windows":
            output = self.run_command("netsh interface show interface")
            for line in output.splitlines():
                if line.strip().startswith("Admin") or line.strip() == "":
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    iface = " ".join(parts[3:])
                    self.net_combo.addItem(iface)
        elif self.os_name == "Linux":
            output = self.run_command("ip -o link show")
            for line in output.splitlines():
                parts = line.split(":")
                if len(parts) > 1:
                    iface = parts[1].strip()
                    self.net_combo.addItem(iface)
        else:
            QMessageBox.information(self, self.tr("Info"), self.tr("OS wird nicht unterstützt für Netzwerk-Interfaces."))

        self.update_network_status()

    def get_network_status(self, interface):
        if self.os_name == "Windows":
            output = self.run_command("netsh interface show interface")
            for line in output.splitlines():
                if interface in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        iface_name = " ".join(parts[3:])
                        if iface_name == interface:
                            state = parts[1].lower()  # connected/disconnected
                            return "Online" if state == "connected" else "Offline"
            return "Unbekannt"
        elif self.os_name == "Linux":
            output = self.run_command(f"cat /sys/class/net/{interface}/operstate")
            return "Online" if output.strip() == "up" else "Offline"
        else:
            return "Unbekannt"

    def update_network_status(self):
        iface = self.net_combo.currentText()
        if iface:
            status = self.get_network_status(iface)
            self.net_status_label.setText(f"Status: {status}")
            ip, mac = get_ip_mac(iface)
            self.net_details_label.setText(f"IP: {ip} | MAC: {mac}")
        else:
            self.net_status_label.setText("Status: -")
            self.net_details_label.setText("IP: N/A | MAC: N/A")

    def confirm_action(self, title, message, action_func, countdown=False):
        if countdown:
            seconds = 10
            dlg = QMessageBox(self)
            dlg.setWindowTitle(title)
            dlg.setText(f"{message}\n\nCountdown: {seconds} Sekunden\nZum Abbrechen 'Abbrechen' klicken.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            dlg.button(QMessageBox.StandardButton.Ok).setText("Jetzt ausführen")
            dlg.button(QMessageBox.StandardButton.Cancel).setText("Abbrechen")

            timer = QTimer(dlg)
            timer.setInterval(1000)

            def countdown_tick():
                nonlocal seconds
                seconds -= 1
                dlg.setText(f"{message}\n\nCountdown: {seconds} Sekunden\nZum Abbrechen 'Abbrechen' klicken.")
                if seconds <= 0:
                    timer.stop()
                    dlg.done(QMessageBox.StandardButton.Ok)

            timer.timeout.connect(countdown_tick)
            timer.start()

            ret = dlg.exec()

            if ret == QMessageBox.StandardButton.Ok:
                action_func()
            else:
                log_action(f"Aktion '{title}' abgebrochen vom Benutzer.")
        else:
            ret = QMessageBox.question(self, title, message,
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                action_func()
            else:
                log_action(f"Aktion '{title}' abgebrochen vom Benutzer.")

    # Bestätigungen + Countdown für Aktionen

    def confirm_network_offline(self):
        iface = self.net_combo.currentText()
        if not iface:
            QMessageBox.warning(self, self.tr("Warnung"), self.tr("Keine Netzwerk-Schnittstelle ausgewählt."))
            return
        self.confirm_action(self.tr("Netzwerk deaktivieren"),
                            self.tr(f"Willst du die Schnittstelle '{iface}' wirklich deaktivieren?"),
                            self.network_offline, countdown=True)

    def confirm_network_online(self):
        iface = self.net_combo.currentText()
        if not iface:
            QMessageBox.warning(self, self.tr("Warnung"), self.tr("Keine Netzwerk-Schnittstelle ausgewählt."))
            return
        self.confirm_action(self.tr("Netzwerk aktivieren"),
                            self.tr(f"Willst du die Schnittstelle '{iface}' wirklich aktivieren?"),
                            self.network_online, countdown=True)

    def confirm_lock(self):
        self.confirm_action(self.tr("Sperren"),
                            self.tr("Willst du den Computer jetzt sperren?"),
                            self.lock)

    def confirm_logout(self):
        self.confirm_action(self.tr("Abmelden"),
                            self.tr("Willst du dich jetzt abmelden?"),
                            self.logout)

    def confirm_restart(self):
        self.confirm_action(self.tr("Neustarten"),
                            self.tr("Willst du den Computer jetzt neu starten?"),
                            self.restart, countdown=True)

    def confirm_shutdown(self):
        self.confirm_action(self.tr("Herunterfahren"),
                            self.tr("Willst du den Computer jetzt herunterfahren?"),
                            self.shutdown, countdown=True)

    # Aktionen

    def network_offline(self):
        iface = self.net_combo.currentText()
        if self.os_name == "Windows":
            cmd = f'netsh interface set interface "{iface}" admin=disabled'
        elif self.os_name == "Linux":
            cmd = f'sudo ip link set {iface} down'
        else:
            QMessageBox.information(self, self.tr("Info"), self.tr("Offline schalten nicht unterstützt auf diesem OS"))
            return
        self.run_command(cmd)
        log_action(f"Netzwerk '{iface}' deaktiviert")
        self.update_network_status()

    def network_online(self):
        iface = self.net_combo.currentText()
        if self.os_name == "Windows":
            cmd = f'netsh interface set interface "{iface}" admin=enabled'
        elif self.os_name == "Linux":
            cmd = f'sudo ip link set {iface} up'
        else:
            QMessageBox.information(self, self.tr("Info"), self.tr("Online schalten nicht unterstützt auf diesem OS"))
            return
        self.run_command(cmd)
        log_action(f"Netzwerk '{iface}' aktiviert")
        self.update_network_status()

    def lock(self):
        if self.os_name == "Windows":
            self.run_command("rundll32.exe user32.dll,LockWorkStation")
        elif self.os_name == "Linux":
            self.run_command("gnome-screensaver-command -l || dm-tool lock")
        else:
            QMessageBox.information(self, self.tr("Info"), self.tr("Lock nicht unterstützt auf diesem OS"))
        log_action("Computer gesperrt")

    def logout(self):
        if self.os_name == "Windows":
            self.run_command("shutdown -l")
        elif self.os_name == "Linux":
            self.run_command("gnome-session-quit --logout --no-prompt")
        else:
            QMessageBox.information(self, self.tr("Info"), self.tr("Logout nicht unterstützt auf diesem OS"))
        log_action("Benutzer abgemeldet")

    def restart(self):
        if self.os_name == "Windows":
            self.run_command("shutdown /r /t 0")
        elif self.os_name == "Linux":
            self.run_command("systemctl reboot")
        else:
            QMessageBox.information(self, self.tr("Info"), self.tr("Restart nicht unterstützt auf diesem OS"))
        log_action("Computer neu gestartet")

    def shutdown(self):
        if self.os_name == "Windows":
            self.run_command("shutdown /s /t 0")
        elif self.os_name == "Linux":
            self.run_command("systemctl poweroff")
        else:
            QMessageBox.information(self, self.tr("Info"), self.tr("Shutdown nicht unterstützt auf diesem OS"))
        log_action("Computer heruntergefahren")

    def open_firewall(self):
        if self.os_name == "Windows":
            self.run_command("control firewall.cpl")
        elif self.os_name == "Linux":
            # Beispiel für gnome-firewall-config, kann je nach Linux-Distribution variieren
            self.run_command("gnome-control-center firewall")
        else:
            QMessageBox.information(self, self.tr("Info"), self.tr("Firewall öffnen nicht unterstützt auf diesem OS"))

    def update_system_info(self):
        self.lbl_cpu.setText(f"CPU: {get_cpu_info()}")
        self.lbl_ram.setText(f"RAM: {get_ram_info()}")
        self.lbl_disk.setText(f"Festplatte: {get_disk_info()}")

    def load_log(self):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                self.log_text.setPlainText(f.read())
        except FileNotFoundError:
            self.log_text.setPlainText("")

    def change_language(self, index):
        # Einfacher Umschalter für Demo, echte Mehrsprachigkeit mit Qt-Translator ist möglich
        if index == 0:
            self.current_language = "de"
        else:
            self.current_language = "en"
        # Hier könntest du Qt Translator einbinden, für jetzt nur Labels aktualisieren
        self.retranslate_ui()

    def retranslate_ui(self):
        # Einfach alle Texte aktualisieren – hier minimal, da PyQt nicht automatisch
        de = self.current_language == "de"
        self.net_status_label.setText(self.net_status_label.text())  # Status bleibt gleich
        self.net_details_label.setText(self.net_details_label.text())

        self.btn_net_offline.setText("Offline (deaktivieren)" if de else "Offline (disable)")
        self.btn_net_online.setText("Online (aktivieren)" if de else "Online (enable)")
        self.btn_lock.setText("Sperren" if de else "Lock")
        self.btn_logout.setText("Abmelden" if de else "Logout")
        self.btn_restart.setText("Neustarten" if de else "Restart")
        self.btn_shutdown.setText("Herunterfahren" if de else "Shutdown")
        self.btn_firewall.setText("Firewall-Einstellungen öffnen" if de else "Open Firewall Settings")
        self.setWindowTitle("SysCommander - System Control Tool" if not de else "SysCommander - Systemsteuerung")

    def closeEvent(self, event):
        self.load_log()
        super().closeEvent(event)


def main():
    if platform.system() == "Windows":
        if not is_admin():
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()

    app = QApplication(sys.argv)
    window = SysCommander()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
