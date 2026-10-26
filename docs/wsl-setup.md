# Windows + WSL2: Installation und Bedienung

Diese Anleitung dokumentiert unsere Entwicklungsumgebung für den **Casper TAB-WB72 (Allwinner A13)**. Wir bauen Linux, U-Boot und BusyBox in Ubuntu unter WSL2 und kopieren nur die fertigen Dateien auf die microSD.

> **Getestete Umgebung:** Windows mit WSL2 und Ubuntu 26.04.1, Benutzer `casper`. Andere Ubuntu-Versionen funktionieren eventuell, sind hier aber nicht getestet.

## 1. WSL2 unter Windows installieren

**Normale PowerShell** als Administrator öffnen – **nicht PowerShell ISE**. Bei unserer Installation hing die interaktive Ubuntu-Benutzeranlage in PowerShell ISE.

```powershell
wsl --install -d Ubuntu
```

Wenn Windows dazu auffordert, neu starten. Anschließend Ubuntu über das Startmenü oder `wsl -d Ubuntu` in einem **interaktiven Terminal** öffnen und Linux-Benutzer samt Passwort anlegen. Die Eingabe eines Linux-Passworts bleibt am Bildschirm unsichtbar.

Prüfen:

```powershell
wsl --status
wsl --list --verbose
```

Die Ubuntu-Distribution sollte mit **VERSION 2** angezeigt werden. Falls nötig, erst **nach** der Installation und anhand des tatsächlichen Distributionsnamens umstellen:

```powershell
wsl --set-version Ubuntu 2
```

WSL aktualisieren:

```powershell
wsl --update
```

## 2. Ubuntu aktualisieren und Build-Werkzeuge installieren

**Die folgenden Befehle laufen in Ubuntu, nicht in PowerShell.**

```bash
sudo apt update
sudo apt upgrade
sudo apt install -y \
  build-essential git make bc bison flex \
  libssl-dev libelf-dev libncurses-dev \
  gcc-arm-linux-gnueabi gcc-arm-linux-gnueabihf \
  binutils-arm-linux-gnueabi binutils-arm-linux-gnueabihf \
  device-tree-compiler u-boot-tools \
  python3 cpio gzip xz-utils wget curl file
```

Versionsprüfung:

```bash
uname -a
arm-linux-gnueabihf-gcc --version
arm-linux-gnueabi-gcc --version
nproc
free -h
```

Bei unserem Projekt liefen die Builds mit `-j2`; mehr parallele Jobs nur nutzen, wenn RAM/CPU ausreichen.

## 3. Entwicklungsverzeichnis

In Ubuntu:

```bash
mkdir -p ~/casper-a13
cd ~/casper-a13
pwd
```

Bei Benutzer `casper` entspricht das `/home/casper/casper-a13`.

Das GitHub-Repository enthält hauptsächlich die Dokumentation. **Die drei Upstream-Quellbäume sind nicht darin enthalten**, sondern liegen lokal unter:

```text
~/casper-a13/
├── linux/                   # Linux-Quellen und Kernel-Build
├── busybox/                 # BusyBox-Quellen
├── build-casper/            # lokales U-Boot Build-Verzeichnis
├── initramfs/               # temporärer Root-Dateibaum
├── initramfs.cpio.gz        # resultierendes Archiv
├── boot-linux.cmd           # U-Boot Bootskript (Quelle)
└── backups/                 # lokale Sicherungen
```

Diese Darstellung dokumentiert den tatsächlich verwendeten Aufbau. Das Repository ist **kein automatischer Komplettinstaller**. Für Beschaffung und Versionen der Upstream-Sourcen siehe [Bauen und Booten](build-and-boot.md).

## 4. Zwischen PowerShell und Ubuntu wechseln

PowerShell:

```powershell
wsl -d Ubuntu
```

Ubuntu verlassen:

```bash
exit
```

Ubuntu-Dateien im Windows-Explorer öffnen:

```text
\\wsl$\Ubuntu\home\casper\casper-a13
```

Alternativ in Ubuntu:

```bash
explorer.exe .
```

Ein fertiges `zImage` auf die FAT32-microSD kopieren (PowerShell-Beispiel):

```powershell
# Laufwerksbuchstaben unmittelbar vorher prüfen; J: war nur unser Testaufbau!
Copy-Item "\\wsl$\Ubuntu\home\casper\casper-a13\linux\arch\arm\boot\zImage" "J:\zImage" -Force
```

**Wichtig:** Linux-Quellbäume für die Build-Arbeit besser im WSL-Dateisystem (`~/...`) liegen lassen, nicht unter `/mnt/c`; damit werden Linux-Dateirechte und Dateisystemverhalten zuverlässig unterstützt.

## 5. Was liegt auf der microSD?

Das FAT32-Dateisystem der getesteten Karte enthält:

```text
zImage
sun5i-a13-q8-tablet.dtb
initramfs.cpio.gz
boot.scr
```

U-Boot selbst liegt **nicht** als Datei in dieser FAT32-Partition, sondern wurde im freien Bereich vor der ersten Partition abgelegt. Die SD-Partition beginnt beim getesteten Medium bei 4 MiB. Die Bootloader-Installation ist deshalb **ein separater, risikobehafteter Rohdatenträger-Schritt**. Keine `dd`-/`PhysicalDrive`-Befehle aus fremden Anleitungen ungeprüft übernehmen.

Beim Kernel-Update normalerweise nur `zImage` (und falls geändert die `.dtb`) ersetzen. Für geänderte Programme im initramfs auch `initramfs.cpio.gz` aktualisieren. Für geänderte U-Boot-Kommandos `boot.scr` neu erzeugen.

## 6. USB/FEL über WSL (optional, Rettungs- und Diagnoseweg)

Der erfolgreiche Standardstart erfolgt inzwischen direkt von **microSD**. FEL war für das Testen des Bootloaders wichtig und ist weiterhin nützlich:

- Tablet in den **FEL-Modus** bringen (bei unserem Gerät funktionierte Home + Power).
- Windows-USB-Gerät mit VID:PID `1f3a:efe8` identifizieren.
- `usbipd-win` wird für das Durchreichen eines USB-Geräts an WSL benötigt; Installation und Bus-ID sind hostabhängig.

In administrativer PowerShell:

```powershell
usbipd list
# Beispiel aus unserem Test, nicht blind übernehmen:
usbipd bind --busid 3-3 --force
usbipd attach --wsl --busid 3-3
```

In Ubuntu:

```bash
lsusb
# Falls sunxi-tools lokal gebaut wurden:
cd ~/casper-a13/sunxi-tools
sudo ./sunxi-fel version
```

Die USB-Bus-ID `3-3` ist **nur ein historisches Beispiel**. Sie kann nach Umstecken oder Neustart anders sein. Der `--force`-Schalter war im Test wegen einer USBPcap-Belegung nötig und sollte nur bewusst eingesetzt werden.

## 7. Fehlerbehebung

| Problem | Prüfen |
|---|---|
| Benutzeranlage hängt | Normales Windows Terminal/PowerShell statt PowerShell ISE verwenden |
| `arm-linux-gnueabihf-gcc: command not found` | `sudo apt install gcc-arm-linux-gnueabihf` |
| Kein Zugriff auf `\\wsl$\Ubuntu` | `wsl --list --verbose` prüfen und Ubuntu starten |
| Kernel-Build dauert lange | Bei laufendem `CC`/`AR` nicht abbrechen; mit `nproc`, `free -h` und `ps` Ressourcen kontrollieren |
| USB in WSL fehlt | Gerät in `usbipd list` suchen, korrekte Bus-ID verwenden und erneut anhängen |
| Tablet bootet nicht von SD | Karte, FAT32-Dateien und Bootloader-Position prüfen; **NAND nicht beschreiben** |

## 8. GitHub-Dokumentation lokal bearbeiten

PowerShell oder Ubuntu (mit installiertem Git):

```bash
cd ~
git clone https://github.com/lexxi/casper-a13-linux.git
cd casper-a13-linux
git status
```

Änderungen lokal committen (mit eigener Git-Identität und eingerichtetem GitHub-Zugang):

```bash
git add README.md docs/
git commit -m "docs: update Casper installation notes"
git push origin main
```

Das Hochladen von NAND-Abbildern, `*.bin`, `*.fex`, WLAN-Passwörtern und privaten Schlüsseln ist bewusst ausgeschlossen. Ein `.gitignore` allein schützt **nicht** vor dem absichtlichen Erzwingen solcher Dateien.
