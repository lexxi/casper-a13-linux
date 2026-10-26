# Build and boot notes

This describes **what has been confirmed on the tested device**. It is not a ready-made universally safe flashing script.

## Host environment

- Windows host with **WSL2 Ubuntu** (development files under `/home/casper/casper-a13`)
- Cross compiler: `arm-linux-gnueabihf-` (GCC 15.2.0 in the tested setup)
- Linux **6.12.0**
- U-Boot **2025.01** using `q8_a13_tablet_defconfig` as the reference
- BusyBox **1.37.0**, statically linked for ARM

## U-Boot

A working U-Boot artifact was created in the local `~/casper-a13/build-casper/` directory:

```text
u-boot-sunxi-with-spl.bin
```

In the test setup, it was written to the SD medium **at byte offset 8192**, leaving the MBR and a FAT32 partition beginning at **4 MiB** intact. The SD card was first backed up; the write was performed only after identifying and locking the correct Windows volume. Do not use a hard-coded `PhysicalDrive` number or blindly reproduce raw writes.

The verified SPL header started with `eGON.BT0`. The U-Boot reference configuration used DDR at 384 MHz, DRAM_ZQ=123, EMR1=4, and ODT disabled. SPL reported 512 MiB DRAM, and U-Boot detected the microSD.

## Kernel and device tree

Output artifacts from the confirmed working Linux kernel build:

```text
linux/arch/arm/boot/zImage
linux/arch/arm/boot/dts/allwinner/sun5i-a13-q8-tablet.dtb
```

Important built-in (`=y`) options included:

```text
CONFIG_ARCH_SUNXI=y
CONFIG_DEVTMPFS=y
CONFIG_INPUT_EVDEV=y
CONFIG_SERIAL_8250=y
CONFIG_SERIAL_8250_CONSOLE=y
CONFIG_DRM_SUN4I=y
CONFIG_FB_SIMPLE=y
CONFIG_MMC=y
CONFIG_MMC_SUNXI=y
CONFIG_EXT4_FS=y
CONFIG_FAT_FS=y
CONFIG_VFAT_FS=y
CONFIG_TMPFS=y
CONFIG_BLK_DEV_INITRD=y
CONFIG_RD_GZIP=y
CONFIG_INPUT_KEYBOARD=y
CONFIG_HID_GENERIC=y
CONFIG_USB_HID=y
CONFIG_USB_EHCI_HCD=y
CONFIG_USB_OHCI_HCD=y
```

A subsequent configuration, **not yet boot-tested**, has:

```text
CONFIG_USB_OTG=y
CONFIG_USB_MUSB_HDRC=y
CONFIG_USB_MUSB_DUAL_ROLE=y
CONFIG_USB_MUSB_SUNXI=y
CONFIG_USB_PHY=y
CONFIG_USB_ROLE_SWITCH=y
```

To rebuild **after any currently running build has finished**:

```bash
cd ~/casper-a13/linux
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j2 zImage dtbs
```

The exact `sun5i-a13-q8-tablet.dts` USB host/OTG nodes and `dr_mode` still need review. Built-in drivers alone do not prove a working keyboard connection.

## BusyBox / initramfs

BusyBox was compiled for ARM with static linking and installed to `~/casper-a13/initramfs`; archive at `~/casper-a13/initramfs.cpio.gz`. Two BusyBox 1.37.0 build adjustments were needed with the GCC 15.2/Linux-header setup:

- Disable `CONFIG_SHA1_HWACCEL` and `CONFIG_SHA256_HWACCEL` when x86-specific SHA intrinsics failed on ARM.
- Disable `CONFIG_TC` / `CONFIG_FEATURE_TC_INGRESS` due to removed CBQ header dependencies.

The initramfs `/init` mounts `proc`, `sysfs` and `devtmpfs`, then starts a shell with:

```sh
exec setsid cttyhack /bin/sh </dev/console >/dev/console 2>&1
```

Required console nodes were created when assembling the initramfs: `/dev/console` (character 5:1) and `/dev/null` (character 1:3).

**Working outcome:** Linux messages and a BusyBox shell prompt (`~ #`) are visible on the tablet LCD.

## microSD FAT32 boot files

The card contains:

```text
zImage
sun5i-a13-q8-tablet.dtb
initramfs.cpio.gz
boot.scr
```

The `boot.scr` was generated with U-Boot `mkimage` from `boot-linux.cmd`:

```bash
~/casper-a13/build-casper/tools/mkimage \
  -A arm -O linux -T script -C none \
  -n 'Casper A13 Linux Boot' \
  -d ~/casper-a13/boot-linux.cmd \
  ~/casper-a13/boot.scr
```

The successful boot sequence loads the kernel, initramfs and device tree from FAT32 on `mmc 0:1`, remembering the initramfs length **before** loading the DTB:

```text
mmc dev 0
fatload mmc 0:1 0x42000000 zImage
fatload mmc 0:1 0x43000000 initramfs.cpio.gz
setenv initrd_size ${filesize}
fatload mmc 0:1 0x44000000 sun5i-a13-q8-tablet.dtb
setenv bootargs 'console=ttyS1,115200 console=tty0 loglevel=8 ignore_loglevel rdinit=/init'
bootz 0x42000000 0x43000000:${initrd_size} 0x44000000
```

This is the documented boot-command sequence; the exact `boot-linux.cmd` source remains on the local build machine. Note that U-Boot overwrites `filesize` after each `fatload`, so `initrd_size` must be saved immediately after the initramfs load.

## Guardrails

1. Preserve NAND; never use `nand write`, `flash` or eMMC/NAND installation commands without an independently verified recovery path.
2. Back up the SD card and verify disk identity before touching raw sectors.
3. Do not commit binaries, original FEX firmware dumps, NAND images, SSH host/private keys or WLAN credentials.
4. Validate the USB OTG device-tree setup and Wi-Fi firmware selection before describing them as working.
