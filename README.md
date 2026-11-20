# mbp-sway — Arch + sway ISO for the 2011 MacBook Pro 13″ (A1278 / MacBookPro8,1)

A live USB that boots straight into a configured sway session, plus a one-shot
installer that puts the same system on the internal disk.

## Build (on your Arch machine)

```sh
sudo pacman -S --needed archiso
./build.sh
```

The ISO lands in `out/`. The build needs ~10 GB free and internet access.
It is layered on Arch's official `releng` profile, so it stays current with archiso.

## Write to USB

```sh
lsblk                                   # find the stick, e.g. /dev/sdb
sudo dd bs=4M if=out/mbp-sway-*.iso of=/dev/sdX status=progress oflag=sync
```

## Boot & install

1. Hold **Option (⌥)** at the chime, pick **EFI Boot**.
2. sway starts automatically (user `live`, no password) and a **welcome window** opens.
   It shows whether you're online, the essential shortcuts, and what the installer will do:
   - **W** picks a Wi-Fi network (or use the network icon in the bar).
     No Wi-Fi? Plug in an Android phone and turn on USB tethering — it needs no driver.
   - **K** lists every shortcut.
   - **Enter** starts the installer. It asks for disk, hostname, user, password, timezone and
     language, then **wipes the whole disk** (macOS included) and installs. Your live Wi-Fi
     connection is carried over.
   - **Q** closes the window; reopen it from the launcher as *Install mbp-sway*
     (or run `sudo mbp-install` in a terminal).
3. When it's done, remove the stick and press Enter to reboot. Log in on the console —
   sway starts by itself.

## What's in it

| Area | Choice |
|---|---|
| Graphics | Intel HD 3000 (i915 + Mesa crocus), early KMS, VA-API video decoding, Xwayland |
| Wi-Fi | `broadcom-wl-dkms` (BCM4331, built for the kernel at install) via NetworkManager + nm-applet |
| Session | sway, swaybar + i3status, swayidle/swaylock, mako, fuzzel, foot |
| Shell | fish (autostarts sway on tty1) |
| Audio | PipeWire + WirePlumber, pavucontrol |
| Power | TLP, zram swap (zstd); lock at 5 min idle, screen off at 10, suspend at 15 on battery; battery warnings at 15% and 5% |
| Devices | USB drives auto-mount (udiskie, tray icon), Bluetooth tray (blueman) |
| Apps | btop, fastfetch, Flatpak (Flathub added; apps show up in the launcher), LibreWolf, Thunar, Ristretto, Zathura, Mousepad, Xarchiver |
| Dev | git, base-devel, vim, Python + PyGObject, GTK 4, libadwaita |
| Boot | systemd-boot on UEFI (GRUB if booted in legacy/BIOS mode) |

## Keys (⌘ = Mod)

All shortcuts work in both the US and Russian layouts. Caps Lock and Escape are swapped.

| Keys | Action |
|---|---|
| ⌘ D (or ⌘ Return) | terminal |
| ⌘ Space / ⌘ Q | app launcher |
| ⌘ E / ⌘ B | Thunar / LibreWolf |
| ⌘ V | clipboard history |
| ⌘ W | close window |
| ⌘ Tab / ⌘ ⇧ Tab | cycle through all windows, forward / back |
| ⌘ [ / ⌘ ] | previous / next window on this workspace |
| ⌘ H J K L or arrows | focus; add ⇧ to move the window |
| ⌘ A / ⌘ S | previous / next workspace (past the last: a fresh empty one) |
| ⌘ ⇧ A / ⌘ ⇧ S | take the window to the previous / next workspace |
| ⌘ 1…0 / ⌘ ⇧ 1…0 | go to / send window to workspace |
| ⌘ F / ⌘ ⇧ F | fullscreen / floating |
| ⌘ ⇧ Space | switch focus between floating and tiled |
| ⌘ \\ / ⌘ - | split side by side / top and bottom |
| ⌘ . / ⌘ , / ⌘ T | tiling (press again to flip split direction) / tabbed / stacked |
| ⌘ P | focus parent container |
| ⌘ R | resize mode (arrows or HJKL, Esc to leave) |
| ⌘ \` / ⌘ ⇧ \` | show / stash scratchpad |
| ⌘ Ctrl S / ⌘ Ctrl ⇧ S | screenshot region / whole screen (saved + copied) |
| ⌘ ⇧ Q or ⌘ Esc | power menu (lock, suspend, log out, reboot, power off) |
| ⌘ ⇧ C | reload sway config |
| ⌘ N | night light on / off (on by default, 4000 K) |
| Alt ⇧ | switch US ⇄ RU |
| F1/F2, F5/F6, F10–F12 | screen brightness, keyboard backlight, volume (with a popup bar) |
| F7 / F8 / F9 | previous / play-pause / next, for any player |

New workspaces open in tabbed layout, and screen brightness is set to 100% at every login.
Screenshots go to `~/Pictures/Screenshots`. Helper scripts live in `/usr/local/bin/sway-*`.
The default wallpaper is `/usr/share/backgrounds/mbp-sway/wallpaper.jpg` (change the `output * bg` line in the sway config to use another). The fish prompt is `[$PWD]$`, set in `~/.config/fish/functions/fish_prompt.fish`.

Configs live in `~/.config/{sway,foot,fuzzel,mako,i3status,fish}`.

## Tether (phone and computer bridge)

[Tether](https://github.com/knap43/tether) is fetched when the ISO is built and installed
trimmed down to **clipboard sync and file sharing**. Its other features (notifications,
phone audio/screen, remote input, commands) start switched off.

- Open **Tether** from the launcher to pair your phone or another computer (same pairing as usual).
- **Clipboard** syncs automatically (via wl-clipboard; sway starts the service after login).
- **Send files:** right-click in Thunar → *Send with Tether*. With several devices connected,
  a menu asks which one. Incoming files land in `~/Downloads/Tether`.
- **Browse the phone** in Thunar (WebDAV, through `gvfs-dnssd`), and set up **folder sync** in the Tether window.
- The window uses a light, square-cornered look from `~/.config/tether/style.css`;
  the launcher entry starts it with `TETHER_COLOR_SCHEME=light`.

To build with a different copy of Tether: `TETHER_REPO=/path/or/url ./build.sh`.

## Games

Three tiny dark-fantasy games from `knap43/tiny-games` are fetched at build time and appear in the launcher:
**Graven** (top-down roguelike), **Vigil** (wave survival) and **Litany** (typing game; switch to the US
layout first). They start fullscreen; F11 gives a window. The repository is private, so the build uses your
git login (HTTPS credentials, or `GAMES_REPO=git@github.com:knap43/tiny-games.git ./build.sh` for SSH);
without access the ISO is built without them. Best scores are kept in `~/.local/share/<game>`.

## Layout

```
build.sh            builds the ISO (releng + this overlay)
packages.system     packages for both live ISO and installed system
overlay/            files copied onto the live root filesystem
  etc/skel/.config  desktop configs (also copied to the installed system)
  usr/local/bin/mbp-install       the installer
  usr/local/bin/live-user-setup   creates the live user at boot
  usr/local/bin/live-welcome      the live session's walkthrough (live ISO only)
  usr/local/bin/sway-*            workspace, window-cycle, power-menu, screenshot, OSD and battery helpers
  usr/local/bin/tether*           Tether launcher and the Thunar send action
```
