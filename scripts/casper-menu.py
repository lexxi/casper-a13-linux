#!/usr/bin/env python3
"""Casper TAB-WB72 – Touch-Menü v0.2 mit MC3230-Lageanzeige."""

import os
import subprocess
import tkinter as tk
from pathlib import Path

BG = "#14212d"
PANEL = "#203747"
FG = "#f4f7fa"
MUTED = "#b3c4d0"

BACKLIGHT = Path("/sys/class/backlight/backlight/brightness")
SAVED_BRIGHTNESS = Path("/run/casper-display-brightness")
ACCEL = Path("/sys/bus/iio/devices/iio:device1")

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
        self.child = None
        self.initializing = True

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

        tk.Button(
            bottom,
            text="Display ausschalten",
            command=self.display_off,
            font=("DejaVu Sans", 12),
            bg=PANEL, fg=FG,
            activebackground="#315166",
            activeforeground=FG,
            relief="flat",
            padx=10,
        ).pack(side="left")

        tk.Label(
            bottom,
            text="HOME: Aufwecken / Tastatur",
            bg=BG, fg=MUTED,
            font=("DejaVu Sans", 10),
        ).pack(side="right")

        self.orientation = tk.StringVar(value="Lage: wird ermittelt")
        tk.Label(
            root,
            textvariable=self.orientation,
            bg=BG, fg=MUTED,
            font=("DejaVu Sans", 10),
        ).pack(pady=(2, 0))
        self.root.after(500, self.update_orientation)

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

    def launch(self, name):
        if self.child is not None:
            return

        command = TOOLS[name]

        if not Path(command[0]).is_file():
            self.info.set(f"Programm fehlt: {name}")
            return

        env = os.environ.copy()
        env.setdefault("DISPLAY", ":0")

        try:
            self.child = subprocess.Popen(command, env=env)
        except OSError as exc:
            self.info.set(f"Startfehler: {exc}")
            self.child = None
            return

        self.root.withdraw()
        self.root.after(350, self.watch_child)

    def watch_child(self):
        if self.child is None:
            return

        if self.child.poll() is None:
            self.root.after(350, self.watch_child)
            return

        code = self.child.returncode
        self.child = None

        self.info.set(
            "Anwendung beendet"
            if code == 0
            else f"Beendet: Code {code}"
        )

        self.root.deiconify()
        self.root.lift()

    def close(self):
        self.root.destroy()


def main():
    root = tk.Tk()
    CasperMenu(root)
    root.mainloop()


if __name__ == "__main__":
    main()
