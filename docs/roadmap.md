# Roadmap and evidence

Updated 2026-10-26.

| Feature | Status | Evidence / next step |
| --- | --- | --- |
| Original Android NAND backup | **Done** | Ten NAND partitions copied locally |
| FEL access | **Done** | A13 `sunxi-fel version` detection |
| U-Boot SPL from SD | **Done** | Autonomous reset-to-boot confirmed |
| Linux 6.12 kernel and LCD console | **Done** | Kernel messages visible |
| BusyBox 1.37 static initramfs | **Done** | `~ #` shell prompt visible |
| USB OTG host mode | **In progress** | MUSB built-in configuration; DT and host cable to test |
| USB keyboard | **Pending** | Mini-USB OTG host adapter required |
| USB WLAN `0bda:8176` | **Identified only** | Evaluate `rtl8xxxu` and firmware, bring interface up |
| DHCP / WPA2 | **Pending** | Build userspace and configure credentials locally |
| SSH access | **Pending** | Build Dropbear, provision keys and network |
| Goodix GT811 touch | **Pending** | Review I²C/pin config, DT integration |
| Graphical touch UI | **Pending** | Choose small offline UI / terminal |
| Second tablet | **Repair separate** | Deep-discharged battery; no Linux boot yet |

## Why Wi-Fi before keyboard?

The Casper has only one Mini-USB port. A Micro-USB OTG adapter is available, but not a Mini-USB OTG host cable. WLAN + SSH could provide a shell without extra input hardware, **if** the USB Wi-Fi chip, firmware and Linux USB host path work.

## Next Linux Wi-Fi experiment

Android reported USB VID:PID `0bda:8176` with product string `802.11n WLAN Adapter`. Candidate Linux driver `RTL8XXXU`; confirm kernel configuration and firmware requirements before packaging into the initramfs. Keep network secrets outside Git.
