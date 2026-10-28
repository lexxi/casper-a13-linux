# Casper TAB-WB72 — Linux on Allwinner A13

Reviving a 2012-era Casper / INTREEO TAB-WB72 tablet with mainline Linux, U-Boot and BusyBox, booted **from microSD without modifying the original Android NAND**.

> **Status (2026-10-28):** Linux 6.12.0 kernel #10 boots from microSD without changing Android NAND. Native 800×480 DRM/LCD output, fast `rtl8192cu` WLAN, Dropbear SSH, AXP209 battery monitoring and safe power-button shutdown work. The original Goodix GT811 touch panel is now initialized automatically at boot and generates verified Linux evdev events via `/dev/uinput`.

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
15. Implemented GT811 panel initialization and a userspace I²C-to-uinput single-touch bridge; verified `BTN_TOUCH`, `ABS_X` and `ABS_Y` on `/dev/input/event1` after a complete reboot, with both processes automatically started from the initramfs.

## Einrichtung und Bedienung

- **[Windows und WSL2 installieren und verwenden](docs/wsl-setup.md)** — Ubuntu, Cross-Compiler, Windows/WSL-Dateizugriff und FEL per USB.
- **[Casper starten und bedienen](docs/bedienung.md)** — SD-Boot, Bootdateien, aktuelle Eingabemöglichkeiten und Diagnose.
- **[Kernel, U-Boot und BusyBox bauen](docs/build-and-boot.md)** — dokumentierte Build- und Bootschritte.
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

- Preserve the working `rtl8192cu` kernel and initramfs locally; keep the older `rtl8xxxu` kernel as fallback.
- WLAN baseline: 30 pings at original position, 0% loss, 2.388/5.811/12.322 ms min/avg/max; 300 pings, 0% loss, 2.148/9.315/502.740 ms (occasional jitter remains).
- Validate battery readings and USB input voltage under load.
- GT811 single-touch now works after reboot. Next: corner/orientation calibration, investigate sporadic coordinate outliers, and build a lightweight 800×480 DRM touch UI.

See [roadmap](docs/roadmap.md) and [operation guide](docs/bedienung.md).

## Safety and distribution

- **Keep original Android NAND untouched.** Existing NAND backups stay local.
- **Never publish** raw NAND images, device-specific firmware dumps, credentials, private SSH keys or Wi-Fi secrets.
- Inspect the destination disk carefully before any raw write. Windows `PhysicalDriveN` numbers and drive letters can change between sessions.
- This project is experimental, hardware-specific and provided without guarantees.

## Acknowledgments

Built on [U-Boot](https://www.denx.de/wiki/U-Boot/), [Linux](https://kernel.org/) and [BusyBox](https://busybox.net/), using the community Allwinner sunxi device-tree and board support.
