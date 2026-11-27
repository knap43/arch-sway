# mbp — Arch Linux ISOs with sway, Hyprland or Mango

Live USBs that boot straight into a configured tiling session, plus a one-shot installer
that puts the same system on the internal disk. Made for the 2011 MacBook Pro 13″
(A1278 / MacBookPro8,1) and the ThinkPad T460s, and fine on most Intel laptops.

There are three flavours. Each has the same apps, keys and look; only the compositor differs.

| Flavour | Compositor | New workspaces open | Bar |
|---|---|---|---|
| `sway` (default) | sway | tabbed | swaybar + i3status (+ a Bluetooth icon) |
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
   - **W** picks a Wi-Fi network (or Settings → Network). Networks you join here are
     saved in the new system **with their passwords**.
   - **K** lists every shortcut for this flavour.
   - **Enter** starts the installer. It asks for disk, hostname, user, password, timezone and
     language, then **wipes the whole disk** (macOS or Windows included) and installs.
   - **Q** closes the window; reopen it from the launcher as *Install to Disk*
     (or run `sudo mbp-install` in a terminal).
3. When it's done, press Enter to reboot. **Keep the stick in until the screen goes dark** or shows
   the maker's logo — the live system runs from it right to the end — then remove it. If the live
   system starts again, remove the stick and reboot once more.
   Log in on the console — the compositor starts by itself.

## What's in it

| Area | Choice |
|---|---|
| Graphics | Intel HD 3000 (MacBook, Mesa crocus) and HD 520 (ThinkPad, Mesa iris), early KMS, VA-API video decoding, Xwayland |
| Wi-Fi | NetworkManager, managed in Settings; its icon in the bar shows the signal (Hyprland, Mango: click for Settings, hover for the network). MacBook: `broadcom-wl-dkms` (BCM4331, built for the kernel at install); ThinkPad: iwlwifi from `linux-firmware`. `wheel` users manage networks without a password prompt, and Wi-Fi passwords are stored system-wide |
| Session | sway, Hyprland or Mango; swayidle/gtklock, mako, fuzzel, foot, wob popups |
| Shell | fish (starts the compositor on tty1) |
| Audio | PipeWire + WirePlumber, pavucontrol |
| Power | TLP, zram swap (zstd); lock at 5 min idle, screen off at 10, suspend at 15 on battery; battery warnings at 15% and 5% |
| Devices | USB drives auto-mount (udiskie, tray icon), Bluetooth in Settings with an icon in the bar (on, off, connected; blueman handles pairing prompts and file transfers), touchpad tap-to-click, TrackPoint |
| Apps | btop, fastfetch, nnn (terminal file manager), Flatpak (Flathub added; apps show up in the launcher), Zen Browser (Flatpak, preinstalled with uBlock Origin and Vimium; `ZEN_EXTENSIONS=` at build time changes the list), mpv (hardware decoding on; F7–F9 control it via mpv-mpris), kew (terminal music player; F7–F9 control it), Thunar, Ristretto, Zathura, Mousepad, Xarchiver |
| Dev | git, base-devel, vim, Python + PyGObject, GTK 4, libadwaita |
| Boot | systemd-boot on UEFI (GRUB if booted in legacy/BIOS mode) |

## Keys (⌘ = Mod)

⌘ is the Command key on the MacBook. On a PC keyboard such as the ThinkPad's, Alt and the Windows key
trade places, so ⌘ is the key next to the space bar there too (the Alt key), and Alt moves to the
Windows key, so the layout switch is **Win ⇧** there (Option ⇧ on the MacBook: the same spot, just left of ⌘). The choice is made per machine (anything but a Mac swaps); *Settings* →
Keyboard can turn it on or off for good. All shortcuts work in
both the US and Russian layouts. Caps Lock and Escape are swapped.

### Changeable in Settings

*Settings* → **Keyboard shortcuts** lets you change these (press the new keys; it warns about keys
already taken), remove them, give a shortcut to Settings or the lock screen, and add your own
shortcuts that run any command. The changes live in `~/.config/mbp/shortcuts.conf`; the ⌘ / cheat
sheet always shows the keys as they are now. The defaults:

| Keys | Action |
|---|---|
| ⌘ D | terminal |
| ⌘ Space / ⌘ Q | app launcher |
| ⌘ E / ⌘ B | Thunar / Zen Browser |
| ⌘ V | clipboard history |
| ⌘ W | close window |
| ⌘ Tab | switch between tabbed and tiled |
| ⌘ F / ⌘ ⇧ F | fullscreen / floating |
| ⌘ G | float every window on this workspace, or tile them all again (none of the three has a true floating layout) |
| ⌘ Return | tiled: this window takes the left half, the others share the right (Mango: swaps it into the master area) |
| ⌘ ⇧ Tab | cycle through all windows (sway, Hyprland) |
| ⌘ ⇧ Q | Mango: overview of every window (pick one, or Esc or ⌘ ⇧ Q to leave) |
| ⌘ \` / ⌘ ⇧ \` | show / stash scratchpad |
| ⌘ R | resize mode (arrows or HJKL, Esc to leave) |
| ⌘ / | keyboard shortcuts cheat sheet, in a terminal: type to search (⌘ / or Esc closes it) |
| ⌘ Ctrl S / ⌘ Ctrl ⇧ S | screenshot region / whole screen (saved + copied) |
| ⌘ Esc or ⌘ ⇧ Q | power menu (lock, suspend, log out, reboot, power off); Mango: ⌘ Esc only |
| ⌘ T | switch theme: Default or Everforest (terminal colours, accent colour and wallpaper together) |
| ⌘ N | night light on / off (on by default, 4000 K) |
| ⌘ ⇧ C | reload the config |

### Fixed

These are the same in every flavour:

| Keys | Action |
|---|---|
| ⌘ [ / ⌘ ] | previous / next window on this workspace |
| ⌘ arrows | focus; add ⇧ to move the window (⌘ ⇧ H J K L too) |
| ⌘ H J K L | resize: narrower, taller, shorter, wider (hold to repeat) |
| ⌘ ⇧ A / ⌘ ⇧ S | take the window to the previous / next workspace |
| Win ⇧ (Mac: Option ⇧) | switch US ⇄ RU (the key just left of ⌘, plus Shift) |
| F1/F2, F5/F6, F10–F12 | screen brightness, keyboard backlight, volume (with a popup bar) |
| F7 / F8 / F9 | previous / play-pause / next, for any player |

### sway

| Keys | Action |
|---|---|
| ⌘ A / ⌘ S | previous / next workspace (past the last: a fresh empty one) |
| ⌘ 1…0 / ⌘ ⇧ 1…0 | go to / send window to workspace |
| ⌘ ⇧ Space | switch focus between floating and tiled |
| ⌘ \\ / ⌘ - | split side by side / top and bottom |
| ⌘ . / ⌘ , | tiling (press again to flip split direction) / tabbed |
| ⌘ P | focus parent container |

### Hyprland

| Keys | Action |
|---|---|
| ⌘ A / ⌘ S | previous / next workspace (past the last: a fresh empty one) |
| ⌘ 1…0 / ⌘ ⇧ 1…0 | go to / send window to workspace |
| ⌘ ⇧ Space | switch focus between floating and tiled |
| ⌘ \\ / ⌘ - | open the next window to the right / below |
| ⌘ . | tiled: break the tabs apart (press again to flip the split direction) |
| ⌘ , | tabbed: the whole workspace as tabs |
| ⌘ [ / ⌘ ] | in tabs: previous / next tab (or click a tab) |

### Mango

| Keys | Action |
|---|---|
| ⌘ A / ⌘ S | tag (workspace) to the left / right |
| ⌘ 1…9 / ⌘ ⇧ 1…9 | go to / send window to tag (Mango has nine) |
| ⌘ . | tiled: switch between side-by-side and top-and-bottom |
| ⌘ , | tabbed (press ⌘ . to go back to tiled) |

Focus follows the mouse pointer, displays 1080p or taller are scaled 1.5× and brightness is set to
100% at every login; all of that can be changed in *Settings* (below). Screenshots go to `~/Pictures/Screenshots`.
Helper scripts live in `/usr/local/bin/mbp-*`. The default wallpaper is
`/usr/share/backgrounds/mbp/wallpaper.jpg`.

**Themes** (⌘ T, or *Settings* → Appearance → Theme) set the colours of the terminal, the menus (fuzzel)
and the bar, the accent colour and the wallpaper together: *Default* is the look described here; *Everforest* uses the
[Everforest](https://github.com/sainnhe/everforest) dark palette in the terminal, its green as the
accent and a foggy forest (`/usr/share/backgrounds/mbp/everforest.jpg`). Menus and the bar change at once;
terminals opened afterwards get the new colours; the accent and wallpaper can still be changed on their own. `mbp-conf theme NAME`
does it from a shell. Themes live in `THEMES` in `mbp-conf`. The fish prompt is `[$PWD]$`, set in
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
| Keyboard shortcuts | change the keys of the main actions (apps, closing, fullscreen, floating, layouts, scratchpad, screenshots, power menu, lock, cheat sheet...): press the new keys, add a second one or turn one off; it warns when a key is taken and can take it over. Add your own shortcuts that run any command. Moving, resizing and workspace keys stay fixed |
| Mouse & touchpad | pointer speed, left-handed, focus follows mouse, hiding the pointer when idle (3 s) and while typing, tap to click, natural scrolling, ignore while typing, three-finger swipe between workspaces |
| Appearance | theme, dark or light apps, text size, accent colour, wallpaper (thumbnails, or any image), borders, gaps; in Hyprland and Mango also rounded corners, animations, shadows, blur; terminal (foot), menu (fuzzel) and bar opacity |
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
`~/.config/mbp/generated/{sway.conf,sway-vars.conf,sway-binds.conf,hyprland.lua,mango.conf,mango-binds.conf,waybar.css,mako.conf}`, which the
compositors, Waybar and mako load after their own defaults (regenerated at every login for the machine it runs on).
Edit the file by hand if you like, then run `mbp-conf apply`. In Mango, a rotated display isn't remembered
after logging out: its display rules have no rotation.

## Tether (phone and computer bridge)

[Tether](https://github.com/knap43/tether) is fetched when the ISO is built and installed in full: clipboard
sync, file sharing and folder sync, the phone's notifications on the desktop, the phone's audio and screen
here, playing what the phone shares, and commands. Remote control of this computer from the phone and the
remote shell start switched off, as Tether ships them (remote control needs GNOME, so it can't work here).

- Open **Tether** from the launcher to pair your phone or another computer.
- **Clipboard** syncs automatically (via wl-clipboard; the service starts after login).
- **Send files:** right-click in Thunar → *Send with Tether*. With several devices connected,
  a menu asks which one. Incoming files land in `~/Downloads/Tether`.
- **Browse the phone** in Thunar (WebDAV, through `gvfs-dnssd`), and set up **folder sync** in the Tether window.
- The window has the same square look and colours as Settings, following its theme and accent
  colour: mbp-conf writes `~/.config/tether/style.css` from Settings' own stylesheet whenever the
  settings change (reopen Tether's window to see a change).

To build with a different copy of Tether: `TETHER_REPO=/path/or/url ./build.sh`.

## RetroHub (game launcher)

[RetroHub](https://github.com/knap43/retrohub) is a terminal game launcher, fetched when the ISO is built.
It scans `~/Games` (`Windows/` and `Linux/` inside it), runs Windows games through Proton via
umu-launcher, falls back to Wine, and starts native Linux ports directly. It also plays the consoles
below: put ROMs in `~/Games/PS1`, `PS2` or `N64` (sub-folders are categories), and RetroHub starts
them fullscreen in DuckStation, PCSX2 or Mupen64Plus. Open it from the launcher
or run `retrohub` (fish completions included); `retrohub doctor` shows the paths and runners.

- **Proton needs Vulkan**, so it works on the ThinkPad (HD 520) but not on the MacBook (HD 3000 has
  no Vulkan driver). There, set a game's runner to *Wine* with `e`, or rely on native ports.
- umu downloads UMU-Proton (or GE-Proton) on the first Windows launch, so that needs a connection.
- `winetricks`, `gamemode` (`gamemoderun %command%`) and `mangohud` (`MANGOHUD=1 %command%`) are
  installed; users are in the `gamemode` group.
- The multilib repository is enabled on the installed system for umu-launcher and the 32-bit drivers.

To build with a different copy: `RETROHUB_REPO=/path/or/url ./build.sh`.

## Emulators

| system | emulator | how it's installed |
|---|---|---|
| PlayStation | [DuckStation](https://github.com/stenzek/duckstation) | its AppImage, unpacked into `/opt/duckstation` |
| PlayStation 2 | [PCSX2](https://github.com/PCSX2/pcsx2) | its AppImage (latest stable), unpacked into `/opt/pcsx2` |
| Nintendo 64 | mupen64plus | Arch package; the launcher entry asks for a ROM (Esc quits) |

`build.sh` downloads the two AppImages (cached in `./cache`), checks them against the SHA-256 GitHub
records for each release asset, and unpacks them, so they need no FUSE and start a little quicker. If
one can't be fetched or verified, the ISO is built without it. They update with the next ISO build.

DuckStation and PCSX2 need a BIOS dumped from your own console; point them at it on first start.
PCSX2 asks a lot of the graphics, so expect the ThinkPad to manage far more than the MacBook.

## toofan (typing practice)

[toofan](https://github.com/vyrx-dev/toofan), a typing-speed test for the terminal, is in the launcher and on the
command line (`toofan`): English words or real code snippets, live WPM and accuracy, a review of your mistakes,
ranks and races against your own last ten tests. **Ctrl+T** cycles its themes, **Ctrl+P** opens your profile.
Everything stays local, in `~/.config/toofan`. The build bundles the latest release's binary, checked against the
release's checksums (`TOOFAN_VERSION=2.4.2 ./build.sh` pins one); if GitHub can't be reached, it's left out.

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
compositors/<flavour>/
  packages               the compositor and its bar
  overlay/               its config, fish autostart and (sway) workspace/window helpers
```
