# Roadmap and evidence

Updated 2026-11-09 (kernel reconstruction milestone).

| Feature | Status | Evidence / next step |
| --- | --- | --- |
| Original Android NAND backup | **Done** | Ten NAND partitions copied locally |
| FEL access | **Done** | A13 `sunxi-fel version` detection |
| U-Boot SPL from SD | **Done** | Autonomous reset-to-boot confirmed |
| Linux 6.12 kernel and LCD console | **Done** | Kernel messages visible |
| BusyBox 1.37 static initramfs | **Done** | `~ #` shell prompt visible |
| Internal USB host and PHY | **Done** | AXP209 power supply built-in; EHCI enumerates internal USB adapter |
| USB keyboard | **Pending** | Mini-USB OTG host adapter required |
| USB WLAN `0bda:8176` | **Working** | RTL8188CU rev A; preferred built-in `RTL8192CU=y`, TMSC firmware; `RTL8XXXU` disabled |
| DHCP / WPA2 | **Working** | WPA2 association and DHCP address confirmed |
| SSH access | **Working** | Dropbear root login using matching ED25519 public key, proper `/root` ownership |
| AXP209 battery sysfs | **Working** | Battery and USB classes; charge/discharge measured, capacity not calibrated |
| AXP209 power key | **Working** | `KEY_POWER` events verified; ARMHF daemon autostarts and requests safe shutdown |
| NTP time sync | **Working at boot** | BusyBox against local `192.168.98.32` |
| Power monitor CSV | **Working at boot** | 300-second `/mnt/sd/casper-power.csv` monitor |
| Safe shutdown / persistent storage | **Working** | Monitor stops, FAT32 sync/unmount succeeds, poweroff and restart tested |
| Wi-Fi latency / reception | **Improved** | With `rtl8192cu`, 30 pings avg 5.811 ms/max 12.322 ms; 300 pings avg 9.315 ms/max 502.740 ms, 0% loss |
| Goodix GT811 touch | **Working at boot (IRQ)** | PB3 wakeup, original 108-byte I²C config, PG11 falling-edge IRQ userspace bridge with post-read ACK; evdev confirms press/move/release after cold boot |
| Graphical touch diagnostic | **Working locally** | 800×480, 32-bpp `/dev/fb0` grid/crosshair, input from `event1`; X correction in test app; bottom-left coordinate display (X≈8–788, Y≈4–472 at edges). Local source not yet published |
| Permanent coordinate conversion | **Pending** | Fix centrally in driver; rebuilt experimental IRQ variant crashed with `Bus error`, so boot image remains known-good |
| Complete graphical application/UI | **Pending** | Diagnostic crosshair is not a full app shell or desktop environment |
| Second tablet | **Repair separate** | Deep-discharged battery; no Linux boot yet |

## Why Wi-Fi before keyboard?

The Casper has only one Mini-USB port. A Micro-USB OTG adapter is available, but not a Mini-USB OTG host cable. WLAN + SSH could provide a shell without extra input hardware, **if** the USB Wi-Fi chip, firmware and Linux USB host path work.

## Confirmed 2026-10-27 findings

Using `rtl8xxxu`, 19 pings near the AP averaged 472.282 ms with maximum 1707.050 ms. Switching to built-in `rtl8192cu` reduced latency drastically (30-ping sample at original location: 2.388/5.811/12.322 ms min/avg/max, no loss). Longer 300-ping test showed rare jitter spikes (maximum 502.740 ms) but no packet loss.

Power key `axp20x-pek` exposes `/dev/input/event0`, `KEY_POWER` code 116. An ARMHF power-button program is started by `/init` and runs `/casper-shutdown.sh` upon key release. This stops the CSV monitor, syncs and unmounts FAT32, then requests `poweroff -f`. It shut down successfully; display and ping ceased, and the tablet booted again using its button.

Initial unmount `EBUSY` was caused by Dropbear inheriting `casper-boot.log` descriptors. Redirecting its standard streams to `/dev/null` resolved the problem.

On 2026-10-28, kernel #10 enabled `CONFIG_INPUT_UINPUT=y`. The original Android `gt811_ts_icon.ko` supplied a panel initialization payload (106 config bytes plus the two-byte register address `0x06A2`, kept private). The revised `/gt811-start.sh` executes PB3 wakeup and panel init, then starts `gt811-uinput --irq` on PG11 with the Android-style `80 00` report ACK. Cold-boot and evdev finger events were confirmed. A standalone `/dev/fb0` grid/crosshair app was built and tested; with X corrected in the app and displayed Y inverted, finger tracking and observed edge coordinates were good (left/right X 8/788, bottom/top Y 4/472). A separately rebuilt X-fixed IRQ driver later reported `Bus error`; root cause still unknown. A historical isolated coordinate outlier to (800,0) remains worth monitoring.

Remaining: battery/USB voltage validation, shutdown failure recovery, regulatory database, investigation of experimental GT811 `Bus error`, stable driver-side orientation fix, and full graphical UI. Original Android NAND remains untouched.

## Confirmed 2026-10-29 Debian/X11 milestone

The Casper now boots Debian GNU/Linux 13 trixie (armhf) from microSD: FAT32 `mmcblk0p1` for U-Boot/kernel/DTB/initramfs and ext4 `mmcblk0p2` for SysVinit/OpenSSH Debian. Kernel 6.12 #10 and sun4i DRM framebuffer still work. At one measured point, 411 MiB RAM was available and 2.9 GiB ext4 free. Installed minimal Xorg fbdev, Matchbox, xterm, and Matchbox Keyboard; tested Xorg startup via SSH and confirmed the Goodix GT811 appears in `xinput list` as a pointer. Keyboard is visibly drawn. **Still pending:** verify key entry/touch axis orientation, address a left margin before `q`, configure lasting XInput transformation and autostart.

WLAN: Debian `ifupdown` and `wpa_supplicant` work but device may be renamed from `wlan0` to `wlx000d724820c2`; repeated AP association and `DISASSOC_LOW_ACK` remain. Initial early RTL8192CU firmware errors disappeared on a subsequent diagnostic boot; archive comparison showed all three Realtek firmware blobs already present, so the root cause remains uncertain. Adjusted the initramfs diagnostic order to log before moving `/proc`, `/sys`, `/dev`; the early diagnostic log is now created. See [Debian 13 and X11](debian13-x11.md).

## Confirmed 2026-11-09: reproducible Linux 6.12 kernel reconstruction

The original #10 kernel `.config` could not be retrieved from WSL files, `/proc/config.gz`, `/boot/config*` or `extract-ikconfig`. A new ARM `multi_v7_defconfig`-based configuration was built in stages:

- **#1:** Debian 13, WLAN, SSH and GT811 registered; only `simplefb`, no DRM or backlight.
- **#2:** `CONFIG_PINCTRL_AXP209=y` enabled AXP209 GPIO and backlight registration; LCD stayed black because the sun4i display backend was unbound.
- **#3:** `CONFIG_DRM_SUN4I_BACKEND=y` enabled native sun4i DRM, `/dev/dri/card0`, `sun4i-drmdrmfb`, visible display/keyboard and working touch. Kernel #10 retained as SD fallback.

**Open defect:** AXP209 IRQ 54 rises to about 100,001 interrupts and is disabled with `irq 54: nobody cared` at ~90 s; this was reproduced on the original kernel #10 too. It must not be described as a regression introduced by #3. Read-only PMIC IRQ investigations are next; assess power-key and charger event reliability before relying on them.

The local full `.config` and compact `casper_a13_defconfig` are not yet committed; **do not confuse the documented key options with a complete reproducible config**. See [2026-11-09 kernel reconstruction and A/B procedure](kernel-reconstruction-2026-11-09.md).

## 2026-11-10: kernel #5 physical HOME input and keyboard toggle

| Feature | Status | Evidence / next step |
| --- | --- | --- |
| Physical second HOME button via sun4i LRADC | **Verified** | Kernel #5; `CONFIG_KEYBOARD_SUN4I_LRADC=y`; `evtest /dev/input/event1` showed two KEY_HOME 102 press/release cycles |
| Matchbox Keyboard hardware-toggle | **Verified interactively** | Python evdev reader toggles keyboard; `EVIOCGRAB` removes stray `^[[H` in xterm |
| SysVinit keyboard-toggle boot startup | **Verified after reboot** | `/etc/rc2.d/S03rc.local` runs `run-parts /etc/boot.d`; user confirmed automatic launch and working button-toggle after reboot on 2026-11-10 |

See [full kernel #5 LRADC/keyboard instructions](physical-home-key.md). Earlier pending graphics and kernel notes above describe historical stages; do not assume their input `eventN` numbers are current.

## Verified 2026-11-10: touchscreen toolbox, SD recovery and external USB

| Item | Status | Evidence |
| --- | --- | --- |
| Casper WiFi v0.2 and saved network switching | **Verified after reboot** | `wpa_supplicant` `update_config=1`; SSID switching via touch and old SSID displayed as stored |
| Casper Battery v0.2 | **Verified** | AXP209 CLI dump and Tkinter GUI, charging/discharging and USB voltage/current |
| Casper touch-menu boot integration | **Verified after reboot** | `/root/.xinitrc` launches `casper-menu.py`; apps return to menu |
| Matchbox QWERTZ number row | **Verified** | Extra `1234567890@!` row; small touch targets, usability polish open |
| SD ext4 root and dpkg recovery | **Repaired and booted** | fsck on image copy, verified clean; original image retained, physical SD reliability not yet established |
| ESPsoup / ESP32-C5 external USB | **Blocked by OTG detection** | MUSB `b_idle`; PG2 / `usb0_id_det` HIGH with Goobay 95006; alternate proper Mini-USB OTG host adapter pending |

Sources: [tool setup and autostart](casper-tools-2026-11-10.md), [SD repair and USB OTG investigation](casper-sd-repair-2026-11-10.md). Existing AXP209 IRQ-54 behavior and previously recorded SD corruption should not be conflated; both need independent validation.

## Verified 2026-11-12: motion sensor and menu status

| Item | Status | Evidence / next step |
| --- | --- | --- |
| Internal accelerometer | **Working with MC3230 driver** | Android legacy `mma7660` module srcversion confirmed; mainline Linux 6.12 `mma7660` returned 0/0/0; `mc3230.ko` at I²C-1/0x4c produces varying X/Y/Z raw values |
| MC3230 reboot persistence | **Verified after reboot** | Local `/usr/local/sbin/casper-mc3230-init`, `/etc/boot.d/85-casper-mc3230`, kernel #5 unchanged |
| Casper menu v0.2 | **Live tilt status verified** | Four buttons WLAN/Akku/Terminal/NetSurf; brightness, display-off, HOME hint and 1-second IIO status refresh |
| Orientation calibration / rotation | **Pending** | Physical sensor axes still need reliable direction mapping. Xrandr dynamic rotation previously caused Xorg SIGSEGV; no auto-rotation enabled |
| Camera and further keys | **Pending** | Original Android reports `gc0308`/`gc0309` and `sun5i_csi0`, `sun4i-keyboard`; no Debian camera validation yet |

Full evidence and local installation notes: [MC3230 accelerometer](mc3230-accelerometer-2026-11-12.md). Keep original Android NAND and extracted proprietary artifacts out of this repo.
