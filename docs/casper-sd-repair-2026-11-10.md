# Casper TAB-WB72: ext4-/dpkg-Reparatur und USB-OTG-Diagnose (10.11.2026)

## Dateisystemfehler nach Tkinter-Installation

Beim Versuch, `python3-tk` unter Debian 13 armhf zu installieren, brach `dpkg` mit `Bad message` für `/var/lib/dpkg/info/libapparmor1:armhf.list` ab. Im Kernel-Log des Geräts: `EXT4-fs error (device mmcblk0p2): ext4_lookup: iget: checksum invalid`, u. a. Inodes 463, 481, 472, 495, 502, 487. Root ist `/dev/mmcblk0p2` (3.49 GiB ext4), Boot `/dev/mmcblk0p1` (256 MiB FAT32). Ursache noch nicht geklärt: alter Schreibfehler, unsauberer Shutdown oder Medienfehler sind Hypothesen; kein Nachweis für eine bestimmte Ursache.

### Vollständiges Windows-Image und Reparaturversuch

Windows sah den USB-Multireader mit einer **4.014.997.504-Byte-SD-Karte** (Disk-Nummer war zuerst 4 und später anders). `wsl --mount \\.\PHYSICALDRIVE<N> --bare` schlug mit `ERROR_INVALID_DRIVE` fehl. Ein vollständiges sektorweises Image über Win32 Disk Imager wurde unter `C:\Users\Alex\casper-a13-backup\linux_backup.img` erstellt. **SHA256 Originalimage**:

```text
8C9CC4F063FF69A0F0EF62A51A24BBCD8187D98A2BBB0A4A3862A841C927196B
```

Dieser Hash identifiziert das gesicherte Image, beweist aber allein keine fehlerfreien Mediensektoren. **Niemals** auf das einzige Backup schreiben.

In WSL Ubuntu wurde `linux_backup.img` per `losetup --read-only --partscan` untersucht. `e2fsck -fn /dev/loop0p2` zeigte schwere Inodebeschädigungen im Bereich 461–504 (ungültige Prüfsummen, absurde Dateigrößen, Extent-Fehler); Prüfung abgebrochen. Auf einer **separaten Arbeitskopie** `linux_repair_test.img` wurde `e2fsck -f -y` ausgeführt. Dabei wurden beschädigte Metadaten korrigiert und Dateien nach `lost+found` verschoben. Anschließende vollständige `e2fsck -f -n`-Prüfung ohne Fehler:

```text
CASPER_ROOT: 29980/228480 files (0.8% non-contiguous), 516236/913664 blocks
```

Beispiel: Die Reparatur **niemals auf einem gemounteten Root-Filesystem** oder auf der Original-SD unter laufendem Casper durchführen. Die genaue Loop-Nummer jedes Mal durch `losetup -l` und `lsblk` verifizieren.

Eine `ro,noload`-Einbindung der reparierten Kopie zeigte lesbare `/var/lib/dpkg/status`, die Touch-Matrix `-1 0 1 0 1 0 0 0 1`, HOME-Toggle-Skript und WLAN-Konfiguration. `lost+found` enthielt zahlreiche verwaiste Dateistrukturen mit LevelDB/SQLite-typischen Inhalten. Das zeigt, dass ein sauberer ext4-Check nicht automatisch alle Inhalte rekonstruiert. Nach `umount` und `wsl --shutdown` wurde `linux_repair_test.img` mit Win32 Disk Imager zurück auf die SD-Karte geschrieben. **Achtung:** Schreiben überschreibt den gesamten ausgewählten Datenträger und erfordert eindeutige Ziellaufwerksprüfung.

### Debian-Paketverwaltung nach Boot repariert

Neustart gelang. `dmesg | grep -Ei 'EXT4-fs error|checksum invalid|I/O error'` war leer, Touch-Kalibrierung korrekt. `dpkg --audit` zeigte fehlende Verwaltungsdateien für `dbus`, `dbus-daemon`, `dbus-system-bus-common`, `systemd-standalone-sysusers`. Die Reinstallation scheiterte zuerst an `libapparmor1:armhf.list`: Datei hatte fremde `libexpat`-Zeilen, Nullbytes und keinen abschließenden Zeilenumbruch.

Exakt passende Paketdatei war vorhanden:
`/var/cache/apt/archives/libapparmor1_4.1.0-1_armhf.deb`; `dpkg-query` bestätigte Version `4.1.0-1 armhf`.

Die **Dateiliste**, nicht ein ganzes Paket, wurde aus dem Paketarchiv neu aufgebaut und die führende Leerzeile aus `./` entfernt:

```sh
DEB=/var/cache/apt/archives/libapparmor1_4.1.0-1_armhf.deb
LIST='/var/lib/dpkg/info/libapparmor1:armhf.list'
cp -a "$LIST" /root/libapparmor1.list.corrupt
dpkg-deb --fsys-tarfile "$DEB" |
  tar -tf - |
  sed -e 's#^\./#/#' -e 's#/$##' |
  sort -u | sed '/^$/d' > /tmp/libapparmor1.list.new
install -o root -g root -m 644 /tmp/libapparmor1.list.new "$LIST"

DEBIAN_FRONTEND=noninteractive apt-get install --reinstall \
  dbus dbus-daemon dbus-system-bus-common systemd-standalone-sysusers
dpkg --audit
```

Anschließend wurde `python3-tk` installiert und ein einfaches Tkinter-Fenster am Gerät getestet; Casper Battery und das Menü wurden grafisch erfolgreich gestartet. Der Nutzer hat die Paketverwaltungsreparatur als passend bestätigt. Die Paketdatenbank nach Medienfehlern weiter überwachen; `e2fsck` kann inhaltliche Schäden nicht ausschließen.

**Keine** NAND-Daten, WPA-Konfiguration, SSH-Schlüssel oder Rohimages ins öffentliche Repo stellen.

## ESPsoup / ESP32-C5 über externes USB-OTG: noch offen

Ziel: ESP32-C5 via Mini-USB am Casper für ESPsoup testen. `usbutils/lsusb` installiert. Der Linux-USB-Baum:

```text
Bus 001: musb-hdrc root_hub (externer USB-OTG-Pfad)
Bus 002: ehci-platform root_hub
  Realtek RTL8188CUS 0bda:8176 (internes WLAN)
```

Mit Goobay **Art. 95006**, Mini-USB auf USB-A-Buchse, zweitem Kabel zu ESP sowie testweise aktivem Hub gab es **keine USB-Enumeration und keine neuen dmesg-Ereignisse**. Am aktiven Hub leuchtete die rote ESP-LED; zugleich nahm der Casper über USB Strom auf. Dies beweist Versorgung, **nicht** korrekte Host-Datenfunktion; aktive Hubs können ungewollt rückspeisen und wurden für die weitere Diagnose abgezogen.

MUSB meldete:
`/sys/devices/platform/soc/1c13000.usb/musb-hdrc.1.auto/mode` → `b_idle`.

Das Original-Android-FEX in `original-android/script.fex`:

```text
[usbc0]
usb_port_type = 2
usb_detect_type = 1
usb_id_gpio = port:PG02<0><1><default><default>
usb_det_vbus_gpio = port:PG01<0><0><default><default>
usb_drv_vbus_gpio = port:PG12<1><0><default><0>
usb_host_init_state = 0
```

Linux unter `arch/arm/boot/dts/allwinner/sun5i-reference-design-tablet.dtsi` verwendet dazu passend `dr_mode = "otg"`, PG2 ID, PG1 VBUS-Erkennung und PG12 VBUS-Regler. Daher derzeit **kein Beleg für falsch zugewiesene DT-GPIOs**.

Nach Einhängen von debugfs (`mount -t debugfs debugfs /sys/kernel/debug`) zeigt `/sys/kernel/debug/gpio`:

```text
gpio-193 usb0_vbus_det  in  lo IRQ
gpio-194 usb0_id_det    in  hi IRQ
gpio-204 usb0-vbus      out lo
```

**Mit und ohne eingesteckten Goobay-Adapter identisch**; MUSB bleibt `b_idle`. Der Adapter zieht PG2 / OTG-ID nicht auf LOW oder die Leitung/der Kontakt am Tablet ist fehlerhaft. Die exakte Ursache ist noch **nicht bewiesen**. Der Adapter wurde noch nicht elektrisch auf Kurzschluss ID→GND geprüft, da geeignete Messspitzen fehlen. Ein ausdrücklich als **Mini-USB-B-OTG-Host-Adapter mit ID-Pin 4 an GND-Pin 5** spezifizierter Ersatz ist geplant.

Test beim Eintreffen (zunächst **ohne aktiven Hub**, keine Rückspeisung):

```sh
# Falls debugfs nach Neustart nicht aktiv:
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
grep -E 'usb0_id_det|usb0-vbus' /sys/kernel/debug/gpio
cat /sys/devices/platform/soc/1c13000.usb/musb-hdrc.1.auto/mode
lsusb
dmesg | tail -40
```

Erwartung für korrekt erkanntes OTG-Hostkabel: `usb0_id_det` LOW; MUSB kann nach Host-Aktivierung `a_idle` oder `a_host` melden. Erst dann USB-Stick/Hub und ESP32-C5 testen. **Keinen Kernel-/DTB-Umbau auf Verdacht**: Die aktuelle Linux-6.12-Kernel-#5-Konfiguration, LCD, Touch und Toolbox funktionieren.
