# mbp — Arch Linux ISOs with sway, Hyprland or Mango

Live USBs that boot straight into a configured tiling session, plus a one-shot installer
that puts the same system on the internal disk. Made for the 2011 MacBook Pro 13″
(A1278 / MacBookPro8,1) and the ThinkPad T460s, and fine on most Intel laptops.

There are three flavours. Each has the same apps, keys and look; only the compositor differs.

| Flavour | Compositor | New workspaces open | Bar |
|---|---|---|---|
| `sway` (default) | sway | tabbed | swaybar + i3status |
| `hyprland` | Hyprland 0.57 (Lua config) | tabbed | Waybar |
| `mango` | Mango (mangowm) 0.18 | tabbed | Waybar |

## Build (on your Arch machine)

```sh
sudo pacman -S --needed archiso
./build.sh              # sway
./build.sh hyprland
./build.sh mango
```

The ISO lands in `out/` as `mbp-<flavour>-<date>-x86_64.iso`. The build needs ~15 GB free and
internet access. Besides the live system, the ISO carries a small package repository with
everything the installed system needs (~1.5 GB), so installing works offline. Those packages land
in your normal pacman cache, which the ISO build uses anyway, so nothing is downloaded twice.
It is layered on Arch's official `releng` profile, so it stays current with archiso.

## Write to USB

```sh
lsblk                                   # find the stick, e.g. /dev/sdb
sudo dd bs=4M if=out/mbp-sway-*.iso of=/dev/sdX status=progress oflag=sync
```

## Boot & install

1. **MacBook:** hold **Option (⌥)** at the chime and pick **EFI Boot**.
   **ThinkPad:** press **F12** at the red logo and pick the USB stick. If it refuses to boot,
   turn off *Secure Boot* in the setup (Enter, then F1).
2. The session starts automatically (user `live`, no password) and a **welcome window** opens.
   It shows the essential shortcuts and what the installer will do:
   - **Installing needs no internet.** Every package is on the stick, so the installer works offline.
   - **W** picks a Wi-Fi network (or use the network icon in the bar). Networks you join here are
     saved in the new system **with their passwords**.
   - **K** lists every shortcut for this flavour.
   - **Enter** starts the installer. It asks for disk, hostname, user, password, timezone and
     language, then **wipes the whole disk** (macOS or Windows included) and installs.
   - **Q** closes the window; reopen it from the launcher as *Install to Disk*
     (or run `sudo mbp-install` in a terminal).
3. When it's done, press Enter to power off. **Keep the stick in until the machine is off** —
   the live system runs from it right to the end — then remove it and turn the machine on.
   Log in on the console — the compositor starts by itself.

## What's in it

| Area | Choice |
|---|---|
| Graphics | Intel HD 3000 (MacBook, Mesa crocus) and HD 520 (ThinkPad, Mesa iris), early KMS, VA-API video decoding, Xwayland |
| Wi-Fi | NetworkManager + nm-applet. MacBook: `broadcom-wl-dkms` (BCM4331, built for the kernel at install); ThinkPad: iwlwifi from `linux-firmware`. `wheel` users manage networks without a password prompt, and Wi-Fi passwords are stored system-wide |
| Session | sway, Hyprland or Mango; swayidle/swaylock, mako, fuzzel, foot, wob popups |
| Shell | fish (starts the compositor on tty1) |
| Audio | PipeWire + WirePlumber, pavucontrol |
| Power | TLP, zram swap (zstd); lock at 5 min idle, screen off at 10, suspend at 15 on battery; battery warnings at 15% and 5% |
| Devices | USB drives auto-mount (udiskie, tray icon), Bluetooth tray (blueman), touchpad tap-to-click, TrackPoint |
| Apps | btop, fastfetch, nnn (terminal file manager), Flatpak (Flathub added; apps show up in the launcher), LibreWolf, mpv (hardware decoding on; F7–F9 control it via mpv-mpris), kew (terminal music player; F7–F9 control it), Thunar, Ristretto, Zathura, Mousepad, Xarchiver |
| Dev | git, base-devel, vim, Python + PyGObject, GTK 4, libadwaita |
| Boot | systemd-boot on UEFI (GRUB if booted in legacy/BIOS mode) |

## Keys (⌘ = Mod)

⌘ is the Command key on the MacBook. On a PC keyboard such as the ThinkPad's, Alt and the Windows key
trade places, so ⌘ is the key next to the space bar there too (the Alt key), and Alt moves to the
Windows key, so the layout switch is **Win ⇧** there (Option ⇧ on the MacBook: the same spot, just left of ⌘). The choice is made per machine (anything but a Mac swaps); *Settings* →
Keyboard can turn it on or off for good. All shortcuts work in
both the US and Russian layouts. Caps Lock and Escape are swapped. These are the same in every flavour:

| Keys | Action |
|---|---|
| ⌘ D | terminal |
| ⌘ Space / ⌘ Q | app launcher |
| ⌘ E / ⌘ B | Thunar / LibreWolf |
| ⌘ V | clipboard history |
| ⌘ W | close window |
| ⌘ [ / ⌘ ] | previous / next window on this workspace |
| ⌘ H J L or arrows | focus (up: ⌘ ↑); add ⇧ to move the window (up: ⌘ ⇧ K) |
| ⌘ K | keyboard shortcuts cheat sheet (⌘ K or Esc closes it) |
| ⌘ ⇧ A / ⌘ ⇧ S | take the window to the previous / next workspace |
| ⌘ F / ⌘ ⇧ F | fullscreen / floating |
| ⌘ Return | tiled: this window takes the left half, the others share the right (Mango: swaps it into the master area) |
| ⌘ / | float every window on this workspace, or tile them all again (none of the three has a true floating layout) |
| ⌘ R | resize mode (arrows or HJKL, Esc to leave) |
| ⌘ \` / ⌘ ⇧ \` | show / stash scratchpad |
| ⌘ Ctrl S / ⌘ Ctrl ⇧ S | screenshot region / whole screen (saved + copied) |
| ⌘ ⇧ Q or ⌘ Esc | power menu (lock, suspend, log out, reboot, power off) |
| ⌘ ⇧ C | reload the config |
| ⌘ N | night light on / off (on by default, 4000 K) |
| Win ⇧ (Mac: Option ⇧) | switch US ⇄ RU (the key just left of ⌘, plus Shift) |
| F1/F2, F5/F6, F10–F12 | screen brightness, keyboard backlight, volume (with a popup bar) |
| F7 / F8 / F9 | previous / play-pause / next, for any player |

### sway

| Keys | Action |
|---|---|
| ⌘ Tab | switch between tabbed and tiled |
| ⌘ ⇧ Tab | cycle through all windows |
| ⌘ A / ⌘ S | previous / next workspace (past the last: a fresh empty one) |
| ⌘ 1…0 / ⌘ ⇧ 1…0 | go to / send window to workspace |
| ⌘ ⇧ Space | switch focus between floating and tiled |
| ⌘ \\ / ⌘ - | split side by side / top and bottom |
| ⌘ . / ⌘ , / ⌘ T | tiling (press again to flip split direction) / tabbed / stacked |
| ⌘ P | focus parent container |

### Hyprland

| Keys | Action |
|---|---|
| ⌘ Tab | switch between tabbed and tiled |
| ⌘ ⇧ Tab | cycle through all windows |
| ⌘ A / ⌘ S | previous / next workspace (past the last: a fresh empty one) |
| ⌘ 1…0 / ⌘ ⇧ 1…0 | go to / send window to workspace |
| ⌘ ⇧ Space | switch focus between floating and tiled |
| ⌘ \\ / ⌘ - | open the next window to the right / below |
| ⌘ . | tiled: break the tabs apart (press again to flip the split direction) |
| ⌘ , or ⌘ T | tabbed: the whole workspace as tabs (Hyprland has no stacked layout) |
| ⌘ [ / ⌘ ] | in tabs: previous / next tab (or click a tab) |

### Mango

| Keys | Action |
|---|---|
| ⌘ Tab | switch between tabbed and tiled |
| ⌘ ⇧ Tab | overview of every window (pick one, or ⌘ ⇧ Tab again to leave) |
| ⌘ A / ⌘ S | tag (workspace) to the left / right |
| ⌘ 1…9 / ⌘ ⇧ 1…9 | go to / send window to tag (Mango has nine) |
| ⌘ . | tiled: switch between side-by-side and top-and-bottom |
| ⌘ , / ⌘ T | tabbed / stacked (press ⌘ . to go back to tiled) |

Focus follows the mouse pointer, displays 1080p or taller are scaled 1.5× and brightness is set to
100% at every login; all of that can be changed in *Settings* (below). Screenshots go to `~/Pictures/Screenshots`.
Helper scripts live in `/usr/local/bin/mbp-*`. The default wallpaper is
`/usr/share/backgrounds/mbp/wallpaper.jpg`. The fish prompt is `[$PWD]$`, set in
`~/.config/fish/functions/fish_prompt.fish`.

Configs live in `~/.config/`: `sway` + `i3status`, `hypr/hyprland.lua` + `waybar`, or
`mango/config.conf` + `waybar`; plus `foot`, `fuzzel`, `mako` and `fish` in every flavour.
Autostart, idle and night light are shared by all three, in `/usr/local/bin/mbp-session-start`.

## Settings

**Settings** in the launcher (or `mbp-settings [panel]`, e.g. `mbp-settings network`) is a GTK 4 app in the
desktop's square, dark style. It works the same in all three flavours and changes take effect at once:

| Panel | What's in it |
|---|---|
| Network | Wi-Fi on/off, networks (connect with a password, disconnect, forget), wired status, VPNs on/off |
| Bluetooth | on/off, search, pair, connect, disconnect, remove; battery level of connected devices |
| Sound | output and input device, volume, mute |
| Displays | per display: on/off, resolution, refresh rate, scale, rotation, position next to the built-in one (with *Keep these settings?* and a 15-second undo); brightness now and at login; night light and its temperature; scale for other displays |
| Keyboard | layouts, Alt ⇄ Win swap, Caps Lock ⇄ Escape, key repeat; every shortcut for this flavour |
| Mouse & touchpad | pointer speed, left-handed, focus follows mouse, tap to click, natural scrolling, ignore while typing, three-finger swipe between workspaces |
| Appearance | dark or light apps, text size, accent colour, wallpaper (thumbnails, or any image), borders, gaps; in Hyprland and Mango also rounded corners, animations, shadows, blur, unfocused-window opacity |
| Windows | whether new workspaces open tabbed or tiled |
| Notifications | do not disturb, how long they stay, where they appear, show the last one again |
| Power | battery charge, health and power draw; lock / screen off / suspend times; what closing the lid does |
| Date & time | automatic time, time zone, setting the time by hand |
| Users | your account and password; add or remove users (administrators can use sudo) |
| Default apps | browser, email, files, text, images, video, music, PDFs, archives |
| About | computer name (editable), model, processor, memory, graphics, disk, system, kernel, uptime |

The rarer things open the full tools: *All connections* (`nm-connection-editor`) for static addresses, enterprise
Wi-Fi and new VPNs; the Bluetooth manager (`blueman-manager`); and the volume control (`pavucontrol`) for
per-app volumes. The lid and user changes ask for an administrator's password (polkit).

The desktop settings live in `~/.config/mbp/settings.conf`; `mbp-conf` turns them into
`~/.config/mbp/generated/{sway.conf,sway-vars.conf,hyprland.lua,mango.conf,waybar.css,mako.conf}`, which the
compositors, Waybar and mako load after their own defaults (regenerated at every login for the machine it runs on).
Edit the file by hand if you like, then run `mbp-conf apply`. In Mango, a rotated display isn't remembered
after logging out: its display rules have no rotation.

## Tether (phone and computer bridge)

[Tether](https://github.com/knap43/tether) is fetched when the ISO is built and installed
trimmed down to **clipboard sync and file sharing**. Its other features (notifications,
phone audio/screen, remote input, commands) start switched off, and the window shows only the
clipboard and file controls (`TETHER_FEATURES=clipboard,files` in its launcher entry).

- Open **Tether** from the launcher to pair your phone or another computer (same pairing as usual).
- **Clipboard** syncs automatically (via wl-clipboard; the service starts after login).
- **Send files:** right-click in Thunar → *Send with Tether*. With several devices connected,
  a menu asks which one. Incoming files land in `~/Downloads/Tether`.
- **Browse the phone** in Thunar (WebDAV, through `gvfs-dnssd`), and set up **folder sync** in the Tether window.
- The window uses a light, square-cornered look from `~/.config/tether/style.css`;
  the launcher entry starts it with `TETHER_COLOR_SCHEME=light`.

To build with a different copy of Tether: `TETHER_REPO=/path/or/url ./build.sh`.

## Lantern

[Lantern](https://github.com/knap43/lantern), a text RPG with a small local LLM as the Dungeon Master,
is fetched at build time and appears in the launcher. The launcher entry opens it in a terminal and
starts the llama.cpp server in the background (stopping it when you quit), so one click is enough.
The fine-tuned ~530 MB model is bundled in the ISO (`/usr/share/lantern/models`), so it plays offline
right after installing. `build.sh` downloads it once, reusing `~/.cache/lantern` or `./cache` when it's
already there, and checks its checksum. The server's log is in `~/.local/state/lantern/server.log`.
Saves: `~/.local/share/lantern`.

## wmai (change the config by asking)

[wm-config-llm](https://github.com/knap43/wm-config-llm)'s `wmai` is installed with the model from its
latest release (~690 MB, bundled, so it works offline; checked against GitHub's published checksum). It edits whichever compositor you're running from a
plain-language request, checks the result with `sway -C`, `Hyprland --verify-config` or `mango -p`,
and asks before applying:

```fish
wmai "make the borders thicker"
wmai "bind super+m to kew in a terminal"
wmai undo
```

It never rewrites your config: its changes go to `~/.config/sway/ai.conf`, `~/.config/hypr/ai.lua`
or `~/.config/mango/ai.conf`, which the configs on this ISO already load last (`wmai init` is done
for you). The first request starts the model's server (`wmai-server`, a user service), which takes a
few seconds and then stays up; `systemctl --user stop wmai-server` frees its memory (~1 GB).
To build with a different copy: `WMAI_REPO=/path/or/url ./build.sh`; to bundle a specific model,
set `WMAI_MODEL_URL` and `WMAI_MODEL_SHA256`.

## Games

Five tiny dark-fantasy games from `knap43/tiny-games` are fetched at build time and appear in the launcher:
**Graven** (top-down roguelike), **Vigil** (wave survival), **Litany** (typing game; switch to the US
layout first), **Cenotaph** (turn-based tactics) and **Reliquary** (deck builder). They start fullscreen; F11 gives a window. The repository is private, so the build uses your
git login (HTTPS credentials, or `GAMES_REPO=git@github.com:knap43/tiny-games.git ./build.sh` for SSH);
without access the ISO is built without them. Best scores are kept in `~/.local/share/<game>`.

## Layout

```
build.sh                 builds the ISO: ./build.sh [sway|hyprland|mango]
packages.system          packages shared by every flavour (live ISO and installed system)
overlay/                 files copied onto every flavour's root filesystem
  etc/skel/.config       shared desktop configs (also copied to the installed system)
  usr/local/bin/mbp-install         the installer
  usr/local/bin/mbp-session-start   autostart, idle/lock, night light (all compositors)
  usr/local/bin/mbp-settings        starts Settings (the app lives in usr/lib/mbp-settings)
  usr/lib/mbp-settings/             the Settings app (Python, GTK 4) and its pkexec helper
  usr/local/bin/mbp-conf            the desktop settings: settings.conf -> each compositor's snippet, apply
  usr/local/bin/mbp-*               power menu, screenshot, OSD, battery, night-light and idle helpers
  etc/xkb/                          the mbp:swap_alt_win keyboard option (Alt ⇄ Win on PC keyboards)
  usr/local/bin/live-user-setup     creates the live user at boot
  usr/local/bin/live-welcome        the live session's walkthrough (live ISO only)
  usr/local/bin/tether*             Tether launcher and the Thunar send action
  usr/local/bin/wmai                wmai wrapper (bundled model, starts its server on demand)
compositors/<flavour>/
  packages               the compositor and its bar
  overlay/               its config, fish autostart and (sway) workspace/window helpers
```
