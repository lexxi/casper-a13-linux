#!/usr/bin/env python3
"""Casper TAB-WB72 – Touch-Menü v0.6: MENU-Navigation wiederhergestellt, Power-Aktionen."""

import os
import shutil
import struct
import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

BG = "#14212d"
PANEL = "#203747"
FG = "#f4f7fa"
MUTED = "#b3c4d0"

BACKLIGHT = Path("/sys/class/backlight/backlight/brightness")
SAVED_BRIGHTNESS = Path("/run/casper-display-brightness")
ACCEL = Path("/sys/bus/iio/devices/iio:device1")
INPUT_EVENT = struct.Struct("llHHi")  # Linux ARM 32-bit input_event
EV_KEY = 1
KEY_MENU = 139
GT811_NAME = "Casper Goodix GT811 Touchscreen"

TOOLS = {
    "WLAN": ["/usr/bin/python3", "/usr/local/bin/casper-wifi.py"],
    "Akku": ["/usr/bin/python3", "/usr/local/bin/casper-battery.py"],
    "Terminal": ["/usr/bin/xterm", "-geometry", "80x24+0+0",
                 "-fa", "Monospace", "-fs", "10"],
    "Browser": ["/usr/bin/netsurf-gtk"],
}


def read_number(path, default):
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return default


class CasperMenu:
    def __init__(self, root):
        self.root = root
        self.children = set()
        self.initializing = True
        self.key_fd = None
        self.key_buffer = b""

        root.title("Casper – Werkzeuge")
        root.geometry("800x288+0+0")
        root.resizable(False, False)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)

        top = tk.Frame(root, bg=BG)
        top.pack(fill="x", padx=16, pady=(6, 2))

        tk.Label(
            top, text="Casper – Werkzeuge",
            fg=FG, bg=BG,
            font=("DejaVu Sans", 17, "bold")
        ).pack(side="left")

        self.info = tk.StringVar(value="Anwendung auswählen")
        tk.Label(
            top, textvariable=self.info,
            fg=MUTED, bg=BG,
            font=("DejaVu Sans", 10)
        ).pack(side="right")

        grid = tk.Frame(root, bg=BG)
        grid.pack(fill="x", padx=14, pady=5)

        for index, name in enumerate(TOOLS):
            button = tk.Button(
                grid,
                text=name,
                command=lambda n=name: self.launch(n),
                font=("DejaVu Sans", 15, "bold"),
                bg=PANEL, fg=FG,
                activebackground="#315166",
                activeforeground=FG,
                relief="flat",
                height=2,
            )
            button.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=4,
                pady=3,
            )

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        display = tk.Frame(root, bg=BG)
        display.pack(fill="x", padx=17, pady=(2, 0))

        tk.Label(
            display, text="Helligkeit",
            bg=BG, fg=FG,
            font=("DejaVu Sans", 12)
        ).pack(side="left")

        current = read_number(BACKLIGHT, 8)
        saved = read_number(SAVED_BRIGHTNESS, 8)
        self.level = current if current > 0 else saved
        self.level = max(1, min(10, self.level))

        self.level_label = tk.Label(
            display, text=str(self.level),
            bg=BG, fg=FG,
            font=("DejaVu Sans", 12, "bold"),
            width=3
        )
        self.level_label.pack(side="right")

        self.slider = tk.Scale(
            display,
            from_=1,
            to=10,
            orient="horizontal",
            showvalue=False,
            command=self.set_brightness,
            bg=BG, fg=FG,
            troughcolor=PANEL,
            activebackground="#5bafde",
            highlightthickness=0,
            bd=0,
            resolution=1,
        )
        self.slider.pack(
            side="left", fill="x",
            expand=True, padx=12
        )
        self.slider.set(self.level)
        self.initializing = False

        bottom = tk.Frame(root, bg=BG)
        bottom.pack(fill="x", padx=18, pady=(3, 4))

        for label, callback in (
            ("Display aus", self.display_off),
            ("Neustart", lambda: self.power_action("reboot")),
            ("Ausschalten", lambda: self.power_action("poweroff")),
        ):
            tk.Button(
                bottom, text=label, command=callback,
                font=("DejaVu Sans", 12),
                bg=PANEL, fg=FG, activebackground="#315166",
                activeforeground=FG, relief="flat", padx=9,
            ).pack(side="left", padx=(0, 8))
        tk.Label(
            bottom, text="MENU: Menü  HOME: Tastatur",
            bg=BG, fg=MUTED, font=("DejaVu Sans", 9),
        ).pack(side="right")

        self.orientation = tk.StringVar(value="Lage: wird ermittelt")
        tk.Label(
            root,
            textvariable=self.orientation,
            bg=BG, fg=MUTED,
            font=("DejaVu Sans", 10),
        ).pack(pady=(2, 0))
        self.root.after(500, self.update_orientation)
        self.root.after(250, self.poll_menu_key)

    def update_orientation(self):
        try:
            x = int((ACCEL / "in_accel_x_raw").read_text())
            y = int((ACCEL / "in_accel_y_raw").read_text())
            z = int((ACCEL / "in_accel_z_raw").read_text())

            values = {"X": x, "Y": y, "Z": z}
            axis = max(values, key=lambda a: abs(values[a]))
            peak = values[axis]

            if abs(peak) < 55:
                position = "Unbestimmt"
            elif axis == "Z":
                position = "Flach"
            else:
                position = f"Neigung {axis}{'+' if peak > 0 else '-'}"

            self.orientation.set(
                f"Lage: {position}    X:{x:+d} Y:{y:+d} Z:{z:+d}"
            )
        except (OSError, ValueError):
            self.orientation.set("Lage: Sensor nicht verfügbar")

        self.root.after(1000, self.update_orientation)

    def set_brightness(self, value):
        if self.initializing:
            return

        level = max(1, min(10, int(float(value))))

        try:
            SAVED_BRIGHTNESS.write_text(str(level) + "\n")
            BACKLIGHT.write_text(str(level) + "\n")
            self.level_label.configure(text=str(level))
            self.level = level
        except OSError as exc:
            self.info.set(f"Displayfehler: {exc}")

    def display_off(self):
        try:
            SAVED_BRIGHTNESS.write_text(str(self.level) + "\n")
            BACKLIGHT.write_text("0\n")
        except OSError as exc:
            self.info.set(f"Displayfehler: {exc}")

    def power_action(self, action):
        """Confirm system power action before executing it."""
        if action == "reboot":
            title = "Neustart bestätigen"
            question = "Casper wirklich neu starten? Offene Arbeiten gehen verloren."
            flag = "-r"
        elif action == "poweroff":
            title = "Ausschalten bestätigen"
            question = "Casper wirklich herunterfahren? Offene Arbeiten gehen verloren."
            flag = "-h"
        else:
            return

        if not messagebox.askyesno(
            title, question, parent=self.root, default=messagebox.NO
        ):
            return

        binary = shutil.which("shutdown") or "/sbin/shutdown"
        try:
            subprocess.Popen([binary, flag, "now"], close_fds=True)
            self.info.set("Neustart läuft" if action == "reboot"
                          else "Casper fährt herunter")
        except OSError as exc:
            self.info.set(f"Systemaktion fehlgeschlagen: {exc}")

    def find_gt811_event(self):
        """Resolve event node by device name; number may change at reboot."""
        for entry in sorted(Path("/sys/class/input").glob("event*")):
            try:
                name = (entry / "device/name").read_text().strip()
                if name == GT811_NAME:
                    return os.open(
                        str(Path("/dev/input") / entry.name),
                        os.O_RDONLY | os.O_NONBLOCK,
                    )
            except OSError:
                continue
        return None

    def poll_menu_key(self):
        """Nonblocking GT811 MENU reader; does not grab touchscreen events."""
        try:
            if self.key_fd is None:
                self.key_fd = self.find_gt811_event()
            if self.key_fd is not None:
                try:
                    chunk = os.read(self.key_fd, 32 * INPUT_EVENT.size)
                    if not chunk:
                        os.close(self.key_fd)
                        self.key_fd = None
                        self.key_buffer = b""
                    else:
                        self.key_buffer += chunk
                except BlockingIOError:
                    pass
                while len(self.key_buffer) >= INPUT_EVENT.size:
                    event = self.key_buffer[:INPUT_EVENT.size]
                    self.key_buffer = self.key_buffer[INPUT_EVENT.size:]
                    _, _, event_type, code, value = INPUT_EVENT.unpack(event)
                    if event_type == EV_KEY and code == KEY_MENU and value == 1:
                        self.root.deiconify()
                        self.root.lift()
                        self.root.focus_force()
        except OSError:
            if self.key_fd is not None:
                try:
                    os.close(self.key_fd)
                except OSError:
                    pass
            self.key_fd = None
            self.key_buffer = b""
        finally:
            self.root.after(100, self.poll_menu_key)

    def launch(self, name):
        # MENU can reopen the launcher while another tool is still running.
        # Do not prevent launching a second tool in that situation.
        command = TOOLS[name]
        if not Path(command[0]).is_file():
            self.info.set(f"Programm fehlt: {name}")
            return

        env = os.environ.copy()
        env.setdefault("DISPLAY", ":0")

        try:
            child = subprocess.Popen(command, env=env)
        except OSError as exc:
            self.info.set(f"Startfehler: {exc}")
            return

        self.children.add(child)
        self.root.withdraw()
        self.root.after(350, lambda proc=child: self.watch_child(proc))

    def watch_child(self, child):
        if child.poll() is None:
            self.root.after(350, lambda proc=child: self.watch_child(proc))
            return

        self.children.discard(child)
        code = child.returncode
        self.info.set(
            "Anwendung beendet" if code == 0 else f"Beendet: Code {code}"
        )

        # Do not steal focus from another still-running tool.
        # MENU remains available to bring the launcher forward any time.
        if not self.children:
            self.root.deiconify()
            self.root.lift()

    def close(self):
        if self.key_fd is not None:
            os.close(self.key_fd)
            self.key_fd = None
        self.root.destroy()


def main():
    root = tk.Tk()
    CasperMenu(root)
    root.mainloop()


if __name__ == "__main__":
    main()
