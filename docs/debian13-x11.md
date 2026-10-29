# Debian 13 (trixie) on Casper A13 — SD boot, X11 and troubleshooting

**Tested 2026-10-28/29** on Casper / INTREEO TAB-WB72 (Allwinner A13, 512 MiB RAM, 800×480 LCD), Linux 6.12.0 kernel #10. This is the currently booted **Debian** configuration, separate from the earlier BusyBox-only rescue environment. Original Android NAND remains untouched.

## Verified configuration

- SD: `/dev/mmcblk0p1` FAT32 `CASPER_BOOT`; `/dev/mmcblk0p2` ext4 `CASPER_ROOT` mounted as `/`.
- Boot: SPL/U-Boot → `zImage` + `sun5i-a13-q8-tablet.dtb` + `initramfs-debian.cpio.gz` → `/init` mounts ext4 and `switch_root /newroot /sbin/init` → Debian 13 with **SysVinit**, elogind, D-Bus and OpenSSH.
- Active `boot.scr` performs `fatload mmc 0:1 0x43000000 initramfs-debian.cpio.gz` and uses dynamically obtained `initrd_size`.
- `/boot` in Debian is initially empty; to inspect the actual FAT32 boot files, use `mkdir -p /mnt/casper-boot; mount -o ro /dev/mmcblk0p1 /mnt/casper-boot`. This mount does not persist across reboots.
- Baseline: `free -h` showed 447 MiB total / 411 MiB available; ext4 3.4 GiB total / initially 2.9 GiB free.
- Xorg (fbdev on `/dev/fb0`), `matchbox-window-manager`, `xterm` and `matchbox-keyboard` installed and tested; X recognizes `Casper Goodix GT811 Touchscreen` as a pointer device (observed XInput ID 7; IDs may change).
- Screen keyboard displays on 800×480. Touch X is horizontally reversed unless corrected; a visible blank strip before the left `q` key remains to be investigated. Functional typing and a persistent Xorg input configuration have **not** yet been confirmed.

## WLAN on Debian

Debian `ifupdown` configuration:

```ini
# /etc/network/interfaces.d/wlan0 (historical filename)
auto wlan0
iface wlan0 inet dhcp
    wpa-conf /etc/wpa_supplicant/casper.conf
```

The WLAN interface was later automatically renamed to `wlx000d724820c2`. Do not assume it is always named `wlan0`; inspect `ip -br addr` and the active configuration. One `wpa_supplicant` process was seen. Firmware uses `rtlwifi/rtl8192cufw_TMSC.bin`. A 30-ping gateway test returned 30/30, average 20.832 ms, max 130.356 ms. At one point signal was −66 dBm, TX PHY 150 Mbit/s, RX PHY 2 Mbit/s, power saving off. WLAN remains functional for SSH but experiences AP switching and `DISASSOC_LOW_ACK` (reason 34); sustained stability is **not** verified.

### Early firmware and diagnostic investigation

One boot reported `Direct firmware load for rtlwifi/rtl8192cufw_TMSC.bin failed with error -2` and `Firmware is not ready to run!`. Both the existing `initramfs-debian.cpio.gz` and a rebuilt working copy contained `rtl8192cufw_A.bin`, `rtl8192cufw_B.bin` and `rtl8192cufw_TMSC.bin`. These copies were byte-identical (SHA256 `5e0879fcf3ca4f9b9d10e26c674aa9b13fa93e5e14abc73a883744162c8db1e5`); **missing firmware inside that archive was not the explanation**. A subsequent diagnostic boot did not report the Realtek firmware load failure; the exact reason for the difference remains unproven. A separate `regulatory.db` warning remains.

A diagnostic initramfs (`initramfs-debian-diag.cpio.gz`, SHA256 `b6061620fb97b766d8018f695e9353ff027693c29b4aa12b4edc114958356b60`) adjusted `/init` to test firmware presence and call `/casper-wlan-diag.sh` **before** moving `/proc`, `/sys` and `/dev` into `/newroot`:

```sh
[ -s /lib/firmware/rtlwifi/rtl8192cufw_TMSC.bin ] \
    && echo "[OK] RTL8192CU firmware present" >/dev/console
/casper-wlan-diag.sh || echo "[WARN] WLAN diagnostic failed" >/dev/console
mount --move /proc /newroot/proc
mount --move /sys /newroot/sys
mount --move /dev /newroot/dev
exec /sbin/switch_root /newroot /sbin/init
```

The earlier logging order was incorrect: after those moves, `/dev/mmcblk0p1` and `/sys/class/net` were not accessible via their old paths. The diagnostic boot successfully produced `casper-debian-wlan-diag.log` on the FAT32 partition. At ~3 s it showed `lo`, `sit0` and the USB device but no WLAN netdevice yet; this is early initialization, **not proof of a wireless failure**. Its date was Jan 1, 1970 because time was not synchronized at that stage. The diagnostic initramfs subsequently booted Debian with working SSH.

**Boot safety:** keep original `initramfs-debian.cpio.gz` backups, kernel and boot scripts. Testing a new boot image via SSH alone risks losing access if boot fails. Do not write Android NAND. Keep the original Android panel configuration and firmware blobs private; do not commit device images, secrets or private keys.

## X11 and touchscreen from SSH

Installed minimal packages (without full desktop environment):

```sh
apt install --no-install-recommends xserver-xorg-core xserver-xorg-video-fbdev \
  xserver-xorg-input-libinput xserver-xorg-legacy xinit xterm \
  matchbox-window-manager x11-xserver-utils xinput xauth xfonts-base \
  matchbox-keyboard
```

A local `/etc/X11/xorg.conf.d/20-casper-fbdev.conf` selects the `fbdev` driver using `/dev/fb0` (800×480); `/root/.xinitrc` starts Matchbox and xterm. Working remote start without USB keyboard:

```sh
nohup xinit /root/.xinitrc -- /usr/bin/Xorg :0 vt1 \
  -keeptty -nolisten tcp > /root/xorg-start.log 2>&1 < /dev/null &
sleep 5
DISPLAY=:0 XAUTHORITY=/root/.Xauthority xinput list
DISPLAY=:0 XAUTHORITY=/root/.Xauthority matchbox-keyboard \
  > /tmp/matchbox-keyboard.log 2>&1 &
```

XInput listed `Casper Goodix GT811 Touchscreen` as pointer. To test **horizontal X inversion** in X11 without replacing the known-good GT811 uinput driver:

```sh
DISPLAY=:0 XAUTHORITY=/root/.Xauthority xinput set-prop 7 \
  'Coordinate Transformation Matrix' -1 0 1 0 1 0 0 0 1
```

Restore identity: `xinput set-prop 7 'Coordinate Transformation Matrix' 1 0 0 0 1 0 0 0 1`. Query current XInput device ID on every restart. A persistent candidate is an Xorg `InputClass` with `MatchProduct "Casper Goodix GT811 Touchscreen"` and `Option "TransformationMatrix" "-1 0 1 0 1 0 0 0 1"`, **only after orientation is verified on the running tablet**. Avoid double inversion in driver, framebuffer diagnostic and Xorg.

## Next work

1. Verify correctly mapped physical touches on left/right Matchbox keyboard keys and actual characters in xterm.
2. Investigate visible left margin before `q` via Matchbox layout and window geometry (`xwininfo -root -tree`); do not confuse layout padding with input-coordinate inversion.
3. Test German keyboard layout and a lightweight launcher; only then configure X autostart (currently manual through SSH).
4. Resolve remaining WLAN roaming/`DISASSOC_LOW_ACK`, review proper regulatory database, and ensure service configuration survives interface renaming.
5. Retain known-good boot backups and recheck the early firmware sequence if failures recur.
