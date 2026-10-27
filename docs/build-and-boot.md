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

The **successfully boot-tested network kernel** additionally has:

```text
CONFIG_USB_OTG=y
CONFIG_USB_MUSB_HDRC=y
CONFIG_USB_MUSB_DUAL_ROLE=y
CONFIG_USB_MUSB_SUNXI=y
CONFIG_USB_PHY=y
CONFIG_USB_ROLE_SWITCH=y
CONFIG_PHY_SUN4I_USB=y
CONFIG_POWER_SUPPLY=y
CONFIG_MFD_AXP20X=y
CONFIG_REGULATOR_AXP20X=y
CONFIG_AXP20X_POWER=y
CONFIG_CFG80211=y
CONFIG_MAC80211=y
CONFIG_RTL8XXXU=y
CONFIG_RTL8XXXU_UNTESTED=y
CONFIG_IIO=y
CONFIG_AXP20X_ADC=y
CONFIG_BATTERY_AXP20X=y
CONFIG_INPUT_AXP20X_PEK=y
```

To rebuild **after any currently running build has finished**:

```bash
cd ~/casper-a13/linux
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j2 zImage dtbs
```

The compiled device tree has `usb_otg`, `usbphy` and EHCI enabled; OHCI is disabled. The USB PHY initially remained in deferred probe because the device tree's `usb0_vbus_power-supply` provider was not available: `CONFIG_AXP20X_POWER=m` had no loadable-module infrastructure in the initramfs. Switching to **`CONFIG_AXP20X_POWER=y`** brought up MUSB and EHCI, which enumerated USB `0bda:8176` at `2-1`. `rtl8xxxu` did not bind until **`CONFIG_RTL8XXXU_UNTESTED=y`**, as the `0x8176` ID is conditional in `drivers/net/wireless/realtek/rtl8xxxu/core.c`. External keyboard remains untested.

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

## Network-enabled initramfs (tested)

`~/casper-a13/initramfs-network/` extends the original BusyBox initramfs with ARMHF userspace libraries, `wpa_supplicant`, DHCP via BusyBox `udhcpc`, Dropbear and SSH public-key authentication. The script mounts the FAT32 microSD partition and writes diagnostics to **`/mnt/sd/casper-boot.log`**; it reads local **`/mnt/sd/wlan.conf`**. The tested card uses the generated `initramfs-network.cpio.gz` under the boot filename `initramfs.cpio.gz`. Firmware includes `rtlwifi/rtl8192cufw_TMSC.bin` (along with other CU firmware variants).

Important SSH permissions: root's home directory and `/root/.ssh` must be owned by **UID 0/GID 0** and set to `0700`; `/root/.ssh/authorized_keys` owned by root and set to `0600`. The first SSH attempt failed with `Permission denied (publickey)` even though the public keys matched, because `/root` in the initramfs had been archived with non-root ownership. After correcting ownership and repacking, key-based root login succeeded.

The ARMHF dependency packages are maintained with an isolated APT configuration in `armhf-packages/`. The `sources.list` needs **separate entries** for `resolute`, `resolute-updates` and `resolute-security`. `iw` and its ARMHF `libnl-3`/`libnl-genl-3` dependencies were transferred via SSH for live diagnostics. Avoid publishing SSH private keys, Wi-Fi passwords, host keys or raw captures from the live SD card.

## Battery and background services

AXP209 battery and USB power supplies are available on the verified device under `/sys/class/power_supply/axp20x-battery` and `/sys/class/power_supply/axp20x-usb`. The reference device tree enables `&battery_power_supply` already. `CONFIG_INPUT_AXP20X_PEK=y` is included, but **button events and safe poweroff have not been tested**. Details and captured readings: [power management](power-management.md).

The local network-initramfs source now includes an experimental `casper-power-monitor.sh` and `power-services.sh`, and `network-start.sh` invokes the latter after Dropbear. The monitor writes `/mnt/sd/casper-power.csv` every 300 seconds; the services script attempts a bounded BusyBox NTP update first. A **manual launch** was confirmed to synchronize the clock and append one CSV record. The last boot showed both scripts present as mode `0644`, so automatic execution **failed**. Set both to `0755` in the source tree, repack, then reboot and test. Do not claim persistent startup is working until that check succeeds.

## microSD FAT32 boot files

The card contains:

```text
zImage
sun5i-a13-q8-tablet.dtb
initramfs.cpio.gz
boot.scr
wlan.conf               # local only, never commit
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
4. Wi-Fi and the internal USB host path are tested; external USB keyboard and touchscreen are not.
5. Wi-Fi link is functional but performance is not yet satisfactory. Do not mistake PHY link bitrate for achievable throughput.

## Updated reference build — rtl8192cu and shutdown (2026-10-27)

The earlier `rtl8xxxu` settings and unverified-power status documented above describe the **initial** build only. The tested, preferred Linux 6.12 kernel now has:

```text
CONFIG_RTL_CARDS=y
CONFIG_RTL8192CU=y
CONFIG_RTLWIFI=y
CONFIG_RTLWIFI_USB=y
CONFIG_RTL8192C_COMMON=y
# CONFIG_RTL8XXXU is not set
```

The RTL8188CU rev A loads `rtlwifi/rtl8192cufw_TMSC.bin`. On `rtl8xxxu`, a near-AP 19-ping comparison averaged 472.282 ms (max 1707.050 ms); with `rtl8192cu` at the original position, 30 pings averaged 5.811 ms (max 12.322 ms) and 300 pings averaged 9.315 ms (max 502.740 ms), all with zero loss. PHY bitrate is not throughput. Keep the previous kernel as a fallback.

The current network initramfs includes ARMHF `/usr/sbin/iw`, `/usr/bin/evtest`, their libraries, and a locally compiled `/usr/sbin/casper-power-button` daemon. `/init` launches it in the background. The daemon observes `KEY_POWER` release on `/dev/input/event0` and runs `/casper-shutdown.sh` for clean monitor termination, SD sync/unmount and kernel poweroff. Successful shutdown and button-based boot were tested.

To prevent `umount /mnt/sd` from returning `EBUSY`, Dropbear must not inherit `/mnt/sd/casper-boot.log` descriptors from the parent script. The tested invocation adds `</dev/null >/dev/null 2>&1` to the Dropbear command. Local NTP now targets `192.168.98.32`.

The built initramfs includes local credentials and must not be committed to the public repository.
