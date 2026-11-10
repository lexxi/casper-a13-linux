# Casper TAB-WB72: Touch-Tools, Boot-Autostart und WLAN (10.11.2026)

## Bestätigter Stand

Casper TAB-WB72 / INTREEO, Allwinner A13, Debian 13 armhf, Linux 6.12 Kernel #5 mit korrigiertem Casper-LCD-DTB. Xorg + Matchbox + Tkinter, Bildschirm 800×480. Die physische HOME-Taste schaltet Matchbox Keyboard; das Passwortfeld bleibt auf der oberen Bildschirmhälfte sichtbar.

| Tool | Installationspfad | Teststand |
|---|---|---|
| Casper WiFi v0.2 | `/usr/local/bin/casper-wifi.py` | Scan, Touch-Auswahl und WLAN-Beitritt getestet; Netzwerkwechsel über Reboot persistent nach `update_config=1` |
| Casper Battery v0.2 | `/usr/local/bin/casper-battery.py` | `--dump` und grafische Anzeige getestet |
| Casper-Menü v0.1 | `/usr/local/bin/casper-menu.py` | Touch-Navigation zu beiden Tools getestet; automatischer Start nach Reboot bestätigt |

Quellcode: `scripts/casper-wifi.py`, `scripts/casper-battery.py`, `scripts/casper-menu.py` (sofern im Repository vorhanden). Diese Datei dokumentiert die **am Gerät bestätigte Konfiguration**, keine Behauptung über alle denkbaren WLAN-Netzwerke.

## Voraussetzungen / Systemdetails

- `python3`, `python3-tk`, `wpa_cli`, `wpa_supplicant`, `dhclient`, Xorg/Matchbox.
- Getestetes Netzwerkinterface `wlx000d724820c2`; vor Nutzung mit `iw dev` verifizieren, da Interface-Namen wechseln können.
- `wpa_supplicant` läuft mit `-i wlx000d724820c2 -c /etc/wpa_supplicant/casper.conf`; Control Socket in `/run/wpa_supplicant/`.
- Aktuelle `/etc/wpa_supplicant/casper.conf` ist ein **lokales Geheimnis** und darf niemals ins öffentliche Repo. Dateimodus `0600`, Eigentümer root.
- Laufzeit als root, weil das Tool den lokalen WPA-Control-Socket verwendet. Nicht als unprivilegierten User startbar, ohne Berechtigungen und Architektur anzupassen.
- Die grafischen Tools nutzen ein Fenster mit `800x288+0+0`; unten reserviert die Matchbox-Tastatur `800x192`.

## WLAN-Manager

Netze suchen, aktuelle SSID anzeigen, neue WPA2-PSK- oder offene Netzwerke auswählen, Verbindungswechsel bestätigen, gespeicherte Netze markieren. WEP, Enterprise/EAP und WPA3-SAE-only werden in dieser Version nicht als neue Netze eingerichtet. Passwort wird im GUI eingetragen und für WPA2 lokal zu einer PSK abgeleitet; kein Passwort-Logging oder Shell-Interpolation.

**Persistenzproblem und Lösung:** Das ursprünglich eingesetzte `casper.conf` hatte `update_config=0`. Daher war ein WLAN-Wechsel nur bis zum Neustart wirksam. Bestätigtes Vorgehen:

```sh
IFACE=wlx000d724820c2
cp -a /etc/wpa_supplicant/casper.conf /root/casper.conf.backup
wpa_cli -i "$IFACE" set update_config 1
wpa_cli -i "$IFACE" save_config
grep '^update_config=' /etc/wpa_supplicant/casper.conf
```

Anschließend neues WLAN lokal am Casper auswählen, `wpa_cli -i "$IFACE" list_networks` prüfen und Neustarttest durchführen. Das wurde am 10.11.2026 erfolgreich bestätigt; der alte AP erscheint als „gespeichert“. Nicht die private Konfigurationsdatei einchecken.

**Grenzen:** Ein Netzwechsel kann die SSH-Verbindung unterbrechen. Die GUI hat derzeit keine automatische Rückschaltung. Ein erfolgreicher WPA-Zustand garantiert nicht, dass DHCP erfolgreich neu ausgehandelt wurde; daher IP und Netzwerkzugang separat prüfen. Der `save_config`-Fehler wird als „NICHT dauerhaft gespeichert“ angezeigt. Mehrere verfügbare gespeicherte Netze/Prioritäten sind noch nicht systematisch getestet.

## Bildschirmtastatur

`/root/casper-keyboard/keyboard.xml` ist ein eigenes QWERTZ-Layout. Ergänzt wurde eine **fünfte Zeile** mit `1234567890@!`. Die Ziffern und Sonderzeichen sind am Gerät getestet; nötig z. B. für WLAN-Passwörter. Diese XML bleibt lokal; beim nächsten Neuaufbau muss die Ziffernreihe wiederhergestellt werden. Wegen fünf Reihen auf nur 192 px sind die Touch-Ziele klein; der Nutzer trifft die Tasten zuverlässig leicht unterhalb der optischen Mitte. Die globale Touch-Matrix **nicht** dafür verstellen.

## Akku-Tool

`casper-battery.py` liest ausschließlich die AXP209-Sysfs-Dateien unter:

- `/sys/class/power_supply/axp20x-battery/`: `capacity`, `status`, `voltage_now`, `current_now`
- `/sys/class/power_supply/axp20x-usb/`: `online`, `voltage_now`, `current_now`

```sh
python3 /usr/local/bin/casper-battery.py --dump
DISPLAY=:0 python3 /usr/local/bin/casper-battery.py
```

GUI aktualisiert alle fünf Sekunden, bietet Ladebalken, Spannung, Strom, USB-Status und „Schließen“. In v0.1 war versehentlich `command=root.destroy()` enthalten; **v0.2 verwendet korrekt `command=root.destroy`** und wurde getestet.

Beispielmessungen: Akku 1 %, 3.500 V, Entladen mit 723 mA ohne USB; nach Anschluss 4 %, 3.62 V, Laden mit ~86–91 mA, USB ~4.32–4.34 V/~817–819 mA. **Akkukapazität nicht kalibriert**; Restlaufzeit nicht berechnen. Niedrige USB-Eingangsspannung prüfen, bevor daraus Aussagen zur Ladeleistung abgeleitet werden.

## Menüstarter und X11-Autostart

`/root/.xinitrc` wurde gesichert als `/root/.xinitrc.backup-menu`. Die bestehende Sitzung verwendet SysVinit und startet Xorg über `xinit`; `xterm` bleibt der Sitzungshauptprozess. Der bei Reboot bestätigte `.xinitrc`-Aufbau:

```sh
#!/bin/sh
export DISPLAY=:0
export MB_KBD_CONFIG=/root/casper-keyboard/keyboard.xml

xset s off
xset -dpms

matchbox-window-manager -use_titlebar no &
sleep 2
matchbox-keyboard > /tmp/casper-keyboard.log 2>&1 &

(
    sleep 3
    /usr/bin/python3 /usr/local/bin/casper-menu.py > /var/log/casper-menu.log 2>&1
) &

exec xterm -geometry 80x24+0+0 -fa Monospace -fs 10
```

Menü beim Start im Vordergrund, Button „WLAN verwalten“ bzw. „Akku anzeigen“. Beim Schließen eines Tools erscheint das Menü wieder. HOME-Button toggelt die Tastatur über den **separaten** SysVinit-Boot-Hook `/etc/boot.d/90-casper-keyboard` und `/usr/local/bin/casper-keyboard-toggle.py`. Den Hook nicht doppelt aus `.xinitrc` starten.

Beispielinstallation, wenn die Quellskripte im Repo vorhanden sind:

```sh
install -o root -g root -m 0755 scripts/casper-wifi.py /usr/local/bin/casper-wifi.py
install -o root -g root -m 0755 scripts/casper-battery.py /usr/local/bin/casper-battery.py
install -o root -g root -m 0755 scripts/casper-menu.py /usr/local/bin/casper-menu.py
```

Falls das Repo auf WSL statt am Casper ausgecheckt ist, Dateien per `scp` übertragen und anschließend auf dem Tablet installieren. Das Menü erwartet exakt diese Zielpfade.

**Diagnose:** `cat /var/log/casper-menu.log`, `DISPLAY=:0 python3 /usr/local/bin/casper-menu.py`, `dpkg --audit`, `dmesg | grep -Ei 'EXT4-fs error|I/O error'`.

## Weiter offen

- Optional: dauerhafter Desktop ohne xterm als Sitzungshalter, aber nur nach separatem Neustarttest.
- WLAN-Prioritäten, DHCP nach Wechsel, Rückfallmechanismus bei nicht erreichbarem AP.
- Größere Tastatur-Touchziele ohne das Passwortfeld zu verdecken.
- Rückkehr zur robusten SD-Integrität und Stromversorgung (siehe [SD-Reparatur](casper-sd-repair-2026-11-10.md)).
