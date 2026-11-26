"""Keyboard shortcuts that can be changed in Settings, and the user's own.

Plain Python with no GTK import: Settings edits them, and mbp-conf loads this
file to write each compositor's bindings (sway-binds.conf, mango-binds.conf, and
a table in hyprland.lua) and the cheat sheet reads it to show the current keys.

A shortcut is written "Mod+Shift+q": modifiers (Mod, Ctrl, Alt, Shift) and an
xkb key name, the key as it is on a US keyboard ("slash", not "question").
Mod is the Super key: ⌘ on the MacBook, Alt on a PC keyboard (they're swapped).

Only changes are stored, in ~/.config/mbp/shortcuts.conf:

    terminal = Mod+Return              one or more shortcuts, comma-separated
    lock =                             no shortcut at all
    custom = Mod+Shift+t | foot btop   your own: shortcut | command
"""

import os

FLAVOURS = ("sway", "hyprland", "mango")
MODS = ("Mod", "Ctrl", "Alt", "Shift")


class Action:
    def __init__(self, id, group, label, default, sway=None, mango=None, hyprland=True, defaults=None):
        self.id, self.group, self.label = id, group, label
        self.default = default                  # [shortcut, ...]
        self.defaults = defaults or {}          # flavour -> [shortcut, ...], where it differs
        self.sway, self.mango = sway, mango     # the command; None: not in that flavour
        self.hyprland = hyprland                # hyprland.lua implements it (by id)

    def available(self, flavour):
        return {"sway": self.sway, "mango": self.mango, "hyprland": self.hyprland}[flavour] not in (None, False)

    def default_for(self, flavour):
        return list(self.defaults.get(flavour, self.default))


CLIP = 'cliphist list | fuzzel --dmenu --prompt "Clipboard: " | cliphist decode | wl-copy'
ZEN = "flatpak run app.zen_browser.zen"

ACTIONS = [
    Action("terminal", "Apps", "Terminal", ["Mod+d"], "exec $term", "spawn,foot"),
    Action("launcher", "Apps", "App launcher", ["Mod+space", "Mod+q"], "exec $menu", "spawn,fuzzel"),
    Action("files", "Apps", "Files", ["Mod+e"], "exec thunar", "spawn,thunar"),
    Action("browser", "Apps", "Web browser", ["Mod+b"], f"exec {ZEN}", f"spawn,{ZEN}"),
    Action("clipboard", "Apps", "Clipboard history", ["Mod+v"], f"exec {CLIP}", f"spawn_shell,{CLIP}"),
    Action("settings", "Apps", "Settings", [], "exec mbp-settings", "spawn,mbp-settings"),

    Action("close", "Windows", "Close window", ["Mod+w"], "kill", "killclient"),
    Action("layout_toggle", "Windows", "Switch tabbed ⇄ tiled", ["Mod+Tab"],
           "layout toggle tabbed split", "spawn,mango-tabs-toggle"),
    Action("fullscreen", "Windows", "Fullscreen", ["Mod+f"], "fullscreen", "togglefullscreen"),
    Action("float", "Windows", "Float or tile the window", ["Mod+Shift+f"], "floating toggle", "togglefloating"),
    Action("float_all", "Windows", "Float or tile every window here", ["Mod+g"],
           "exec sway-layout float-all", "toggle_all_floating"),
    Action("left_half", "Windows", "Window to the left half", ["Mod+Return"], "exec sway-layout left-half", "zoom"),
    Action("cycle_windows", "Windows", "Cycle through every window", ["Mod+Shift+Tab"],
           "exec sway-cycle-windows", None),
    Action("overview", "Windows", "Overview", ["Mod+Shift+q"], None, "toggleoverview", hyprland=False),
    Action("scratchpad_move", "Windows", "Stash the window (scratchpad)", ["Mod+Shift+grave"],
           "move scratchpad", "minimized"),
    Action("scratchpad_show", "Windows", "Show stashed windows", ["Mod+grave"], "scratchpad show", "toggle_scratchpad"),
    Action("resize_mode", "Windows", "Resize mode", ["Mod+r"], 'mode "resize"', "setkeymode,resize"),

    Action("cheatsheet", "System", "Shortcuts cheat sheet", ["Mod+slash"],
           "exec mbp-shortcuts --toggle", "spawn,mbp-shortcuts --toggle"),
    Action("screenshot", "System", "Screenshot of an area", ["Mod+Ctrl+s"], "exec mbp-screenshot", "spawn,mbp-screenshot"),
    Action("screenshot_full", "System", "Screenshot of the screen", ["Mod+Ctrl+Shift+s"],
           "exec mbp-screenshot --full", "spawn,mbp-screenshot --full"),
    Action("power_menu", "System", "Power menu", ["Mod+Escape", "Mod+Shift+q"],
           "exec mbp-power-menu", "spawn,mbp-power-menu", defaults={"mango": ["Mod+Escape"]}),
    Action("lock", "System", "Lock the screen", [], "exec mbp-lock", "spawn,mbp-lock"),
    Action("theme", "System", "Switch theme", ["Mod+t"], "exec mbp-theme", "spawn,mbp-theme"),
    Action("nightlight", "System", "Night light on or off", ["Mod+n"],
           "exec mbp-nightlight toggle", "spawn,mbp-nightlight toggle"),
    Action("reload", "System", "Reload the desktop", ["Mod+Shift+c"], "reload", "reload_config"),
]
BY_ID = {a.id: a for a in ACTIONS}

# The keys that stay fixed (focus, move, resize, workspaces, layouts): a new
# shortcut can't take them. Name, then the shortcuts.
_dirs = [("h", "Left"), ("j", "Down"), ("k", "Up"), ("l", "Right")]
FIXED = [
    ("Resize the window", [f"Mod+{k}" for k, _ in _dirs]),
    ("Focus", [f"Mod+{a}" for _, a in _dirs]),
    ("Move the window", [f"Mod+Shift+{k}" for pair in _dirs for k in pair]),
    ("Workspaces", [f"Mod+{n}" for n in "1234567890"] + [f"Mod+Shift+{n}" for n in "1234567890"]),
    ("Workspace left / right", ["Mod+a", "Mod+s", "Mod+Shift+a", "Mod+Shift+s"]),
    ("Previous / next tab", ["Mod+bracketleft", "Mod+bracketright"]),
    ("Layouts", ["Mod+backslash", "Mod+minus", "Mod+period", "Mod+comma"]),
    ("Focus floating ⇄ tiled", ["Mod+Shift+space"]),
    ("Focus the parent", ["Mod+p"]),
]
# Leaves the capture mode Settings uses while you press a new shortcut, in case
# Settings goes away mid-way. Can't be given to anything else.
ESCAPE_HATCH = "Mod+Ctrl+Escape"


# ---- shortcuts as text ---------------------------------------------------------
def normalize(text):
    """'shift+mod+Q' -> 'Mod+Shift+q'; None if it isn't a shortcut."""
    parts = [p.strip() for p in text.split("+")]
    if not parts or not parts[-1]:
        return None
    key, mods = parts[-1], set()
    for p in parts[:-1]:
        name = {"super": "Mod", "mod4": "Mod", "control": "Ctrl", "mod1": "Alt"}.get(p.lower(), p.capitalize())
        if name not in MODS:
            return None
        mods.add(name)
    if len(key) == 1:
        key = key.lower()
    return "+".join([m for m in MODS if m in mods] + [key])


def split(shortcut):
    parts = shortcut.split("+")
    return parts[:-1], parts[-1]


LABELS = {"Mod": "⌘", "Ctrl": "Ctrl", "Alt": "Alt", "Shift": "⇧"}
KEY_LABELS = {"space": "Space", "Return": "Enter", "Escape": "Esc", "slash": "/", "backslash": "\\",
              "grave": "`", "minus": "-", "equal": "=", "comma": ",", "period": ".", "semicolon": ";",
              "apostrophe": "'", "bracketleft": "[", "bracketright": "]", "Tab": "Tab", "BackSpace": "Backspace",
              "Left": "←", "Right": "→", "Up": "↑", "Down": "↓", "Print": "Print"}


def label(shortcut):
    """'Mod+Shift+slash' -> '⌘ ⇧ /', as the README and cheat sheet write keys."""
    mods, key = split(shortcut)
    key = KEY_LABELS.get(key, key.upper() if len(key) == 1 else key)
    return " ".join([LABELS[m] for m in mods] + [key])


# ---- the file --------------------------------------------------------------------
def path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "mbp", "shortcuts.conf")


def load(file=None):
    """(changes, custom): {action id: [shortcut]}, [(shortcut, command)]."""
    changes, custom = {}, []
    try:
        lines = open(file or path(), encoding="utf-8").read().splitlines()
    except OSError:
        return changes, custom
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = (s.strip() for s in line.split("=", 1))
        if name == "custom":
            keys, _, command = value.partition("|")
            keys, command = normalize(keys), command.strip()
            if keys and command:
                custom.append((keys, command))
        elif name in BY_ID:
            changes[name] = [k for k in (normalize(v) for v in value.split(",") if v.strip()) if k]
    return changes, custom


def save(changes, custom, file=None):
    file = file or path()
    os.makedirs(os.path.dirname(file), exist_ok=True)
    out = ["# Keyboard shortcuts changed in Settings (Settings → Keyboard shortcuts).",
           "# Everything not listed keeps its default. See shortcuts.py in mbp-settings.", ""]
    for a in ACTIONS:
        if a.id in changes:
            out.append(f"{a.id} = {', '.join(changes[a.id])}")
    for keys, command in custom:
        out.append(f"custom = {keys} | {command}")
    with open(file + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.replace(file + ".tmp", file)


def current(flavour, changes=None, custom=None):
    """[(action, [shortcut])] for the actions this flavour has, and the custom list."""
    if changes is None:
        changes, custom = load()
    rows = [(a, changes.get(a.id, a.default_for(flavour))) for a in ACTIONS if a.available(flavour)]
    return rows, custom or []


def owner(shortcut, flavour, changes, custom, skip=None):
    """Who has this shortcut: ("action", Action) / ("custom", index) / ("fixed", name) / None.
    skip: ("action", id) or ("custom", index), the one being edited."""
    rows, custom = current(flavour, changes, custom)
    for a, keys in rows:
        if shortcut in keys and skip != ("action", a.id):
            return ("action", a)
    for i, (keys, _) in enumerate(custom):
        if keys == shortcut and skip != ("custom", i):
            return ("custom", i)
    for name, keys in FIXED:
        if shortcut in keys:
            return ("fixed", name)
    if shortcut == ESCAPE_HATCH:
        return ("fixed", "Leaving the shortcut capture")
    return None


# ---- each compositor's bindings ------------------------------------------------------
def _sway_keys(s):
    mods, key = split(s)
    names = {"Mod": "$mod", "Ctrl": "Ctrl", "Alt": "Mod1", "Shift": "Shift"}
    return "+".join([names[m] for m in mods] + [key])


def _mango_keys(s):
    mods, key = split(s)
    names = {"Mod": "SUPER", "Ctrl": "CTRL", "Alt": "ALT", "Shift": "SHIFT"}
    return ("+".join(names[m] for m in mods) or "NONE") + "," + key


def _lua(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


HEADER = "Generated by mbp-conf from Settings → Keyboard shortcuts; edits here are overwritten"


def sway_binds(changes=None, custom=None):
    rows, custom = current("sway", changes, custom)
    out = [f"# {HEADER}", "bindsym --to-code {"]
    for a, keys in rows:
        out += [f"    {_sway_keys(k)} {a.sway}" for k in keys]
    for keys, command in custom:
        # Quoted, so a ; or , in it isn't read as the start of another sway command
        quoted = command.replace("\\", "\\\\").replace('"', '\\"')
        out.append(f'    {_sway_keys(keys)} exec "{quoted}"')
    out += ["}", "",
            "# Settings switches to this mode while you press a new shortcut, so the",
            f"# keys reach it; {label(ESCAPE_HATCH)} leaves it should Settings go away.",
            'mode "mbp-capture" {',
            f"    bindsym --to-code {_sway_keys(ESCAPE_HATCH)} mode default",
            "}", ""]
    return "\n".join(out)


def mango_binds(changes=None, custom=None):
    rows, custom = current("mango", changes, custom)
    out = [f"# {HEADER}"]
    for a, keys in rows:
        out += [f"bind={_mango_keys(k)},{a.mango}" for k in keys]
    for keys, command in custom:
        out.append(f"bind={_mango_keys(keys)},spawn_shell,{command}")
    out += ["",
            "# Settings switches to this mode while you press a new shortcut, so the",
            f"# keys reach it; {label(ESCAPE_HATCH)} leaves it should Settings go away.",
            "key_mode=mbp-capture",
            f"bind={_mango_keys(ESCAPE_HATCH)},setkeymode,default",
            "key_mode=default", ""]
    return "\n".join(out)


def hyprland_lua(changes=None, custom=None):
    """The `shortcuts` and `custom_shortcuts` fields of the generated hyprland.lua:
    { mods = "SHIFT", mod = true, key = "Q", action = "power_menu" }."""
    rows, custom = current("hyprland", changes, custom)

    def entry(s, field, value):
        mods, key = split(s)
        extra = " + ".join({"Ctrl": "CTRL", "Alt": "ALT", "Shift": "SHIFT"}[m] for m in mods if m != "Mod")
        key = key.upper() if len(key) == 1 else key
        return (f"{{ mod = {'true' if 'Mod' in mods else 'false'}, mods = {_lua(extra)}, "
                f"key = {_lua(key)}, {field} = {_lua(value)} }}")

    binds = [entry(k, "action", a.id) for a, keys in rows for k in keys]
    own = [entry(k, "command", c) for k, c in custom]
    return ("    shortcuts = {\n" + "".join(f"        {b},\n" for b in binds) + "    },\n"
            "    custom_shortcuts = {\n" + "".join(f"        {b},\n" for b in own) + "    },\n")


def capture_mode(flavour, on):
    """The command that turns the capture mode on or off in this compositor."""
    if flavour == "sway":
        return ["swaymsg", "mode", "mbp-capture" if on else "default"]
    if flavour == "hyprland":
        return ["hyprctl", "dispatch", "submap", "mbp-capture" if on else "reset"]
    if flavour == "mango":
        return ["mmsg", "dispatch", f"setkeymode,{'mbp-capture' if on else 'default'}"]
    return None
