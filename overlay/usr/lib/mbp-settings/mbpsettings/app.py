"""The Settings window: a sidebar of panels, built when first opened."""
import sys
import traceback

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .common import Conf, compositor
from . import bluetooth, desktop, displays, network, power, shortcuts, sound, system

APP_ID = "org.mbp.Settings"
ACCENTS = {"blue": ("#5e81ac", "#ffffff"), "teal": ("#88c0d0", "#1e1e1e"), "green": ("#a3be8c", "#1e1e1e"),
           "yellow": ("#ebcb8b", "#1e1e1e"), "orange": ("#d08770", "#1e1e1e"), "red": ("#bf616a", "#ffffff"),
           "purple": ("#b48ead", "#1e1e1e"), "grey": ("#6b6b6b", "#ffffff")}

# id, title, icon, builder(win, conf) -> Adw.PreferencesPage
PANELS = [
    ("network", "Network", "network-wireless-symbolic", network.network),
    ("bluetooth", "Bluetooth", "bluetooth-symbolic", bluetooth.bluetooth),
    ("sound", "Sound", "audio-speakers-symbolic", sound.sound),
    ("displays", "Displays", "video-display-symbolic", displays.displays),
    ("keyboard", "Keyboard", "input-keyboard-symbolic", desktop.keyboard),
    ("mouse", "Mouse & touchpad", "input-mouse-symbolic", desktop.mouse),
    ("appearance", "Appearance", "preferences-desktop-appearance-symbolic", desktop.appearance),
    ("windows", "Windows", "view-grid-symbolic", desktop.windows),
    ("notifications", "Notifications", "preferences-system-notifications-symbolic", desktop.notifications),
    ("power", "Power", "battery-symbolic", power.power),
    ("datetime", "Date & time", "preferences-system-time-symbolic", system.datetime_page),
    ("users", "Users", "system-users-symbolic", system.users_page),
    ("apps", "Default apps", "preferences-desktop-apps-symbolic", system.apps_page),
    ("about", "About", "help-about-symbolic", system.about_page),
]

# The desktop's look: flat, square corners, dark greys and the accent colour.
BASE_CSS = """
* { border-radius: 0; }
window, .background, .view, preferencespage, scrolledwindow { background-color: @window_bg_color; }
headerbar { background-color: #2a2a2a; box-shadow: none; border-bottom: 1px solid #333333; min-height: 38px; }
.navigation-sidebar { background-color: #232323; padding: 6px 0; }
.navigation-sidebar row { padding: 8px 12px; margin: 0; }
.navigation-sidebar row:selected { background-color: @accent_bg_color; color: @accent_fg_color; }
.navigation-sidebar row:selected image { color: @accent_fg_color; }
.boxed-list, list.boxed-list, .card { background-color: #2a2a2a; box-shadow: none; border: 1px solid #333333; }
row.activatable:hover { background-color: #303030; }
row separator, list.boxed-list > row { border-color: #333333; }
button { box-shadow: none; }
button:not(.flat) { background-color: #3b3b3b; }
button.suggested-action { background-color: @accent_bg_color; color: @accent_fg_color; }
switch { border-radius: 0; }
switch slider { border-radius: 0; }
scale trough, scale highlight, scale slider { border-radius: 0; }
toast { border-radius: 0; background-color: #2a2a2a; border: 1px solid @accent_bg_color; }
dialog-host > dialog, dialog .dialog-contents, window.dialog, alertdialog sheet, sheet { border-radius: 0; }
popover contents, popover > arrow { border-radius: 0; }
button.accent-swatch { min-width: 22px; min-height: 22px; padding: 0; border: 2px solid transparent; }
button.accent-swatch:checked { border-color: @window_fg_color; }
""" + "".join(f"button.accent-swatch.swatch-{n}, button.accent-swatch.swatch-{n}:checked, "
              f"button.accent-swatch.swatch-{n}:hover {{ background: {c}; background-image: none; }}\n"
              for n, (c, _) in ACCENTS.items()) + """
.wallpapers flowboxchild { padding: 2px; border: 2px solid transparent; }
.wallpapers flowboxchild:selected { border-color: @accent_bg_color; background: none; }
"""
DARK_COLOURS = """
@define-color window_bg_color #1e1e1e;
@define-color window_fg_color #dddddd;
@define-color view_bg_color #1e1e1e;
@define-color view_fg_color #dddddd;
@define-color headerbar_bg_color #2a2a2a;
@define-color headerbar_fg_color #dddddd;
@define-color sidebar_bg_color #232323;
@define-color card_bg_color #2a2a2a;
@define-color popover_bg_color #2a2a2a;
@define-color dialog_bg_color #2a2a2a;
"""


_accent_provider = Gtk.CssProvider()


def install_style():
    """The desktop's look for every window of the app (Settings and the cheat sheet)."""
    from .common import run
    theme = run("mbp-conf", "get", "THEME").stdout.strip() or "dark"
    accent = run("mbp-conf", "get", "ACCENT").stdout.strip() or "blue"
    dark = theme != "light"
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK if dark else Adw.ColorScheme.FORCE_LIGHT)
    base = Gtk.CssProvider()
    base.load_from_string(BASE_CSS + (DARK_COLOURS if dark else ""))
    display = Gdk.Display.get_default()
    Gtk.StyleContext.add_provider_for_display(display, base, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    Gtk.StyleContext.add_provider_for_display(display, _accent_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
    set_accent(accent)


def set_accent(name):
    bg, fg = ACCENTS.get(name, ACCENTS["blue"])
    _accent_provider.load_from_string(
        f"@define-color accent_bg_color {bg}; @define-color accent_fg_color {fg}; @define-color accent_color {bg};")


class Window(Adw.ApplicationWindow):
    def __init__(self, app, start=None):
        super().__init__(application=app, title="Settings", default_width=1020, default_height=700)
        self.flavour = compositor()
        self.conf = Conf(self)
        self.built = {}

        self.toasts = Adw.ToastOverlay()
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.NONE)
        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        for pid, title, icon, _ in PANELS:
            box = Gtk.Box(spacing=12)
            box.append(Gtk.Image(icon_name=icon))
            box.append(Gtk.Label(label=title, xalign=0))
            row = Gtk.ListBoxRow(child=box)
            row.pid = pid
            self.listbox.append(row)
        self.listbox.connect("row-selected", self.on_select)

        side_view = Adw.ToolbarView()
        side_header = Adw.HeaderBar(show_end_title_buttons=False)
        side_header.set_title_widget(Gtk.Label(label="Settings", css_classes=["heading"]))
        side_view.add_top_bar(side_header)
        side_view.set_content(Gtk.ScrolledWindow(child=self.listbox, hscrollbar_policy=Gtk.PolicyType.NEVER))
        self.content_page = Adw.NavigationPage(title="Settings")
        content_view = Adw.ToolbarView()
        content_view.add_top_bar(Adw.HeaderBar())
        content_view.set_content(self.stack)
        self.content_page.set_child(content_view)

        split = Adw.NavigationSplitView(min_sidebar_width=210, max_sidebar_width=240)
        split.set_sidebar(Adw.NavigationPage(title="Settings", child=side_view))
        split.set_content(self.content_page)
        self.toasts.set_child(split)
        self.set_content(self.toasts)

        ids = [p[0] for p in PANELS]
        self.listbox.select_row(self.listbox.get_row_at_index(ids.index(start) if start in ids else 0))

    def set_accent(self, name):
        set_accent(name)

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(text), timeout=4))

    def on_select(self, lb, row):
        if row is None:
            return
        pid = row.pid
        title = next(t for p, t, *_ in PANELS if p == pid)
        if pid not in self.built:
            builder = next(b for p, *_, b in PANELS if p == pid)
            try:
                widget = builder(self, self.conf)
            except Exception:
                traceback.print_exc()
                widget = Adw.StatusPage(icon_name="dialog-error-symbolic", title=f"{title} couldn't be opened",
                                        description=GLib.markup_escape_text(traceback.format_exc().strip().splitlines()[-1]))
            self.built[pid] = widget
            self.stack.add_named(widget, pid)
        self.stack.set_visible_child_name(pid)
        self.content_page.set_title(title)


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.start = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        install_style()

    def do_command_line(self, cmdline):
        args = cmdline.get_arguments()[1:]
        start = args[0] if args else None
        if start == "shortcuts":        # the cheat sheet (Mod+K): toggles
            shortcuts.toggle(self)
            return 0
        win = next((w for w in self.get_windows() if isinstance(w, Window)), None)
        if win:
            ids = [p[0] for p in PANELS]
            if start in ids:
                win.listbox.select_row(win.listbox.get_row_at_index(ids.index(start)))
            win.present()
        else:
            Window(self, start).present()
        return 0


def main():
    return App().run(sys.argv)
