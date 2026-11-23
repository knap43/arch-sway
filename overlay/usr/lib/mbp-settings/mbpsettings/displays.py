"""Displays: resolution, refresh rate, scale, rotation, arrangement, on/off,
plus brightness and night light.

Changes apply at once through wlr-randr (every flavour supports the wlroots
output-management protocol it uses); after "Keep these settings?" they're
saved as DISPLAYS in the desktop settings, so they come back at every login."""
import json

from gi.repository import Adw, GLib, Gtk

from .common import action_row, combo_row, group, page, run, spin_row, switch_row

SCALES = [1.0, 1.25, 1.5, 1.75, 2.0]
ROTATIONS = [("normal", "None"), ("90", "90° clockwise"), ("180", "Upside down"), ("270", "90° anticlockwise")]
POSITIONS = [("right", "Right of the built-in display"), ("left", "Left of the built-in display"),
             ("above", "Above the built-in display"), ("below", "Below the built-in display")]
REVERT_SECONDS = 15


def outputs():
    result = run("wlr-randr", "--json")
    try:
        return json.loads(result.stdout)
    except ValueError:
        return None


def is_builtin(o):
    return o["name"].startswith(("eDP", "LVDS", "DSI"))


def current_mode(o):
    for m in o.get("modes", []):
        if m.get("current"):
            return m
    return (o.get("modes") or [{}])[0]


def logical_size(o, mode=None, scale=None, transform=None):
    m = mode or current_mode(o)
    w, h = m.get("width", 0), m.get("height", 0)
    if (transform or o.get("transform", "normal")) in ("90", "270", "flipped-90", "flipped-270"):
        w, h = h, w
    s = scale or o.get("scale") or 1
    return round(w / s), round(h / s)


def state_of(o):
    m = current_mode(o)
    return {"mode": f"{m.get('width')}x{m.get('height')}@{m.get('refresh', 0):.3f}",
            "x": o.get("position", {}).get("x", 0), "y": o.get("position", {}).get("y", 0),
            "scale": o.get("scale", 1), "transform": o.get("transform", "normal"),
            "enabled": o.get("enabled", True)}


def randr_args(name, st):
    if not st["enabled"]:
        return ["--output", name, "--off"]
    w_h, _, rate = st["mode"].partition("@")
    mode = f"{w_h}@{float(rate):.3f}Hz" if rate else w_h
    return ["--output", name, "--on", "--mode", mode, "--pos", f"{int(st['x'])},{int(st['y'])}",
            "--scale", f"{float(st['scale']):g}", "--transform", st["transform"]]


class DisplaysPage:
    def __init__(self, win, conf):
        self.win, self.conf = win, conf
        self.page = page("Displays", "video-display-symbolic")
        self.groups = []
        self.building = False
        self.build()

    # -- layout of the page --------------------------------------------------------
    def build(self):
        for g in self.groups:
            self.page.remove(g)
        self.groups = []
        outs = outputs()
        if outs is None:
            g = group(self.page, "Displays", "Couldn't read the displays (wlr-randr isn't working here).")
            self.groups.append(g)
        else:
            self.outs = outs
            self.builtin = next((o for o in outs if is_builtin(o) and o.get("enabled")), None)
            for o in outs:
                self.groups.append(self.output_group(o))
        self.groups.append(self.brightness_group())
        self.groups.append(self.nightlight_group())
        self.groups.append(self.default_scale_group())

    def output_group(self, o):
        self.building = True
        m = current_mode(o)
        title = "Built-in display" if is_builtin(o) else (" ".join(x for x in (o.get("make"), o.get("model")) if x and x != "Unknown") or o["name"])
        sub = f"{o['name']} · {m.get('width')} × {m.get('height')}" if o.get("enabled") else f"{o['name']} · off"
        g = group(self.page, title, sub)

        if len(self.outs) > 1:
            on = Adw.SwitchRow(title="On", active=bool(o.get("enabled")))
            on.connect("notify::active", lambda r, _: self.change(o, enabled=r.get_active()))
            g.add(on)
        if not o.get("enabled"):
            self.building = False
            return g

        # resolution
        sizes = []
        for mode in o.get("modes", []):
            key = (mode["width"], mode["height"])
            if key not in sizes:
                sizes.append(key)
        sizes.sort(key=lambda s: s[0] * s[1], reverse=True)
        preferred = next(((md["width"], md["height"]) for md in o["modes"] if md.get("preferred")), None)
        res = Adw.ComboRow(title="Resolution")
        res.set_model(Gtk.StringList.new([f"{w} × {h}" + (" (best)" if (w, h) == preferred else "") for w, h in sizes]))
        cur = (m.get("width"), m.get("height"))
        if cur in sizes:
            res.set_selected(sizes.index(cur))
        g.add(res)

        # refresh rate, for the chosen resolution
        rate = Adw.ComboRow(title="Refresh rate")
        g.add(rate)

        def rates_for(size):
            return sorted({md["refresh"] for md in o["modes"] if (md["width"], md["height"]) == size}, reverse=True)

        def fill_rates(size, select=None):
            rs = rates_for(size)
            rate.rates = rs
            rate.set_model(Gtk.StringList.new([f"{r:.2f} Hz" for r in rs]))
            if select is not None:
                best = min(range(len(rs)), key=lambda i: abs(rs[i] - select)) if rs else 0
                rate.set_selected(best)
        fill_rates(cur, m.get("refresh", 0))

        def on_res(r, _):
            if self.building:
                return
            size = sizes[r.get_selected()]
            fill_rates(size, rates_for(size)[0] if rates_for(size) else 0)
            self.change(o, mode=(size, rate.rates[rate.get_selected()]))
        res.connect("notify::selected", on_res)
        rate.connect("notify::selected", lambda r, _: None if self.building else
                     self.change(o, mode=(sizes[res.get_selected()], r.rates[r.get_selected()])))

        # scale
        scales = list(SCALES)
        if o.get("scale") and round(o["scale"], 2) not in [round(s, 2) for s in scales]:
            scales.append(o["scale"])
            scales.sort()
        sc = Adw.ComboRow(title="Scale", subtitle="Bigger text and windows; 1.5 suits 1080p laptop screens")
        sc.set_model(Gtk.StringList.new([f"{s * 100:g}%" for s in scales]))
        sc.set_selected(min(range(len(scales)), key=lambda i: abs(scales[i] - (o.get("scale") or 1))))
        sc.connect("notify::selected", lambda r, _: None if self.building else self.change(o, scale=scales[r.get_selected()]))
        g.add(sc)

        # rotation
        rot = Adw.ComboRow(title="Rotation")
        rot.set_model(Gtk.StringList.new([label for _, label in ROTATIONS]))
        keys = [k for k, _ in ROTATIONS]
        rot.set_selected(keys.index(o.get("transform")) if o.get("transform") in keys else 0)
        rot.connect("notify::selected", lambda r, _: None if self.building else self.change(o, transform=keys[r.get_selected()]))
        g.add(rot)

        # arrangement (external displays, relative to the built-in one)
        if self.builtin and o is not self.builtin:
            pos = Adw.ComboRow(title="Position")
            pos.set_model(Gtk.StringList.new([label for _, label in POSITIONS]))
            pos.set_selected([k for k, _ in POSITIONS].index(self.guess_position(o)))
            pos.connect("notify::selected", lambda r, _: None if self.building else
                        self.arrange(o, POSITIONS[r.get_selected()][0]))
            g.add(pos)
        self.building = False
        return g

    def guess_position(self, o):
        b, p = self.builtin.get("position", {}), o.get("position", {})
        bw, bh = logical_size(self.builtin)
        if p.get("x", 0) >= b.get("x", 0) + bw:
            return "right"
        if p.get("x", 0) + logical_size(o)[0] <= b.get("x", 0):
            return "left"
        if p.get("y", 0) + logical_size(o)[1] <= b.get("y", 0):
            return "above"
        if p.get("y", 0) >= b.get("y", 0) + bh:
            return "below"
        return "right"

    # -- changing things -----------------------------------------------------------
    def change(self, o, mode=None, scale=None, transform=None, enabled=None):
        old = {x["name"]: state_of(x) for x in self.outs}
        new = json.loads(json.dumps(old))
        st = new[o["name"]]
        if mode is not None:
            (w, h), r = mode
            st["mode"] = f"{w}x{h}@{r:.3f}"
        if scale is not None:
            st["scale"] = scale
        if transform is not None:
            st["transform"] = transform
        if enabled is not None:
            st["enabled"] = enabled
            if not enabled and not any(v["enabled"] for k, v in new.items() if k != o["name"]):
                self.win.toast("At least one display has to stay on")
                self.build()
                return
        self.keep_externals_beside(new)
        self.try_states(old, new, [o["name"]])

    def arrange(self, o, where):
        old = {x["name"]: state_of(x) for x in self.outs}
        new = json.loads(json.dumps(old))
        self.place(new, o["name"], where)
        self.try_states(old, new, [o["name"], self.builtin["name"]])

    def size_of(self, name, st):
        o = next(x for x in self.outs if x["name"] == name)
        w_h, _, r = st["mode"].partition("@")
        w, h = (int(x) for x in w_h.split("x"))
        return logical_size(o, {"width": w, "height": h}, float(st["scale"]), st["transform"])

    def place(self, new, name, where):
        b = self.builtin["name"]
        bw, bh = self.size_of(b, new[b])
        ew, eh = self.size_of(name, new[name])
        spots = {"right": ((0, 0), (bw, 0)), "left": ((ew, 0), (0, 0)),
                 "above": ((0, eh), (0, 0)), "below": ((0, 0), (0, bh))}
        (bx, by), (ex, ey) = spots[where]
        new[b].update(x=bx, y=by)
        new[name].update(x=ex, y=ey)

    def keep_externals_beside(self, new):
        """After a size change, move other displays so nothing overlaps."""
        if not self.builtin:
            return
        for o in self.outs:
            if o is not self.builtin and new[o["name"]]["enabled"]:
                self.place(new, o["name"], self.guess_position(o))

    def try_states(self, old, new, names):
        changed = [n for n in new if new[n] != old[n]]
        if not changed:
            return
        args = []
        for n in changed:
            args += randr_args(n, new[n])
        result = run("wlr-randr", *args)
        if result.returncode != 0:
            self.win.toast("The display didn't accept that: " + (result.stderr.strip().splitlines() or ["unknown error"])[-1])
            self.build()
            return
        self.confirm(old, new, changed)

    def confirm(self, old, new, changed):
        dialog = Adw.AlertDialog(heading="Keep these display settings?")
        dialog.add_response("revert", "Revert")
        dialog.add_response("keep", "Keep")
        dialog.set_response_appearance("keep", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("keep")
        dialog.set_close_response("revert")
        left = [REVERT_SECONDS]
        state = {"timer": 0, "answered": False}

        def tick():
            left[0] -= 1
            if left[0] <= 0:
                state["timer"] = 0
                dialog.close()          # -> "revert"
                return False
            dialog.set_body(f"They'll be undone in {left[0]} seconds.")
            return True
        dialog.set_body(f"They'll be undone in {REVERT_SECONDS} seconds.")
        state["timer"] = GLib.timeout_add_seconds(1, tick)

        def answered(d, response):
            if state["answered"]:       # only the first answer counts
                return
            state["answered"] = True
            if state["timer"]:
                GLib.source_remove(state["timer"])
                state["timer"] = 0
            if response == "keep":
                self.save(new, changed)
            else:
                args = []
                for n in changed:
                    args += randr_args(n, old[n])
                run("wlr-randr", *args)
            self.build()
        dialog.connect("response", answered)
        dialog.present(self.win)

    def save(self, new, changed):
        try:
            saved = json.loads(self.conf.get("DISPLAYS", "{}"))
        except ValueError:
            saved = {}
        for n in changed:
            saved[n] = new[n]
        self.conf.set("DISPLAYS", json.dumps(saved, separators=(",", ":")), apply=False)
        if self.win.flavour == "mango" and any(new[n]["transform"] != "normal" for n in changed):
            self.win.toast("Mango can't remember rotation: it's back to normal at the next login")

    # -- brightness, night light, default scale -------------------------------------------
    def brightness_group(self):
        g = group(self.page, "Brightness")
        info = run("brightnessctl", "-m", "-c", "backlight").stdout.strip().split(",")
        if len(info) >= 4 and info[3].endswith("%"):
            row = action_row("Screen brightness")
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 5, 100, 1)
            scale.set_size_request(260, -1)
            scale.set_draw_value(False)
            scale.set_value(int(info[3].rstrip("%")))
            scale.connect("value-changed", lambda s: run("brightnessctl", "-c", "backlight", "set", f"{int(s.get_value())}%"))
            row.add_suffix(scale)
            g.add(row)
        g.add(combo_row(self.conf, "BRIGHTNESS", {"keep": "Leave as it was", "30": "30%", "50": "50%",
                                                  "70": "70%", "100": "100%"}, "At login"))
        return g

    def nightlight_group(self):
        g = group(self.page, "Night light", "Warmer colours; ⌘N switches it for the session.")
        g.add(switch_row(self.conf, "NIGHTLIGHT", "Night light"))
        g.add(spin_row(self.conf, "NIGHTLIGHT_TEMP", "Colour temperature (K)", "Lower is warmer; 6500 is neutral", step=100))
        return g

    def default_scale_group(self):
        g = group(self.page, "Other displays")
        g.add(combo_row(self.conf, "SCALE", {"auto": "Automatic", "1": "100%", "1.25": "125%", "1.5": "150%",
                                             "1.75": "175%", "2": "200%"},
                        "Scale for displays not set above",
                        "Automatic: 150% on displays 1080p or taller"))
        return g


def displays(win, conf):
    return DisplaysPage(win, conf).page
