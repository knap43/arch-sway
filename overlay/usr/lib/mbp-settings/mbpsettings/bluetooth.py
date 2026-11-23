"""Bluetooth: power, scanning, pairing, connecting and removing devices, over
BlueZ's D-Bus API. PIN and passkey prompts come from blueman-applet's agent
(started with the session); the full manager is blueman-manager."""
from gi.repository import Gio, GLib, Gtk

from .common import action_row, button, group, page, status, tool_row

BLUEZ = "org.bluez"
ADAPTER = "org.bluez.Adapter1"
DEVICE = "org.bluez.Device1"


def prop(proxy, name, default=None):
    v = proxy.get_cached_property(name)
    return v.unpack() if v is not None else default


class BluetoothPage:
    def __init__(self, win, conf):
        self.win = win
        self.page = page("Bluetooth", "bluetooth-symbolic")
        self.rebuild_source = 0
        self.scanning = False
        try:
            self.manager = Gio.DBusObjectManagerClient.new_for_bus_sync(
                Gio.BusType.SYSTEM, Gio.DBusObjectManagerClientFlags.NONE, BLUEZ, "/", None, None, None)
        except GLib.Error:
            self.manager = None
        if self.manager is None or self.manager.get_name_owner() is None:
            status(self.page, "bluetooth-disabled-symbolic", "Bluetooth isn't available",
                   "The Bluetooth service isn't running: sudo systemctl enable --now bluetooth")
            return
        self.power = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.power.connect("notify::active", self.toggle_power)
        self.scan_button = button("Search", css=(), on_click=self.toggle_scan)
        box = Gtk.Box(spacing=6)
        box.append(self.scan_button)
        box.append(self.power)
        self.devices_group = group(self.page, "Devices", suffix=box)
        self.nearby_group = group(self.page, "Nearby", "Put the device in pairing mode, then click it.")
        adv = group(self.page, "Advanced")
        adv.add(tool_row("Bluetooth manager", "File transfer, audio profiles, every option", ["blueman-manager"]))
        self.rows = {self.devices_group: [], self.nearby_group: []}
        for sig in ("object-added", "object-removed", "interface-proxy-properties-changed"):
            self.manager.connect(sig, lambda *_: self.queue_rebuild())
        self.rebuild()

    # -- helpers -----------------------------------------------------------------
    def adapter(self):
        for obj in self.manager.get_objects():
            iface = obj.get_interface(ADAPTER)
            if iface:
                return iface
        return None

    def devices(self):
        return [obj.get_interface(DEVICE) for obj in self.manager.get_objects() if obj.get_interface(DEVICE)]

    def call(self, proxy, method, params=None, timeout=30000, ok=None):
        proxy.call(method, params, Gio.DBusCallFlags.NONE, timeout, None,
                   lambda p, res: self._done(p, res, ok))

    def _done(self, proxy, res, ok):
        try:
            proxy.call_finish(res)
            if ok:
                self.win.toast(ok)
        except GLib.Error as e:
            msg = Gio.DBusError.get_remote_error(e) or ""
            self.win.toast({"org.bluez.Error.AuthenticationFailed": "Pairing failed: wrong code or cancelled",
                            "org.bluez.Error.AuthenticationCanceled": "Pairing cancelled",
                            "org.bluez.Error.Failed": "The device didn't respond",
                            "org.bluez.Error.Blocked": "Bluetooth is blocked (airplane mode / rfkill)",
                            }.get(msg, e.message.split(":")[-1].strip()))
        self.queue_rebuild()

    def set_prop(self, proxy, name, value, ok=None):
        props = Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None, BLUEZ,
                                               proxy.get_object_path(), "org.freedesktop.DBus.Properties", None)
        self.call(props, "Set", GLib.Variant("(ssv)", (proxy.get_interface_name(), name, value)), ok=ok)

    def queue_rebuild(self):
        if not self.rebuild_source:
            self.rebuild_source = GLib.timeout_add(250, self.rebuild)

    # -- actions ---------------------------------------------------------------------
    def toggle_power(self, sw, _):
        a = self.adapter()
        if a and bool(prop(a, "Powered")) != sw.get_active():
            self.set_prop(a, "Powered", GLib.Variant("b", sw.get_active()))

    def toggle_scan(self):
        a = self.adapter()
        if not a:
            return
        self.call(a, "StopDiscovery" if prop(a, "Discovering") else "StartDiscovery")

    def activate_device(self, d):
        name = prop(d, "Alias") or prop(d, "Name") or prop(d, "Address")
        if prop(d, "Connected"):
            self.call(d, "Disconnect", ok=f"Disconnected {name}")
        elif prop(d, "Paired"):
            self.call(d, "Connect", ok=f"Connected {name}")
        else:
            self.win.toast(f"Pairing with {name}… confirm on the device if it asks")
            d.call("Pair", None, Gio.DBusCallFlags.NONE, 60000, None, lambda p, res: self.paired(p, res, name))

    def paired(self, d, res, name):
        try:
            d.call_finish(res)
        except GLib.Error as e:
            self._done_error(e)
            return
        self.set_prop(d, "Trusted", GLib.Variant("b", True))
        self.call(d, "Connect", ok=f"Paired and connected {name}")

    def _done_error(self, e):
        self.win.toast("Pairing failed: " + e.message.split(":")[-1].strip())
        self.queue_rebuild()

    def remove(self, d):
        a = self.adapter()
        if a:
            self.call(a, "RemoveDevice", GLib.Variant("(o)", (d.get_object_path(),)),
                      ok=f"Removed {prop(d, 'Alias') or prop(d, 'Address')}")

    # -- the lists -----------------------------------------------------------------
    def rebuild(self):
        self.rebuild_source = 0
        for g in self.rows:
            for r in self.rows[g]:
                g.remove(r)
            self.rows[g] = []
        a = self.adapter()
        if not a:
            self.power.set_sensitive(False)
            self.scan_button.set_sensitive(False)
            self._add(self.devices_group, action_row("No Bluetooth adapter found"))
            self.nearby_group.set_visible(False)
            return False
        powered = bool(prop(a, "Powered"))
        self.power.set_active(powered)
        self.scan_button.set_sensitive(powered)
        self.scan_button.set_label("Stop" if prop(a, "Discovering") else "Search")
        if not powered:
            self._add(self.devices_group, action_row("Bluetooth is off"))
            self.nearby_group.set_visible(False)
            return False
        paired = [d for d in self.devices() if prop(d, "Paired")]
        nearby = [d for d in self.devices() if not prop(d, "Paired") and (prop(d, "Name") or prop(d, "Alias"))]
        for d in sorted(paired, key=lambda d: (not prop(d, "Connected"), (prop(d, "Alias") or "").lower())):
            self._add(self.devices_group, self.device_row(d))
        if not paired:
            self._add(self.devices_group, action_row("No paired devices", "Click Search to find some"))
        self.nearby_group.set_visible(bool(nearby) or bool(prop(a, "Discovering")))
        for d in sorted(nearby, key=lambda d: -(prop(d, "RSSI") or -200)):
            self._add(self.nearby_group, self.device_row(d))
        if not nearby and prop(a, "Discovering"):
            self._add(self.nearby_group, action_row("Searching…"))
        return False

    def _add(self, g, row):
        g.add(row)
        self.rows[g].append(row)

    def device_row(self, d):
        name = prop(d, "Alias") or prop(d, "Name") or prop(d, "Address")
        if prop(d, "Connected"):
            sub = "Connected"
            battery = None
            obj = self.manager.get_object(d.get_object_path())
            bat = obj.get_interface("org.bluez.Battery1") if obj else None
            if bat:
                battery = prop(bat, "Percentage")
            if battery is not None:
                sub += f" · battery {battery}%"
        else:
            sub = "Not connected" if prop(d, "Paired") else "Click to pair"
        row = action_row(name, sub, activatable=True)
        row.add_prefix(Gtk.Image(icon_name=(prop(d, "Icon") or "bluetooth") + "-symbolic"))
        if prop(d, "Paired"):
            row.add_suffix(button(icon="user-trash-symbolic", tooltip="Remove this device",
                                  on_click=lambda: self.remove(d)))
        row.connect("activated", lambda *_: self.activate_device(d))
        return row


def bluetooth(win, conf):
    return BluetoothPage(win, conf).page
