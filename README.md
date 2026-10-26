# Casper TAB-WB72 — Linux on Allwinner A13

Reviving a 2012-era Casper / INTREEO TAB-WB72 tablet with mainline Linux, U-Boot and BusyBox, booted **from microSD without modifying the original Android NAND**.

> **Status (2026-10-26):** SD boot to a visible BusyBox shell is **confirmed working**. USB keyboard input, Wi-Fi networking, SSH and touchscreen are **not yet confirmed**. The latest kernel rebuild is still in progress.

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

Read [build and boot notes](docs/build-and-boot.md) before attempting to reproduce this. The SD flashing operation is destructive if the wrong disk is selected.

## Working tree (development machine)

The actual sources and build artifacts are maintained in WSL Ubuntu under `~/casper-a13/`:

- `linux/` — upstream Linux source tree
- `busybox/` — upstream BusyBox source tree
- `build-casper/` — U-Boot build directory
- `initramfs/` and `initramfs.cpio.gz`
- `boot-linux.cmd` — U-Boot script source
- `casper_original.fex` — hardware dump from the original device (**local only; not distributed here**)

The upstream Linux, U-Boot and BusyBox source trees are **not vendored** into this documentation repository.

## Current priorities

- Get USB host / OTG keyboard input working.
- Enable the USB Realtek WLAN adapter (`0bda:8176`) under Linux 6.12, include required firmware, associate to Wi-Fi and acquire an IP address.
- Add an SSH service (e.g. Dropbear) with safe key-based authentication.
- Bring up the Goodix touchscreen and a small graphical interface.

See [roadmap](docs/roadmap.md).

## Safety and distribution

- **Keep original Android NAND untouched.** Existing NAND backups stay local.
- **Never publish** raw NAND images, device-specific firmware dumps, credentials, private SSH keys or Wi-Fi secrets.
- Inspect the destination disk carefully before any raw write. Windows `PhysicalDriveN` numbers and drive letters can change between sessions.
- This project is experimental, hardware-specific and provided without guarantees.

## Acknowledgments

Built on [U-Boot](https://www.denx.de/wiki/U-Boot/), [Linux](https://kernel.org/) and [BusyBox](https://busybox.net/), using the community Allwinner sunxi device-tree and board support.
