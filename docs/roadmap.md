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
| USB WLAN `0bda:8176` | **Working** | RTL8188CU rev A; `RTL8XXXU_UNTESTED=y`, `rtl8192cufw_TMSC.bin` |
| DHCP / WPA2 | **Working** | WPA2 association and DHCP address confirmed |
| SSH access | **Working** | Dropbear root login using matching ED25519 public key, proper `/root` ownership |
| AXP209 battery sysfs | **Working** | Battery and USB classes; charge/discharge measured, capacity not calibrated |
| AXP209 power key | **Driver built-in, not tested** | `CONFIG_INPUT_AXP20X_PEK=y`; verify input events before shutdown actions |
| NTP time sync | **Manually verified** | BusyBox `ntpd` set UTC clock after starting services manually; boot automation unverified |
| Power monitor CSV | **Manually verified** | 300-second monitor, `/mnt/sd/casper-power.csv`; fix script executable modes in initramfs |
| Safe shutdown / persistent storage | **Pending** | Test poweroff, avoid FAT32 corruption, later read-only root/data partition |
| Wi-Fi latency / reception | **In progress** | About −79 dBm, RX link 13 Mbit/s, severe ping jitter; test near AP and orientation |
| Goodix GT811 touch | **Pending** | Review I²C/pin config, DT integration |
| Graphical touch UI | **Pending** | Choose small offline UI / terminal |
| Second tablet | **Repair separate** | Deep-discharged battery; no Linux boot yet |

## Why Wi-Fi before keyboard?

The Casper has only one Mini-USB port. A Micro-USB OTG adapter is available, but not a Mini-USB OTG host cable. WLAN + SSH could provide a shell without extra input hardware, **if** the USB Wi-Fi chip, firmware and Linux USB host path work.

## Current power-management work

See [AXP209 battery, NTP and power-monitor notes](power-management.md). The test kernel includes `CONFIG_AXP20X_ADC=y`, `CONFIG_BATTERY_AXP20X=y` and `CONFIG_INPUT_AXP20X_PEK=y`. AXP209 readings show USB input around 4.2–4.4 V under load (with PC USB and separate 5 V supply) and battery discharge around −530 mA in a short test. Validate wiring/cable and battery measurements before setting any automatic cutoff. The prototype has working NTP and CSV when launched manually, but the next reboot needs to confirm corrected `0755` permissions and service autostart.

## Next WLAN tests

The Linux USB bus now sees `0bda:8176`, firmware loads, and Wi-Fi plus SSH work. `iw` version 6.17 was temporarily transferred to the live ARMHF system. It reports `Power save: off`, 2.4 GHz channel 6 (2437 MHz), approximately **−79 dBm**, RX bitrate **13 Mbit/s** and TX bitrate **72.2 Mbit/s** at the measured instant. Ping responses have shown large intermittent latency spikes. Next: repeat signal and ping tests 1–2 m from the access point and at different tablet orientations; inspect retry statistics. If reception remains poor, check antenna and compare drivers. The absent `regulatory.db` is a separate cleanup item. Keep credentials out of Git.
