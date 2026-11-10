#!/usr/bin/env python3
"""Casper TAB-WB72 – touch-friendly launcher for WiFi and Battery.

Debian 13 / Xorg / Matchbox, designed for a 800x480 screen with a
192-pixel on-screen keyboard. No privileged changes or shell commands.
"""
import os
import subprocess
import tkinter as tk
from pathlib import Path

TOOLS = {
    'WLAN verwalten': Path('/usr/local/bin/casper-wifi.py'),
    'Akku anzeigen': Path('/usr/local/bin/casper-battery.py'),
}
BG = '#14212d'
PANEL = '#203747'
FG = '#f4f7fa'
MUTED = '#b3c4d0'


class CasperMenu:
    def __init__(self, root):
        self.root = root
        self.child = None
        root.title('Casper – Werkzeuge')
        root.geometry('800x288+0+0')
        root.configure(bg=BG)
        root.resizable(False, False)
        root.protocol('WM_DELETE_WINDOW', self.close)

        header = tk.Frame(root, bg=BG)
        header.pack(fill='x', padx=20, pady=(12, 5))
        tk.Label(header, text='Casper – Werkzeuge', bg=BG, fg=FG,
                 font=('DejaVu Sans', 21, 'bold')).pack(side='left')
        tk.Button(header, text='Schließen', command=self.close,
                  font=('DejaVu Sans', 12), bg=PANEL, fg=FG,
                  activebackground='#315166', activeforeground=FG,
                  padx=14, pady=4, relief='flat').pack(side='right')

        self.info = tk.StringVar(value='Anwendung antippen, um sie zu öffnen.')
        tk.Label(root, textvariable=self.info, bg=BG, fg=MUTED,
                 font=('DejaVu Sans', 11)).pack(anchor='w', padx=22, pady=(0, 11))

        buttons = tk.Frame(root, bg=BG)
        buttons.pack(fill='both', expand=True, padx=20, pady=(0, 17))
        for label in TOOLS:
            tk.Button(buttons, text=label, command=lambda name=label: self.launch(name),
                      font=('DejaVu Sans', 19, 'bold'), bg=PANEL, fg=FG,
                      activebackground='#315166', activeforeground=FG,
                      relief='flat', padx=12, pady=20, cursor='hand2',
                      wraplength=290).pack(side='left', fill='both', expand=True,
                                           padx=(0, 8) if label == 'WLAN verwalten' else (8, 0))

    def launch(self, name):
        if self.child is not None:
            return
        path = TOOLS[name]
        if not path.is_file():
            self.info.set(f'Nicht gefunden: {path.name}')
            return
        env = os.environ.copy()
        env.setdefault('DISPLAY', ':0')
        try:
            self.child = subprocess.Popen(['/usr/bin/python3', str(path)], env=env)
        except OSError as exc:
            self.info.set(f'Start fehlgeschlagen: {exc}')
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
        exit_code = self.child.returncode
        self.child = None
        self.info.set('Anwendung beendet – Werkzeug auswählen.' if exit_code == 0
                      else f'Anwendung beendet (Code {exit_code}).')
        self.root.deiconify()
        self.root.lift()

    def close(self):
        self.root.destroy()


def main():
    root = tk.Tk()
    CasperMenu(root)
    root.mainloop()


if __name__ == '__main__':
    main()
