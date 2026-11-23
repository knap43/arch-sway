"""Pages backed by the desktop settings: keyboard, mouse, appearance, windows,
notifications."""
import glob
import os

from gi.repository import Adw, Gio, GLib, Gtk

from .common import (action_row, button, combo_row, entry_row, group, page, run,
                     scale_row, spawn, spin_row, switch_row)

FX_NOTE = "Hyprland and Mango only; sway has no such effects."


# ---- Keyboard ----------------------------------------------------------------
def keyboard(win, conf):
    p = page("Keyboard", "input-keyboard-symbolic")
    g = group(p, "Layouts", "The key just left of ⌘ plus Shift switches between them: "
                            "Win + Shift on a PC keyboard, Option + Shift on a Mac.")
    g.add(entry_row(conf, "LAYOUTS", "Layouts (comma-separated, e.g. us,ru)"))

    g = group(p, "Keys")
    g.add(combo_row(conf, "SWAP_ALT_WIN", {"auto": "Automatic", "on": "Always", "off": "Never"},
                    subtitle="Puts ⌘ (Super) next to the space bar. Automatic: on PC keyboards, not on a Mac."))
    g.add(switch_row(conf, "SWAP_CAPS_ESC"))

    g = group(p, "Key repeat")
    g.add(spin_row(conf, "REPEAT_DELAY", "Delay before repeating (ms)", step=25))
    g.add(spin_row(conf, "REPEAT_RATE", "Repeats per second"))
    g.add(Adw.EntryRow(title="Type here to try the repeat"))

    g = group(p, "Shortcuts")
    row = action_row("Keyboard shortcuts", "Every shortcut for this desktop (also ⌘K anywhere)", activatable=True)
    row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
    row.connect("activated", lambda *_: spawn("mbp-shortcuts", "--toggle"))
    g.add(row)
    return p


# ---- Mouse & touchpad --------------------------------------------------------
def mouse(win, conf):
    p = page("Mouse & touchpad", "input-mouse-symbolic")
    g = group(p, "Pointer")
    g.add(scale_row(conf, "POINTER_SPEED", "Speed", "Slower to the left, faster to the right",
                    marks=((0, None),)))
    g.add(switch_row(conf, "LEFT_HANDED", "Left-handed", "Swap the left and right buttons"))
    g.add(switch_row(conf, "FOCUS_FOLLOWS_MOUSE", "Focus follows the mouse",
                     "Windows take the keyboard when the pointer moves over them"))
    g.add(spin_row(conf, "HIDE_CURSOR_SEC", "Hide the pointer when idle", "After this many seconds; 0 never hides it"))
    g.add(switch_row(conf, "HIDE_CURSOR_TYPING", "Hide the pointer while typing", "It comes back when the mouse moves"))
    g = group(p, "Touchpad")
    g.add(switch_row(conf, "TAP_TO_CLICK", "Tap to click"))
    g.add(switch_row(conf, "NATURAL_SCROLL", "Natural scrolling", "Content moves with your fingers"))
    g.add(switch_row(conf, "DISABLE_WHILE_TYPING", "Ignore while typing"))
    g.add(switch_row(conf, "SWIPE_WORKSPACES", "Swipe between workspaces",
                     "Three fingers left or right"))
    return p


# ---- Appearance --------------------------------------------------------------
ACCENT_HEX = {"blue": "5e81ac", "teal": "88c0d0", "green": "a3be8c", "yellow": "ebcb8b",
              "orange": "d08770", "red": "bf616a", "purple": "b48ead", "grey": "6b6b6b"}


def appearance(win, conf):
    p = page("Appearance", "preferences-desktop-appearance-symbolic")

    g = group(p, "Style")
    g.add(combo_row(conf, "THEME", {"dark": "Dark", "light": "Light"}, "Applications",
                    "GTK applications; the desktop itself stays dark"))
    g.add(combo_row(conf, "TEXT_SCALE", {"0.9": "Smaller", "1": "Normal", "1.1": "Larger",
                                         "1.25": "Large", "1.5": "Largest"}, "Text size",
                    "GTK applications"))
    g.add(accent_row(win, conf))

    g = group(p, "Wallpaper")
    g.add(wallpaper_chooser(win, conf))

    g = group(p, "Windows")
    g.add(spin_row(conf, "BORDER_WIDTH", "Border width (px)"))
    g.add(spin_row(conf, "GAPS_INNER", "Gaps between windows (px)"))
    g.add(spin_row(conf, "GAPS_OUTER", "Gaps at the screen edges (px)"))

    g = group(p, "Effects", FX_NOTE + " They cost GPU time on older laptops.")
    g.add(spin_row(conf, "ROUNDING", "Rounded corners (px)"))
    g.add(switch_row(conf, "ANIMATIONS", "Animations", "Windows only; menus and the launcher appear at once"))
    g.add(switch_row(conf, "SHADOWS", "Shadows", " "))
    g.add(switch_row(conf, "BLUR", "Blur", "Behind see-through windows"))
    g.add(combo_row(conf, "INACTIVE_OPACITY", {"1": "Opaque", "0.95": "95%", "0.9": "90%",
                                               "0.85": "85%", "0.8": "80%"},
                    "Unfocused windows", " "))
    return p


def accent_row(win, conf):
    row = Adw.ActionRow(title="Accent colour")
    row.set_subtitle("Focused borders, the active tab, the bar's current workspace")
    box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
    buttons = {}
    for name, hexv in ACCENT_HEX.items():
        b = Gtk.ToggleButton()
        b.set_tooltip_text(name.capitalize())
        b.add_css_class("accent-swatch")
        b.add_css_class(f"swatch-{name}")
        b.set_size_request(26, 26)
        buttons[name] = b
        box.append(b)
    first = None
    for name, b in buttons.items():
        if first:
            b.set_group(first)
        first = first or b
        b.set_active(conf.get("ACCENT") == name)
        b.connect("toggled", lambda btn, n=name: btn.get_active() and (conf.set("ACCENT", n), win.set_accent(n)))
    row.add_suffix(box)
    return row


def wallpapers():
    found = []
    for pattern in ("/usr/share/backgrounds/**/*", os.path.expanduser("~/Pictures/**/*")):
        found += [f for f in glob.glob(pattern, recursive=True)
                  if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    return sorted(set(found))[:60]


def wallpaper_chooser(win, conf):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.SINGLE, max_children_per_line=4,
                       min_children_per_line=2, column_spacing=8, row_spacing=8, homogeneous=True)
    flow.add_css_class("wallpapers")
    current = conf.get("WALLPAPER")
    paths = wallpapers()
    if current and current not in paths and os.path.exists(current):
        paths.insert(0, current)
    for path in paths:
        pic = Gtk.Picture.new_for_filename(path)
        pic.set_content_fit(Gtk.ContentFit.COVER)
        pic.set_size_request(150, 94)
        pic.set_tooltip_text(os.path.basename(path))
        child = Gtk.FlowBoxChild(child=pic)
        child.path = path
        flow.append(child)
        if path == current:
            flow.select_child(child)
    flow.connect("child-activated", lambda f, c: conf.set("WALLPAPER", c.path))
    box.append(flow)

    def choose():
        dialog = Gtk.FileDialog(title="Choose a wallpaper")
        filt = Gtk.FileFilter()
        filt.set_name("Images")
        for pat in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.PNG"):
            filt.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filt)
        dialog.set_filters(filters)

        def done(d, res):
            try:
                f = d.open_finish(res)
            except GLib.Error:
                return
            if f and f.get_path() and conf.set("WALLPAPER", f.get_path()):
                pic = Gtk.Picture.new_for_filename(f.get_path())
                pic.set_content_fit(Gtk.ContentFit.COVER)
                pic.set_size_request(150, 94)
                child = Gtk.FlowBoxChild(child=pic)
                child.path = f.get_path()
                flow.insert(child, 0)
                flow.select_child(child)
        dialog.open(win, None, done)
    box.append(button("Choose an image…", css=(), on_click=choose))
    box.set_margin_top(6)
    box.set_margin_bottom(6)
    group_box = Adw.PreferencesRow(activatable=False)
    group_box.set_child(box)
    return group_box


# ---- Windows -----------------------------------------------------------------
def windows(win, conf):
    p = page("Windows", "view-grid-symbolic")
    g = group(p, "Layout", "⌘ Tab switches the current workspace between tabbed and tiled.")
    g.add(combo_row(conf, "DEFAULT_LAYOUT", {"tabbed": "Tabbed", "tiled": "Tiled"}, "New workspaces open"))
    return p


# ---- Notifications -----------------------------------------------------------
def notifications(win, conf):
    p = page("Notifications", "preferences-system-notifications-symbolic")
    g = group(p, "Notifications")
    dnd = Adw.SwitchRow(title="Do not disturb", subtitle="Hide notifications until you turn this off")
    modes = run("makoctl", "mode").stdout.split()
    dnd.set_active("do-not-disturb" in modes)

    def toggle(r, _):
        r2 = run("makoctl", "mode", "-a" if r.get_active() else "-r", "do-not-disturb")
        if r2.returncode != 0:
            win.toast("Couldn't reach the notification daemon (mako)")
    dnd.connect("notify::active", toggle)
    g.add(dnd)
    g.add(spin_row(conf, "NOTIFY_TIMEOUT", "Hide after (seconds)", "0 keeps them until clicked"))
    g.add(combo_row(conf, "NOTIFY_POSITION", {
        "top-right": "Top right", "top-center": "Top centre", "top-left": "Top left",
        "bottom-right": "Bottom right", "bottom-center": "Bottom centre", "bottom-left": "Bottom left"},
        "Position"))
    row = action_row("Show the last notification again", activatable=True)
    row.connect("activated", lambda *_: run("makoctl", "restore"))
    g.add(row)
    test = action_row("Send a test notification", activatable=True)
    test.connect("activated", lambda *_: spawn("notify-send", "Desktop settings", "This is what notifications look like."))
    g.add(test)
    return p
