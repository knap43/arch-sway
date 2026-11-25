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

-- Desktop settings (mbp-settings), written for this machine by mbp-conf:
-- keyboard, touchpad, focus follows mouse, default layout and display scale.
local S = {}
do
    local ok, t = pcall(dofile, (os.getenv("HOME") or "") .. "/.config/mbp/generated/hyprland.lua")
    if ok and type(t) == "table" then S = t end
end
local function setting(key, default)
    if S[key] == nil then return default end
    return S[key]
end

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })
for _, m in ipairs(setting("monitors", {})) do
    hl.monitor({ output = m.output, mode = "preferred", position = "auto", scale = m.scale })
end
-- Displays arranged in the Displays panel (mode, position, scale, rotation, off)
for _, m in ipairs(setting("displays", {})) do hl.monitor(m) end

hl.config({
    general = {
        gaps_in = setting("gaps_in", 0),
        gaps_out = setting("gaps_out", 0),
        border_size = setting("border_size", 2),
        col = {
            active_border = "rgb(" .. setting("accent", "5e81ac") .. ")",
            inactive_border = "rgb(2a2a2a)",
        },
        resize_on_border = false,
        layout = "dwindle",                  -- tiles inside, but windows open tabbed (see "Tabbed by default")
    },
    decoration = {
        rounding = setting("rounding", 0),
        inactive_opacity = setting("inactive_opacity", 1),
        shadow = { enabled = setting("shadows", false) },
        blur = { enabled = setting("blur", false) },
    },
    animations = { enabled = setting("animations", false) },
    -- New windows always open to the right (or below), not on the cursor's side
    dwindle = { preserve_split = true, force_split = 2 },
    group = {
        auto_group = true,                   -- new windows join the focused tab group
        group_on_movetoworkspace = true,     -- and so do windows sent to another workspace
        col = { border_active = "rgb(" .. setting("accent", "5e81ac") .. ")", border_inactive = "rgb(2a2a2a)" },
        groupbar = {
            font_size = 10,
            height = 18,
            col = { active = "rgb(" .. setting("accent", "5e81ac") .. ")", inactive = "rgb(2a2a2a)" },
            text_color = "rgb(" .. setting("accent_text", "ffffff") .. ")",
            text_color_inactive = "rgb(888888)",
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

hl.config({
    -- Hide the pointer after a few idle seconds and while typing (Settings → Mouse)
    cursor = {
        inactive_timeout = setting("hide_cursor_sec", 3),
        hide_on_key_press = setting("hide_cursor_typing", true),
    },
    input = {
        kb_layout = setting("kb_layout", "us,ru"),
        -- Alt+Shift switches layout (on a PC: the Win key, which sends Alt, as
        -- Alt and Win trade places there; on a Mac: Option); Caps Lock and
        -- Escape are swapped. mbp:swap_alt_win is defined in /etc/xkb.
        kb_options = setting("kb_options", "grp:alt_shift_toggle,caps:swapescape"),
        -- Binds follow the first layout (US), so they also work in Russian.
        resolve_binds_by_sym = false,
        repeat_delay = setting("repeat_delay", 300),
        repeat_rate = setting("repeat_rate", 35),
        follow_mouse = setting("follow_mouse", 1),   -- focus follows the pointer
        sensitivity = setting("sensitivity", 0),
        left_handed = setting("left_handed", false),
        touchpad = {
            tap_to_click = setting("tap_to_click", true),
            natural_scroll = setting("natural_scroll", true),
            disable_while_typing = setting("disable_while_typing", true),
            clickfinger_behavior = true,
        },
    },
})

-------------------------------------------------------------------------------
-- Autostart
-------------------------------------------------------------------------------

hl.on("hyprland.start", function()
    hl.exec_cmd("waybar")
    hl.exec_cmd("mbp-conf wallpaper")
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

-- Mod+Shift+Tab: cycle through every window on every workspace (like Alt+Tab).
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

-- With animations on (Settings → Appearance), they're for windows only: the
-- launcher, menus, bar and notifications (layers, popups) appear at once.
hl.animation({ leaf = "layers", enabled = false })
hl.animation({ leaf = "fadeLayers", enabled = false })
hl.animation({ leaf = "fadePopups", enabled = false })

-- Three-finger horizontal swipe on the touchpad switches workspaces
if setting("swipe", true) then
    hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
end

-- ---- Tabbed by default -------------------------------------------------------
-- Like the sway flavour, new workspaces start tabbed. Hyprland's tabs are
-- window groups: the first tiled window on a workspace becomes a group, later
-- ones join the focused group (auto_group), and windows sent to a workspace
-- join its group (group_on_movetoworkspace). After Mod+. (tiled), new windows
-- tile alongside as usual; Mod+, makes the workspace tabbed again.
local function first_tiled_on_workspace(w)
    if not w or w.floating or w.group or not w.workspace or w.workspace.special then return false end
    for _, other in ipairs(hl.get_windows()) do
        if other.mapped and not other.floating and other.workspace
            and other.workspace.id == w.workspace.id and other.stable_id ~= w.stable_id then
            return false
        end
    end
    return true
end

-- Checked a moment later, once auto_group / group_on_movetoworkspace have had
-- their say, so a window is never wrapped in a group beside the one it joined.
local function tab_if_first(w)
    hl.timer(function()
        local cur = hl.get_window(w)
        if setting("tabbed", true) and first_tiled_on_workspace(cur) then hl.dispatch(hl.dsp.group.toggle({ window = cur })) end
    end, { timeout = 50, type = "oneshot" })
end
hl.on("window.open", tab_if_first)
hl.on("window.move_to_workspace", tab_if_first)   -- e.g. sent to an empty workspace

-- Mod+, / Mod+T: the whole workspace as tabs (sway's "layout tabbed").
local function tab_workspace()
    local w = hl.get_active_window()
    if not w or w.floating or not w.workspace then return end
    if not w.group then
        hl.dispatch(hl.dsp.group.toggle({ window = w }))
        w = hl.get_active_window()
        if not w or not w.group then return end
    end
    for _, other in ipairs(hl.get_windows()) do
        if other.mapped and not other.floating and not other.group and other.workspace
            and other.workspace.id == w.workspace.id and other.stable_id ~= w.stable_id then
            w.group:add(other)
        end
    end
end

-- Mod+.: tiled (sway's "layout toggle split"): break the tabs apart, or, when
-- the windows are already tiled, flip the split direction.
local function tile_or_flip()
    local w = hl.get_active_window()
    if w and w.group then
        hl.dispatch(hl.dsp.group.toggle({ window = w }))
    else
        hl.dispatch(hl.dsp.layout("togglesplit"))
    end
end

-- Mod+G: float every window on this workspace, or, if they all float already,
-- tile them again (Mango's toggle_all_floating; none of the three has a
-- floating layout as such). Tab groups are broken up first.
local function toggle_all_floating()
    local ws = hl.get_active_workspace()
    if not ws or not ws.id then return end
    local wins, any_tiled = {}, false
    for _, w in ipairs(hl.get_windows()) do
        if w.mapped and w.workspace and w.workspace.id == ws.id then
            wins[#wins + 1] = w
            any_tiled = any_tiled or not w.floating
        end
    end
    if any_tiled then
        for _, w in ipairs(wins) do
            local cur = hl.get_window(w)
            if cur and cur.group then hl.dispatch(hl.dsp.group.toggle({ window = cur })) end
        end
    end
    for _, w in ipairs(wins) do
        hl.dispatch(hl.dsp.window.float({ action = any_tiled and "set" or "unset", window = w }))
    end
end

-- Mod+Return (tiled): the window takes the left half of the screen and the
-- rest share the right half. movetoroot makes it one side of the top split;
-- then it's turned side by side, put on the left and set to 50/50.
local function xy(v)
    if type(v) ~= "table" then return nil end
    return v.x or v[1], v.y or v[2]
end
local function to_left_half()
    local w = hl.get_active_window()
    if not w or w.floating then return end
    hl.dispatch(hl.dsp.layout("movetoroot"))
    local function step(fn) hl.timer(fn, { timeout = 30, type = "oneshot" }) end
    step(function()
        local cur = hl.get_window(w)
        local mon = cur and cur.monitor
        if not cur or not mon then return end
        local mw = mon.width / (mon.scale or 1)
        local sw = xy(cur.size)
        if sw and sw > mw * 0.75 then                  -- top/bottom split: make it side by side
            hl.dispatch(hl.dsp.layout("togglesplit"))
        end
        step(function()
            cur = hl.get_window(w)
            local x = cur and xy(cur.at)
            local mx = mon.x or (mon.position and mon.position.x) or 0
            if x and x > mx + mw / 4 then              -- it ended up on the right
                hl.dispatch(hl.dsp.layout("swapsplit"))
            end
            hl.dispatch(hl.dsp.layout("splitratio 1 exact"))
        end)
    end)
end

-- Mod+Tab: switch the workspace between tabbed and tiled.
local function tabs_or_tiles()
    local w = hl.get_active_window()
    if w and w.group then
        hl.dispatch(hl.dsp.group.toggle({ window = w }))
    else
        tab_workspace()
    end
end

local function bind(keys, action, opts) hl.bind(mod .. " + " .. keys, action, opts) end
local function run(cmd) return hl.dsp.exec_cmd(cmd) end

-------------------------------------------------------------------------------
-- Apps
-------------------------------------------------------------------------------

bind("D",      run(term))
bind("space",  run(menu))
bind("Q",      run(menu))
bind("E",      run("thunar"))
bind("B",      run("flatpak run app.zen_browser.zen"))
bind("V",      run('cliphist list | fuzzel --dmenu --prompt "Clipboard: " | cliphist decode | wl-copy'))

-------------------------------------------------------------------------------
-- Windows
-------------------------------------------------------------------------------

bind("W",            hl.dsp.window.close())
bind("Tab",          tabs_or_tiles)                -- tabbed <-> tiled
bind("SHIFT + Tab",  function() cycle_all(1) end)  -- every window, everywhere
bind("bracketleft",  function() tab_or_window(false) end)
bind("bracketright", function() tab_or_window(true) end)
bind("F",            hl.dsp.window.fullscreen())
bind("SHIFT + F",    hl.dsp.window.float({ action = "toggle" }))
bind("SHIFT + space", focus_mode_toggle)

-- Mod+H J K L resize (narrower, taller, shorter, wider; hold to repeat), Mod+arrows
-- focus, and Shift with either moves the window
for key, dir in pairs({ H = "l", J = "d", K = "u", L = "r",
                        left = "l", down = "d", up = "u", right = "r" }) do
    if #key > 1 then bind(key, hl.dsp.focus({ direction = dir })) end
    bind("SHIFT + " .. key, hl.dsp.window.move({ direction = dir }))
end
for key, d in pairs({ H = { -20, 0 }, J = { 0, 20 }, K = { 0, -20 }, L = { 20, 0 } }) do
    bind(key, hl.dsp.window.resize({ x = d[1], y = d[2], relative = true }), { repeating = true })
end
-- Mod+/: the keyboard shortcuts cheat sheet
bind("slash", run("mbp-shortcuts --toggle"))

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
bind("period",    tile_or_flip)                   -- tiled (again: flip the split)
bind("comma",     tab_workspace)                  -- tabbed
bind("T",         tab_workspace)                  -- (no stacked layout: tabs too)
bind("Return",    to_left_half)                   -- tiled: this window takes the left half
bind("G",         toggle_all_floating)            -- float / tile every window here
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
hl.window_rule({ name = "mbp-shortcuts", match = { class = "^mbp-shortcuts$" },
                 float = true, size = "820 640", center = true })
hl.window_rule({ name = "settings", match = { class = "^org\\.mbp\\.Settings$" },
                 float = true, size = "1020 700", center = true })
hl.window_rule({ name = "suppress-maximize", match = { class = ".*" }, suppress_event = "maximize" })

-- No border when one tiled window fills the screen (Settings → Appearance): w[tv1]
-- is a workspace with one visible tiled window, which includes a tab group (only its
-- current tab is visible), f[1] one in fullscreen. Floating windows keep theirs.
if setting("smart_borders", true) then
    hl.window_rule({ name = "smart-borders", match = { float = false, workspace = "w[tv1]" }, border_size = 0 })
    hl.window_rule({ name = "smart-borders-fs", match = { float = false, workspace = "f[1]" }, border_size = 0 })
end

