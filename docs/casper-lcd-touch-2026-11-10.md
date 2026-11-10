# Casper TAB-WB72: LCD-Timings und Touch-Kalibrierung (10.11.2026)

## Ergebnis (am Gerät nach Neustart bestätigt)

Der ursprüngliche horizontale Bildversatz (links ungenutzter Rand, rechts abgeschnittene Darstellung) ist behoben. Das 800×480-LCD zeigt nun xterm und Matchbox Keyboard vollständig. Die Touchpositionen wurden korrigiert und funktionieren auch nach einem vollständigen Neustart. Der physische HOME-Taster schaltet die Bildschirmtastatur weiterhin um.

**Getestete Kombination:** Debian 13 armhf, Linux 6.12 Kernel #5 (`zImage-test` auf der Test-SD), neuer **Device Tree**, Xorg/Matchbox, Goodix GT811; ursprüngliches Android-NAND unverändert. Es war **kein neuer Kernel-Build** erforderlich. Die ursprünglichen Kernel-#5-ZImage- und DTB-Artefakte müssen als Rückfallstand erhalten bleiben.

## Ursache und Abgleich

Der ursprünglich verwendete DT-Panel-Knoten enthielt `compatible = "bananapi,s070wv20-ct16"`. Der zugehörige Modus in `drivers/gpu/drm/panel/panel-simple.c` unter Linux 6.12 lautet:

| Wert | generisches Banana-Pi-Panel | erfolgreicher Casper-Test |
| --- | ---: | ---: |
| Pixeltakt | 30 MHz | 33 MHz |
| aktive Pixel | 800 × 480 | 800 × 480 |
| H front / sync / back | 40 / 48 / 40 | 209 / 1 / 45 |
| H total | 928 | 1055 |
| V front / sync / back | 13 / 3 / 29 | 22 / 1 / 22 |
| V total | 525 | 525 |

Die Testwerte wurden aus `original-android/script.fex` des echten Casper abgeleitet: `lcd_x=800`, `lcd_y=480`, `lcd_dclk_freq=33`, `lcd_hbp=46`, `lcd_ht=1055`, `lcd_vbp=23`, `lcd_vt=1050`, `lcd_hv_hspw=0`, `lcd_hv_vspw=0`. Alte sunxi-FEX- und Linux-DRM-Felder sind nicht generell identisch; die folgenden Werte sind **an diesem Gerät praktisch getestet**. Die Timingdifferenz ist eine plausible technische Erklärung für den Versatz; eine separate elektrische Messung erfolgte nicht.

## Device-Tree-Ergänzung

Lokale Quelldatei (der vollständige Linux-Quellbaum wird **nicht** in diesem Repository verteilt):

`~/casper-a13/linux/arch/arm/boot/dts/allwinner/sun5i-a13-q8-tablet.dts`

**Am Ende der Datei**, auf Top-Level nach `&lradc { ... };`, die folgende Erweiterung anfügen. Den vorhandenen `panel: panel`-Knoten mit `power-supply`, `enable-gpios`, `backlight` und `port` **nicht** entfernen:

```dts
/*
 * Casper TAB-WB72 / INTREEO LCD
 * Values derived from original Android 4.0.4 script.fex.
 * Tested with Linux 6.12 kernel #5 on 2026-11-10.
 */
&panel {
        compatible = "panel-dpi";

        panel-timing {
                clock-frequency = <33000000>;
                hactive = <800>;
                vactive = <480>;
                hfront-porch = <209>;
                hsync-len = <1>;
                hback-porch = <45>;
                vfront-porch = <22>;
                vsync-len = <1>;
                vback-porch = <22>;
        };
};
```

`CONFIG_DRM_PANEL_SIMPLE=y` war im getesteten Kernel bereits gesetzt. `panel-dpi` wird hier vom Kernel-Paneltreiber unterstützt.

Build **nur des DTB** auf WSL Ubuntu:

```sh
cd ~/casper-a13/linux
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j2 allwinner/sun5i-a13-q8-tablet.dtb
mkdir -p ~/casper-a13/backups/kernel-6-display-test
cp arch/arm/boot/dts/allwinner/sun5i-a13-q8-tablet.dtb ~/casper-a13/backups/kernel-6-display-test/
dtc -I dtb -O dts arch/arm/boot/dts/allwinner/sun5i-a13-q8-tablet.dtb 2>/dev/null | grep -A 35 'panel {'
```

Die Bezeichnung `kernel-6-display-test` ist nur der lokale Backup-Ordner: Tatsächlich läuft weiterhin **Kernel #5** mit einem geänderten DTB.

## Sicherer Austausch unter Windows

1. Casper **sauber herunterfahren**, microSD entnehmen, am Windows-PC einstecken. In der Testsitzung war die FAT32-Bootpartition `G:` (Laufwerksbuchstaben jedes Mal kontrollieren).
2. Die funktionierende DTB-Datei **vor dem Überschreiben** sichern:

```powershell
Copy-Item G:\sun5i-a13-q8-tablet.dtb G:\sun5i-a13-q8-tablet.kernel5-backup.dtb
```

3. Neuer DTB aus der WSL-Distribution `Ubuntu-24.04`:

```powershell
Copy-Item "\\wsl$\Ubuntu-24.04\home\alex\casper-a13\linux\arch\arm\boot\dts\allwinner\sun5i-a13-q8-tablet.dtb" "G:\sun5i-a13-q8-tablet.dtb"
```

4. Hashes vergleichen (`Get-FileHash` in PowerShell und `sha256sum` in WSL), Windows-Medium **sicher auswerfen**, am Casper starten. Am 10.11.2026 waren die Größen der alten und neuen DTB-Version **18.205 / 18.447 Bytes**. Die Dateigröße ist *kein* Integritätsnachweis.
5. Bei schwarzem Bildschirm / fehlgeschlagenem Boot nach dem Ausschalten der SD-Karte unter Windows zurückrollen:

```powershell
Copy-Item G:\sun5i-a13-q8-tablet.kernel5-backup.dtb G:\sun5i-a13-q8-tablet.dtb -Force
```

**Boot-Hinweis:** Die eingesetzte Test-SD enthielt `zImage` und `zImage-test`; das zuvor geprüfte aktive `boot.scr` lädt `zImage-test`. Vor einem erneuten Wechsel den tatsächlichen Bootpfad prüfen. Das ursprüngliche Android-NAND nicht verändern. Keine WLAN-Konfiguration, Schlüssel, Firmware-Dumps oder Rohbackups veröffentlichen.

## Persistente Touch-Kalibrierung

Nach dem korrigierten LCD-Scanout war der vorherige Touch-Offset `0.962` um ungefähr 30 px unpassend. XInput-Gerät:

`Casper Goodix GT811 Touchscreen` (in dieser Testsitzung **ID 8**, dynamisch)

Funktionierender Soforttest:

```sh
DISPLAY=:0 xinput set-prop 8 'Coordinate Transformation Matrix' -1 0 1 0 1 0 0 0 1
```

**Dauerhaft** in Debian `/etc/X11/xorg.conf.d/40-casper-touch.conf` die bestehende Zeile korrigieren:

```conf
Option "TransformationMatrix" "-1 0 1 0 1 0 0 0 1"
```

Die bisherige `40-casper-touch.conf` vor Änderungen nach `/root/40-casper-touch.conf.backup` sichern. Für den Live-Test `xinput list` und `xinput list-props <ID>` verwenden; nicht auf die unveränderliche ID 8 vertrauen.

**Bestätigter Neustarttest (10.11.2026):** LCD vollständig, Touch-Zuordnung verbessert und funktionsfähig, Matchbox-Keyboard einschließlich Enter/Backspace, HOME-Toggle nach Boot.

## Noch offen

- Die lokale DTS-Quelle sowie die finale `.config` sind nicht Bestandteil dieses Dokumentations-Repositories. Die Änderung muss auf dem WSL-Build-Rechner erhalten bleiben und beim nächsten Rebuild explizit übernommen werden.
- Das unabhängig beobachtete AXP209-IRQ-54-Problem ist damit **nicht** als behoben nachgewiesen.
