# Physical HOME key and on-screen keyboard — kernel #5 (2026-11-10)

## Status

**Verified on Casper TAB-WB72 / INTREEO, Allwinner A13, Debian 13 armhf, Linux 6.12.0 kernel #5:**

- Physical **second hardware button** (distinct from the AXP209 power button and the six capacitive GT811 bezel icons) produces press/release events `KEY_HOME` (102).
- A native Python evdev reader toggles `matchbox-keyboard` on the 800×480 Xorg/Matchbox desktop.
- `EVIOCGRAB` prevents Xorg/xterm from receiving the same HOME key and printing `^[[H`.
- Manual launch of `/etc/boot.d/90-casper-keyboard` started the Python process, grabbed LRADC and logged successful startup.
- **Automatic restart/boot integration is configured but the post-reboot verification is still pending.** Do not mark it completed until verified.

The original Android NAND is unchanged.

## Hardware discovery

Under the original rooted Android 4.0.4, the physical button generated `KEY_HOME` from `sun4i-keyboard`. Direct reading of LRADC DATA0 at `0x01c2280c` with Android BusyBox `devmem` showed:

| State | ADC data0 (6-bit) |
| --- | --- |
| Pressed | `0x1b` = 27 |
| Released | `0x3f` = 63 |

For the `allwinner,sun4i-a10-lradc-keys` compatible driver and the 3.0 V `reg_ldo2` supply, the Linux driver uses reference scaling 2/3, yielding `2,000,000 µV` and a key target `27 × 2000000 / 63 = 857142 µV`.

The initial reconstructed kernel lacked the LRADC input driver. Enable it as a built-in:

```sh
cd ~/casper-a13/linux
scripts/config --enable KEYBOARD_SUN4I_LRADC
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- olddefconfig
grep CONFIG_KEYBOARD_SUN4I_LRADC .config
# CONFIG_KEYBOARD_SUN4I_LRADC=y
```

In `linux/arch/arm/boot/dts/allwinner/sun5i-a13-q8-tablet.dts`, append the following to override the **reference tablet's incorrect analog Volume Up/Down mappings**. This code is a patch snippet, not a complete DTS.

```dts
/*
 * Casper physical HOME: LRADC data0 pressed=0x1b, released=0x3f.
 * Reference 3.0 V * 2/3 = 2.0 V; 27 * 2000000 / 63 = 857142 uV.
 */
&lradc {
        vref-supply = <&reg_ldo2>;
        status = "okay";

        /delete-node/ button-200;
        /delete-node/ button-400;

        button-857 {
                label = "Casper Physical Home";
                linux,code = <KEY_HOME>;
                channel = <0>;
                voltage = <857142>;
        };
};
```

**DTS syntax pitfall:** `vref-supply` and `status` (properties) must precede the `/delete-node/` directives and child node. An earlier ordering failed with `Properties must precede subnodes`.

Build and check:

```sh
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j2 allwinner/sun5i-a13-q8-tablet.dtb
dtc -I dtb -O dts arch/arm/boot/dts/allwinner/sun5i-a13-q8-tablet.dtb 2>/dev/null |
    grep -A 20 'lradc@1c22800'
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j2 zImage
```

The compiled LRADC node contains just `button-857`, with `linux,code = <0x66>` (102) and `voltage = <0xd1436>` (857142), not the generic reference-board buttons.

### Locally tested #5 artifacts (not committed)

| Artifact | SHA256 |
| --- | --- |
| `backups/kernel-5/zImage` | `467cb6269a8d9ff813720976b8ec6d89ae942111587843a13c4486c991523f48` |
| `backups/kernel-5/sun5i-a13-q8-tablet.dtb` | `1905cdaeedc184f6c23a918c01b28ede3dddc1101a25e8247542c98f1302253f` |

## Boot-file selection and recovery

**Inspect the actual SD card's active `boot.scr`, not an older WSL copy.** On the tested FAT32 volume `CASPER_BOOT`, the active `boot.scr` loaded:

```text
fatload mmc 0:1 0x42000000 zImage-test
fatload mmc 0:1 0x43000000 initramfs-debian.cpio.gz
fatload mmc 0:1 0x44000000 sun5i-a13-q8-tablet.dtb
bootz 0x42000000 0x43000000:${initrd_size} 0x44000000
```

A separate `boot-debian.scr` loaded `zImage`; the active test script did **not**. For #5, the new `zImage` was copied to **`zImage-test`** and the compiled DTB to `sun5i-a13-q8-tablet.dtb`. Do not replace `zImage` expecting this active boot script to use it. Do not change `initramfs-debian.cpio.gz`.

Before SD edits, preserve the exact current `zImage-test`, DTB and `boot.scr` off-card, verify their hashes, and keep the older known-good boot files for rollback. The host's WSL `lsblk` showed only virtual disks; the actual FAT32 SD partition was accessed via Windows drive letter `G:` in this test, **not a permanent drive-letter assignment**. Avoid writing raw disks, and never modify Android NAND.

### Runtime evidence

```sh
cat /proc/bus/input/devices
dmesg | grep -i lradc
evtest /dev/input/event1
```

Observed:

```text
N: Name="1c22800.lradc"
H: Handlers=kbd event1
B: KEY=40 0 0 0
[    1.167315] input: 1c22800.lradc ...
Event: type 1 (EV_KEY), code 102 (KEY_HOME), value 1
Event: type 1 (EV_KEY), code 102 (KEY_HOME), value 0
```

Two separate physical button presses produced the expected press and release events. On this build, `event0` is AXP209 power, `event1` LRADC HOME, and `event2` Goodix GT811 touchscreen. **Event numbers are not stable across kernel/input configuration changes; check before reusing the script.**

## On-screen keyboard toggle

The tested UI uses Xorg `:0`, Matchbox window manager and Matchbox Keyboard. `/root/.xinitrc` includes:

```sh
export DISPLAY=:0
export MB_KBD_CONFIG=/root/casper-keyboard/keyboard.xml
xset s off
xset -dpms
matchbox-window-manager -use_titlebar no &
sleep 2
matchbox-keyboard > /tmp/casper-keyboard.log 2>&1 &
exec xterm -geometry 80x24+0+0 -fa Monospace -fs 10
```

Initially, `wmctrl -lG` showed an 800×192 keyboard at `0,288` and an 800×288 xterm; closing the keyboard expanded xterm to 800×480. Sending `wmctrl -ic <keyboard-window-id>` closed the keyboard process correctly. The toggle script uses the process name rather than a volatile window ID.

To install the **tested source from this repository**:

```sh
install -m 0755 scripts/casper-keyboard-toggle.py /usr/local/bin/casper-keyboard-toggle.py
python3 -m py_compile /usr/local/bin/casper-keyboard-toggle.py
```

The repository copy is intended to be copied to the tablet (e.g. via `scp`) first; the command above runs where the repository exists.

Test interactively (stop any already-running instance to avoid competing grabs):

```sh
python3 -u /usr/local/bin/casper-keyboard-toggle.py
```

Each `KEY_HOME` press toggles the keyboard. The script uses `pgrep -f '^(/usr/bin/)?matchbox-keyboard$'` and matching `pkill`; **do not** use `pgrep -x -f matchbox-keyboard`, because it fails to match the full command line and creates duplicate keyboard instances. Python `fcntl.ioctl(..., EVIOCGRAB, 1)` gives the reader exclusive access to LRADC, stopping Xorg from emitting `^[[H` in xterm. It grabs only the analog HOME input, not touchscreen or AXP209 power.

## SysVinit startup

This Debian image has **SysVinit**, not systemd: `systemctl` is absent. `/etc/rc2.d/S03rc.local -> ../init.d/rc.local` is present and executable `/etc/rc.local` calls:

```sh
if test -d /etc/boot.d ; then
        run-parts /etc/boot.d
fi
```

Install the repository's `scripts/90-casper-keyboard` as `/etc/boot.d/90-casper-keyboard`, executable. The shell script starts the Python reader in the background, avoids duplicate launches and logs to `/var/log/casper-keyboard-toggle.log`:

```sh
mkdir -p /etc/boot.d
install -m 0755 scripts/90-casper-keyboard /etc/boot.d/90-casper-keyboard
sh -n /etc/boot.d/90-casper-keyboard
/etc/boot.d/90-casper-keyboard
pgrep -af casper-keyboard-toggle.py
tail -10 /var/log/casper-keyboard-toggle.log
```

**Manually verified output:** one Python process, `LRADC grabbed exclusively`, `Waiting for HOME button...`.

**Still pending:** after reboot, confirm that the process starts automatically *without* SSH launch and the physical button works with Xorg running. If not, examine `/etc/rc.local` execution and `/var/log/casper-keyboard-toggle.log`. There is no systemd unit on this installation.

## Follow-up

- Confirm post-reboot SysVinit startup.
- Keep backups of the known-good kernel/DTB/boot script and record #5 config for reproducibility.
- If the input device enumeration changes, replace the hardcoded `/dev/input/event1` with a stable `/dev/input/by-path`/udev match or a lookup by `Name="1c22800.lradc"`.
