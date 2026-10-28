# Goodix GT811 Touchscreen — Casper TAB-WB72

**Verified on 2026-10-28:** Automatic GT811 startup and single-touch input work after a full microSD Linux reboot. This documents a working userspace bridge, **not** an upstream Linux kernel GT811 driver.

## Hardware and provenance

- Device: Casper / INTREEO TAB-WB72, Allwinner A13, LCD **800 × 480**.
- Controller: Goodix **GT811**, I²C bus **1**, address **0x5d**; chip ID register **0x0715** returned **0x11**.
- Original Android 4.0.4 boot ramdisk loads `/system/vendor/modules/gt811_ts_icon.ko`.
- Original FEX: `ctp_name=gt811_ts`, `ctp_twi_id=1`, `ctp_twi_addr=0x5d`, interrupt **PG11**, wake **PB03**, X/Y exchange and Y inversion configured.
- The original module's `goodix_init_panel` embeds a panel-specific configuration: **108 bytes total**, comprising 2-byte register prefix `06 A2` and 106 payload bytes. The runtime config includes display dimensions **800 × 480**.
- The module, NAND backups and derived panel-config binary remain **local only**. They are **not licensed for public redistribution** by this project.

## Verified software architecture

- Linux **6.12.0 kernel #10**, `CONFIG_INPUT_UINPUT=y`, evdev enabled.
- `/usr/sbin/gt811-init-test` opens `/dev/i2c-1`, confirms chip ID and sends panel configuration via one I²C write to `0x5d`.
- `/usr/sbin/gt811-uinput` polls GT811 touch status at register `0x0721` every **20 ms** and emits Linux `BTN_TOUCH`, `ABS_X`, `ABS_Y` and `SYN_REPORT` through `/dev/uinput`.
- Current single-touch coordinate conversion: `screen_x = 800 - raw_y`, `screen_y = raw_x`. Orientation is plausible but **not yet calibrated at all four corners**.
- `/gt811-start.sh` runs in the background from `/init`, after `devtmpfs` is mounted. It waits for `/dev/i2c-1` and `/dev/uinput`, initializes the panel and starts the uinput bridge. A touch failure must not prevent boot or SSH.
- `/tmp/gt811.log` is RAM-backed, avoiding open log descriptors on the removable FAT32 partition.

## Private initramfs paths

The tested image includes:

```text
/gt811-start.sh
/usr/sbin/gt811-init-test
/usr/sbin/gt811-uinput
/etc/gt811/config.bin
```

The local WSL working tree uses `~/casper-a13/initramfs-network/`. **Do not commit this directory or its archive:** it contains locally configured network and access material. Do not publish `gt811/original-android/` or the derived `config.bin`.

## Test on tablet

```sh
cat /tmp/gt811.log
cat /proc/bus/input/devices
evtest /dev/input/event1
```

Successful boot test log included:

```text
Configuration: 108 bytes, register 0x06A2
Chip ID: 0x11 [OK]
I2C write acknowledged.
[OK] GT811 initialized
[INFO] Starting GT811 uinput driver
Casper GT811 uinput driver started
Polling: 20 ms
Display: 800x480
```

`/proc/bus/input/devices` exposed **Casper Goodix GT811 Touchscreen** as `event1`. An `evtest` session after reboot demonstrated finger press/release, smooth horizontal movement with X approximately **63 → 710** and Y **352 → 369**, and touches across the display.

An isolated jump to **(800, 0)** during a different gesture suggests occasional invalid samples; investigate checksum/bounds before use in a UI. As of this milestone, no graphical touch interface is installed.

## Next steps

1. Back up exact known-good kernel #10, DTB and initramfs locally.
2. Verify orientation and X/Y scaling at each display corner; adjust conversion if required.
3. Handle invalid samples/checksum, add direct-touch input property and evaluate interrupt-triggered reading on PG11 instead of 20 ms polling.
4. Build a minimal **DRM/KMS** 800×480 graphical touch test without X11/Wayland.
