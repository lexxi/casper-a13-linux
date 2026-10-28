# Goodix GT811 touchscreen — Casper TAB-WB72

**Status: 2026-10-28.** Confirmed cold-boot automatic GT811 initialization under Linux 6.12.0 (#10), evdev press/move/release, and a standalone framebuffer crosshair test. This is a **userspace I²C-to-uinput implementation**, not an upstream GT811 kernel driver.

## Hardware and private provenance

- Casper / INTREEO TAB-WB72, Allwinner A13, 800×480 LCD, 512 MiB RAM.
- Goodix GT811 at I²C-1 address `0x5d`, chip ID `0x11` (register `0x0715`).
- IRQ: PG11 (falling edge). Wakeup: PB3, driven LOW then returned to input with pull-up.
- Stock Android 4.0.4 used `/system/vendor/modules/gt811_ts_icon.ko`. Its `goodix_init_panel` embeds an original 108-byte I²C write (register prefix `06 A2` and 106 data bytes). Panel settings used locally specify X maximum 800, Y maximum 480.
- **Do not publish** the Android kernel module, extracted panel configuration, firmware, NAND dumps, Wi-Fi credentials, or private SSH keys. They remain on the development machine.

## Current proven boot path

The SD-card image `recovery/initramfs-gt811-ack.cpio.gz` was generated locally (14,856,966 compressed bytes) and copied to the boot partition as `initramfs.cpio.gz`. `boot.scr` uses dynamic `initrd_size` from FAT loading, with addresses `0x43000000` for initramfs and `0x44000000` for the DTB; no boot-script changes were needed.

`/init` launches `/gt811-start.sh` in the background. The startup script waits for the required devices and then:

1. Runs `/usr/sbin/gt811-wakeup` to toggle PB3.
2. Runs `/usr/sbin/gt811-init-test /etc/gt811/config.bin --apply`.
3. Runs `/usr/sbin/gt811-uinput --irq`, using PG11 falling-edge interrupts.

The original Android driver writes a final `80 00` ACK after touch reports; the ACK and no-ACK test variants both produced four press/release cycles in controlled trials. The ACK variant was chosen for the boot image to mirror the original protocol. Reports use a repeated-start I²C read of 34 bytes at `0x0721`.

Confirmed boot log:

```text
=== Casper GT811 startup ===
[INFO] GT811 wakeup
PB3: LOW
PB3: INPUT + PULL-UP
GT811 wakeup sequence completed
[INFO] Applying panel configuration
Configuration: 108 bytes, register 0x06A2
Y max: 480, X max: 800
Chip ID: 0x11 [OK]
I2C write acknowledged.
[OK] GT811 initialized
[INFO] Starting GT811 IRQ driver with ACK
Casper GT811 uinput driver started
Mode: PG11 falling-edge IRQ; Display: 800x480
```

The touchscreen appears as `Casper Goodix GT811 Touchscreen` on `/dev/input/event1` in tested boots. Binary `od` inspection confirmed Linux `BTN_TOUCH` (press and release), `ABS_X`, `ABS_Y`, and `SYN_REPORT`, including smooth continuous motion.

## Framebuffer touch demonstration and coordinate system

A standalone crosshair diagnostic was built on the WSL host at `framebuffer/casper-touch-test.c`, statically cross-compiled for ARMHF, transferred by SSH stdin (`scp` is not supported by the minimal Dropbear environment), and run from `/tmp`. It opens:

- `/dev/fb0`: 800×480, 32-bpp, 3200-byte line stride.
- `/dev/input/event1`: the GT811 evdev interface.

The test displays a grid, crosshair, touch state and live coordinates. No X11/Wayland is required. **The source and binary are currently local development artifacts, not committed to this public repository.**

The visually correct crosshair follows the finger after applying horizontal X inversion in the **diagnostic app** while leaving the known-good boot driver untouched. Its Y **display** is inverted to express a bottom-left logical origin; framebuffer pixel Y still increases downward. Desired logical range:

| Edge | Observed |
| --- | --- |
| Left | X ≈ 8 |
| Right | X ≈ 788 |
| Bottom | Y ≈ 4 |
| Top | Y ≈ 472 |

Desired origin: bottom-left `(0,0)`; X increases rightward, Y upward. The measured edge deviations are small, and no extra scaling has yet been justified. **Do not apply horizontal inversion in both the driver and the diagnostic app.**

## Experimental driver limitation

A separately rebuilt test variant `gt811-uinput-ack-fixed` changed the X conversion from `screen_x = SCREEN_W - raw_y` to `screen_x = raw_y`; Y remained `raw_x`. It initially registered a Linux input device but later exited with **`Bus error`** while running in IRQ mode. The kernel tail and redirect log did not identify the crash cause. The known-good `/usr/sbin/gt811-uinput --irq` was restored and the graphical UI's X transform was used for calibration.

**Do not replace the boot image with the experimental rebuilt driver until the crash is explained and retested.** A later production change should implement the intended logical coordinate convention centrally, followed by fresh cold-boot, evdev and graphics tests.

## Diagnostics

On the tablet:

```sh
cat /tmp/gt811.log
ps | grep '[g]t811'
cat /proc/bus/input/devices
ls -l /dev/input/event*
od -An -tx1 -w16 /dev/input/event1
```

On the WSL host, a verified way to send a locally compiled static ARM binary without SFTP is:

```sh
ssh -i ~/.ssh/casper_a13 root@<tablet-ip> \
  'cat > /tmp/casper-touch-test && chmod 755 /tmp/casper-touch-test' \
  < /tmp/casper-touch-test
```

The static framebuffer tool is started on the device as `/tmp/casper-touch-test` (or the local variant file name). Running test binaries from `/tmp` does not modify the persistent microSD initramfs or original Android NAND.

## Storage warning

One boot displayed `FAT-fs (mmcblk0p1): Volume was not properly unmounted`. A subsequent offline Windows `chkdsk E:` checked the FAT32 card and reported **no filesystem problems**; no `/f` repair was needed. Always shut the device down cleanly and safely eject the SD card.

## Next tasks

1. Preserve the current working SD boot image.
2. Investigate `Bus error` in the experimental driver and stabilize a single central X/Y conversion.
3. Retest automatic IRQ startup and the four screen edges after any driver change.
4. Optionally publish a reviewed, self-contained framebuffer touch diagnostic source without private artifacts.
