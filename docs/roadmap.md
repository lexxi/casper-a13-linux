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
| Wi-Fi latency / reception | **In progress** | About −79 dBm, RX link 13 Mbit/s, severe ping jitter; test near AP and orientation |
| Goodix GT811 touch | **Pending** | Review I²C/pin config, DT integration |
| Graphical touch UI | **Pending** | Choose small offline UI / terminal |
| Second tablet | **Repair separate** | Deep-discharged battery; no Linux boot yet |

## Why Wi-Fi before keyboard?

The Casper has only one Mini-USB port. A Micro-USB OTG adapter is available, but not a Mini-USB OTG host cable. WLAN + SSH could provide a shell without extra input hardware, **if** the USB Wi-Fi chip, firmware and Linux USB host path work.

## Next WLAN tests

The Linux USB bus now sees `0bda:8176`, firmware loads, and Wi-Fi plus SSH work. `iw` version 6.17 was temporarily transferred to the live ARMHF system. It reports `Power save: off`, 2.4 GHz channel 6 (2437 MHz), approximately **−79 dBm**, RX bitrate **13 Mbit/s** and TX bitrate **72.2 Mbit/s** at the measured instant. Ping responses have shown large intermittent latency spikes. Next: repeat signal and ping tests 1–2 m from the access point and at different tablet orientations; inspect retry statistics. If reception remains poor, check antenna and compare drivers. The absent `regulatory.db` is a separate cleanup item. Keep credentials out of Git.
