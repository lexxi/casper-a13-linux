# Hardware identification and recovery notes

## Tested device

- **Product:** Casper / INTREEO TAB-WB72, Android 4.0.4
- **SoC:** Allwinner A13 / sun5i, ARM Cortex-A8
- **RAM:** 512 MiB DDR3
- **Display:** 800 × 480; LCD console output confirmed under Linux
- **Touchscreen:** Goodix GT811; not yet enabled in the Linux image
- **Storage:** ~4 GB internal NAND; microSD boot successfully tested
- **Connector:** one Mini-USB, used previously for ADB and FEL; an OTG adapter is needed to test an external keyboard
- **Wi-Fi:** USB device at `/sys/bus/usb/devices/2-1` under original Android:
  - `idVendor` = `0bda`
  - `idProduct` = `8176`
  - `product` = `802.11n WLAN Adapter`
  - Realtek RTL8188CUS family; `rtl8xxxu` is a candidate on modern Linux, **not tested yet**
  - `rtl8150` in the Android modules listing is an Ethernet driver and not identification of the Wi-Fi module

## Original Android hardware data

The original FEX configuration was recovered locally from the NAND (through a backup of `/dev/block/nanda`). Observed configuration:

- DDR clock: 432 MHz
- DDR3: 512 MiB, 16-bit bus
- DRAM ZQ: `0x7b`
- DRAM EMR1: `0`
- LCD: 800 × 480, pixel clock ~33 MHz
- PWM backlight pin: PB02
- SD controller: SDC0 on PF pins

The Q8 A13 reference board's U-Boot settings **do work** for this unit despite differing from some values in its original FEX. Do not assume these settings apply to every board revision.

## FEL / USB rescue

The tablet entered FEL with the physical Home + Power combination during testing. USB device: `1f3a:efe8`. Under the tested Windows + WSL setup:

```powershell
usbipd bind --busid 3-3 --force
usbipd attach --wsl --busid 3-3
```

The bus ID above was observed **on one specific machine** and must be discovered again on other hosts. In WSL, `sunxi-fel version` identified an Allwinner A13 (`soc=00001625`). FEL was useful for U-Boot tests, but everyday boots now run from microSD.

## Backups

All ten original NAND partitions were backed up locally before experimenting. The first 4 MiB of the original SD medium were also saved before the initial bootloader write. Keep backups offline/private; no images are uploaded here.

## Second tablet (separate repair)

A second otherwise similar unit does **not** boot. Its LiPo measured approximately 0.5 V while attached and 2.0 V after disconnecting; it is deeply discharged and must not be assumed safe to recharge. The working Linux experiment uses the **first** tablet. Do not confuse observations from these two devices.
