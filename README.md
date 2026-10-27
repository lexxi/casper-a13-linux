# Casper TAB-WB72 — Linux on Allwinner A13

Reviving a 2012-era Casper / INTREEO TAB-WB72 tablet with mainline Linux, U-Boot and BusyBox, booted **from microSD without modifying the original Android NAND**.

> **Status (2026-10-27):** U-Boot 2025.01 → Linux 6.12.0 → BusyBox boots autonomously from microSD. **Internal Realtek Wi-Fi, WPA2, DHCP and SSH with public-key authentication are confirmed working.** AXP209 battery/USB measurements and one-shot NTP plus CSV power monitoring are also tested. WLAN latency/performance, autonomous monitoring after reboot, touchscreen and external USB keyboard remain pending.

## Hardware

| Component | Identified hardware |
| --- | --- |
| Tablet | Casper / INTREEO TAB-WB72 |
| SoC | Allwinner A13 (sun5i), ARM Cortex-A8 |
| RAM | 512 MiB DDR3 |
| Display | 800 × 480 RGB LCD; Linux framebuffer/console output works |
| Touch panel | Goodix GT811 (integration pending) |
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
11. Verified BusyBox NTP synchronization and logging after manual launch; persistent autostart still needs a reboot test.

## Einrichtung und Bedienung

- **[Windows und WSL2 installieren und verwenden](docs/wsl-setup.md)** — Ubuntu, Cross-Compiler, Windows/WSL-Dateizugriff und FEL per USB.
- **[Casper starten und bedienen](docs/bedienung.md)** — SD-Boot, Bootdateien, aktuelle Eingabemöglichkeiten und Diagnose.
- **[Kernel, U-Boot und BusyBox bauen](docs/build-and-boot.md)** — dokumentierte Build- und Bootschritte.
- [Hardwaredetails](docs/hardware.md), [AXP209-Akku, NTP und Power Monitor](docs/power-management.md) und [Entwicklungsfahrplan](docs/roadmap.md).

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

The upstream Linux, U-Boot and BusyBox source trees are **not vendored** into this documentation repository.

## Current priorities

- Verify the executable bits and **reboot-time autostart** of NTP and the power monitor; avoid duplicate log writers.
- Validate battery measurements, USB cable voltage drop and safe shutdown / AXP209 power-button handling.

- Diagnose poor Wi-Fi reception and severe ping jitter (measured approximately **−79 dBm**, RX link rate **13 Mbit/s**, at about 5 m with one wall); compare close to access point and tablet orientation.
- Compare `rtl8xxxu` to alternative `rtl8192cu` only if reception tests do not explain the issue.
- Package `iw` and dependencies in the persistent image; verify regulatory database and further networking refinements.
- Test Mini-USB OTG keyboard and Goodix GT811 touchscreen; explore a lightweight interface.

See [roadmap](docs/roadmap.md) and [operation guide](docs/bedienung.md).

## Safety and distribution

- **Keep original Android NAND untouched.** Existing NAND backups stay local.
- **Never publish** raw NAND images, device-specific firmware dumps, credentials, private SSH keys or Wi-Fi secrets.
- Inspect the destination disk carefully before any raw write. Windows `PhysicalDriveN` numbers and drive letters can change between sessions.
- This project is experimental, hardware-specific and provided without guarantees.

## Acknowledgments

Built on [U-Boot](https://www.denx.de/wiki/U-Boot/), [Linux](https://kernel.org/) and [BusyBox](https://busybox.net/), using the community Allwinner sunxi device-tree and board support.
