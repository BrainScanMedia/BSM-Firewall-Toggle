#!/usr/bin/env python3
"""
BSM Firewall Toggle - Simple GTK4 firewall on/off app for Fedora
By BrainScanMedia.com, Inc.
Requires: python3-gobject, gtk4
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GLib, Gio, GdkPixbuf
import subprocess
import sys
import threading
import tempfile
import os


SHIELD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="80" height="80">
  <path d="M32 4 L58 14 L58 34 C58 50 46 60 32 62 C18 60 6 50 6 34 L6 14 Z"
        fill="{fill}" opacity="0.95"/>
  <path d="M32 10 L54 19 L54 34 C54 47 44 56 32 58 C20 56 10 47 10 34 L10 19 Z"
        fill="{fill_dark}" opacity="0.8"/>
  <polyline points="21,32 29,41 45,23"
        fill="none" stroke="white" stroke-width="5"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

GREEN_FILL      = "#2ea043"
GREEN_FILL_DARK = "#1a7f37"
RED_FILL        = "#f85149"
RED_FILL_DARK   = "#da3633"


def make_shield_pixbuf(blocking):
    fill      = RED_FILL      if blocking else GREEN_FILL
    fill_dark = RED_FILL_DARK if blocking else GREEN_FILL_DARK
    svg_data  = SHIELD_SVG.format(fill=fill, fill_dark=fill_dark).encode("utf-8")
    loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
    loader.write(svg_data)
    loader.close()
    return loader.get_pixbuf()


def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0, result.stdout.strip() + result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def get_active_interfaces():
    _, out = run_cmd(["firewall-cmd", "--get-active-zones"])
    interfaces = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("interfaces:"):
            interfaces += line.replace("interfaces:", "").split()
    return interfaces


def get_current_zone():
    ok, out = run_cmd(["firewall-cmd", "--get-default-zone"])
    if ok:
        return out.strip()
    return "unknown"


def is_blocking():
    return get_current_zone() in ("block", "drop")


def apply_zone(zone):
    interfaces = get_active_interfaces()
    lines = ["#!/bin/bash"]
    lines.append(f"firewall-cmd --set-default-zone={zone}")
    for iface in interfaces:
        lines.append(f"firewall-cmd --zone={zone} --change-interface={iface}")
    lines.append("firewall-cmd --reload")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh',
                                     delete=False, prefix='bsm_fw_') as f:
        f.write('\n'.join(lines))
        script_path = f.name

    os.chmod(script_path, 0o755)
    try:
        ok, msg = run_cmd(["pkexec", "bash", script_path])
    finally:
        os.unlink(script_path)

    return ok, msg


class FirewallToggleApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.brainscanmedia.FirewallToggle",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = FirewallWindow(application=app)
        self.win.present()


class FirewallWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("BSM Firewall Toggle")
        self.set_default_size(420, 380)
        self.set_resizable(False)

        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.apply_css(blocking=False)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_css_classes(["root-box"])
        root.set_margin_top(28)
        root.set_margin_bottom(24)
        root.set_margin_start(40)
        root.set_margin_end(40)
        self.set_child(root)

        # Shield image
        self.shield_image = Gtk.Image()
        self.shield_image.set_pixel_size(80)
        self.shield_image.set_margin_bottom(8)
        root.append(self.shield_image)

        title = Gtk.Label(label="FIREWALL")
        title.set_css_classes(["app-title"])
        title.set_margin_top(4)
        root.append(title)

        subtitle = Gtk.Label(label="by BrainScanMedia.com, Inc.")
        subtitle.set_css_classes(["app-subtitle"])
        subtitle.set_margin_top(4)
        root.append(subtitle)

        div = Gtk.Box()
        div.set_css_classes(["divider"])
        div.set_margin_top(20)
        div.set_margin_bottom(20)
        root.append(div)

        self.status_label = Gtk.Label(label="[ CHECKING... ]")
        self.status_label.set_css_classes(["status-label"])
        self.status_label.set_margin_bottom(24)
        root.append(self.status_label)

        switch_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        switch_row.set_halign(Gtk.Align.CENTER)
        root.append(switch_row)

        allow_label = Gtk.Label(label="ALLOW")
        allow_label.set_css_classes(["toggle-label"])
        switch_row.append(allow_label)

        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.switch.connect("state-set", self.on_switch_toggled)
        switch_row.append(self.switch)

        block_label = Gtk.Label(label="BLOCK ALL")
        block_label.set_css_classes(["toggle-label"])
        switch_row.append(block_label)

        self.spinner = Gtk.Spinner()
        self.spinner.set_margin_top(16)
        self.spinner.set_halign(Gtk.Align.CENTER)
        root.append(self.spinner)

        div2 = Gtk.Box()
        div2.set_css_classes(["divider"])
        div2.set_margin_top(20)
        div2.set_margin_bottom(12)
        root.append(div2)

        version = Gtk.Label(label="VERSION 1.02")
        version.set_css_classes(["version-label"])
        version.set_halign(Gtk.Align.CENTER)
        root.append(version)

        GLib.idle_add(self.refresh_state)

    def apply_css(self, blocking):
        """Load static CSS; switch color handled via named classes."""
        self.css_provider.load_from_string("""
            window { background-color: #0d1117; }
            .root-box { background-color: #0d1117; }
            .app-title {
                font-family: monospace;
                font-size: 26px;
                font-weight: bold;
                color: #58a6ff;
                letter-spacing: 3px;
            }
            .app-subtitle {
                font-family: monospace;
                font-size: 11px;
                color: #ffffff;
                letter-spacing: 1px;
            }
            .status-label {
                font-family: monospace;
                font-size: 13px;
                letter-spacing: 1px;
            }
            .blocking { color: #f85149; }
            .allowing { color: #ffffff; }
            .toggle-label {
                font-family: monospace;
                font-size: 13px;
                color: #8b949e;
                letter-spacing: 1px;
            }
            .version-label {
                font-family: monospace;
                font-size: 10px;
                color: #ffffff;
                letter-spacing: 2px;
            }
            .divider { background-color: #21262d; min-height: 1px; }
            switch { background-color: #21262d; border-color: #30363d; }
            switch:checked { background-color: #2ea043; border-color: #1a7f37; }
            switch.blocking-switch:checked { background-color: #f85149; border-color: #da3633; }
            switch slider { background-color: #c9d1d9; }
        """)

    def refresh_state(self):
        blocking = is_blocking()
        zone = get_current_zone()

        # Update shield color
        pixbuf = make_shield_pixbuf(blocking)
        self.shield_image.set_from_pixbuf(pixbuf)

        # Update switch CSS class to match state
        if blocking:
            self.switch.set_css_classes(["blocking-switch"])
        else:
            self.switch.set_css_classes([])

        self.switch.handler_block_by_func(self.on_switch_toggled)
        self.switch.set_active(blocking)
        self.switch.handler_unblock_by_func(self.on_switch_toggled)

        if blocking:
            self.status_label.set_label(f"[ BLOCKING ALL INCOMING ]  zone: {zone}")
            self.status_label.set_css_classes(["status-label", "blocking"])
        else:
            self.status_label.set_label(f"[ TRAFFIC ALLOWED ]  zone: {zone}")
            self.status_label.set_css_classes(["status-label", "allowing"])

        return False

    def on_switch_toggled(self, switch, state):
        self.switch.set_sensitive(False)
        self.spinner.start()

        def do_apply():
            zone = "block" if state else "public"
            ok, msg = apply_zone(zone)
            GLib.idle_add(self.apply_done, ok, msg)

        threading.Thread(target=do_apply, daemon=True).start()
        return True

    def apply_done(self, ok, msg):
        self.spinner.stop()
        self.switch.set_sensitive(True)
        if not ok:
            dialog = Gtk.AlertDialog()
            dialog.set_message("Failed to change firewall zone")
            dialog.set_detail(msg)
            dialog.show(self)
        self.refresh_state()
        return False


def main():
    app = FirewallToggleApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()