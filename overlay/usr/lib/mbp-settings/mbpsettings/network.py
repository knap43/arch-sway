"""Network: Wi-Fi (on/off, networks, connect, forget), wired, VPN, through
NetworkManager's libnm. Rare things (enterprise Wi-Fi, static addresses, new
VPNs) go to nm-connection-editor."""
import uuid

import gi

gi.require_version("NM", "1.0")
from gi.repository import Adw, GLib, Gtk, NM  # noqa: E402

from .common import action_row, button, group, page, status, tool_row  # noqa: E402

APF = getattr(NM, "80211ApFlags")
SEC = getattr(NM, "80211ApSecurityFlags")


def ssid_of(ap):
    b = ap.get_ssid()
    return b.get_data().decode("utf-8", "replace") if b else ""


def security(ap):
    """'open', 'psk', 'sae' or 'enterprise'."""
    flags = ap.get_wpa_flags() | ap.get_rsn_flags()
    if flags & SEC.KEY_MGMT_802_1X:
        return "enterprise"
    if flags & SEC.KEY_MGMT_SAE and not flags & SEC.KEY_MGMT_PSK:
        return "sae"
    if flags & SEC.KEY_MGMT_PSK or ap.get_flags() & APF.PRIVACY:
        return "psk"
    return "open"


def signal_icon(strength):
    for limit, name in ((75, "excellent"), (50, "good"), (25, "ok"), (0, "weak")):
        if strength >= limit:
            return f"network-wireless-signal-{name}-symbolic"
    return "network-wireless-signal-none-symbolic"


class NetworkPage:
    def __init__(self, win, conf):
        self.win = win
        self.page = page("Network", "network-wireless-symbolic")
        self.rebuild_source = 0
        try:
            self.client = NM.Client.new(None)
        except GLib.Error:
            self.client = None
        if not self.client or not self.client.get_nm_running():
            status(self.page, "network-offline-symbolic", "NetworkManager isn't running",
                   "Start it with: sudo systemctl enable --now NetworkManager")
            return

        self.wifi_switch = Gtk.Switch(valign=Gtk.Align.CENTER, active=self.client.wireless_get_enabled())
        self.wifi_switch.connect("notify::active", self.toggle_wifi)
        refresh = button(icon="view-refresh-symbolic", tooltip="Look for networks", on_click=self.scan)
        box = Gtk.Box(spacing=6)
        box.append(refresh)
        box.append(self.wifi_switch)
        self.wifi_group = group(self.page, "Wi-Fi", suffix=box)
        self.wired_group = group(self.page, "Wired")
        self.vpn_group = group(self.page, "VPN")
        adv = group(self.page, "Advanced")
        adv.add(tool_row("All connections", "Static addresses, enterprise Wi-Fi, new VPNs, hotspots…",
                         ["nm-connection-editor"]))
        self.rows = {self.wifi_group: [], self.wired_group: [], self.vpn_group: []}

        for sig in ("notify::active-connections", "connection-added", "connection-removed",
                    "notify::wireless-enabled", "device-added", "device-removed"):
            self.client.connect(sig, lambda *_: self.queue_rebuild())
        for dev in self.client.get_devices():
            self.watch(dev)
        self.client.connect("device-added", lambda c, d: self.watch(d))
        self.rebuild()
        self.scan()

    def watch(self, dev):
        dev.connect("notify::state", lambda *_: self.queue_rebuild())
        if isinstance(dev, NM.DeviceWifi):
            dev.connect("access-point-added", lambda *_: self.queue_rebuild())
            dev.connect("access-point-removed", lambda *_: self.queue_rebuild())

    def queue_rebuild(self):
        if not self.rebuild_source:
            self.rebuild_source = GLib.timeout_add(300, self.rebuild)

    # -- devices ---------------------------------------------------------------
    def wifi_devices(self):
        return [d for d in self.client.get_devices() if isinstance(d, NM.DeviceWifi)]

    def scan(self):
        for d in self.wifi_devices():
            d.request_scan_async(None, lambda dev, res: self._finish(dev.request_scan_finish, res, quiet=True))

    def toggle_wifi(self, sw, _):
        on = sw.get_active()
        if on == self.client.wireless_get_enabled():
            return
        self.client.dbus_set_property(NM.DBUS_PATH, NM.DBUS_INTERFACE, "WirelessEnabled",
                                      GLib.Variant("b", on), -1, None,
                                      lambda c, res: self._finish(c.dbus_set_property_finish, res))

    def _finish(self, fn, res, quiet=False, ok=None):
        try:
            fn(res)
            if ok:
                self.win.toast(ok)
        except GLib.Error as e:
            if not quiet:
                self.win.toast(e.message.split(":")[-1].strip() or "That didn't work")
        self.queue_rebuild()

    # -- the lists -----------------------------------------------------------------
    def clear(self, g):
        for r in self.rows[g]:
            g.remove(r)
        self.rows[g] = []

    def add(self, g, row):
        g.add(row)
        self.rows[g].append(row)

    def rebuild(self):
        self.rebuild_source = 0
        self.wifi_switch.set_active(self.client.wireless_get_enabled())
        saved = {}
        for c in self.client.get_connections():
            sw = c.get_setting_wireless()
            if sw and sw.get_ssid():
                saved[sw.get_ssid().get_data().decode("utf-8", "replace")] = c

        # Wi-Fi
        self.clear(self.wifi_group)
        devs = self.wifi_devices()
        if not devs:
            self.add(self.wifi_group, action_row("No Wi-Fi adapter found"))
        elif not self.client.wireless_get_enabled():
            self.add(self.wifi_group, action_row("Wi-Fi is off"))
        else:
            dev = devs[0]
            active_ap = dev.get_active_access_point()
            active_ssid = ssid_of(active_ap) if active_ap else None
            best = {}
            for ap in dev.get_access_points():
                s = ssid_of(ap)
                if s and (s not in best or ap.get_strength() > best[s].get_strength()):
                    best[s] = ap
            order = sorted(best.values(), key=lambda a: (ssid_of(a) != active_ssid, ssid_of(a) not in saved,
                                                         -a.get_strength()))
            for ap in order[:30]:
                self.add(self.wifi_group, self.ap_row(dev, ap, ssid_of(ap) == active_ssid, saved.get(ssid_of(ap))))
            if not order:
                self.add(self.wifi_group, action_row("Looking for networks…"))
            for s, c in sorted(saved.items()):
                if s not in best:
                    self.add(self.wifi_group, self.saved_row(s, c))

        # wired
        self.clear(self.wired_group)
        eth = [d for d in self.client.get_devices() if isinstance(d, NM.DeviceEthernet)]
        for d in eth:
            st = d.get_state()
            text = ("Connected" + (f" · {d.get_speed()} Mb/s" if d.get_speed() else "")
                    if st == NM.DeviceState.ACTIVATED else
                    "Cable unplugged" if st == NM.DeviceState.UNAVAILABLE else
                    "Connecting…" if NM.DeviceState.PREPARE <= st < NM.DeviceState.ACTIVATED else "Disconnected")
            row = action_row(d.get_iface(), text)
            row.add_prefix(Gtk.Image(icon_name="network-wired-symbolic"))
            self.add(self.wired_group, row)
        self.wired_group.set_visible(bool(eth))

        # VPN / WireGuard
        self.clear(self.vpn_group)
        active = {a.get_uuid(): a for a in self.client.get_active_connections()}
        vpns = [c for c in self.client.get_connections()
                if c.get_connection_type() in (NM.SETTING_VPN_SETTING_NAME, NM.SETTING_WIREGUARD_SETTING_NAME)]
        for c in vpns:
            row = Adw.SwitchRow(title=GLib.markup_escape_text(c.get_id()), active=c.get_uuid() in active)
            row.connect("notify::active", lambda r, _, c=c: self.toggle_vpn(c, r.get_active(), active.get(c.get_uuid())))
            self.add(self.vpn_group, row)
        if not vpns:
            self.add(self.vpn_group, action_row("No VPNs", "Add one under Advanced → All connections"))
        return False

    def ap_row(self, dev, ap, is_active, conn):
        sec = security(ap)
        sub = "Connected" if is_active else ("Saved" if conn else
                                             {"open": "Open", "enterprise": "Enterprise (set up in All connections)"}.get(sec, "Secured"))
        row = action_row(ssid_of(ap), sub, activatable=not is_active)
        row.add_prefix(Gtk.Image(icon_name=signal_icon(ap.get_strength())))
        if sec != "open":
            row.add_suffix(Gtk.Image(icon_name="channel-secure-symbolic", tooltip_text="Secured"))
        if is_active:
            ac = dev.get_active_connection()
            row.add_suffix(button("Disconnect", css=(), on_click=lambda: self.client.deactivate_connection_async(
                ac, None, lambda c, res: self._finish(c.deactivate_connection_finish, res))))
        if conn:
            row.add_suffix(button(icon="user-trash-symbolic", tooltip="Forget this network",
                                  on_click=lambda: self.forget(conn)))
        if not is_active:
            row.connect("activated", lambda *_: self.connect_ap(dev, ap, conn, sec))
        return row

    def saved_row(self, ssid, conn):
        row = action_row(ssid, "Saved · out of range")
        row.add_prefix(Gtk.Image(icon_name="network-wireless-offline-symbolic"))
        row.add_suffix(button(icon="user-trash-symbolic", tooltip="Forget this network",
                              on_click=lambda: self.forget(conn)))
        return row

    # -- actions ---------------------------------------------------------------------
    def connect_ap(self, dev, ap, conn, sec):
        if conn:
            self.client.activate_connection_async(conn, dev, ap.get_path(), None,
                                                  lambda c, res: self._finish(c.activate_connection_finish, res))
            return
        if sec == "enterprise":
            self.win.toast("Enterprise networks are set up in Advanced → All connections")
            return
        if sec == "open":
            self.add_and_activate(dev, ap, sec, None)
            return
        self.ask_password(ssid_of(ap), lambda pw: self.add_and_activate(dev, ap, sec, pw))

    def ask_password(self, ssid, then):
        dialog = Adw.AlertDialog(heading=f"Connect to “{ssid}”", body="Enter the network's password.")
        entry = Gtk.PasswordEntry(show_peek_icon=True, activates_default=True)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("connect", "Connect")
        dialog.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("connect")
        dialog.set_close_response("cancel")
        dialog.set_response_enabled("connect", False)
        entry.connect("changed", lambda e: dialog.set_response_enabled("connect", len(e.get_text()) >= 8))
        dialog.connect("response", lambda d, r: r == "connect" and then(entry.get_text()))
        dialog.present(self.win)
        entry.grab_focus()

    def add_and_activate(self, dev, ap, sec, password):
        ssid = ssid_of(ap)
        conn = NM.SimpleConnection.new()
        s_con = NM.SettingConnection()
        s_con.set_property("id", ssid)
        s_con.set_property("uuid", str(uuid.uuid4()))
        s_con.set_property("type", NM.SETTING_WIRELESS_SETTING_NAME)
        s_con.set_property("autoconnect", True)
        conn.add_setting(s_con)
        s_wifi = NM.SettingWireless()
        s_wifi.set_property("ssid", GLib.Bytes.new(ssid.encode()))
        s_wifi.set_property("mode", "infrastructure")
        conn.add_setting(s_wifi)
        if sec in ("psk", "sae"):
            s_sec = NM.SettingWirelessSecurity()
            s_sec.set_property("key-mgmt", "sae" if sec == "sae" else "wpa-psk")
            s_sec.set_property("psk", password)
            conn.add_setting(s_sec)
        for cls in (NM.SettingIP4Config, NM.SettingIP6Config):
            s = cls()
            s.set_property("method", "auto")
            conn.add_setting(s)
        self.client.add_and_activate_connection_async(
            conn, dev, ap.get_path(), None,
            lambda c, res: self._finish(c.add_and_activate_connection_finish, res, ok=f"Connecting to {ssid}…"))

    def forget(self, conn):
        name = conn.get_id()
        conn.delete_async(None, lambda c, res: self._finish(c.delete_finish, res, ok=f"Forgot {name}"))

    def toggle_vpn(self, conn, on, active):
        if on and not active:
            self.client.activate_connection_async(conn, None, None, None,
                                                  lambda c, res: self._finish(c.activate_connection_finish, res))
        elif not on and active:
            self.client.deactivate_connection_async(active, None,
                                                    lambda c, res: self._finish(c.deactivate_connection_finish, res))


def network(win, conf):
    return NetworkPage(win, conf).page
