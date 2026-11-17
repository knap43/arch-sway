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
2. sway starts automatically (user `live`, no password).
3. Connect to Wi-Fi with the network icon in the bar (or `nmtui`).
   No Wi-Fi? Plug in an Android phone and turn on USB tethering — it needs no driver.
4. ⌘+Return for a terminal, then `sudo mbp-install`.
   It asks for disk, hostname, user, password, timezone, language,
   then **wipes the whole disk** (macOS included) and installs.
   Your live Wi-Fi connection is carried over.
5. Reboot, remove the stick, log in on the console — sway starts by itself.

## What's in it

| Area | Choice |
|---|---|
| Graphics | Intel HD 3000 (i915 + Mesa crocus), early KMS, VA-API video decoding, Xwayland |
| Wi-Fi | `broadcom-wl-dkms` (BCM4331, built for the kernel at install) via NetworkManager + nm-applet |
| Session | sway, swaybar + i3status, swayidle/swaylock, mako, fuzzel, foot |
| Shell | fish (autostarts sway on tty1) |
| Audio | PipeWire + WirePlumber, pavucontrol |
| Power | TLP, zram swap (zstd) |
| Apps | Firefox, Thunar, Ristretto, Zathura, Mousepad, Xarchiver |
| Dev | git, base-devel, vim, Python + PyGObject, GTK 4, libadwaita |
| Boot | systemd-boot on UEFI (GRUB if booted in legacy/BIOS mode) |

## Keys (⌘ = Mod)

All shortcuts work in both the US and Russian layouts. Caps Lock and Escape are swapped.

| Keys | Action |
|---|---|
| ⌘ D (or ⌘ Return) | terminal |
| ⌘ Space / ⌘ Q | app launcher |
| ⌘ E / ⌘ B | Thunar / Firefox |
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
| ⌘ T / ⌘ , / ⌘ . | toggle split / tabbed / stacked |
| ⌘ P | focus parent container |
| ⌘ R | resize mode (arrows or HJKL, Esc to leave) |
| ⌘ \` / ⌘ ⇧ \` | show / stash scratchpad |
| ⌘ Ctrl S / ⌘ Ctrl ⇧ S | screenshot region / whole screen (saved + copied) |
| ⌘ Esc | lock |
| ⌘ ⇧ Q | power menu (lock, suspend, log out, reboot, power off) |
| ⌘ ⇧ C | reload sway config |
| ⌘ N | night light on / off (on by default, 4000 K) |
| Alt ⇧ | switch US ⇄ RU |
| F1/F2, F5/F6, F10–F12 | screen brightness, keyboard backlight, volume |

Screenshots go to `~/Pictures/Screenshots`. Helper scripts live in `/usr/local/bin/sway-*`.
The default wallpaper is `/usr/share/backgrounds/mbp-sway/wallpaper.jpg` (change the `output * bg` line in the sway config to use another). The fish prompt is `[$PWD]$`, set in `~/.config/fish/functions/fish_prompt.fish`.

Configs live in `~/.config/{sway,foot,fuzzel,mako,i3status,fish}`.

## Layout

```
build.sh            builds the ISO (releng + this overlay)
packages.system     packages for both live ISO and installed system
overlay/            files copied onto the live root filesystem
  etc/skel/.config  desktop configs (also copied to the installed system)
  usr/local/bin/mbp-install       the installer
  usr/local/bin/live-user-setup   creates the live user at boot
  usr/local/bin/sway-*            workspace, window-cycle, power-menu and screenshot helpers
```
