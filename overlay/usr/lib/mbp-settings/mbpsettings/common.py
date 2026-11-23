"""Shared helpers: running commands, the mbp-conf settings, and row builders."""
import json
import os
import subprocess
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402


# ---- commands ----------------------------------------------------------------
def run(*cmd, input=None, timeout=15):
    """Run a command, never raising: a CompletedProcess (returncode 127 if missing)."""
    try:
        return subprocess.run(cmd, input=input, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


def run_async(cmd, done=None, input=None, timeout=60):
    """Run a command in a thread; call done(result) on the main loop."""
    def work():
        result = run(*cmd, input=input, timeout=timeout)
        if done:
            GLib.idle_add(lambda: (done(result), False)[1])
    threading.Thread(target=work, daemon=True).start()


def spawn(*cmd):
    """Start a program and forget about it (the advanced tools, a terminal)."""
    try:
        subprocess.Popen(cmd, start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def root_helper(*args, input=None, done=None):
    """Run the privileged helper through pkexec (asks for the password)."""
    run_async(["pkexec", "/usr/lib/mbp-settings/mbp-settings-helper", *args], done, input=input)


def read(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


# ---- the desktop settings (mbp-conf) -------------------------------------------
class Conf:
    """The settings in ~/.config/mbp/settings.conf, read and written through mbp-conf.

    Changes are saved at once; applying them (which reloads the compositor) is
    batched, so moving a slider doesn't reload it a dozen times."""

    def __init__(self, window):
        self.window = window
        result = run("mbp-conf", "schema")
        try:
            self.schema = {s["key"]: s for s in json.loads(result.stdout)}
        except ValueError:
            self.schema = {}
        self.values = {k: s["value"] for k, s in self.schema.items()}
        self.listeners = {}
        self._apply_source = 0

    def get(self, key, default=""):
        return self.values.get(key, default)

    def spec(self, key):
        return self.schema.get(key, {"label": key, "help": "", "kind": "text", "choices": None, "range": None})

    def on_change(self, key, callback):
        self.listeners.setdefault(key, []).append(callback)

    def set(self, key, value, apply=True):
        value = str(value)
        if self.values.get(key) == value:
            return True
        result = run("mbp-conf", "set", f"{key}={value}")
        if result.returncode != 0:
            self.window.toast(result.stderr.strip().removeprefix("mbp-conf: ") or "Couldn't save that")
            return False
        self.values[key] = value
        for callback in self.listeners.get(key, []):
            callback(value)
        if apply:
            self.schedule_apply()
        else:
            run_async(["mbp-conf", "generate"])
        return True

    def schedule_apply(self, delay=700):
        if self._apply_source:
            GLib.source_remove(self._apply_source)
        self._apply_source = GLib.timeout_add(delay, self._apply)

    def _apply(self):
        self._apply_source = 0
        run_async(["mbp-conf", "apply"])
        return False


# ---- building blocks ---------------------------------------------------------
def page(title, icon):
    p = Adw.PreferencesPage(title=title, icon_name=icon)
    return p


def group(page_, title, description=None, suffix=None):
    g = Adw.PreferencesGroup(title=title)
    if description:
        g.set_description(description)
    if suffix is not None:
        g.set_header_suffix(suffix)
    page_.add(g)
    return g


def action_row(title, subtitle=None, activatable=False):
    row = Adw.ActionRow(title=GLib.markup_escape_text(title))
    if subtitle:
        row.set_subtitle(GLib.markup_escape_text(subtitle))
    row.set_activatable(activatable)
    return row


def button(label=None, icon=None, tooltip=None, css=("flat",), on_click=None):
    b = Gtk.Button()
    if icon:
        b.set_icon_name(icon)
    if label:
        b.set_label(label)
    if tooltip:
        b.set_tooltip_text(tooltip)
    for c in css:
        b.add_css_class(c)
    b.set_valign(Gtk.Align.CENTER)
    if on_click:
        b.connect("clicked", lambda *_: on_click())
    return b


def tool_row(title, subtitle, command):
    """A row that opens one of the full tools (nm-connection-editor, blueman...)."""
    row = action_row(title, subtitle, activatable=True)
    row.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic"))
    row.connect("activated", lambda *_: spawn(*command))
    return row


def status(page_, icon, title, description):
    """An explanatory empty state inside a page."""
    s = Adw.StatusPage(icon_name=icon, title=title, description=description)
    g = Adw.PreferencesGroup()
    g.add(s)
    page_.add(g)
    return s


# ---- rows bound to a setting -------------------------------------------------
def switch_row(conf, key, title=None, subtitle=None):
    spec = conf.spec(key)
    row = Adw.SwitchRow(title=title or spec["label"])
    if subtitle or spec.get("help"):
        row.set_subtitle(GLib.markup_escape_text(subtitle or spec["help"]))
    row.set_active(conf.get(key) == "on")
    row.connect("notify::active", lambda r, _: conf.set(key, "on" if r.get_active() else "off"))
    return row


def combo_row(conf, key, labels=None, title=None, subtitle=None):
    spec = conf.spec(key)
    choices = spec.get("choices") or []
    labels = labels or {}
    row = Adw.ComboRow(title=title or spec["label"])
    if subtitle or spec.get("help"):
        row.set_subtitle(GLib.markup_escape_text(subtitle or spec["help"]))
    row.set_model(Gtk.StringList.new([labels.get(c, c) for c in choices]))
    if conf.get(key) in choices:
        row.set_selected(choices.index(conf.get(key)))
    row.connect("notify::selected", lambda r, _: conf.set(key, choices[r.get_selected()]))
    return row


def spin_row(conf, key, title=None, subtitle=None, step=1):
    spec = conf.spec(key)
    lo, hi = spec.get("range") or (0, 100)
    row = Adw.SpinRow.new_with_range(lo, hi, step)
    row.set_title(title or spec["label"])
    if subtitle or spec.get("help"):
        row.set_subtitle(GLib.markup_escape_text(subtitle or spec["help"]))
    try:
        row.set_value(int(conf.get(key, lo)))
    except ValueError:
        pass
    row.connect("notify::value", lambda r, _: conf.set(key, int(r.get_value())))
    return row


def scale_row(conf, key, title=None, subtitle=None, marks=()):
    """A slider for an int setting (saved when it stops moving)."""
    spec = conf.spec(key)
    lo, hi = spec.get("range") or (0, 100)
    row = action_row(title or spec["label"], subtitle or spec.get("help"))
    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, 1)
    scale.set_hexpand(True)
    scale.set_size_request(260, -1)
    scale.set_draw_value(False)
    for value, label in marks:
        scale.add_mark(value, Gtk.PositionType.BOTTOM, label)
    try:
        scale.set_value(int(conf.get(key, lo)))
    except ValueError:
        pass
    pending = [0]

    def changed(s):
        if pending[0]:
            GLib.source_remove(pending[0])
        pending[0] = GLib.timeout_add(350, lambda: (conf.set(key, int(s.get_value())), pending.__setitem__(0, 0), False)[2])
    scale.connect("value-changed", changed)
    row.add_suffix(scale)
    return row


def entry_row(conf, key, title=None):
    spec = conf.spec(key)
    row = Adw.EntryRow(title=title or spec["label"])
    row.set_text(conf.get(key))
    row.set_show_apply_button(True)
    row.connect("apply", lambda r: conf.set(key, r.get_text().strip()) or r.set_text(conf.get(key)))
    return row


def scaled_icon(name):
    return Gtk.Image(icon_name=name, pixel_size=16)


def compositor():
    if os.environ.get("SWAYSOCK"):
        return "sway"
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hyprland"
    if run("pgrep", "-x", "mango").returncode == 0:
        return "mango"
    return None
