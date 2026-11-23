"""Power: battery, idle (lock, screen off, suspend) and what the lid does."""
import glob

from gi.repository import Adw, GLib, Gtk

from .common import action_row, combo_row, group, page, read, root_helper, spin_row

LID_CONF = "/etc/systemd/logind.conf.d/50-mbp-lid.conf"
LID = [("suspend", "Suspend"), ("lock", "Lock the screen"), ("ignore", "Nothing"), ("poweroff", "Power off")]


def battery():
    for d in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        def num(*names):
            for n in names:
                v = read(f"{d}/{n}")
                if v.lstrip("-").isdigit():
                    return int(v)
            return None
        now, full, design = num("energy_now", "charge_now"), num("energy_full", "charge_full"), \
            num("energy_full_design", "charge_full_design")
        power = num("power_now", "current_now")
        return {"capacity": num("capacity"), "status": read(f"{d}/status"), "now": now, "full": full,
                "design": design, "power": power, "unit": "W" if read(f"{d}/energy_now") else "A"}
    return None


def lid_action():
    for line in read(LID_CONF).splitlines():
        if line.startswith("HandleLidSwitch="):
            return line.split("=", 1)[1].strip()
    return "suspend"


def power(win, conf):
    p = page("Power", "battery-symbolic")
    bat = battery()
    if bat:
        g = group(p, "Battery")
        charge = action_row("Charge")
        health = action_row("Health")
        draw = action_row("Power draw")
        for r in (charge, health, draw):
            g.add(r)

        def update():
            b = battery()
            if not b:
                return True
            state = {"Charging": "charging", "Discharging": "on battery", "Full": "full",
                     "Not charging": "plugged in, not charging"}.get(b["status"], b["status"].lower())
            left = ""
            if b["power"] and b["now"] is not None and b["status"] in ("Discharging", "Charging"):
                hours = (b["now"] if b["status"] == "Discharging" else (b["full"] or 0) - b["now"]) / b["power"]
                left = f" · {int(hours)} h {int(hours * 60) % 60} min {'left' if b['status'] == 'Discharging' else 'to full'}"
            charge.set_subtitle(f"{b['capacity']}% · {state}{left}")
            if b["full"] and b["design"]:
                health.set_subtitle(f"{round(100 * b['full'] / b['design'])}% of its original capacity")
            else:
                health.set_visible(False)
            if b["power"] and b["unit"] == "W":
                draw.set_subtitle(f"{b['power'] / 1e6:.1f} W")
            else:
                draw.set_visible(False)
            return True
        update()
        src = GLib.timeout_add_seconds(10, update)
        p.connect("destroy", lambda *_: GLib.source_remove(src))

    g = group(p, "When idle", "Minutes without using the keyboard or mouse; 0 means never.")
    g.add(spin_row(conf, "LOCK_MIN", "Lock the screen after"))
    g.add(spin_row(conf, "SCREEN_OFF_MIN", "Turn the screen off after"))
    g.add(spin_row(conf, "SUSPEND_MIN", "Suspend after"))
    g.add(combo_row(conf, "SUSPEND_WHEN", {"battery": "Only on battery", "always": "Always", "never": "Never"},
                    "Suspend when idle"))

    g = group(p, "Lid")
    lid = Adw.ComboRow(title="When the lid is closed", subtitle="Asks for your password to change")
    lid.set_model(Gtk.StringList.new([label for _, label in LID]))
    keys = [k for k, _ in LID]
    current = lid_action()
    lid.set_selected(keys.index(current) if current in keys else 0)
    state = {"value": lid.get_selected(), "reverting": False}

    def changed(r, _):
        if state["reverting"]:
            return
        new = keys[r.get_selected()]

        def done(res):
            if res.returncode == 0:
                state["value"] = r.get_selected()
                win.toast("Lid setting saved")
            else:
                state["reverting"] = True
                r.set_selected(state["value"])
                state["reverting"] = False
                win.toast("Not changed" + (": " + res.stderr.strip() if res.stderr.strip() else ""))
        root_helper("lid", new, done=done)
    lid.connect("notify::selected", changed)
    g.add(lid)
    return p
