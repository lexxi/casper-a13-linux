# MC3230-Beschleunigungssensor unter Debian 13 (12.11.2026)

## Ergebnis: Auf dem Casper bestätigt

Das Casper TAB-WB72 / INTREEO mit Allwinner A13 bootet Debian 13 armhf von microSD, Linux 6.12.0 **Kernel #5**. Der interne Android-4.0.4-NAND wurde nicht verändert.

Der Lagesensor funktioniert mit dem **mainline IIO-Treiber `mc3230.ko`** an **I²C-Bus 1, Adresse 0x4c**. X/Y/Z-Rohwerte verändern sich beim Kippen, z. B. `(-4,19,118)`, `(-68,-24,69)`, `(16,98,67)`. Das Modul wird über einen lokalen Casper-Boot-Hook gestartet; der Nutzer bestätigte Betrieb **nach Reboot**. Die grafische Lageanzeige in `/usr/local/bin/casper-menu.py` aktualisiert Werte jede Sekunde.

**Offen:** Kalibrierung der vier Displayorientierungen, stabiler Rotationsmechanismus (dynamisches Xrandr verursachte zuvor Xorg-SIGSEGV), dauerhafte Device-Tree-Beschreibung, robuste IIO-Geräteerkennung statt festem `iio:device1`. Keine automatische Displayrotation aktiviert.

## Warum nicht MMA7660?

Die Original-Android-FEX nennt `gsensor_name="mma7660"`, `gsensor_twi_id=1`, `gsensor_twi_addr=0x4c` und alternativ DMARD06 (Adresse 0x1c, nicht bestätigt). Original-Android mit Linux 3.0.8+ lässt das Modul `mma7660` laufen. Der Abgleich der `/sys/module/mma7660/srcversion` mit den gesicherten Moduldateien identifizierte **`mma7660.ko`** (srcversion `19DDF3E188D06ACF9CBAF67`), nicht `mma7660_d06.ko` (`5F6F1C33F006A879695F733`). Unter Android lieferten `/dev/input/event3` und `getevent` variable Beschleunigungsdaten. Das Display musste dafür entsperrt sein.

Disassembly von `mma7660_probe` im originalen Modul zeigt diese Initialisierungsfolge:

| Register | Wert |
|---|---|
| `0x07` | `0x00` |
| `0x08` | `0x51` |
| `0x06` | `0x0b` |
| `0x05` | `0xa0` |
| `0x07` | `0x41` |

Danach liest der Treiber `0x18` und `0x3b` und vergleicht die Kennungen mit `0x01` bzw. `0x19`, um einen Sonderpfad zu aktivieren. Der Code enthält `MC3230_i2c_read` (Registerzeiger senden, 10 ms warten, ein Byte lesen). Die Kombination und die erfolgreichen Linux-MC3230-Messungen sprechen stark für einen MC3230-kompatiblen Chip; eine separate Chipmarkierungs-/Hardware-ID-Verifikation wurde nicht durchgeführt.

Ein testweise gebauter mainline `mma7660.ko` für Linux 6.12 konnte an `1-004c` binden und `iio:device1` bereitstellen, lieferte jedoch nur `0,0,0`. Erst der mainline-Treiber `mc3230.ko` lieferte bewegliche Daten. Der alte Treibername ist also kein zuverlässiger Beleg für einen MMA7660-Chip.

## Build auf X1 / WSL

Quellen: `~/casper-a13/linux`, ARM GCC `arm-linux-gnueabihf-`, Kernel 6.12.0 #5. Vorhandene `vmlinux`, `System.map`, `.config` und `zImage` gehörten zum laufenden Build. `Module.symvers` fehlte zunächst; `make ... modules` erzeugte es. Ein reines `make ... vmlinux` hatte es **nicht** erzeugt.

```bash
cd ~/casper-a13/linux
cp -a .config ../config-kernel5-before-mma7660
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j4 modules

scripts/config --module MC3230
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- olddefconfig
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j4 drivers/iio/accel/mc3230.ko

modinfo drivers/iio/accel/mc3230.ko
```

Build-Artefakte wie `*.ko`, `Module.symvers` und originale Android-Module bleiben lokal. **Den laufenden Kernel #5 nicht ersetzen.** Das Modul muss zum genauen laufenden Kernelbuild passen; gleiche Release-Zeichenfolge allein ist keine vollständige Kompatibilitätsgarantie.

## Test auf dem Casper

Vor der Neuregistrierung muss ein gegebenenfalls vorhandenes Testgerät `1-004c` entfernt werden. **Nur wenn es existiert und von einem Testtreiber gebunden ist:**

```sh
test -e /sys/bus/i2c/devices/1-004c && \
  echo 0x4c > /sys/bus/i2c/devices/i2c-1/delete_device
```

Dann `mma7660` gegebenenfalls entladen, `mc3230.ko` transferieren und laden. Das folgende Beispiel setzt voraus, dass die Adresse frei ist:

```sh
/usr/sbin/insmod /tmp/mc3230.ko
echo mc3230 0x4c > /sys/bus/i2c/devices/i2c-1/new_device
cat /sys/bus/iio/devices/iio:device1/name
cat /sys/bus/iio/devices/iio:device1/in_accel_{x,y,z}_raw
```

Der Sysfs-`new_device`-Aufruf ist **nicht rein lesend**: Der Treiber initialisiert die Sensorregister. Nach dem Test wurde `mc3230` erfolgreich gebunden, mit laufenden Messwerten. `power/runtime_status=unsupported` ist kein Messfehler; der Treiber meldet keine Runtime-PM-Statusunterstützung.

## Persistenz nach Neustart

Auf dem Gerät wurde das Modul lokal nach `/lib/modules/6.12.0/extra/mc3230.ko` kopiert. `depmod -a 6.12.0` erzeugte `modules.dep`, warnte jedoch wegen fehlender `modules.order`, `modules.builtin` und `modules.builtin.modinfo`. Der Boot-Hook benutzt daher testweise den **absoluten Modulpfad** mit `insmod`, nicht `modprobe`.

Installierte lokale Skripte:

- `/usr/local/sbin/casper-mc3230-init` – lädt das Modul, falls `/sys/module/mc3230` fehlt; meldet `mc3230 0x4c` nur an, wenn `1-004c` fehlt.
- `/etc/boot.d/85-casper-mc3230` – ruft das Initialisierungsskript auf.
- Bestehender SysVinit-Startmechanismus führt `run-parts /etc/boot.d` aus; der HOME-Tasten-Hook liegt separat in `90-casper-keyboard`.

**Achtung:** Bei `run-parts` ohne `--regex` werden Dateinamen mit Punkten normalerweise ausgelassen; der gewählte Name `85-casper-mc3230` ist geeignet. Das Startskript ist lokal installiert und der post-reboot-Sensortest wurde bestätigt. `/lib/modules/6.12.0/extra/` und `/etc/boot.d/` sind nicht allein durch GitHub-Dokumentation auf einem frisch installierten Gerät vorhanden.

## Menüintegration

Der auf dem Gerät getestete Stand `casper-menu.py` v0.2 enthält vier Schaltflächen (WLAN, Akku, Terminal, NetSurf-Browser), Helligkeitsregler (1–10), Display ausschalten, HOME-Hinweis sowie Sensorstatus. Die Statuszeile liest derzeit `/sys/bus/iio/devices/iio:device1/in_accel_{x,y,z}_raw` jede Sekunde und zeigt *Flach*, *Neigung X+/X-/Y+/Y-* oder *Unbestimmt* sowie Rohwerte an.

Die Lage-Erkennung ist noch **keine kalibrierte 0/90/180/270-Grad-Orientierung**. Die erste Messreihe `(0,23,117)`, `(-3,20,118)`, `(0,111,28)`, `(-5,-71,26)` zeigt zwei nahezu identische flache Messungen und eine eindeutige Y-Achsenänderung beim Aufrichten. Die Benennung von links/rechts/normal/invertiert bleibt offen.

**Sicherheit:** Android-NAND-Images, `script.bin`, originale proprietäre Android-`.ko`-Module, private WLAN-Konfiguration und SSH-Schlüssel **nicht** in GitHub hochladen.
