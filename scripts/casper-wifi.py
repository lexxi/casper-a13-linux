#!/usr/bin/env python3
"""Casper TAB-WB72 WiFi touch UI, using the existing wpa_supplicant.

Run as root within the Casper Xorg session. No additional Python packages
beyond tkinter. Passwords are never logged or included on command lines.
"""
import hashlib
import os
import re
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

IFACE = os.environ.get('CASPER_WIFI_IFACE', 'wlx000d724820c2')
WPA_CLI = '/usr/sbin/wpa_cli'
TIMEOUT = 12


def wpa(*args, timeout=TIMEOUT):
    result = subprocess.run([WPA_CLI, '-i', IFACE, *map(str, args)],
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'wpa_cli failed').strip())
    lines = result.stdout.strip()
    if lines.startswith('FAIL') or lines.startswith('UNKNOWN COMMAND'):
        raise RuntimeError(lines)
    return lines


def kv_status():
    return dict(line.split('=', 1) for line in wpa('status').splitlines() if '=' in line)


def networks():
    result = []
    for line in wpa('list_networks').splitlines()[1:]:
        parts = line.split('\t')
        if len(parts) >= 2 and parts[0].isdigit():
            result.append((parts[0], parts[1], parts[3] if len(parts) > 3 else ''))
    return result


def scan_results():
    items = {}
    for line in wpa('scan_results').splitlines()[1:]:
        bits = line.split('\t', 4)
        if len(bits) < 5:
            continue
        bssid, freq, level, flags, ssid = bits
        if not ssid:
            continue
        try:
            strength = int(level)
        except ValueError:
            continue
        previous = items.get(ssid)
        if previous is None or strength > previous[0]:
            items[ssid] = (strength, flags)
    return sorted(((ssid, *vals) for ssid, vals in items.items()),
                  key=lambda x: x[1], reverse=True)


def network_type(flags):
    if any(s in flags for s in ('WPA2-', 'WPA-', 'RSN-', 'WPA3-', 'SAE')):
        if 'EAP' in flags or '802.1X' in flags:
            return 'enterprise'
        if 'SAE' in flags and 'PSK' not in flags:
            return 'sae_only'
        if 'PSK' in flags:
            return 'psk'
        return 'unsupported'
    if 'WEP' in flags:
        return 'wep'
    return 'open'


class WiFiApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Casper WiFi')
        self.root.geometry('800x288+0+0')
        self.root.minsize(640, 250)
        self.root.configure(bg='#edf2f7')
        self.rows = []
        self.busy = False
        self.connected_ssid = ''
        self.saved = []
        self._ui()
        self.refresh_status()
        self.root.after(500, self.scan)
        self.root.after(12000, self.poll)

    def _ui(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('TButton', font=('DejaVu Sans', 12), padding=(6, 2))
        style.configure('TLabel', font=('DejaVu Sans', 11))
        style.configure('TEntry', font=('DejaVu Sans', 14))
        style.configure('Treeview', font=('DejaVu Sans', 12), rowheight=26)
        style.configure('Treeview.Heading', font=('DejaVu Sans', 12, 'bold'))
        head = tk.Frame(self.root, bg='#1f334b', height=38)
        head.pack(fill='x')
        tk.Label(head, text='Casper WiFi', fg='white', bg='#1f334b',
                 font=('DejaVu Sans', 16, 'bold')).pack(side='left', padx=10, pady=3)
        ttk.Button(head, text='Schließen', command=self.root.destroy).pack(side='right', padx=10)

        self.info = tk.StringVar(value='Verbindungsstatus wird geladen ...')
        tk.Label(self.root, textvariable=self.info, bg='#edf2f7', anchor='w',
                 font=('DejaVu Sans', 10)).pack(fill='x', padx=10, pady=(2, 0))

        body = tk.Frame(self.root, bg='#edf2f7')
        body.pack(fill='both', expand=True, padx=8, pady=1)
        self.table = ttk.Treeview(body, columns=('signal', 'security'),
                                  show='tree headings', selectmode='browse', height=3)
        self.table.heading('#0', text='WLAN / SSID')
        self.table.heading('signal', text='Signal')
        self.table.heading('security', text='Sicherheit')
        self.table.column('#0', width=370, minwidth=180)
        self.table.column('signal', width=105, minwidth=80, anchor='center')
        self.table.column('security', width=130, minwidth=100)
        scrollbar = ttk.Scrollbar(body, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.table.pack(side='left', fill='both', expand=True)
        self.table.bind('<<TreeviewSelect>>', self.selected)

        foot = tk.Frame(self.root, bg='#edf2f7')
        foot.pack(fill='x', padx=8, pady=1)
        ttk.Label(foot, text='Passwort:').pack(side='left')
        self.password = tk.StringVar()
        self.password_entry = ttk.Entry(foot, textvariable=self.password, show='*', width=35)
        self.password_entry.pack(side='left', fill='x', expand=True, padx=8)
        self.reveal = tk.BooleanVar(value=False)
        ttk.Checkbutton(foot, text='Anzeigen', variable=self.reveal,
                        command=lambda: self.password_entry.configure(show='' if self.reveal.get() else '*')).pack(side='left')

        buttons = tk.Frame(self.root, bg='#edf2f7')
        buttons.pack(fill='x', padx=8, pady=2)
        self.scan_button = ttk.Button(buttons, text='Neu suchen', command=self.scan)
        self.scan_button.pack(side='left', padx=3)
        self.connect_button = ttk.Button(buttons, text='Verbinden', command=self.connect)
        self.connect_button.pack(side='left', padx=3)
        ttk.Button(buttons, text='Status', command=self.refresh_status).pack(side='left', padx=3)
        ttk.Label(buttons, text='HOME: Tastatur',
                  font=('DejaVu Sans', 9)).pack(side='right')
        self.message = tk.StringVar(value='Bereit')
        tk.Label(self.root, textvariable=self.message, bg='#dae5ef', anchor='w',
                 font=('DejaVu Sans', 10)).pack(fill='x', ipady=2)

    def async_task(self, fn, on_done):
        if self.busy:
            return
        self.busy = True
        self.scan_button.configure(state='disabled')
        self.connect_button.configure(state='disabled')

        def work():
            try:
                outcome = (True, fn())
            except Exception as exc:
                outcome = (False, str(exc))
            def finish():
                self.busy = False
                self.scan_button.configure(state='normal')
                self.connect_button.configure(state='normal')
                on_done(*outcome)
            self.root.after(0, finish)
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        if not self.busy:
            self.refresh_status()
        self.root.after(12000, self.poll)

    def refresh_status(self):
        try:
            st = kv_status()
            self.saved = networks()
            self.connected_ssid = st.get('ssid', '') if st.get('wpa_state') == 'COMPLETED' else ''
            ip = st.get('ip_address') or 'keine IP'
            label = f"Verbindung: {self.connected_ssid or st.get('wpa_state', 'unbekannt')}   |   IP: {ip}"
            self.info.set(label)
        except Exception as exc:
            self.info.set(f'WLAN-Steuerung nicht erreichbar: {exc}')

    def scan(self):
        self.message.set('Suche nach WLAN-Netzen ... (aktive Verbindung bleibt bestehen)')
        def task():
            wpa('scan')
            import time
            time.sleep(3.0)
            return scan_results()
        def done(ok, value):
            if not ok:
                self.message.set('Suche fehlgeschlagen: ' + value)
                return
            self.rows = value
            self.table.delete(*self.table.get_children())
            for i, (ssid, strength, flags) in enumerate(self.rows):
                kind = network_type(flags)
                sec = {'psk': 'WPA-PSK', 'open': 'Offen',
                       'wep': 'WEP (nicht unterstützt)', 'enterprise': 'Enterprise',
                       'sae_only': 'WPA3/SAE', 'unsupported': 'Andere'}[kind]
                saved = any(x[1] == ssid for x in self.saved)
                label = ssid + ('  ✓' if ssid == self.connected_ssid else ('  · gespeichert' if saved else ''))
                self.table.insert('', 'end', iid=str(i), text=label,
                                  values=(f'{strength} dBm', sec))
            self.message.set(f'{len(value)} WLAN-Netze gefunden')
        self.async_task(task, done)

    def selected(self, event=None):
        self.password.set('')
        selected = self.table.selection()
        if not selected:
            return
        ssid = self.rows[int(selected[0])][0]
        self.message.set(f'Ausgewählt: {ssid} – Passwort unten eingeben')
        self.password_entry.focus_set()

    def connect(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo('WLAN', 'Bitte zuerst ein WLAN auswählen.')
            return
        ssid, strength, flags = self.rows[int(selected[0])]
        kind = network_type(flags)
        existing = next((x[0] for x in self.saved if x[1] == ssid), None)
        if kind not in ('psk', 'open') and existing is None:
            messagebox.showwarning('Nicht unterstützt',
                                   'Diese WLAN-Sicherheitsart unterstützt Version 0.1 nicht.')
            return
        password = self.password.get()
        if kind == 'psk' and existing is None and not (8 <= len(password) <= 63):
            messagebox.showerror('WLAN-Passwort', 'WPA2-Passwort muss 8 bis 63 Zeichen haben.')
            return
        if ssid == self.connected_ssid:
            messagebox.showinfo('WLAN', 'Mit diesem Netzwerk bereits verbunden.')
            return
        if not messagebox.askyesno('WLAN wechseln',
                                   f'Zu „{ssid}“ verbinden?\n\n'
                                   'Die SSH-Verbindung kann dabei abbrechen.\n'
                                   'Diesen Wechsel nur direkt am Casper durchführen.'):
            return
        self.message.set(f'Verbinde zu {ssid} ...')
        hex_ssid = ssid.encode('utf-8').hex()
        derived_psk = (hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'),
                                         ssid.encode('utf-8'), 4096, 32).hex()
                       if kind == 'psk' and existing is None else None)
        self.password.set('')

        def task():
            nid = existing
            if nid is None:
                nid = wpa('add_network').splitlines()[-1]
                if not nid.isdigit():
                    raise RuntimeError('Ungültige neue Netzwerk-ID: ' + nid)
                try:
                    wpa('set_network', nid, 'ssid', hex_ssid)
                    if kind == 'psk':
                        wpa('set_network', nid, 'key_mgmt', 'WPA-PSK')
                        wpa('set_network', nid, 'psk', derived_psk)
                    else:
                        wpa('set_network', nid, 'key_mgmt', 'NONE')
                except Exception:
                    wpa('remove_network', nid)
                    raise
            wpa('select_network', nid)
            import time
            for _ in range(15):
                time.sleep(2)
                st = kv_status()
                if st.get('wpa_state') == 'COMPLETED' and st.get('ssid') == ssid:
                    try:
                        wpa('save_config')
                        persisted = True
                    except Exception:
                        persisted = False
                    return ('connected', st.get('ip_address', ''), persisted)
            return ('timeout', '', False)

        def done(ok, result):
            self.refresh_status()
            if not ok:
                self.message.set(f'Verbindung fehlgeschlagen: {result}')
                messagebox.showerror('WLAN', result)
                return
            if result[0] == 'connected':
                addr = result[1]
                saved_note = 'gespeichert' if result[2] else 'NICHT dauerhaft gespeichert (update_config prüfen)'
                self.message.set(f'WLAN verbunden: {ssid}; IP: {addr or "noch keine"}; {saved_note}')
                if not addr:
                    messagebox.showwarning('DHCP',
                                           'WLAN ist assoziiert, aber keine IP wurde bestätigt.\n'
                                           'Bestehendes ifupdown/dhclient separat prüfen.')
            else:
                self.message.set('Verbindung nicht bestätigt. Vorheriges WLAN ggf. über SSH wiederherstellen.')
                messagebox.showwarning('WLAN', 'Verbindung nicht bestätigt. Keine automatische Rückschaltung.')
        self.async_task(task, done)


def main():
    if os.geteuid() != 0:
        raise SystemExit('Als root starten (wpa_supplicant-Control-Socket).')
    root = tk.Tk()
    WiFiApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
