"""Keyboard shortcuts: change the main actions' keys and add your own.

The list of actions, their defaults and the file they're kept in are in
shortcuts.py, which mbp-conf also reads to write each compositor's bindings.
While you press a new shortcut, the compositor is switched to a mode with no
bindings of its own (mbp-capture), so the keys reach this window instead of
opening a terminal or closing it.
"""
from gi.repository import Adw, Gdk, GLib, Gtk

from . import shortcuts as sc
from .common import action_row, group, page, run_async, spawn

MODIFIER_KEYS = {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Super_L", "Super_R",
                 "Meta_L", "Meta_R", "Hyper_L", "Hyper_R", "ISO_Level3_Shift", "ISO_Next_Group",
                 "ISO_Prev_Group", "Caps_Lock", "Num_Lock", "Mode_switch"}


def keys_text(keys):
    return "   ".join(sc.label(k) for k in keys) if keys else "Off"


def needs_no_modifier(key):
    """Keys that may be a shortcut on their own: F1-F24, Print, media keys."""
    return key == "Print" or key.startswith("XF86") or (key[:1] == "F" and key[1:].isdigit())


def combo_from_event(keyval, keycode, state):
    """The shortcut a key press makes ("Mod+Shift+q"); None for a lone modifier.
    The key is named as on the first layout without Shift (US), as the
    compositors match it, so Shift+/ is "Shift+slash", not "question"."""
    base = None
    ok, keys, vals = Gdk.Display.get_default().map_keycode(keycode)
    if ok:
        for k, v in zip(keys, vals):
            if k.group == 0 and k.level == 0:
                base = v
                break
    name = Gdk.keyval_name(base if base is not None else Gdk.keyval_to_lower(keyval)) or ""
    if not name or name in MODIFIER_KEYS:
        return None
    mods = []
    if state & Gdk.ModifierType.SUPER_MASK:
        mods.append("Mod")
    if state & Gdk.ModifierType.CONTROL_MASK:
        mods.append("Ctrl")
    if state & Gdk.ModifierType.ALT_MASK:
        mods.append("Alt")
    if state & Gdk.ModifierType.SHIFT_MASK:
        mods.append("Shift")
    return sc.normalize("+".join(mods + [name]))


class Capture:
    """Waits for one shortcut in a dialog: the compositor's own bindings are off
    meanwhile. done(shortcut) or done(None) when cancelled."""

    def __init__(self, owner, flavour, done):
        self.flavour, self.done, self.active = flavour, done, False
        ctrl = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        ctrl.connect("key-pressed", self.on_key)
        owner.add_controller(ctrl)

    def start(self):
        self.active = True
        self._mode(True)

    def stop(self):
        if self.active:
            self.active = False
            self._mode(False)

    def _mode(self, on):
        cmd = sc.capture_mode(self.flavour, on)
        if cmd:
            run_async(cmd)

    def on_key(self, ctrl, keyval, keycode, state):
        if not self.active:
            return False
        state &= Gtk.accelerator_get_default_mod_mask()
        name = Gdk.keyval_name(keyval) or ""
        if name == "Escape" and not state:
            self.stop()
            self.done(None)
            return True
        combo = combo_from_event(keyval, keycode, state)
        if combo is None:
            return True                       # a modifier on its own: wait for the key
        mods, key = sc.split(combo)
        if not mods and not needs_no_modifier(key):
            return True                       # plain letters are for typing
        self.stop()
        self.done(combo)
        return True


class ShortcutsPage:
    def __init__(self, win):
        self.win = win
        self.flavour = win.flavour or "sway"
        self.changes, self.custom = sc.load()
        self._apply_source = 0
        self.rows = {}

        self.page = page("Keyboard shortcuts", "preferences-desktop-keyboard-shortcuts-symbolic")
        intro = group(self.page, "Keyboard shortcuts",
                      "Click a shortcut to change it, add another key for it or turn it off. "
                      "⌘ is the Super key (Alt on a PC keyboard, where the two are swapped).")
        row = action_row("Open the cheat sheet", "Every shortcut, as it is now (also ⌘/ anywhere)",
                         activatable=True)
        row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        row.connect("activated", lambda *_: spawn("mbp-shortcuts", "--toggle"))
        intro.add(row)

        groups = {}
        for a in sc.ACTIONS:
            if not a.available(self.flavour):
                continue
            if a.group not in groups:
                groups[a.group] = group(self.page, a.group)
            r = action_row(a.label, activatable=True)
            keys = Gtk.Label(css_classes=["dim-label"])
            r.add_suffix(keys)
            r.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            r.connect("activated", lambda _r, a=a: self.edit_action(a))
            groups[a.group].add(r)
            self.rows[a.id] = (r, keys)

        add = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add a shortcut",
                         css_classes=["flat"], valign=Gtk.Align.CENTER)
        add.connect("clicked", lambda *_: self.edit_custom(None))
        self.own = group(self.page, "Your own", "Shortcuts that run a command of your choice.", suffix=add)
        self.own_rows = []

        fixed = group(self.page, "Fixed",
                      "Moving around stays on these keys; a new shortcut can't take them.")
        exp = Adw.ExpanderRow(title="Keys that can't be changed")
        for name, keys in sc.FIXED:
            exp.add_row(action_row(name, "   ".join(sc.label(k) for k in keys)))
        fixed.add(exp)

        reset = action_row("Reset every shortcut", "Back to the defaults; your own shortcuts stay",
                           activatable=True)
        reset.add_css_class("error")
        reset.connect("activated", lambda *_: self.reset_all())
        fixed.add(reset)
        self.refresh()

    # ---- the list ----------------------------------------------------------------
    def keys_of(self, a):
        return self.changes.get(a.id, a.default_for(self.flavour))

    def refresh(self):
        for a in sc.ACTIONS:
            if a.id in self.rows:
                r, label = self.rows[a.id]
                label.set_label(keys_text(self.keys_of(a)))
                r.set_subtitle("Changed" if a.id in self.changes else "")
        for r in self.own_rows:
            self.own.remove(r)
        self.own_rows = []
        for i, (keys, command) in enumerate(self.custom):
            r = action_row(command, activatable=True)
            r.add_suffix(Gtk.Label(label=sc.label(keys), css_classes=["dim-label"]))
            r.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            r.connect("activated", lambda _r, i=i: self.edit_custom(i))
            self.own.add(r)
            self.own_rows.append(r)

    def set_keys(self, a, keys):
        keys = list(dict.fromkeys(keys))
        if keys == a.default_for(self.flavour):
            self.changes.pop(a.id, None)
        else:
            self.changes[a.id] = keys

    def save(self):
        try:
            sc.save(self.changes, self.custom)
        except OSError as e:
            self.win.toast(f"Couldn't save the shortcuts: {e.strerror}")
            return
        self.refresh()
        if self._apply_source:
            GLib.source_remove(self._apply_source)
        self._apply_source = GLib.timeout_add(400, self._apply)

    def _apply(self):
        self._apply_source = 0
        run_async(["mbp-conf", "shortcuts"])
        return False

    def reset_all(self):
        if not self.changes:
            self.win.toast("Every shortcut already has its default keys")
            return
        d = Adw.AlertDialog(heading="Reset every shortcut?",
                            body="The main actions go back to their default keys. Your own shortcuts stay.")
        d.add_response("cancel", "Cancel")
        d.add_response("reset", "Reset")
        d.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
        d.set_close_response("cancel")

        def answered(_d, response):
            if response == "reset":
                self.changes = {}
                self.save()
        d.connect("response", answered)
        d.present(self.win)

    # ---- taking a shortcut that's in use -----------------------------------------------
    def claim(self, combo, subject, then):
        """Check who has `combo`; if it's free, or the user agrees to take it from its
        owner, call then(). subject: ("action", id) / ("custom", index) / None (new)."""
        who = sc.owner(combo, self.flavour, self.changes, self.custom, skip=subject)
        if who is None:
            then()
            return
        kind, what = who
        if kind == "fixed":
            self.win.toast(f"{sc.label(combo)} is fixed ({what}); pick another")
            return
        name = what.label if kind == "action" else f"your shortcut “{self.custom[what][1]}”"
        d = Adw.AlertDialog(heading=f"{sc.label(combo)} is taken",
                            body=f"It's used by {name}. Take it for this one instead?")
        d.add_response("cancel", "Cancel")
        d.add_response("take", "Take it")
        d.set_response_appearance("take", Adw.ResponseAppearance.SUGGESTED)
        d.set_close_response("cancel")

        def answered(_d, response):
            if response != "take":
                return
            if kind == "action":
                self.set_keys(what, [k for k in self.keys_of(what) if k != combo])
            else:
                del self.custom[what]
            then()
        d.connect("response", answered)
        d.present(self.win)

    # ---- an action's keys ----------------------------------------------------------
    def edit_action(self, a):
        dialog = Adw.Dialog(title=a.label, content_width=420)
        view = Adw.ToolbarView()
        view.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=18, margin_start=18, margin_end=18)
        listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        prompt = Gtk.Label(label="Press the new shortcut…  (Esc cancels)", visible=False,
                           css_classes=["title-4"], margin_top=6, margin_bottom=6)
        buttons = Gtk.Box(spacing=8, homogeneous=True)
        add = Gtk.Button(label="Add a shortcut")
        reset = Gtk.Button(label="Reset to default")
        buttons.append(add)
        buttons.append(reset)
        box.append(listbox)
        box.append(prompt)
        box.append(buttons)
        view.set_content(box)
        dialog.set_child(view)

        def fill():
            while (child := listbox.get_first_child()):
                listbox.remove(child)
            keys = self.keys_of(a)
            if not keys:
                listbox.append(action_row("No shortcut", "Off: add one to use it from the keyboard"))
            for k in keys:
                r = action_row(sc.label(k))
                rm = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Remove this shortcut",
                                css_classes=["flat"], valign=Gtk.Align.CENTER)
                rm.connect("clicked", lambda *_, k=k: remove(k))
                r.add_suffix(rm)
                listbox.append(r)
            reset.set_sensitive(a.id in self.changes)

        def remove(k):
            self.set_keys(a, [x for x in self.keys_of(a) if x != k])
            self.save()
            fill()

        def captured(combo):
            prompt.set_visible(False)
            buttons.set_sensitive(True)
            if combo is None or combo in self.keys_of(a):
                return

            def take():
                self.set_keys(a, self.keys_of(a) + [combo])
                self.save()
                fill()
            self.claim(combo, ("action", a.id), take)

        capture = Capture(dialog, self.flavour, captured)

        def start(*_):
            prompt.set_visible(True)
            buttons.set_sensitive(False)
            capture.start()

        def do_reset(*_):
            self.changes.pop(a.id, None)
            # The defaults may be taken by now; give them back from whoever has them.
            for k in a.default_for(self.flavour):
                who = sc.owner(k, self.flavour, self.changes, self.custom, skip=("action", a.id))
                if who and who[0] == "action":
                    self.set_keys(who[1], [x for x in self.keys_of(who[1]) if x != k])
                elif who and who[0] == "custom":
                    del self.custom[who[1]]
            self.save()
            fill()

        add.connect("clicked", start)
        reset.connect("clicked", do_reset)
        dialog.connect("closed", lambda *_: capture.stop())
        fill()
        dialog.present(self.win)

    # ---- your own shortcuts -----------------------------------------------------------
    def edit_custom(self, index):
        orig = self.custom[index] if index is not None else None
        keys, command = orig or (None, "")
        state = {"keys": keys}
        dialog = Adw.Dialog(title="Your shortcut" if index is not None else "Add a shortcut", content_width=440)
        view = Adw.ToolbarView()
        header = Adw.HeaderBar(show_end_title_buttons=False, show_start_title_buttons=False)
        cancel = Gtk.Button(label="Cancel")
        save = Gtk.Button(label="Save", css_classes=["suggested-action"])
        header.pack_start(cancel)
        header.pack_end(save)
        view.add_top_bar(header)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=18, margin_start=18, margin_end=18)
        listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        entry = Adw.EntryRow(title="Command, e.g. foot btop")
        entry.set_text(command)
        key_row = action_row("Shortcut", activatable=True)
        key_label = Gtk.Label(css_classes=["dim-label"])
        key_row.add_suffix(key_label)
        listbox.append(entry)
        listbox.append(key_row)
        prompt = Gtk.Label(label="Press the new shortcut…  (Esc cancels)", visible=False,
                           css_classes=["title-4"], margin_top=6)
        box.append(listbox)
        box.append(prompt)
        if index is not None:
            delete = Gtk.Button(label="Delete this shortcut", css_classes=["destructive-action"],
                                halign=Gtk.Align.CENTER, margin_top=6)
            box.append(delete)

            def do_delete(*_):
                if orig in self.custom:
                    self.custom.remove(orig)
                self.save()
                dialog.close()
            delete.connect("clicked", do_delete)
        view.set_content(box)
        dialog.set_child(view)

        def update():
            key_label.set_label(sc.label(state["keys"]) if state["keys"] else "Click to set")
            save.set_sensitive(bool(state["keys"] and entry.get_text().strip()))

        def captured(combo):
            prompt.set_visible(False)
            if combo:
                state["keys"] = combo
            update()

        capture = Capture(dialog, self.flavour, captured)

        def start(*_):
            prompt.set_visible(True)
            key_label.set_label("…")
            capture.start()

        def do_save(*_):
            combo, cmd = state["keys"], entry.get_text().strip()

            def store():
                item = (combo, cmd)
                if orig in self.custom:        # (taking a key may have removed others before it)
                    self.custom[self.custom.index(orig)] = item
                else:
                    self.custom.append(item)
                self.save()
                dialog.close()
            self.claim(combo, ("custom", index) if index is not None else None, store)

        key_row.connect("activated", start)
        entry.connect("changed", lambda *_: update())
        cancel.connect("clicked", lambda *_: dialog.close())
        save.connect("clicked", do_save)
        dialog.connect("closed", lambda *_: capture.stop())
        update()
        dialog.present(self.win)


def keyboard_shortcuts(win, conf):
    view = ShortcutsPage(win)
    view.page.shortcuts = view          # keep it alive with its page
    return view.page
