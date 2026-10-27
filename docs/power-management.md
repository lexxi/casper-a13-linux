# Power management, NTP and logging (2026-10-27)

## Verified hardware

The working Casper TAB-WB72 has an **AXP209** power-management IC. Linux 6.12 now exposes:

- `/sys/class/power_supply/axp20x-battery`
- `/sys/class/power_supply/axp20x-usb`

These kernel features have been enabled **built-in** and the resulting kernel boot-tested:

```text
CONFIG_MFD_AXP20X=y
CONFIG_REGULATOR_AXP20X=y
CONFIG_AXP20X_POWER=y
CONFIG_IIO=y
CONFIG_AXP20X_ADC=y
CONFIG_BATTERY_AXP20X=y
CONFIG_INPUT_AXP20X_PEK=y
```

The Q8 reference device tree includes `axp209.dtsi`, and its `sun5i-reference-design-tablet.dtsi` sets `&battery_power_supply { status = "okay"; };`. No further DT change was required to expose the battery class.

## Observed measurements (not design ratings)

A captured reading with a separate 5 V adapter:

```text
axp20x-battery: status=Charging, present=1, capacity=94,
                voltage_now=4129000 µV, current_now=262000 µA
axp20x-usb:     online=1, voltage_now=4365000 µV, current_now=844000 µA
```

Values from sysfs are microvolts and microamps. USB input voltage is **not** battery voltage and USB input current is **not** battery charging current.

During an unplug/replug test battery status changed from `Charging` (~+180 mA) to `Discharging` (~−522 to −541 mA at ~4.02 V), then back to `Charging` (~+145 mA), later `Not charging` (0 mA). Estimated battery-side draw during this particular discharge was ~2.1 W (instantaneous, not a measured average runtime). AXP209 estimated capacity moved 94 → 90 → 93% within seconds: **do not treat percentage as calibrated**. `health: Good` does not prove remaining battery life.

With both PC USB and a separate 5 V supply, voltage at the AXP209 USB input under load was often only ~4.2–4.4 V at ~0.6–0.85 A. Cable, mini-USB contacts, power source and readings should be checked. Do not alter charge parameters, assume 5 V at the tablet, or deploy unattended charging based on these observations.

To inspect:

```sh
for p in /sys/class/power_supply/*; do
    echo "=== ${p##*/} ==="
    for f in type status present capacity voltage_now current_now health online; do
        [ -r "$p/$f" ] && echo "$f: $(cat "$p/$f")"
    done
done
```

## Power monitor prototype

Local development files (not included in the GitHub repository) are:

- `~/casper-a13/initramfs-network/casper-power-monitor.sh`
- `~/casper-a13/initramfs-network/power-services.sh`
- `~/casper-a13/initramfs-network/network-start.sh`

The monitor logs to the SD FAT32 partition `/mnt/sd/casper-power.csv`, by default every **300 seconds**:

```text
timestamp,uptime_s,battery_status,battery_pct,battery_mv,battery_ma,usb_online,usb_mv,usb_ma
2026-10-27T20:08:08Z,200,Not charging,95,4106,0,1,4219,629
```

The CSV also contains older tests with `1970-01-01` timestamps and a different timestamp format. `uptime_s` helps distinguish measurements; never assume all wall-clock timestamps are valid. Reduce FAT32 writes where possible and perform clean shutdowns.

The `power-services.sh` prototype performs one BusyBox NTP sync (`ntpd -n -q`, subject to a 30-second `timeout`), logs to `/mnt/sd/casper-ntp.log`, then executes `casper-power-monitor.sh 300`. BusyBox was built with `CONFIG_NTPD=y`.

**Manually verified:** After correcting permissions on the live RAM filesystem, running `/power-services.sh` produced an NTP adjustment and a new CSV record. At the last inspection, one monitor process was running. **Autostart after a subsequent reboot is not yet verified**.

### Discovered boot issue: missing executable bits

Both scripts were present in the generated initramfs but booted with mode `0644` rather than `0755`. The network script invoked `/power-services.sh` with output redirected to `/dev/null`; consequently no monitor and no NTP log appeared. Running `chmod 755` on the live tablet fixed manual execution, but this RAM change does **not** persist across reboot.

Correct the *source tree* before repacking:

```bash
cd ~/casper-a13
sudo chmod 755 initramfs-network/power-services.sh \
  initramfs-network/casper-power-monitor.sh
stat -c '%a %n' initramfs-network/{power-services,casper-power-monitor}.sh
sh -n initramfs-network/{power-services,casper-power-monitor}.sh
```

Then repack the `initramfs-network` directory while preserving ownership and modes, copy the resulting archive to the FAT32 boot partition as `initramfs.cpio.gz`, and **verify permissions and service startup after reboot**. A lock directory such as `/run/casper-power-monitor.lock` has been proposed to avoid two logging processes, but its source-tree installation is **not yet confirmed**.

### Follow-up work

1. Ensure executable bits survive repacking, then reboot-test the autonomous service startup.
2. Verify NTP failure and offline behavior; avoid logging misleading timestamps where possible.
3. Add a single-instance monitor lock; keep runtime locks on tmpfs, not the SD card.
4. Test `CONFIG_INPUT_AXP20X_PEK=y` button events separately; implement *safe* shutdown only after observing real event behavior.
5. Collect long-term battery measurements before choosing alerts or shutdown thresholds; use safe power wiring and clean shutdown.
6. Consider a read-only root filesystem with a dedicated persistent data partition rather than frequently writing to FAT32.

Never commit raw SD images, credentials, WLAN configuration, SSH keys or battery-specific identifiers.

## Update 2026-10-27 — confirmed boot and power-button shutdown

The earlier experimental status above is superseded by successful reboot tests. The deployed `power-services.sh` uses `busybox timeout 90 busybox ntpd -n -q -p 192.168.98.32` followed by `casper-power-monitor.sh 300`. Time synchronization and CSV writes were verified automatically after reboot.

`axp20x-pek` exposes `/dev/input/event0`; `evtest` and a separately cross-compiled ARMHF `casper-power-button` program confirmed `KEY_POWER` (116) pressed/released events. `/init` starts the button monitor in the background. On release it executes `/casper-shutdown.sh`, which signals the battery monitor to terminate, pauses briefly, calls `sync`, unmounts `/mnt/sd` (aborts if busy), and invokes `busybox poweroff -f`.

The first unmount attempt failed because the Dropbear listener and session inherited open `/mnt/sd/casper-boot.log` descriptors from `network-start.sh`. Redirecting Dropbear stdin/stdout/stderr to `/dev/null` eliminated these persistent descriptors. Manual and automatic button-initiated shutdown both succeeded, the screen went dark, ping stopped, and the device subsequently powered up using the button.

Remaining limitation: when shutdown aborts, the current script may leave the power monitor stopped. Rework that failure path before treating the implementation as production-grade. Power-off current has not been measured independently.
