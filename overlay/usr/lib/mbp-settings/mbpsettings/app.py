"""The Settings window: a sidebar of panels, built when first opened."""
import sys
import traceback

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .common import Conf, compositor
from . import bluetooth, desktop, displays, keyshortcuts, network, power, sound, system
from .style import ACCENTS, BASE_CSS, accent_css, colours

APP_ID = "org.mbp.Settings"


# id, title, icon, builder(win, conf) -> Adw.PreferencesPage
PANELS = [
    ("network", "Network", "network-wireless-symbolic", network.network),
    ("bluetooth", "Bluetooth", "bluetooth-symbolic", bluetooth.bluetooth),
    ("sound", "Sound", "audio-speakers-symbolic", sound.sound),
    ("displays", "Displays", "video-display-symbolic", displays.displays),
    ("keyboard", "Keyboard", "input-keyboard-symbolic", desktop.keyboard),
    ("shortcuts", "Keyboard shortcuts", "preferences-desktop-keyboard-shortcuts-symbolic",
     keyshortcuts.keyboard_shortcuts),
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

# Settings' own widgets; the shared look is in style.py.
APP_CSS = "".join(f"button.accent-swatch.swatch-{n}, button.accent-swatch.swatch-{n}:checked, "
                  f"button.accent-swatch.swatch-{n}:hover {{ background: {c}; background-image: none; }}\n"
                  for n, (c, _) in ACCENTS.items()) + """
button.accent-swatch { min-width: 22px; min-height: 22px; padding: 0; border: 2px solid transparent; }
button.accent-swatch:checked { border-color: @window_fg_color; }
.wallpapers flowboxchild { padding: 2px; border: 2px solid transparent; }
.wallpapers flowboxchild:selected { border-color: @accent_bg_color; background: none; }
"""


_accent_provider = Gtk.CssProvider()


def install_style():
    """The desktop's look for every window of the app."""
    from .common import run
    theme = run("mbp-conf", "get", "THEME").stdout.strip() or "dark"
    accent = run("mbp-conf", "get", "ACCENT").stdout.strip() or "blue"
    dark = theme != "light"
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK if dark else Adw.ColorScheme.FORCE_LIGHT)
    base = Gtk.CssProvider()
    base.load_from_string(colours(theme) + BASE_CSS + APP_CSS)
    display = Gdk.Display.get_default()
    Gtk.StyleContext.add_provider_for_display(display, base, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    Gtk.StyleContext.add_provider_for_display(display, _accent_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
    set_accent(accent)


def set_accent(name):
    _accent_provider.load_from_string(accent_css(name))


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
        # No window buttons (Mod+W closes): they made this header taller than the
        # sidebar's, so the two edges no longer lined up.
        content_view.add_top_bar(Adw.HeaderBar(show_start_title_buttons=False, show_end_title_buttons=False))
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

    def show_panel(self, pid):
        ids = [p[0] for p in PANELS]
        if pid in ids:
            self.listbox.select_row(self.listbox.get_row_at_index(ids.index(pid)))

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
