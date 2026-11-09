# Kernel 6.12 reconstruction and A/B boot tests (2026-11-09)

## Scope and evidence

Test hardware: Casper / INTREEO TAB-WB72, Allwinner A13 (sun5i), Debian 13 trixie armhf on microSD. Original Android NAND was not modified. All tests use the existing U-Boot 2025.01, the **same known-good** `sun5i-a13-q8-tablet.dtb` on the SD boot partition and `initramfs-debian.cpio.gz`; only the loaded kernel varies.

The originally built Linux 6.12.0 kernel #10 `.config` could not be found under `~/casper-a13/linux/`, in other local backups searched, under `/proc/config.gz`, under `/boot/config*`, or embedded in the backup `zImage` (checked with `scripts/extract-ikconfig`). The kernel was reconstructed from `multi_v7_defconfig` and project notes. **It is not a byte-identical reconstruction of #10.**

| Kernel | Date / test | Findings |
| --- | --- | --- |
| #10, 2026-10-28 | Known-good fallback | Debian/SSH, RTL8192CU, GT811, native sun4i DRM and backlight working; AXP209 IRQ 54 storm persists |
| #1, 2026-11-09 13:05 CET | First reconstructed build | Debian/SSH, WLAN, touchscreen input and visible framebuffer/keyboard; `/dev/fb0` was `simple`, no `/dev/dri/card0`, no backlight class |
| #2, 2026-11-09 14:28 CET | `PINCTRL_AXP209=y` | AXP209 GPIO driver and backlight class present, but black screen; `simple` fb, no DRM device; backend unbound |
| #3, 2026-11-09 14:39 CET | `DRM_SUN4I_BACKEND=y` | Debian, SSH/WLAN, touch, `sun4i-drmdrmfb`, `/dev/dri/card0`, backlight (`brightness=8`, `bl_power=0`) confirmed; known IRQ 54 storm remains |

Kernel #3 is the **currently verified development build**, not a fully stable production replacement. Console and onscreen keyboard were visible and touch worked during the #3 test. Physical key mapping/typing and long-term Wi-Fi stability are not yet fully validated.

## Critical Kconfig findings

Start from the ARM `multi_v7_defconfig` in the **same Linux 6.12.0 source tree**, then enable the hardware-specific builtin options from [build-and-boot](build-and-boot.md), notably:

```text
CONFIG_ARCH_SUNXI=y
CONFIG_MMC_SUNXI=y
CONFIG_EXT4_FS=y
CONFIG_DRM_SUN4I=y
CONFIG_DRM_SUN4I_BACKEND=y
CONFIG_DRM_PANEL_SIMPLE=y
CONFIG_DRM_FBDEV_EMULATION=y
CONFIG_BACKLIGHT_PWM=y
CONFIG_PWM_SUN4I=y
CONFIG_MFD_AXP20X=y
CONFIG_REGULATOR_AXP20X=y
CONFIG_AXP20X_POWER=y
CONFIG_PINCTRL_AXP209=y
CONFIG_BATTERY_AXP20X=y
CONFIG_INPUT_AXP20X_PEK=y
CONFIG_INPUT_UINPUT=y
CONFIG_RTL8192CU=y
# CONFIG_RTL8XXXU is not set
```

Two missing builtin selections were decisive:

- `CONFIG_PINCTRL_AXP209` was absent in #1, causing `pwm-backlight: failed to acquire enable GPIO` and panel deferred probe.
- `CONFIG_DRM_SUN4I_BACKEND=m` remained in #2. With no installed module, `1e60000.display-backend` had **no driver bound**, so native DRM could not initialize. Setting `=y` enabled backend and TCON binding in #3.

`CONFIG_DRM_SUN4I_HDMI=m` and many other `DRM_*` modules do not prevent the A13 internal LCD from working.

### Rebuild and preserve configuration locally

```sh
cd ~/casper-a13/linux
scripts/config --enable PINCTRL_AXP209
scripts/config --enable DRM_SUN4I_BACKEND
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- olddefconfig
grep -E '^CONFIG_(PINCTRL_AXP209|DRM_SUN4I|DRM_SUN4I_BACKEND)=' .config
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j2 zImage dtbs
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- savedefconfig
cp defconfig ../casper_a13_defconfig
cp .config ../casper-a13-working.config
```

Keep `~/casper-a13/backups/kernel-3/` with the full configuration and tested `zImage`. The local `casper_a13_defconfig` generated after the #3 build **has not been uploaded** to this repository; copy and review its real contents before committing it under `configs/`. Do not invent the rest of the Kconfig from the short option list above.

## Known-good boot files and safe A/B selection

On the FAT32 boot partition (`/dev/mmcblk0p1`):

| Filename | Role |
| --- | --- |
| `zImage` | Untouched kernel #10; SHA256 `4cd28d63a6dd39d2aa3c29bef5b9a4195c82d53603ff70aac6f54e7b338efe0d` |
| `zImage-test` | Tested kernel #3 after transfer; do not assume its SHA is that of #1 or #2 |
| `boot-original.scr` | Loads `zImage`, original Debian initramfs and SD DTB |
| `boot-test.scr` | Loads `zImage-test`, same Debian initramfs and SD DTB |
| `boot.scr` | Actual boot script selected by U-Boot; currently test variant during #3 tests |

`boot.scr` for Debian loads the kernel at `0x42000000`, `initramfs-debian.cpio.gz` at `0x43000000`, remembers `initrd_size=${filesize}`, loads the DTB at `0x44000000`, then runs `bootz`. Do not overwrite `initrd_size` by loading the DTB first.

After reboot, **`/mnt/casper-boot` is not automatically mounted**. Mount first:

```sh
mkdir -p /mnt/casper-boot
mountpoint -q /mnt/casper-boot || mount -o ro /dev/mmcblk0p1 /mnt/casper-boot
sha256sum /mnt/casper-boot/boot.scr /mnt/casper-boot/boot-original.scr /mnt/casper-boot/boot-test.scr
```

Changing variants requires deliberate remount RW, copy the desired variant to `boot.scr`, `sync`, SHA256 verification and remount RO **before reboot**. Note that `dd bs=64 skip=1` may leave binary padding when displaying the U-Boot script; use `dumpimage -T script -p 0` for exact extraction, or `grep -a` only for inspection.

A second kernel and boot script on the SD **are not an automatic rollback**. If SSH or boot fails, shut down, remove microSD and restore `boot.scr` from `boot-original.scr` using a card reader. Never write the original NAND. Back up boot files and verify the SD device before raw writes.

During the #3 test:

```text
Linux casper 6.12.0 #3 SMP Mon Nov 9 14:39:58 CET 2026 armv7l
/sys/class/graphics/fb0/name = sun4i-drmdrmfb
/dev/dri/card0 exists
/sys/class/backlight/backlight/brightness = 8
/sys/class/backlight/backlight/bl_power = 0
```

## Open issue: AXP209 PMIC interrupt storm (also present on #10)

All tested #10/#1/#3 builds showed the **same pre-existing defect**: `/proc/interrupts` reached roughly 100,001 interrupts on `IRQ 54` (`sun4i_irq 0 Edge axp20x_irq_chip`) and around 90 seconds after boot:

```text
irq 54: nobody cared (try booting with the "irqpoll" option)
Disabling IRQ #54
```

Consequences for button events, charger changes and battery events **remain to be determined**; the existence of `/sys/class/power_supply/axp20x-battery` does not establish interrupt reliability. The AXP209 was detected on I²C-0 at address `0x34`, and the live vs built DTBs both had `pmic@34 { interrupts = <0x00>; ... }`. That match **does not establish correct interrupt polarity or clearing behavior**.

Observed before investigation:

- `/dev/i2c-0` and `/dev/i2c-1` exist.
- `/sys/kernel/debug/regmap/` not accessible; `debugfs` was not mounted.
- `/proc/irq/54/spurious` reported `count 0` and `unhandled 0` after IRQ shutdown, but kernel logs conclusively showed the storm.

Next: inspect the interrupt wiring/polarity, AXP209 IRQ status/mask/ACK logic and the original board FEX **read-only first**; examine safe diagnostics using `debugfs` or regmap. Do not blindly enable IRQ 54, write PMIC registers, or use `irqpoll` as a supposed fix.

## Other work

- Confirm Matchbox on-screen keyboard character entry and left/right touch mapping; persistent X11 calibration and autostart are not yet verified.
- Investigate the missing `regulatory.db` and occasional WLAN roaming/`DISASSOC_LOW_ACK`.
- Keep device-specific panel configuration, NAND dumps, Wi-Fi credentials and SSH private keys out of GitHub.
