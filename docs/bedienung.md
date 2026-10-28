# Casper bedienen und testen

## Derzeit möglicher Betrieb

Unser Casper TAB-WB72 startet mit eingelegter, entsprechend vorbereiteter microSD **ohne PC-Anschluss**:

```text
Allwinner A13 Boot-ROM
  → SPL
  → U-Boot 2025.01
  → Linux 6.12.0
  → BusyBox 1.37.0 initramfs
  → sichtbare Shell: ~ #
  → internes Realtek-WLAN / WPA2 / DHCP / Dropbear SSH
```

Der Bildschirm zeigt den Linux-Boot und die Shell. Das ist **bestätigt**. Seit Kernel #10 ist außerdem der Goodix-GT811-Touchscreen über einen automatisch gestarteten Userspace-uinput-Treiber als Linux-Eingabegerät nutzbar. Ein eigenständiger grafischer 800×480-Framebuffer-Touch-Test (Raster und Fadenkreuz) wurde über SSH aus `/tmp` erfolgreich gestartet. Eine dauerhaft installierte grafische Oberfläche existiert noch nicht; die Shell selbst ist nicht durch Touch bedienbar. Eine externe USB-Tastatur bleibt ungetestet.

## Start

1. Die vorbereitete microSD im ausgeschalteten Casper einsetzen.
2. Tablet einschalten; im Test war alternativ ein Neustart über die Reset-Öffnung möglich.
3. Nach U-Boot und Kernelmeldungen erscheint die BusyBox-Shell `~ #`.

Ein angeschlossener PC ist dafür nicht erforderlich. **SSH ist erfolgreich getestet**; die Touch-Ereignisse werden nach dem Boot automatisch unter `/dev/input/event1` bereitgestellt. Externe USB-Tastatur noch ungetestet.

## Dateien und Rollen

| Datei auf der microSD | Funktion |
|---|---|
| `zImage` | Linux-Kernel (ARM) |
| `sun5i-a13-q8-tablet.dtb` | Hardwarebeschreibung (Device Tree) |
| `initramfs.cpio.gz` | Minimal-Linux mit BusyBox und `/init` |
| `boot.scr` | von U-Boot ausgeführtes Startskript |
| `wlan.conf` | Lokale WPA2/WLAN-Konfiguration; wird durch das Netzwerk-Startskript gelesen; **niemals veröffentlichen** |
| `casper-boot.log` | Vom Netzwerk-Startskript auf die SD geschriebene Diagnose |
| `casper-power.csv` | Messprotokoll für Akku und USB-Versorgung; Prototyp erfolgreich getestet |
| `casper-ntp.log` | NTP-Diagnose des Power-Service-Prototyps |

Im Linux-System wurde `/init` so eingerichtet, dass `proc`, `sysfs` und `devtmpfs` gemountet werden. Anschließend startet eine Konsole:

```sh
exec setsid cttyhack /bin/sh </dev/console >/dev/console 2>&1
```

## Was aktuell noch nicht geht

- **USB-Tastatur:** Tablet hat nur eine Mini-USB-Buchse. Ein **Mini-USB-OTG-Hostadapter** wird für eine normale USB-Tastatur benötigt. MUSB/HID sind konfiguriert; Device Tree und echter Hostbetrieb müssen noch getestet werden.
- **WLAN:** Funktioniert mit dem integrierten `rtl8192cu` deutlich besser als mit `rtl8xxxu`; gelegentliche Latenzausreißer bleiben.
- **SSH:** Funktioniert per Dropbear/Public-Key. Passwortanmeldung ist deaktiviert; korrektes Eigentum von `/root` ist entscheidend.
- **Touchscreen/Grafik:** GT811-Ein-Finger-Input startet automatisch mit PB3-Wakeup, Panelinitialisierung und PG11-IRQ. Ein grafischer Framebuffer-Test ist lokal erfolgreich; die X-Spiegelung erfolgt derzeit nur im Diagnoseprogramm, die dauerhafte Treiberkorrektur ist noch offen. Die experimentelle neue Treiberversion zeigte einen `Bus error`.

## Goodix GT811: Touch nach dem Boot prüfen

```sh
cat /tmp/gt811.log
cat /proc/bus/input/devices
evtest /dev/input/event1
```

Erwartet: `Casper Goodix GT811 Touchscreen`, `BTN_TOUCH` (330) und `ABS_X` / `ABS_Y`. Nach dem vollständigen Reboot bestätigt `od -An -tx1 -w16 /dev/input/event1` Fingerbewegungen und Loslassen; `evtest` ist nur nutzbar, falls das Zusatzprogramm installiert ist. Aktuell verwendet der Boot-Treiber `--irq` statt des alten Polling-Modus. Zur Initialisierung verwendet das lokale Initramfs `/gt811-start.sh`, `/usr/sbin/gt811-init-test`, `/usr/sbin/gt811-uinput` und `/etc/gt811/config.bin`. Die originale Konfiguration und das Android-Modul gehören **nicht** in dieses öffentliche Repository. Details: [GT811 Touchscreen](gt811-touchscreen.md).

**Grafischer Diagnosetest:** Die lokal gebaute ARMHF-Datei `casper-touch-test` lässt sich per `ssh ... 'cat > /tmp/casper-touch-test && chmod 755 /tmp/casper-touch-test' < /tmp/casper-touch-test` übertragen und direkt starten. Sie zeichnet auf `/dev/fb0` (800×480, 32 Bit, Stride 3200) und liest `/dev/input/event1`. Die horizontal korrigierte Version führt das Kreuz dem Finger nach; die Y-Anzeige verwendet Ursprung links unten. Beobachtete Ränder: X links 8 / rechts 788, Y unten 4 / oben 472. Nicht die X-Spiegelung zusätzlich im Treiber aktivieren, ohne die Test-App anzupassen.

## WLAN-Konfiguration (aktiv)

Später ist eine lokale Datei `wlan.conf` auf der SD vorgesehen, beispielsweise für ein WPA2-Personal-Netz:

```ini
ctrl_interface=/var/run/wpa_supplicant
update_config=0
country=AT

network={
    ssid="MEIN_2_4_GHZ_WLAN"
    psk="MEIN_PASSWORT"
    key_mgmt=WPA-PSK
}
```

**Nicht nach GitHub hochladen.** Diese Datei enthält das Passwort im Klartext. Die Netzwerkvariante des initramfs liest sie beim Start von der microSD und startet `wpa_supplicant`, `udhcpc` und Dropbear.

Vereinfachte Startlogik der getesteten Netzwerkvariante (`wlan0` wurde bestätigt):

```sh
mkdir -p /mnt/sd /var/run/wpa_supplicant
mount -t vfat /dev/mmcblk0p1 /mnt/sd
ip link set wlan0 up
wpa_supplicant -B -i wlan0 -c /mnt/sd/wlan.conf
udhcpc -i wlan0
```

Die tatsächlich verwendete Netzwerkvariante bringt `wpa_supplicant` und DHCP-Skripte samt ARMHF-Laufzeitbibliotheken mit. Die ursprüngliche Minimalvariante `initramfs/` ist davon zu unterscheiden.

## SSH-Zugang und WLAN-Diagnose

Unter Windows (privaten Schlüsselpfad anpassen, Tablet-IP aus DHCP-Leases entnehmen):

```powershell
ssh -i "$env:USERPROFILE\.ssh\casper_a13" -o IdentitiesOnly=yes root@192.168.98.36
```

Die Adresse war die im Test vergebene DHCP-Adresse; sie kann sich ändern. Bei `Permission denied (publickey)` zunächst passenden öffentlichen Schlüssel in `/root/.ssh/authorized_keys` kontrollieren sowie **UID/GID 0** für `/root` und `/root/.ssh` und die Modi `0700` bzw. `0600` prüfen. Der öffentliche Kommentar `casper-a13` ist kein Hostname.

Für die WLAN-Analyse wurde `iw` **temporär per SSH** auf das laufende RAM-System übertragen. Verfügbare Befehle, sofern `iw` vorhanden ist:

```sh
iw dev wlan0 get power_save
iw dev wlan0 link
iw dev wlan0 station dump
```

Gemessen: `Power save: off`, −79 dBm, RX 13 Mbit/s, TX 72,2 Mbit/s, Kanal 6 bei 2437 MHz. Zum nächsten Test Tablet näher an den AP bringen, drehen und parallel vom Windows-Rechner `ping -n 50 192.168.98.36` ausführen. Die Datei `/proc/net/wireless` existiert in der aktuellen Kernelkonfiguration nicht; `iw` liefert die relevanten Werte.

## Akku, NTP und Power Monitor

Der getestete Kernel stellt `/sys/class/power_supply/axp20x-battery` und `axp20x-usb` bereit. Die Werte in `voltage_now` bzw. `current_now` sind **Mikrovolt/Mikroampere**. Zum Nachsehen:

```sh
for p in /sys/class/power_supply/*; do
  echo "=== ${p##*/} ==="
  for f in type status capacity voltage_now current_now online; do
    [ -r "$p/$f" ] && echo "$f: $(cat "$p/$f")"
  done
done
```

Lade- und Entladezustände wurden bestätigt, ebenso das Schreiben von Messungen nach `/mnt/sd/casper-power.csv`. BusyBox-NTP stellte nach manuellem Start von `/power-services.sh` die korrekte UTC-Zeit her. **Autostart ist noch nicht abschließend getestet:** In einem Boot hatten `/power-services.sh` und `/casper-power-monitor.sh` versehentlich nur Rechte `0644`; nach `chmod 755` funktionierte der manuelle Test. Die Rechte müssen in der WSL-Quelldatei korrigiert und ein neues initramfs gebootet werden. Siehe [ausführliche Dokumentation](power-management.md).

```sh
date -u
cat /mnt/sd/casper-ntp.log
tail -5 /mnt/sd/casper-power.csv
ps | grep casper-power
```

Noch **keine automatische Abschaltung** bei niedrigem Akku aktiviert; Prozentanzeige ist nicht ausreichend kalibriert.

## Versions- und Diagnosebefehle

```sh
uname -a
cat /proc/cmdline
cat /proc/partitions
dmesg | tail -50
ls /sys/bus/usb/devices
```

Für die funktionierende WLAN-Konfiguration zusätzlich:

```sh
cat /proc/net/dev
dmesg | grep -i firmware
dmesg | grep -i rtl
```

Falls `grep` in der laufenden Minimalumgebung nicht enthalten ist, über BusyBox-Appletts oder eine serielle/SSH-Sitzung prüfen. **ADB-Befehle im ursprünglichen Android und Linux-BusyBox-Befehle nicht verwechseln.**

## Wichtige Grenzen

- Das originale Android bleibt im NAND. Unsere Linux-Entwicklung erfolgt auf microSD.
- Ein Austausch der Bootdateien auf der SD ersetzt keine Neuinstallation von Android.
- U-Boot auf der SD liegt außerhalb des FAT32-Dateisystems. Ein neu formatiertes Medium bootet daher **nicht automatisch**, nur weil man vier Dateien darauf kopiert.
- Die zweite, defekte Tablet-Hardware ist eine separate Reparatur und gehört nicht zur bestätigten Linux-Bootkonfiguration.
