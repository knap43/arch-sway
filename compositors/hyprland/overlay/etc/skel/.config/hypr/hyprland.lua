-- Hyprland (0.57+, Lua config): the same keymap and conventions as the sway
-- flavour. Mod = Super: ⌘ on the MacBook; on a PC keyboard Alt and Win trade
-- places, so it is the Alt key there (see "Input").
-- Effects (blur, shadows, animations, rounding) are off: light on old GPUs.
-- Reference: https://wiki.hypr.land/configuring/ (checked against the wiki, Nov 2026)

local mod  = "SUPER"
local term = "foot"
local menu = "fuzzel"

-------------------------------------------------------------------------------
-- Monitor, look
-------------------------------------------------------------------------------

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

hl.config({
    general = {
        gaps_in = 0,
        gaps_out = 0,
        border_size = 2,
        col = {
            active_border = "rgb(5e81ac)",
            inactive_border = "rgb(2a2a2a)",
        },
        resize_on_border = false,
        layout = "dwindle",                  -- tiled by default
    },
    decoration = {
        rounding = 0,
        shadow = { enabled = false },
        blur = { enabled = false },
    },
    animations = { enabled = false },
    dwindle = { preserve_split = true },
    group = {
        col = { border_active = "rgb(5e81ac)", border_inactive = "rgb(2a2a2a)" },
        groupbar = {
            font_size = 10,
            height = 18,
            col = { active = "rgb(5e81ac)", inactive = "rgb(2a2a2a)" },
        },
    },
    misc = {
        force_default_wallpaper = 0,
        disable_hyprland_logo = true,
        disable_splash_rendering = true,
        focus_on_activate = true,
    },
})

-------------------------------------------------------------------------------
-- Input
-------------------------------------------------------------------------------

-- On a PC keyboard (anything but a Mac) Alt and Win trade places, so Super is
-- the key next to the space bar, as ⌘ is on the MacBook; Alt+Shift still
-- switches layout. mbp:swap_alt_win is defined in /etc/xkb, and this is the
-- same choice /usr/local/bin/mbp-xkb-options makes (MBP_SWAP_ALT_WIN=0|1 overrides).
local function swap_alt_win()
    local force = os.getenv("MBP_SWAP_ALT_WIN")
    if force == "0" or force == "1" then return force == "1" end
    local f = io.open("/sys/class/dmi/id/sys_vendor")
    local vendor = f and f:read("*l") or ""
    if f then f:close() end
    return vendor:sub(1, 5) ~= "Apple"
end

hl.config({
    input = {
        kb_layout = "us,ru",
        -- Alt+Shift switches layout; Caps Lock and Escape are swapped.
        kb_options = swap_alt_win() and "caps:swapescape,mbp:swap_alt_win"
                                     or "grp:alt_shift_toggle,caps:swapescape",
        -- Binds follow the first layout (US), so they also work in Russian.
        resolve_binds_by_sym = false,
        repeat_delay = 300,
        repeat_rate = 35,
        follow_mouse = 0,                    -- focus follows clicks, not the pointer
        touchpad = {
            tap_to_click = true,
            natural_scroll = true,
            disable_while_typing = true,
            clickfinger_behavior = true,
        },
    },
})

-------------------------------------------------------------------------------
-- Autostart
-------------------------------------------------------------------------------

hl.on("hyprland.start", function()
    hl.exec_cmd("waybar")
    hl.exec_cmd("swaybg -i /usr/share/backgrounds/mbp/wallpaper.jpg -m fill -c 1e1e1e")
    -- Notifications, tray icons, clipboard history, night light, popups, idle
    -- lock/suspend, Tether and (on the live USB) the walkthrough: shared by
    -- every compositor flavour, see /usr/local/bin/mbp-session-start.
    hl.exec_cmd("mbp-session-start")
end)

-------------------------------------------------------------------------------
-- Helpers
-------------------------------------------------------------------------------

-- Mod+S: the next workspace to the right; past the last one, a fresh empty
-- one (unless you're already on an empty one). move = take the window along.
local function workspace_next(move)
    local cur = hl.get_active_workspace()
    if not cur or not cur.id then return end
    local target
    for _, ws in ipairs(hl.get_workspaces()) do
        if not ws.special and ws.id and ws.id > cur.id
            and (not cur.monitor or not ws.monitor or ws.monitor.id == cur.monitor.id)
            and (not target or ws.id < target) then
            target = ws.id
        end
    end
    if not target then
        if (cur.windows or 0) == 0 then return end
        target = cur.id + 1
    end
    if move then
        hl.dispatch(hl.dsp.window.move({ workspace = target, follow = true }))
    else
        hl.dispatch(hl.dsp.focus({ workspace = target }))
    end
end

-- Mod+Tab: cycle through every window on every workspace (like Alt+Tab).
local function cycle_all(step)
    local wins = {}
    for _, w in ipairs(hl.get_windows()) do
        if w.mapped and not w.hidden and w.workspace and not w.workspace.special then
            wins[#wins + 1] = w
        end
    end
    if #wins == 0 then return end
    table.sort(wins, function(a, b)
        if a.workspace.id ~= b.workspace.id then return a.workspace.id < b.workspace.id end
        return a.stable_id < b.stable_id
    end)
    local idx = 0
    for i, w in ipairs(wins) do
        if w.active then idx = i end
    end
    local target = wins[((idx - 1 + step) % #wins) + 1]
    if idx == 0 then target = wins[1] end
    hl.dispatch(hl.dsp.focus({ window = target }))
end

-- Mod+Shift+Space: switch focus between floating and tiled windows.
local function focus_mode_toggle()
    local w = hl.get_active_window()
    if w and w.floating then
        hl.dispatch(hl.dsp.window.cycle_next({ tiled = true }))
    else
        hl.dispatch(hl.dsp.window.cycle_next({ floating = true }))
    end
end

-- Mod+[ / Mod+]: in a tab group (Mod+, or Mod+T) the previous / next tab, as
-- in sway; otherwise the previous / next window on this workspace.
local function tab_or_window(forward)
    local w = hl.get_active_window()
    if w and w.group and (w.group.size or 0) > 1 then
        hl.dispatch(forward and hl.dsp.group.next() or hl.dsp.group.prev())
    else
        hl.dispatch(hl.dsp.window.cycle_next({ next = forward }))
    end
end

local function bind(keys, action, opts) hl.bind(mod .. " + " .. keys, action, opts) end
local function run(cmd) return hl.dsp.exec_cmd(cmd) end

-------------------------------------------------------------------------------
-- Apps
-------------------------------------------------------------------------------

bind("D",      run(term))
bind("Return", run(term))
bind("space",  run(menu))
bind("Q",      run(menu))
bind("E",      run("thunar"))
bind("B",      run("librewolf"))
bind("V",      run('cliphist list | fuzzel --dmenu --prompt "Clipboard: " | cliphist decode | wl-copy'))

-------------------------------------------------------------------------------
-- Windows
-------------------------------------------------------------------------------

bind("W",            hl.dsp.window.close())
bind("Tab",          function() cycle_all(1) end)
bind("SHIFT + Tab",  function() cycle_all(-1) end)
bind("bracketleft",  function() tab_or_window(false) end)
bind("bracketright", function() tab_or_window(true) end)
bind("F",            hl.dsp.window.fullscreen())
bind("SHIFT + F",    hl.dsp.window.float({ action = "toggle" }))
bind("SHIFT + space", focus_mode_toggle)

-- Focus / move with Mod+H J K L or arrows (add Shift to move the window)
for key, dir in pairs({ H = "l", J = "d", K = "u", L = "r",
                        left = "l", down = "d", up = "u", right = "r" }) do
    bind(key,              hl.dsp.focus({ direction = dir }))
    bind("SHIFT + " .. key, hl.dsp.window.move({ direction = dir }))
end

-- Drag with Mod + left button, resize with Mod + right button
bind("mouse:272", hl.dsp.window.drag(),   { mouse = true })
bind("mouse:273", hl.dsp.window.resize(), { mouse = true })

-------------------------------------------------------------------------------
-- Workspaces
-------------------------------------------------------------------------------

-- Mod+A / Mod+S: previous / next. Past the last one, Mod+S opens a fresh one.
bind("A",         hl.dsp.focus({ workspace = "m-1" }))
bind("S",         function() workspace_next(false) end)
bind("SHIFT + A", hl.dsp.window.move({ workspace = "m-1", follow = true }))
bind("SHIFT + S", function() workspace_next(true) end)

for i = 1, 10 do
    local key = tostring(i % 10)             -- workspace 10 is on the 0 key
    bind(key,              hl.dsp.focus({ workspace = i }))
    bind("SHIFT + " .. key, hl.dsp.window.move({ workspace = i, follow = false }))
end

-------------------------------------------------------------------------------
-- Layout
-------------------------------------------------------------------------------

bind("backslash", hl.dsp.layout("preselect r"))   -- next window opens to the right
bind("minus",     hl.dsp.layout("preselect d"))   -- next window opens below
bind("period",    hl.dsp.layout("togglesplit"))   -- tiling: flip the split
bind("comma",     hl.dsp.group.toggle())          -- tabbed (a window group)
bind("T",         hl.dsp.group.toggle())          -- (no stacked layout: tabs too)
bind("grave",         hl.dsp.workspace.toggle_special("scratch"))
bind("SHIFT + grave", hl.dsp.window.move({ workspace = "special:scratch", follow = false }))

bind("R", hl.dsp.submap("resize"))
hl.define_submap("resize", function()
    local step = 20
    for key, d in pairs({ H = { -step, 0 }, left = { -step, 0 }, L = { step, 0 }, right = { step, 0 },
                          K = { 0, -step }, up = { 0, -step }, J = { 0, step }, down = { 0, step } }) do
        hl.bind(key, hl.dsp.window.resize({ x = d[1], y = d[2], relative = true }), { repeating = true })
    end
    hl.bind("Return", hl.dsp.submap("reset"))
    hl.bind("Escape", hl.dsp.submap("reset"))
end)

-------------------------------------------------------------------------------
-- System
-------------------------------------------------------------------------------

bind("CTRL + S",         run("mbp-screenshot"))
bind("CTRL + SHIFT + S", run("mbp-screenshot --full"))
bind("Escape",           run("mbp-power-menu"))
bind("SHIFT + Q",        run("mbp-power-menu"))
bind("SHIFT + C",        hl.dsp.reload_config())
bind("N",                run("mbp-nightlight toggle"))

-- Laptop function keys (work on the lock screen too); levels pop up via wob
local locked = { locked = true, repeating = true }
hl.bind("XF86MonBrightnessUp",   run("mbp-osd brightness up"),   locked)
hl.bind("XF86MonBrightnessDown", run("mbp-osd brightness down"), locked)
hl.bind("XF86KbdBrightnessUp",   run("mbp-osd keyboard up"),     locked)
hl.bind("XF86KbdBrightnessDown", run("mbp-osd keyboard down"),   locked)
hl.bind("XF86AudioRaiseVolume",  run("mbp-osd volume up"),       locked)
hl.bind("XF86AudioLowerVolume",  run("mbp-osd volume down"),     locked)
hl.bind("XF86AudioMute",         run("mbp-osd volume mute"),     { locked = true })
hl.bind("XF86AudioPlay",         run("playerctl play-pause"),    { locked = true })
hl.bind("XF86AudioNext",         run("playerctl next"),          { locked = true })
hl.bind("XF86AudioPrev",         run("playerctl previous"),      { locked = true })

-------------------------------------------------------------------------------
-- Window rules
-------------------------------------------------------------------------------

hl.window_rule({ name = "float-pavucontrol", match = { class = "^(org.pulseaudio.pavucontrol|pavucontrol)$" },
                 float = true })
hl.window_rule({ name = "float-nm-editor", match = { class = "^nm-connection-editor$" }, float = true })
hl.window_rule({ name = "live-welcome", match = { class = "^live-welcome$" },
                 float = true, size = "780 560", center = true })
hl.window_rule({ name = "suppress-maximize", match = { class = ".*" }, suppress_event = "maximize" })

-- Managed by wmai (keep this last so its settings win)
require("ai")
