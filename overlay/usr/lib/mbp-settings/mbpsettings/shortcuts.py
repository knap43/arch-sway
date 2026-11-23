"""The keyboard shortcuts cheat sheet (⌘K): the README's key tables for the
running compositor, with a search box. ⌘K again or Escape closes it."""
from gi.repository import Adw, Gdk, GLib, Gtk

from .common import compositor, read

README = "/usr/local/share/mbp/README.md"
NAMES = {"sway": "sway", "hyprland": "Hyprland", "mango": "Mango"}


def tables(flavour):
    """[(title, [(keys, action)])]: the shared table, then this flavour's."""
    out, current, inkeys = [], None, False
    for line in read(README).splitlines():
        if line.startswith("## "):
            inkeys = line.startswith("## Keys")
            current = ("Everywhere", []) if inkeys else None
            if current:
                out.append(current)
            continue
        if line.startswith("### "):
            name = line[4:].strip()
            current = (f"Only in {NAMES.get(flavour, flavour)}", []) if inkeys and name.lower() == flavour else None
            if current:
                out.append(current)
            continue
        if current and line.startswith("|") and "---" not in line and not line.startswith("| Keys |"):
            cells = [c.strip().replace("\\`", "`").replace("\\\\", "\\") for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2:
                current[1].append((cells[0], cells[1]))
    return [t for t in out if t[1]]


class ShortcutsWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Keyboard shortcuts", default_width=760, default_height=700)
        flavour = compositor() or "sway"
        self.rows = []
        self.groups = []

        search = Gtk.SearchEntry(placeholder_text="Search shortcuts", hexpand=True)
        search.connect("search-changed", lambda e: self.filter(e.get_text()))
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Keyboard shortcuts", css_classes=["heading"]))
        view = Adw.ToolbarView()
        view.add_top_bar(header)
        bar = Gtk.Box(margin_start=12, margin_end=12, margin_top=8, margin_bottom=4)
        bar.append(search)
        view.add_top_bar(bar)

        page = Adw.PreferencesPage()
        data = tables(flavour)
        if not data:
            g = Adw.PreferencesGroup()
            g.add(Adw.ActionRow(title="The shortcut list isn't available", subtitle=README + " is missing"))
            page.add(g)
        for title, rows in data:
            g = Adw.PreferencesGroup(title=title)
            g.rows = []
            for keys, what in rows:
                r = Adw.ActionRow(title=GLib.markup_escape_text(what[:1].upper() + what[1:]))
                lbl = Gtk.Label(label=keys, xalign=1)
                lbl.add_css_class("monospace")
                lbl.add_css_class("dim-label")
                r.add_suffix(lbl)
                r.text = f"{keys} {what}".lower()
                g.add(r)
                g.rows.append(r)
            page.add(g)
            self.groups.append(g)
        view.set_content(page)
        self.set_content(view)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.add_controller(keys)
        search.set_key_capture_widget(self)
        search.grab_focus()

    def on_key(self, ctrl, keyval, code, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def filter(self, text):
        text = text.lower().strip()
        for g in self.groups:
            shown = 0
            for r in g.rows:
                match = all(word in r.text for word in text.split())
                r.set_visible(match)
                shown += match
            g.set_visible(shown > 0)


def toggle(app):
    """Open the cheat sheet, or close it if it's already open."""
    for w in app.get_windows():
        if isinstance(w, ShortcutsWindow):
            w.close()
            return
    ShortcutsWindow(app).present()
