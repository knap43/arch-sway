"""Sound: output and input device, volume, mute (PipeWire through pw-dump and
wpctl). Per-app volumes and device profiles are in pavucontrol."""
import json
import re

from gi.repository import Adw, GLib, Gtk

from .common import action_row, group, page, run, tool_row


def audio_nodes():
    """(sinks, sources, default sink name, default source name) or None."""
    result = run("pw-dump", timeout=5)
    try:
        objs = json.loads(result.stdout)
    except ValueError:
        return None
    sinks, sources, defaults = [], [], {}
    for o in objs:
        info = o.get("info") or {}
        props = info.get("props") or {}
        if o.get("type") == "PipeWire:Interface:Node":
            cls = props.get("media.class", "")
            node = {"id": o["id"], "name": props.get("node.name", ""),
                    "label": props.get("node.description") or props.get("node.nick") or props.get("node.name", "?")}
            if cls == "Audio/Sink":
                sinks.append(node)
            elif cls == "Audio/Source":
                sources.append(node)
        elif o.get("type") == "PipeWire:Interface:Metadata" and props.get("metadata.name") == "default":
            for entry in o.get("metadata") or []:
                if entry.get("key") in ("default.audio.sink", "default.audio.source"):
                    val = entry.get("value")
                    if isinstance(val, str):
                        try:
                            val = json.loads(val)
                        except ValueError:
                            val = {}
                    defaults[entry["key"]] = (val or {}).get("name")
    return sinks, sources, defaults.get("default.audio.sink"), defaults.get("default.audio.source")


def volume(node_id):
    out = run("wpctl", "get-volume", str(node_id)).stdout
    m = re.search(r"Volume:\s*([\d.]+)", out)
    return (float(m.group(1)) if m else 0.0), "[MUTED]" in out


class SoundPage:
    def __init__(self, win, conf):
        self.win = win
        self.page = page("Sound", "audio-speakers-symbolic")
        self.groups = []
        self.updating = False
        self.poll = 0
        self.build()
        self.page.connect("map", lambda *_: self.start_polling())
        self.page.connect("unmap", lambda *_: self.stop_polling())

    def start_polling(self):
        if not self.poll:
            self.poll = GLib.timeout_add_seconds(3, self.refresh)

    def stop_polling(self):
        if self.poll:
            GLib.source_remove(self.poll)
            self.poll = 0

    def build(self):
        self.volume_setters = []
        for g in self.groups:
            self.page.remove(g)
        self.groups = []
        nodes = audio_nodes()
        if nodes is None:
            g = Adw.PreferencesGroup()
            g.add(Adw.StatusPage(icon_name="audio-volume-muted-symbolic", title="No sound server",
                                 description="PipeWire isn't running (or pw-dump is missing)."))
            self.page.add(g)
            self.groups.append(g)
            return
        sinks, sources, dsink, dsource = nodes
        self.snapshot = self.key(nodes)
        self.groups.append(self.device_group("Output", "audio-speakers-symbolic", sinks, dsink))
        self.groups.append(self.device_group("Input", "audio-input-microphone-symbolic", sources, dsource))
        adv = group(self.page, "Advanced")
        adv.add(tool_row("Volume control", "Per-application volume, device profiles, balance", ["pavucontrol"]))
        self.groups.append(adv)

    def key(self, nodes):
        sinks, sources, dsink, dsource = nodes
        return ([n["id"] for n in sinks], [n["id"] for n in sources], dsink, dsource)

    def refresh(self):
        nodes = audio_nodes()
        if nodes is not None and self.key(nodes) != getattr(self, "snapshot", None):
            self.build()
        else:
            for setter in getattr(self, "volume_setters", []):
                setter()
        return True

    def device_group(self, title, icon, nodes, default_name):
        g = group(self.page, title)
        if not nodes:
            g.add(action_row(f"No {title.lower()} devices"))
            return g
        names = [n["name"] for n in nodes]
        current = names.index(default_name) if default_name in names else 0
        dev = Adw.ComboRow(title="Device")
        dev.set_model(Gtk.StringList.new([n["label"] for n in nodes]))
        dev.set_selected(current)
        dev.connect("notify::selected", lambda r, _: run("wpctl", "set-default", str(nodes[r.get_selected()]["id"])))
        g.add(dev)

        node = nodes[current]
        row = action_row("Volume")
        row.add_prefix(Gtk.Image(icon_name=icon))
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_size_request(280, -1)
        scale.set_draw_value(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        mute = Gtk.ToggleButton(icon_name="audio-volume-muted-symbolic", valign=Gtk.Align.CENTER,
                                tooltip_text="Mute")
        mute.add_css_class("flat")

        def load():
            vol, muted = volume(node["id"])
            self.updating = True
            if not scale.has_focus():
                scale.set_value(round(vol * 100))
            mute.set_active(muted)
            self.updating = False
        load()
        self.volume_setters.append(load)
        scale.connect("value-changed", lambda s: self.updating or
                      run("wpctl", "set-volume", str(node["id"]), f"{s.get_value() / 100:.2f}"))
        mute.connect("toggled", lambda b: self.updating or
                     run("wpctl", "set-mute", str(node["id"]), "1" if b.get_active() else "0"))
        row.add_suffix(scale)
        row.add_suffix(mute)
        g.add(row)
        return g


def sound(win, conf):
    return SoundPage(win, conf).page
