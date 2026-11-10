#!/usr/bin/env python3
"""Casper Battery v0.2 – AXP209 battery monitor for Casper TAB-WB72.

Read-only, no external Python dependencies other than Tkinter for the GUI.
On-screen keyboard remains free to occupy the bottom 192 pixels.
"""

import argparse
from pathlib import Path
import tkinter as tk

BATTERY = Path('/sys/class/power_supply/axp20x-battery')
USB = Path('/sys/class/power_supply/axp20x-usb')
REFRESH_MS = 5000
BG = '#14212d'
PANEL = '#1d3040'
FG = '#f4f7fa'
MUTED = '#b3c4d0'


def read_value(folder, name):
    try:
        return (folder / name).read_text(encoding='ascii').strip()
    except (OSError, UnicodeError):
        return None


def number(folder, name):
    value = read_value(folder, name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def capture():
    return {
        'capacity': number(BATTERY, 'capacity'),
        'status': read_value(BATTERY, 'status'),
        'battery_voltage_uv': number(BATTERY, 'voltage_now'),
        'battery_current_ua': number(BATTERY, 'current_now'),
        'usb_online': number(USB, 'online'),
        'usb_voltage_uv': number(USB, 'voltage_now'),
        'usb_current_ua': number(USB, 'current_now'),
    }


def fmt_voltage(uv):
    return '–' if uv is None else f'{uv / 1_000_000:.3f} V'


def fmt_current(ua):
    return '–' if ua is None else f'{abs(ua) / 1000:.0f} mA'


def status_label(s):
    return {
        'Charging': 'Lädt',
        'Discharging': 'Entlädt',
        'Full': 'Voll',
        'Not charging': 'Lädt nicht',
        'Unknown': 'Unbekannt',
    }.get(s, s or 'Nicht verfügbar')


def dump_readings():
    data = capture()
    print('Casper Battery – AXP209')
    print('Akku:', f"{data['capacity']} %" if data['capacity'] is not None else 'Nicht verfügbar')
    print('Status:', status_label(data['status']))
    print('Akkuspannung:', fmt_voltage(data['battery_voltage_uv']))
    print('Akkustrom:', fmt_current(data['battery_current_ua']))
    print('USB:', 'Angeschlossen' if data['usb_online'] == 1 else ('Nicht angeschlossen' if data['usb_online'] == 0 else 'Unbekannt'))
    print('USB-Spannung:', fmt_voltage(data['usb_voltage_uv']))
    print('USB-Strom:', fmt_current(data['usb_current_ua']))


class BatteryApp:
    def __init__(self, root):
        self.root = root
        root.title('Casper Battery')
        root.geometry('800x288+0+0')
        root.minsize(500, 270)
        root.configure(bg=BG)
        root.bind('<Escape>', lambda _e: root.destroy())

        top = tk.Frame(root, bg=BG)
        top.pack(fill='x', padx=16, pady=(10, 4))
        tk.Label(top, text='CASPER BATTERY', font=('DejaVu Sans', 16, 'bold'),
                 fg=FG, bg=BG).pack(side='left')
        tk.Button(top, text='Schließen', command=root.destroy,
                  font=('DejaVu Sans', 12), bg=PANEL, fg=FG,
                  activebackground='#31485a', activeforeground=FG,
                  padx=10, relief='flat').pack(side='right')

        main = tk.Frame(root, bg=BG)
        main.pack(fill='both', expand=True, padx=16, pady=(2, 3))
        left = tk.Frame(main, bg=PANEL, padx=16, pady=7)
        left.pack(side='left', fill='both', expand=True, padx=(0, 9))
        right = tk.Frame(main, bg=PANEL, padx=16, pady=9)
        right.pack(side='left', fill='both', expand=True)

        self.percent = tk.Label(left, text='– %', font=('DejaVu Sans', 48, 'bold'),
                                fg=FG, bg=PANEL)
        self.percent.pack(anchor='w')
        self.bar = tk.Canvas(left, height=24, bg='#31485a', highlightthickness=0,
                             bd=0)
        self.bar.pack(fill='x', pady=(3, 9))
        self.bar.bind('<Configure>', lambda _event: self.draw_bar())
        self.status = tk.Label(left, text='Lese Akkuwerte …', font=('DejaVu Sans', 14),
                               fg=MUTED, bg=PANEL)
        self.status.pack(anchor='w')

        self.fields = {}
        for label in ('Akkuspannung', 'Akkustrom', 'USB-Versorgung', 'USB-Spannung', 'USB-Strom'):
            row = tk.Frame(right, bg=PANEL)
            row.pack(fill='x', pady=4)
            tk.Label(row, text=label, font=('DejaVu Sans', 11), fg=MUTED,
                     bg=PANEL).pack(side='left')
            output = tk.Label(row, text='–', font=('DejaVu Sans', 12, 'bold'),
                              fg=FG, bg=PANEL)
            output.pack(side='right')
            self.fields[label] = output

        self.footer = tk.Label(root, text='AXP209 · Aktualisierung alle 5 s · Prozentwert nicht kalibriert',
                               font=('DejaVu Sans', 9), fg=MUTED, bg=BG)
        self.footer.pack(anchor='w', padx=16, pady=(1, 5))
        self.last_capacity = None
        self.color = '#36bf81'
        self.update()

    def draw_bar(self):
        w = self.bar.winfo_width()
        h = self.bar.winfo_height()
        self.bar.delete('all')
        self.bar.create_rectangle(0, 0, w, h, fill='#31485a', outline='')
        if self.last_capacity is not None:
            fraction = max(0, min(100, self.last_capacity)) / 100
            if fraction > 0:
                self.bar.create_rectangle(0, 0, w * fraction, h,
                                          fill=self.color, outline='')

    def update(self):
        data = capture()
        capacity = data['capacity']
        self.last_capacity = capacity
        self.color = '#ea5b5b' if capacity is not None and capacity <= 15 else (
            '#f5bc58' if capacity is not None and capacity <= 30 else '#36bf81')
        self.percent.configure(text=f'{capacity} %' if capacity is not None else '– %',
                               fg=self.color)
        self.status.configure(text=status_label(data['status']))
        self.fields['Akkuspannung'].configure(text=fmt_voltage(data['battery_voltage_uv']))
        self.fields['Akkustrom'].configure(text=fmt_current(data['battery_current_ua']))
        self.fields['USB-Versorgung'].configure(
            text='Ja' if data['usb_online'] == 1 else (
                'Nein' if data['usb_online'] == 0 else 'Unbekannt'))
        self.fields['USB-Spannung'].configure(text=fmt_voltage(data['usb_voltage_uv']))
        self.fields['USB-Strom'].configure(text=fmt_current(data['usb_current_ua']))
        self.draw_bar()
        self.root.after(REFRESH_MS, self.update)


def main():
    parser = argparse.ArgumentParser(description='Casper AXP209 Akkuanzeige')
    parser.add_argument('--dump', action='store_true', help='Werte ohne X11 einmalig ausgeben')
    args = parser.parse_args()
    if args.dump:
        dump_readings()
        return
    root = tk.Tk()
    BatteryApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
