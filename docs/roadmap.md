# Roadmap and evidence

Updated 2026-10-27.

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
| Goodix GT811 touch | **Pending** | Review I²C/pin config, DT integration |
| Graphical touch UI | **Pending** | Choose small offline UI / terminal |
| Second tablet | **Repair separate** | Deep-discharged battery; no Linux boot yet |

## Why Wi-Fi before keyboard?

The Casper has only one Mini-USB port. A Micro-USB OTG adapter is available, but not a Mini-USB OTG host cable. WLAN + SSH could provide a shell without extra input hardware, **if** the USB Wi-Fi chip, firmware and Linux USB host path work.

## Confirmed 2026-10-27 findings

Using `rtl8xxxu`, 19 pings near the AP averaged 472.282 ms with maximum 1707.050 ms. Switching to built-in `rtl8192cu` reduced latency drastically (30-ping sample at original location: 2.388/5.811/12.322 ms min/avg/max, no loss). Longer 300-ping test showed rare jitter spikes (maximum 502.740 ms) but no packet loss.

Power key `axp20x-pek` exposes `/dev/input/event0`, `KEY_POWER` code 116. An ARMHF power-button program is started by `/init` and runs `/casper-shutdown.sh` upon key release. This stops the CSV monitor, syncs and unmounts FAT32, then requests `poweroff -f`. It shut down successfully; display and ping ceased, and the tablet booted again using its button.

Initial unmount `EBUSY` was caused by Dropbear inheriting `casper-boot.log` descriptors. Redirecting its standard streams to `/dev/null` resolved the problem.

Remaining: battery/USB voltage validation, shutdown failure recovery, regulatory database, touchscreen and graphical UI. Original Android NAND remains untouched.
