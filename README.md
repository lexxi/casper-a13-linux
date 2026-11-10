# Casper TAB-WB72 — Linux on Allwinner A13

Reviving a 2012-era Casper / INTREEO TAB-WB72 tablet with mainline Linux, U-Boot and BusyBox, booted **from microSD without modifying the original Android NAND**.

> **Status (2026-11-09):** Debian 13 (trixie, armhf) boots from microSD with Linux 6.12.0. A lost kernel `.config` was reconstructed and **kernel #3** was successfully boot-tested with WLAN/SSH, native sun4i DRM (`/dev/dri/card0`, `sun4i-drmdrmfb`), AXP209 GPIO/backlight and Goodix GT811 touch. Kernel #10 is retained as a fallback. **Open reliability issue:** AXP209 IRQ 54 storms to ~100,001 events and is disabled around 90 s after boot on both the original #10 and reconstructed kernels; impact on power events is not yet resolved.

## Hardware

| Component | Identified hardware |
| --- | --- |
| Tablet | Casper / INTREEO TAB-WB72 |
| SoC | Allwinner A13 (sun5i), ARM Cortex-A8 |
| RAM | 512 MiB DDR3 |
| Display | 800 × 480 RGB LCD; native Linux DRM/LCD console works |
| Touch panel | Goodix GT811 (`0x5d` on I²C-1), single-touch via userspace uinput (boot-tested) |
| Wi-Fi | Realtek USB device **0bda:8176**, 802.11n WLAN Adapter (RTL8188CUS family) |
| USB connector | One **Mini-USB** port, OTG-capable; separate host port not present |
| Internal storage | ~4 GB NAND containing original Android 4.0.4 |
| Removable storage | microSD, currently boot medium |

The exact board revision matters. See [hardware notes](docs/hardware.md).

## Achieved milestones

1. Backed up all ten NAND partitions and recovered the original Android FEX configuration.
2. Built **U-Boot 2025.01** for the `q8_a13_tablet` reference board.
3. Built a **Linux 6.12.0** ARM `zImage` and `sun5i-a13-q8-tablet.dtb`.
4. Built a statically linked **BusyBox 1.37.0** ARM initramfs.
5. Booted via FEL during initial testing, then installed U-Boot in unused space before the SD card's first FAT32 partition.
6. Confirmed that **resetting the tablet boots from microSD**: SPL → U-Boot → Linux → BusyBox `~ #` on the LCD.
7. Enabled AXP209 USB power-supply support (`CONFIG_AXP20X_POWER=y`) to fix USB PHY deferred probing; EHCI enumerates the internal `0bda:8176` adapter.
8. Enabled `CONFIG_RTL8XXXU_UNTESTED=y` to bind RTL8188CU (`0bda:8176`); loaded `rtlwifi/rtl8192cufw_TMSC.bin` successfully.
9. Confirmed WPA2 association, DHCP lease, and Dropbear SSH login as root via an authorized ED25519 public key.
10. Enabled AXP209 battery/ADC and power-key kernel support; confirmed charging/discharging readings and a working CSV power-monitor prototype.
11. Confirmed automatic local NTP synchronization and CSV battery monitoring after reboot.
12. Confirmed AXP209 `KEY_POWER` input, autostarted ARMHF power-button daemon and successful safe shutdown (monitor stop, sync, FAT32 unmount, poweroff), followed by reboot using the power button.
13. Fixed Dropbear inheriting the SD boot-log file descriptors, which had initially blocked FAT32 unmount.
14. Enabled `CONFIG_INPUT_UINPUT=y` in kernel #10; identified the original Goodix GT811 panel at I²C-1 address `0x5d` and extracted its 108-byte panel configuration from the original Android module, keeping proprietary artifacts local.
15. Implemented GT811 panel initialization and a userspace I²C-to-uinput single-touch bridge; verified `BTN_TOUCH`, `ABS_X` and `ABS_Y` on `/dev/input/event1` after a complete reboot, with automatic startup from the initramfs.
16. Reconstructed the Android GT811 end-of-report ACK (`80 00`), tested PG11 falling-edge interrupt handling, and boot-tested the automatic PB3 wakeup → 108-byte panel configuration → IRQ driver sequence.
17. Tested a standalone 800×480 32-bpp `/dev/fb0` touch crosshair (no X11/Wayland). Corrected X presentation horizontally and displayed Y with bottom-left origin. Edge readings: left X≈8, right X≈788, bottom Y≈4, top Y≈472. Changes are currently in the diagnostic UI, **not yet validated as a production driver fix**.

## Einrichtung und Bedienung

- **[Windows und WSL2 installieren und verwenden](docs/wsl-setup.md)** — Ubuntu, Cross-Compiler, Windows/WSL-Dateizugriff und FEL per USB.
- **[Casper starten und bedienen](docs/bedienung.md)** — SD-Boot, Bootdateien, aktuelle Eingabemöglichkeiten und Diagnose.
- **[Kernel, U-Boot und BusyBox bauen](docs/build-and-boot.md)** — dokumentierte Build- und Bootschritte.
- **[Kernel #3 rekonstruieren und testen (09.11.2026)](docs/kernel-reconstruction-2026-11-09.md)** — Kconfig-Korrekturen, sichere A/B-Bootauswahl, DRM-Ergebnis und AXP209 IRQ-54-Fehler.
- **[Kernel #5: physischer Home-Button und Bildschirmtastatur (10.11.2026)](docs/physical-home-key.md)** — LRADC-DTS, KEY_HOME, Python/EVIOCGRAB, Matchbox-Umschaltung und **nach Neustart bestätigter SysVinit-Autostart**.
- [Hardwaredetails](docs/hardware.md), [GT811 Touchscreen](docs/gt811-touchscreen.md), [AXP209-Akku, NTP und Power Monitor](docs/power-management.md) und [Entwicklungsfahrplan](docs/roadmap.md).

**Achtung:** Die SD-Bootloader-Installation kann bei Wahl des falschen Datenträgers Daten zerstören. Unsere Dokumentation enthält keine blind ausführbare Rohdatenträger-Flash-Anweisung.

## Working tree (development machine)

The actual sources and build artifacts are maintained in WSL Ubuntu under `~/casper-a13/`:

- `linux/` — upstream Linux source tree
- `busybox/` — upstream BusyBox source tree
- `build-casper/` — U-Boot build directory
- `initramfs/` and `initramfs.cpio.gz` — minimal console variant
- `initramfs-network/` and `initramfs-network.cpio.gz` — local network/Dropbear development variant (contains secrets; **do not publish**)
- `boot-linux.cmd` — U-Boot script source
- `casper_original.fex` — hardware dump from the original device (**local only; not distributed here**)
- `gt811/` — local GT811 driver sources, tools, original Android module and panel config (**do not publish the original module, config or extracted firmware**)

The upstream Linux, U-Boot and BusyBox source trees are **not vendored** into this documentation repository.

## Current priorities

- Preserve the working reconstructed #3 `rtl8192cu`/sun4i DRM kernel and initramfs locally; keep **kernel #10** as the proven boot fallback. The actual regenerated `casper_a13_defconfig` is still on the WSL build machine and must be reviewed before publication.
- Investigate the **existing AXP209 IRQ 54 interrupt storm** (also present in kernel #10); do not assume that a working power-supply sysfs interface proves reliable power-button or charger interrupts.
- WLAN baseline: 30 pings at original position, 0% loss, 2.388/5.811/12.322 ms min/avg/max; 300 pings, 0% loss, 2.148/9.315/502.740 ms (occasional jitter remains).
- Validate battery readings and USB input voltage under load.
- GT811 single-touch works after reboot in IRQ mode, and a minimal framebuffer crosshair follows the finger. Next: fix the X coordinate centrally in the driver without double inversion; investigate a `Bus error` seen in an experimental rebuilt IRQ driver; preserve known-good image; optionally package the standalone diagnostic framebuffer tool. The Debian Xorg/Matchbox UI and on-screen keyboard are installed and visible; complete independent use, key mapping and persistent calibration still require validation.

See [roadmap](docs/roadmap.md) and [operation guide](docs/bedienung.md).

## Safety and distribution

- **Keep original Android NAND untouched.** Existing NAND backups stay local.
- **Never publish** raw NAND images, device-specific firmware dumps, credentials, private SSH keys or Wi-Fi secrets.
- Inspect the destination disk carefully before any raw write. Windows `PhysicalDriveN` numbers and drive letters can change between sessions.
- This project is experimental, hardware-specific and provided without guarantees.

## Acknowledgments

Built on [U-Boot](https://www.denx.de/wiki/U-Boot/), [Linux](https://kernel.org/) and [BusyBox](https://busybox.net/), using the community Allwinner sunxi device-tree and board support.

## Debian 13 and touchscreen GUI (2026-10-29)

The current development SD card now boots **Debian GNU/Linux 13 (trixie, armhf)** from a separate ext4 root partition with SysVinit and OpenSSH. The boot FAT32 partition keeps U-Boot, kernel, DTB and a Debian-specific initramfs. The original Android NAND is unchanged. **Xorg with fbdev, Matchbox window manager, xterm and Matchbox Keyboard has been started successfully over SSH** on the 800×480 touchscreen. XInput recognizes the Casper Goodix GT811 pointer. A horizontal X flip is still required/tested at the XInput layer; persistent calibration, correct key typing and the left keyboard-margin/layout issue remain open. GUI autostart is not yet configured.

Early RTL8192CU firmware diagnostics were improved by running the logging script before moving proc/sys/dev at `switch_root`. A diagnostic boot completed and the previously observed Realtek firmware load errors were absent, but WLAN still sometimes disconnects and roams. Both the original and repacked Debian archive already contained the Realtek firmware; do not claim the copy operation fixed it. See **[Debian 13 and X11 setup, diagnostics and next steps](docs/debian13-x11.md)** for details and commands.

## Verified LCD and touch correction (2026-11-10)

**Confirmed after reboot:** The horizontal LCD scanout offset is fixed using a Casper-specific `panel-dpi` device-tree override (33 MHz, 800×480, 1055 horizontal / 525 vertical total). The Goodix GT811 XInput transformation is permanently set to `-1 0 1 0 1 0 0 0 1`; the full on-screen keyboard, touch coordinates and physical HOME keyboard-toggle work. The Linux 6.12 **kernel #5 remains unchanged**; only its DTB was replaced and the previous DTB preserved as an SD-card rollback. The original Android NAND remains untouched.

**[Validated device-tree change, Windows SD-card deployment, persistent touch settings, and rollback](docs/casper-lcd-touch-2026-11-10.md).** Older sections documenting uncorrected LCD margins or pending touch calibration describe historical intermediate stages.

## Touch tools, boot persistence and ESPsoup/OTG status (2026-11-10)

**Confirmed after reboot:** Xorg/Matchbox automatically opens the **Casper tools launcher**; touch UI starts **Casper WiFi v0.2** and **Casper Battery v0.2**. WiFi scanning, joining and persistence after reboot work with the existing `wpa_supplicant` configuration after setting `update_config=1`; Battery reads AXP209 charge, voltage, current and USB status. HOME still toggles the 5-row QWERTZ keyboard (including digits) through the separate SysVinit hook. Sources: [WiFi](scripts/casper-wifi.py), [Battery](scripts/casper-battery.py), [menu](scripts/casper-menu.py); setup/limitations: [Casper touch tools](docs/casper-tools-2026-11-10.md).

**Recovery:** The SD card's ext4 root filesystem developed corrupt inode checksums during an APT installation. A full 4,014,997,504-byte SD image was backed up; `e2fsck` repaired an **image copy**, and the fixed image was restored to SD. Debian boot and subsequent package repair succeeded. Details, backups, limitations: [SD/ext4 and dpkg recovery](docs/casper-sd-repair-2026-11-10.md). Do not assume the physical SD card is reliable until tested further.

**Next hardware work – ESPsoup:** The ESP32-C5 and a powered hub are still **not enumerated** on external Mini-USB. MUSB root hub exists but stays `b_idle`; ID detection GPIO PG2 remains HIGH with the Goobay 95006 adapter. The original Android FEX and Linux DTS agree on PG2/PG1/PG12. **Replacement OTG-ID-grounded adapter pending**; no kernel or DTB change indicated yet. See [OTG diagnostics](docs/casper-sd-repair-2026-11-10.md#espsoup--esp32-c5-über-externes-usb-otg-noch-offen).
