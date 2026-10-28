# Roadmap and evidence

Updated 2026-10-28.

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
