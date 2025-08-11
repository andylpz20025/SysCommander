# SysCommander

**SysCommander** ist ein plattformübergreifendes Systemsteuerungs-Tool in Python mit PyQt6.  
Es ermöglicht das Sperren, Abmelden, Neustarten, Herunterfahren und das Ein-/Ausschalten von Netzwerk-Schnittstellen.  
Mit Features wie Shutdown-Countdown, Aktion-Logging, Mehrsprachigkeit (Deutsch & Englisch), Systeminfo und Firewall-Zugang.

---

## Features

- **Netzwerkverwaltung**: Auswahl der Netzwerkschnittstelle, Anzeige von Status, IP & MAC, Aktivieren/Deaktivieren  
- **Systemaktionen**: Sperren, Abmelden, Neustarten, Herunterfahren mit Bestätigungsdialogen und Countdown  
- **Logging**: Alle Aktionen werden mit Zeitstempel protokolliert (`syscommander.log`)  
- **Mehrsprachig**: Deutsch & Englisch, einfach umschaltbar im UI  
- **Systeminfo**: CPU, RAM, Festplattenstatus im Tab  
- **Firewall**: Direkter Zugriff auf Firewall-Einstellungen (Windows/Linux)  
- **Admin-Prüfung**: Automatischer Neustart mit Administratorrechten unter Windows  

---

## Installation

1. Python 3.8+ installieren (https://www.python.org)  
2. Benötigte Pakete installieren:

```bash
pip install pyqt6 psutil
