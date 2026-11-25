"""System: date & time, users, default applications, about this computer."""
import datetime
import os
import re
import platform
import pwd
import grp
import shutil
import time

from gi.repository import Adw, Gio, GLib, Gtk, Pango

from .common import action_row, button, group, page, read, root_helper, run, spawn


def system_proxy(name, path, iface):
    try:
        return Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
                                              name, path, iface, None)
    except GLib.Error:
        return None


def dbus_call(win, proxy, method, params, ok=None, done=None):
    """Interactive calls: polkit may ask for the password."""
    def finish(p, res):
        try:
            p.call_finish(res)
            if ok:
                win.toast(ok)
        except GLib.Error as e:
            win.toast(e.message.split(":")[-1].strip() or "That didn't work")
        if done:
            done()
    proxy.call(method, params, Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION, 120000, None, finish)


# ---- Date & time -------------------------------------------------------------
def datetime_page(win, conf):
    p = page("Date & time", "preferences-system-time-symbolic")
    td = system_proxy("org.freedesktop.timedate1", "/org/freedesktop/timedate1", "org.freedesktop.timedate1")
    g = group(p, "Now")
    now = action_row(time.strftime("%A %d %B %Y, %H:%M:%S"))
    now.add_css_class("property")
    g.add(now)

    def tick():
        now.set_title(time.strftime("%A %d %B %Y, %H:%M:%S"))
        return True
    src = GLib.timeout_add_seconds(1, tick)
    p.connect("destroy", lambda *_: GLib.source_remove(src))
    if td is None:
        g.add(action_row("Couldn't reach systemd-timedated"))
        return p

    def tdprop(name, default=None):
        v = td.get_cached_property(name)
        return v.unpack() if v is not None else default

    g = group(p, "Settings")
    ntp = Adw.SwitchRow(title="Set the time automatically", subtitle="From the internet (NTP)",
                        active=bool(tdprop("NTP")))
    ntp.set_sensitive(bool(tdprop("CanNTP", True)))
    ntp.connect("notify::active", lambda r, _: dbus_call(win, td, "SetNTP", GLib.Variant("(bb)", (r.get_active(), True)),
                                                         done=lambda: manual.set_sensitive(not r.get_active())))
    g.add(ntp)

    zones = [z for z in run("timedatectl", "list-timezones").stdout.split() if z]
    tz = Adw.ComboRow(title="Time zone", enable_search=True)
    tz.set_model(Gtk.StringList.new([z.replace("_", " ") for z in zones]))
    cur = tdprop("Timezone", "UTC")
    if cur in zones:
        tz.set_selected(zones.index(cur))
    tz.connect("notify::selected", lambda r, _: zones and zones[r.get_selected()] != tdprop("Timezone") and
               dbus_call(win, td, "SetTimezone", GLib.Variant("(sb)", (zones[r.get_selected()], True)),
                         ok=f"Time zone: {zones[r.get_selected()]}"))
    g.add(tz)

    manual = Adw.EntryRow(title="Set the time by hand (YYYY-MM-DD HH:MM)", show_apply_button=True)
    manual.set_text(time.strftime("%Y-%m-%d %H:%M"))
    manual.set_sensitive(not bool(tdprop("NTP")))

    def set_manual(r):
        try:
            t = datetime.datetime.strptime(r.get_text().strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            win.toast("Use the form 2026-11-23 14:05")
            return
        dbus_call(win, td, "SetTime", GLib.Variant("(xbb)", (int(t.timestamp() * 1_000_000), False, True)),
                  ok="Time set")
    manual.connect("apply", set_manual)
    g.add(manual)
    return p


# ---- Users -------------------------------------------------------------------
def users_page(win, conf):
    p = page("Users", "system-users-symbolic")
    me = pwd.getpwuid(os.getuid())
    def admins():
        try:
            return set(grp.getgrnam("wheel").gr_mem)
        except KeyError:
            return set()
    wheel = admins()
    g = group(p, "Your account")
    row = action_row(me.pw_gecos.split(",")[0] or me.pw_name, f"{me.pw_name} · " +
                     ("Administrator" if me.pw_name in wheel else "Standard user"))
    row.add_prefix(Gtk.Image(icon_name="avatar-default-symbolic", pixel_size=32))
    g.add(row)
    pw = action_row("Change password", "Opens a terminal running passwd", activatable=True)
    pw.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic"))
    pw.connect("activated", lambda *_: spawn("foot", "--title=Change password", "sh", "-c",
                                             "passwd; echo; read -r -p 'Press Enter to close. ' _"))
    g.add(pw)

    others = group(p, "Other users", suffix=button("Add…", css=(), on_click=lambda: add_user_dialog(win, refresh)))
    rows = []

    def refresh():
        for r in rows:
            others.remove(r)
        rows.clear()
        wheel_now = admins()
        users = [u for u in pwd.getpwall() if 1000 <= u.pw_uid < 60000 and u.pw_name != me.pw_name]
        for u in users:
            r = action_row(u.pw_gecos.split(",")[0] or u.pw_name,
                           f"{u.pw_name} · " + ("Administrator" if u.pw_name in wheel_now else "Standard user"))
            r.add_prefix(Gtk.Image(icon_name="avatar-default-symbolic", pixel_size=32))
            r.add_suffix(button(icon="user-trash-symbolic", tooltip="Remove this user and their files",
                                on_click=lambda u=u: remove_user(win, u.pw_name, refresh)))
            others.add(r)
            rows.append(r)
        if not users:
            r = action_row("No other users")
            others.add(r)
            rows.append(r)
    refresh()
    return p


def add_user_dialog(win, refresh):
    dialog = Adw.AlertDialog(heading="Add a user")
    box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
    box.add_css_class("boxed-list")
    name = Adw.EntryRow(title="Username (lowercase)")
    full = Adw.EntryRow(title="Full name")
    pw1 = Adw.PasswordEntryRow(title="Password")
    pw2 = Adw.PasswordEntryRow(title="Repeat password")
    admin = Adw.SwitchRow(title="Administrator", subtitle="Can use sudo")
    for r in (name, full, pw1, pw2, admin):
        box.append(r)
    dialog.set_extra_child(box)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("add", "Add")
    dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_close_response("cancel")

    def valid(*_):
        dialog.set_response_enabled("add", bool(re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", name.get_text()))
                                    and pw1.get_text() and pw1.get_text() == pw2.get_text())
    for r in (name, pw1, pw2):
        r.connect("changed", valid)
    valid()

    def response(d, r):
        if r != "add":
            return
        root_helper("adduser", name.get_text(), full.get_text() or name.get_text(), "1" if admin.get_active() else "0",
                    input=pw1.get_text() + "\n",
                    done=lambda res: (win.toast(f"Added {name.get_text()}" if res.returncode == 0 else
                                                (res.stderr.strip() or "Not added")), refresh()))
    dialog.connect("response", response)
    dialog.present(win)


def remove_user(win, username, refresh):
    dialog = Adw.AlertDialog(heading=f"Remove {username}?", body="Their account and home folder are deleted.")
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("remove", "Remove")
    dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_close_response("cancel")
    dialog.connect("response", lambda d, r: r == "remove" and root_helper(
        "deluser", username, done=lambda res: (win.toast(f"Removed {username}" if res.returncode == 0 else
                                                         (res.stderr.strip() or "Not removed")), refresh())))
    dialog.present(win)


# ---- Default applications ----------------------------------------------------
DEFAULTS = [
    ("Web browser", ["x-scheme-handler/http", "x-scheme-handler/https", "text/html"]),
    ("Email", ["x-scheme-handler/mailto"]),
    ("Files", ["inode/directory"]),
    ("Text", ["text/plain"]),
    ("Images", ["image/jpeg", "image/png", "image/gif", "image/webp"]),
    ("Video", ["video/mp4", "video/x-matroska", "video/webm"]),
    ("Music", ["audio/mpeg", "audio/flac", "audio/ogg", "audio/x-wav"]),
    ("PDF documents", ["application/pdf"]),
    ("Archives", ["application/zip", "application/x-tar", "application/x-7z-compressed"]),
]


def apps_page(win, conf):
    p = page("Default apps", "preferences-desktop-apps-symbolic")
    g = group(p, "Open with", "What opens links and files of each kind.")
    for title, mimes in DEFAULTS:
        current = Gio.AppInfo.get_default_for_type(mimes[0], False)
        apps, seen = [], set()
        for m in mimes:
            for a in Gio.AppInfo.get_all_for_type(m):
                # Hidden entries are skipped, except the current default: some
                # apps register their file types only on one (Zathura's backend).
                hidden = not a.should_show() and not (current and a.equal(current))
                if a.get_id() not in seen and not hidden:
                    seen.add(a.get_id())
                    apps.append(a)
        if not apps:
            continue
        row = Adw.ComboRow(title=title)
        row.set_model(Gtk.StringList.new([a.get_display_name() for a in apps]))
        ids = [a.get_id() for a in apps]
        if current and current.get_id() in ids:
            row.set_selected(ids.index(current.get_id()))

        def chosen(r, _, apps=apps, mimes=mimes, title=title):
            app = apps[r.get_selected()]
            try:
                for m in mimes:
                    app.set_as_default_for_type(m)
            except GLib.Error as e:
                win.toast(e.message)
        row.connect("notify::selected", chosen)
        g.add(row)
    return p


# ---- About -------------------------------------------------------------------
def about_page(win, conf):
    p = page("About", "help-about-symbolic")
    hn = system_proxy("org.freedesktop.hostname1", "/org/freedesktop/hostname1", "org.freedesktop.hostname1")
    g = group(p, "This computer")
    name = Adw.EntryRow(title="Computer name", show_apply_button=True)
    name.set_text(platform.node())

    def rename(r):
        new = r.get_text().strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", new):
            win.toast("Use lowercase letters, digits and hyphens")
            return
        if hn:
            dbus_call(win, hn, "SetStaticHostname", GLib.Variant("(sb)", (new, True)),
                      done=lambda: dbus_call(win, hn, "SetHostname", GLib.Variant("(sb)", (new, True)),
                                             ok=f"Renamed to {new}"))
    name.connect("apply", rename)
    g.add(name)

    vendor = read("/sys/class/dmi/id/sys_vendor")
    product = read("/sys/class/dmi/id/product_version") if vendor == "LENOVO" else read("/sys/class/dmi/id/product_name")
    cpu = next((l.split(":", 1)[1].strip() for l in read("/proc/cpuinfo").splitlines() if l.startswith("model name")), "")
    mem_kb = next((int(l.split()[1]) for l in read("/proc/meminfo").splitlines() if l.startswith("MemTotal")), 0)
    gpu = ""
    # lspci -mm: 00:02.0 "VGA compatible controller" "Intel Corporation" "HD Graphics 520" ...
    for line in run("lspci", "-mm").stdout.splitlines():
        q = line.split('"')
        if len(q) > 5 and q[1] in ("VGA compatible controller", "Display controller", "3D controller"):
            gpu = f"{q[3]} {q[5]}".replace(" Corporation", "")
            break
    disk = shutil.disk_usage("/")
    osname = next((l.split("=", 1)[1].strip('"') for l in read("/etc/os-release").splitlines()
                   if l.startswith("PRETTY_NAME=")), "Linux")
    up = int(float(read("/proc/uptime", "0").split()[0]))
    facts = [
        ("Model", " ".join(x for x in (vendor, product) if x) or "Unknown"),
        ("Processor", cpu or platform.processor() or "Unknown"),
        ("Memory", f"{mem_kb / 1024 / 1024:.1f} GiB"),
        ("Graphics", gpu or "Unknown"),
        ("Disk", f"{disk.used / 1e9:.0f} GB used of {disk.total / 1e9:.0f} GB"),
    ]
    for k, v in facts:
        g.add(fact(k, v))
    g = group(p, "Software")
    for k, v in (("System", osname), ("Desktop", win.flavour or "unknown"), ("Kernel", platform.release()),
                 ("Up for", f"{up // 86400} d {up % 86400 // 3600} h {up % 3600 // 60} min" if up >= 86400
                  else f"{up // 3600} h {up % 3600 // 60} min")):
        g.add(fact(k, v))
    return p


def fact(k, v):
    row = Adw.ActionRow(title=k)
    lbl = Gtk.Label(label=v, selectable=True, xalign=1, ellipsize=Pango.EllipsizeMode.END)
    lbl.add_css_class("dim-label")
    row.add_suffix(lbl)
    return row
