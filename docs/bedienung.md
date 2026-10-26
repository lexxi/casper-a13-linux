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
```

Der Bildschirm zeigt den Linux-Boot und die Shell. Das ist **bestätigt**. Die Eingabe über eine externe Tastatur und die spätere Touchbedienung sind noch **nicht** bestätigt.

## Start

1. Die vorbereitete microSD im ausgeschalteten Casper einsetzen.
2. Tablet einschalten; im Test war alternativ ein Neustart über die Reset-Öffnung möglich.
3. Nach U-Boot und Kernelmeldungen erscheint die BusyBox-Shell `~ #`.

Ein angeschlossener PC ist dafür nicht erforderlich. Ohne funktionierende USB-Tastatur, Touch-Treiber oder SSH kann man die Shell zunächst **nur sehen**.

## Dateien und Rollen

| Datei auf der microSD | Funktion |
|---|---|
| `zImage` | Linux-Kernel (ARM) |
| `sun5i-a13-q8-tablet.dtb` | Hardwarebeschreibung (Device Tree) |
| `initramfs.cpio.gz` | Minimal-Linux mit BusyBox und `/init` |
| `boot.scr` | von U-Boot ausgeführtes Startskript |
| `wlan.conf` (geplant) | Lokale WPA/WLAN-Konfiguration; wird aktuell noch nicht automatisch verwendet |

Im Linux-System wurde `/init` so eingerichtet, dass `proc`, `sysfs` und `devtmpfs` gemountet werden. Anschließend startet eine Konsole:

```sh
exec setsid cttyhack /bin/sh </dev/console >/dev/console 2>&1
```

## Was aktuell noch nicht geht

- **USB-Tastatur:** Tablet hat nur eine Mini-USB-Buchse. Ein **Mini-USB-OTG-Hostadapter** wird für eine normale USB-Tastatur benötigt. MUSB/HID sind konfiguriert; Device Tree und echter Hostbetrieb müssen noch getestet werden.
- **WLAN:** Interner Realtek-USB-Adapter `0bda:8176` wurde unter Android ermittelt. `CONFIG_RTL8XXXU=y` wurde in der **neuen** Kernel-Konfiguration bestätigt; erfolgreiche Verbindung unter Linux steht noch aus.
- **SSH:** Dropbear, WLAN-Authentifizierung, DHCP, Boot-Autostart und Schlüsselverwaltung sind noch nicht eingerichtet.
- **Touchscreen/Grafik:** Goodix GT811 ist identifiziert, aber noch nicht in Betrieb.

## WLAN-Konfiguration (Vorbereitung, noch nicht aktiv)

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

**Nicht nach GitHub hochladen.** Diese Datei enthält das Passwort im Klartext. Sie ist **noch keine funktionsfähige Autokonfiguration**: Dazu müssen Linux den WLAN-Adapter erkennen, Firmware (falls nötig), `wpa_supplicant`, DHCP und unser Startskript erst korrekt integriert werden.

Geplante Startlogik nach Validierung des WLAN-Interfaces (Name `wlan0` nur beispielhaft):

```sh
mkdir -p /mnt/sd /var/run/wpa_supplicant
mount -t vfat /dev/mmcblk0p1 /mnt/sd
ip link set wlan0 up
wpa_supplicant -B -i wlan0 -c /mnt/sd/wlan.conf
udhcpc -i wlan0
```

Die `ip`- und `wpa_supplicant`-Programme müssen im initramfs tatsächlich verfügbar sein; der derzeitige BusyBox-Aufbau garantiert das nicht.

## Versions- und Diagnosebefehle (sobald Eingabe möglich)

```sh
uname -a
cat /proc/cmdline
cat /proc/partitions
dmesg | tail -50
ls /sys/bus/usb/devices
```

Nach erfolgreich eingebauter WLAN-Unterstützung zusätzlich:

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
