#!/usr/bin/env bash
# Builds the ISO on top of Arch's official "releng" profile.
# Usage: ./build.sh [sway|hyprland|mango]     (default: sway)
#        needs the 'archiso' package; asks for sudo
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLAVOUR=${1:-sway}
FLAVOUR_DIR="$HERE/compositors/$FLAVOUR"
[[ -d $FLAVOUR_DIR ]] || { echo "Unknown flavour '$FLAVOUR'. Choose one of: $(ls "$HERE/compositors" | tr '\n' ' ')" >&2; exit 1; }
RELENG=/usr/share/archiso/configs/releng
WORK="$HERE/work"
PROFILE="$WORK/profile"
OUT="$HERE/out"

[[ -d $RELENG ]] || { echo "archiso is not installed: sudo pacman -S archiso" >&2; exit 1; }

command -v git >/dev/null || { echo "git is needed to fetch Tether: sudo pacman -S git" >&2; exit 1; }
TETHER_REPO=${TETHER_REPO:-https://github.com/knap43/tether}
GAMES_REPO=${GAMES_REPO:-https://github.com/knap43/tiny-games}
LANTERN_REPO=${LANTERN_REPO:-https://github.com/knap43/lantern}
WMAI_REPO=${WMAI_REPO:-https://github.com/knap43/wm-config-llm}
# wmai's model comes from the latest wm-config-llm release (see below); set
# both of these to bundle a specific file instead.
WMAI_MODEL_URL=${WMAI_MODEL_URL-}
WMAI_MODEL_SHA256=${WMAI_MODEL_SHA256-}


# ---- Never pack or delete through a leftover mount --------------------------
# pacstrap (inside mkarchiso) mounts /proc, /sys and /dev in the image root and
# unmounts them afterwards, but if a program it started is still running there
# the unmount fails with only a warning; mksquashfs then packs the host's live
# /proc (endless "Failed to read file .../proc/..."), and the next build's rm
# would delete through /dev. release_work stops such programs and unmounts.
# Mount points at or below $1, deepest first (mountinfo escapes spaces etc.).
mounts_below() {
    awk -v p="$1/" '{ m = $5; gsub(/\\040/, " ", m); gsub(/\\011/, "\t", m); gsub(/\\012/, "\n", m)
                      gsub(/\\134/, "\\", m); if (index(m, p) == 1) print m }' /proc/self/mountinfo | sort -r
}
release_work() {
    local dir=$1 pid root killed=0 m
    for pid in /proc/[0-9]*; do
        root=$(readlink "$pid/root" 2>/dev/null) || continue
        [[ $root == "$dir" || $root == "$dir"/* ]] || continue
        echo ":: Stopping $(cat "$pid/comm" 2>/dev/null) (pid ${pid#/proc/}), left running inside the image" >&2
        kill "${pid#/proc/}" 2>/dev/null && killed=1
    done
    if (( killed )); then
        sleep 2
        for pid in /proc/[0-9]*; do
            root=$(readlink "$pid/root" 2>/dev/null) || continue
            [[ $root == "$dir" || $root == "$dir"/* ]] && kill -9 "${pid#/proc/}" 2>/dev/null
        done
    fi
    while IFS= read -r m; do
        echo ":: Unmounting leftover $m" >&2
        umount "$m" 2>/dev/null || umount -l "$m"
    done < <(mounts_below "$dir")
    [[ -z $(mounts_below "$dir") ]]
}
release() { sudo bash -c "$(declare -f mounts_below release_work); release_work \"\$1\"" _ "$1"; }
clean_work() {
    release "$WORK" || { echo "!! Something is still mounted under $WORK; not deleting it" >&2; exit 1; }
    sudo rm -rf --one-file-system "$WORK"
}

echo ":: Preparing the $FLAVOUR profile from releng"
clean_work
mkdir -p "$WORK"
cp -a "$RELENG" "$PROFILE"

# The installed system's packages: shared ones + this flavour's.
grep -vhE '^\s*(#|$)' "$HERE/packages.system" "$FLAVOUR_DIR/packages" > "$WORK/system-pkgs"

# Packages: releng's list + ours, deduplicated.
# (releng still lists the prebuilt broadcom-wl, which Arch has dropped
#  in favour of broadcom-wl-dkms, so filter it out.)
grep -vhE '^\s*(#|$)' "$PROFILE/packages.x86_64" "$WORK/system-pkgs" \
    | grep -vx 'broadcom-wl' | sort -u > "$WORK/pkgs"
mv "$WORK/pkgs" "$PROFILE/packages.x86_64"

# Offline install: every package the installed system needs (with all
# dependencies) goes into a small repository inside the ISO, which the
# installer uses instead of the internet. Packages are fetched into the
# normal pacman cache, which mkarchiso reads too, so nothing downloads twice.
echo ":: Collecting packages for offline installation"
mapfile -t SYS_PKGS < "$WORK/system-pkgs"
SYS_PKGS+=(grub)                       # for installs booted in BIOS mode
PKG_CACHE=/var/cache/pacman/pkg
REPO="$PROFILE/airootfs/var/lib/mbp/repo"
mkdir -p "$WORK/dbpath" "$REPO"
pacman_args=(--config "$PROFILE/pacman.conf" --dbpath "$WORK/dbpath" --cachedir "$PKG_CACHE")
sudo pacman -Syw --noconfirm "${pacman_args[@]}" "${SYS_PKGS[@]}"
# The empty database means -Sp lists the complete dependency closure.
mapfile -t PKG_FILES < <(pacman -Sp --print-format '%f' "${pacman_args[@]}" "${SYS_PKGS[@]}")
for f in "${PKG_FILES[@]}"; do
    cp "$PKG_CACHE/$f" "$REPO/"
done
repo-add -q "$REPO/mbp.db.tar.gz" "${PKG_FILES[@]/#/$REPO/}"
echo "   ${#PKG_FILES[@]} packages, $(du -sh "$REPO" | cut -f1)"

# Overlay our files onto the live root filesystem.
cp -a "$HERE/overlay/." "$PROFILE/airootfs/"
cp -a "$FLAVOUR_DIR/overlay/." "$PROFILE/airootfs/"
install -Dm644 "$WORK/system-pkgs" "$PROFILE/airootfs/usr/local/share/mbp/packages.system"
# Marks the live system (the installer doesn't copy it); holds the flavour.
echo "$FLAVOUR" > "$PROFILE/airootfs/etc/mbp-live"
install -Dm644 "$HERE/README.md" "$PROFILE/airootfs/usr/local/share/mbp/README.md"

# Tether (clipboard + file sharing with the phone and other computers).
echo ":: Fetching Tether from $TETHER_REPO"
git clone -q --depth 1 "$TETHER_REPO" "$WORK/tether"
install -d "$PROFILE/airootfs/usr/lib/tether"
cp -r "$WORK/tether/linux/tether" "$PROFILE/airootfs/usr/lib/tether/"
find "$PROFILE/airootfs/usr/lib/tether" -name __pycache__ -prune -exec rm -rf {} +
install -Dm644 "$WORK/tether/linux/desktop/dev.tether.Tether.svg" \
    "$PROFILE/airootfs/usr/share/icons/hicolor/scalable/apps/dev.tether.Tether.svg"

# Lantern (text RPG with a local llama.cpp Dungeon Master). Only the game and
# its server script are bundled; the ~530 MB model downloads on first run.
echo ":: Fetching Lantern from $LANTERN_REPO"
git clone -q --depth 1 "$LANTERN_REPO" "$WORK/lantern"
install -d "$PROFILE/airootfs/usr/lib/lantern/scripts"
cp -r "$WORK/lantern/lantern" "$PROFILE/airootfs/usr/lib/lantern/"
install -m755 "$WORK/lantern/scripts/serve.sh" "$PROFILE/airootfs/usr/lib/lantern/scripts/serve.sh"
find "$PROFILE/airootfs/usr/lib/lantern" -name __pycache__ -prune -exec rm -rf {} +
echo 'file_permissions["/usr/lib/lantern/scripts/serve.sh"]="0:0:755"' >> "$PROFILE/profiledef.sh"

# Lantern's fine-tuned DM (~530 MB), bundled so the game works offline right
# after installing. URL and checksum come from serve.sh. Reuses a copy in
# ~/.cache/lantern (where Lantern itself keeps it) or in ./cache, so it's
# downloaded at most once per machine.
eval "$(grep -E '^TUNED(_URL|_SHA256)?=' "$WORK/lantern/scripts/serve.sh")"
model_name=$(basename "$TUNED")
model_ok() { [[ -f $1 ]] && echo "$TUNED_SHA256  $1" | sha256sum -c --quiet - 2>/dev/null; }
model=""
for candidate in "$TUNED" "$HERE/cache/$model_name"; do
    model_ok "$candidate" && { model=$candidate; break; }
done
if [[ -z $model ]]; then
    echo ":: Downloading Lantern's Dungeon Master (~530 MB, once)"
    mkdir -p "$HERE/cache"
    curl -fL --progress-bar -o "$HERE/cache/$model_name.part" "$TUNED_URL"
    mv "$HERE/cache/$model_name.part" "$HERE/cache/$model_name"
    model_ok "$HERE/cache/$model_name" || { rm -f "$HERE/cache/$model_name"; echo "!! Lantern model checksum mismatch" >&2; exit 1; }
    model="$HERE/cache/$model_name"
fi
install -Dm644 "$model" "$PROFILE/airootfs/usr/share/lantern/models/$model_name"

# wmai (wm-config-llm): edits the compositor config from plain-language
# requests with a small local model. Only the CLI is bundled, the same files
# its install.sh copies; it needs nothing beyond the standard library.
echo ":: Fetching wmai from $WMAI_REPO"
git clone -q --depth 1 "$WMAI_REPO" "$WORK/wmai"
install -Dm644 -t "$PROFILE/airootfs/usr/lib/wmai/wmllm" \
    "$WORK"/wmai/wmllm/{__init__.py,context.py,validate.py,mango.py,flatten_hypr.lua}
install -Dm644 "$WORK/wmai/cli/wmai.py" "$PROFILE/airootfs/usr/lib/wmai/cli/wmai.py"

# Its model (~660 MB), bundled so wmai works offline: the .gguf attached to the
# latest release, verified against the SHA-256 digest GitHub publishes for it.
# If GitHub's API can't be reached, the release known when this was written.
if [[ -z $WMAI_MODEL_URL ]]; then
    wmai_slug=$(sed -nE 's#^(https://|git@)github\.com[:/]([^/]+/[^/.]+)(\.git)?/?$#\2#p' <<<"$WMAI_REPO")
    if [[ -n $wmai_slug ]] && command -v python3 >/dev/null; then
        read -r WMAI_MODEL_URL WMAI_MODEL_SHA256 wmai_tag < <(
            curl -fsSL "https://api.github.com/repos/$wmai_slug/releases/latest" 2>/dev/null | python3 -c '
import json, sys
release = json.load(sys.stdin)
for asset in release.get("assets", []):
    if asset["name"].endswith(".gguf") and (asset.get("digest") or "").startswith("sha256:"):
        print(asset["browser_download_url"], asset["digest"][7:], release["tag_name"])
        break' 2>/dev/null) || true
    fi
    if [[ -n $WMAI_MODEL_URL ]]; then
        echo ":: wmai model: latest release, $wmai_tag"
    else
        echo ":: wmai model: couldn't ask GitHub for the latest release; using v4"
        WMAI_MODEL_URL=https://github.com/knap43/wm-config-llm/releases/download/v4/wmcfg-Q4_K_M.gguf
        WMAI_MODEL_SHA256=3ef23ea4233036dc016d36d0006a52283dbb5f6a160b28647ca5a2e3f3d96356
    fi
fi
# Reuses a matching copy wmai's own installer put in ~/.local/share/wmai, or
# one in ./cache, so each release is downloaded at most once.
wmai_name=$(basename "$WMAI_MODEL_URL")
wmai_ok() { [[ -f $1 ]] && echo "$WMAI_MODEL_SHA256  $1" | sha256sum -c --quiet - 2>/dev/null; }
wmai_model=""
wmai_cached="$HERE/cache/${WMAI_MODEL_SHA256:0:12}-$wmai_name"
for candidate in "${XDG_DATA_HOME:-$HOME/.local/share}/wmai/$wmai_name" "$wmai_cached"; do
    wmai_ok "$candidate" && { wmai_model=$candidate; break; }
done
if [[ -z $wmai_model ]]; then
    echo ":: Downloading wmai's model (~660 MB, once)"
    mkdir -p "$HERE/cache"
    curl -fL --progress-bar -o "$wmai_cached.part" "$WMAI_MODEL_URL"
    mv "$wmai_cached.part" "$wmai_cached"
    wmai_ok "$wmai_cached" || { rm -f "$wmai_cached"; echo "!! wmai model checksum mismatch" >&2; exit 1; }
    for stale in "$HERE/cache/$wmai_name" "$HERE"/cache/*-"$wmai_name"; do   # older releases' copies
        [[ $stale == "$wmai_cached" ]] || rm -f "$stale"
    done
    wmai_model="$wmai_cached"
fi
install -Dm644 "$wmai_model" "$PROFILE/airootfs/usr/share/wmai/wmcfg-Q4_K_M.gguf"

# Games from tiny-games. The repo is private, so this uses your own git
# login; if it can't be fetched, the ISO is built without them.
# Each entry: name|launcher comment|desktop categories
GAMES=(
    "graven|Tiny dark-fantasy top-down roguelike|Game;ActionGame;"
    "vigil|Dark-fantasy wave survival: auto-weapons, souls, a shop between waves|Game;ActionGame;"
    "litany|Dark-fantasy typing game: banish the shades closing in|Game;ActionGame;"
    "cenotaph|Dark-fantasy turn-based tactical roguelike: every move is an attack|Game;StrategyGame;"
    "reliquary|Dark-fantasy roguelike deck builder: three acts, cards, relics|Game;CardGame;StrategyGame;"
)
echo ":: Fetching games from $GAMES_REPO"
if git clone -q --depth 1 "$GAMES_REPO" "$WORK/tiny-games"; then
    for entry in "${GAMES[@]}"; do
        IFS='|' read -r game comment categories <<< "$entry"
        src="$WORK/tiny-games/$game/$game.py"
        if [[ ! -f $src ]]; then
            echo "!! $game not found in tiny-games, skipping" >&2
            continue
        fi
        name="${game^}"
        install -Dm644 "$src" "$PROFILE/airootfs/usr/lib/tiny-games/$game.py"
        printf '#!/bin/sh\nexec python3 /usr/lib/tiny-games/%s.py "$@"\n' "$game" \
            | install -Dm755 /dev/stdin "$PROFILE/airootfs/usr/local/bin/$game"
        printf '[Desktop Entry]\nType=Application\nName=%s\nComment=%s\nExec=/usr/local/bin/%s\nIcon=applications-games\nTerminal=false\nCategories=%s\n' \
            "$name" "$comment" "$game" "$categories" \
            | install -Dm644 /dev/stdin "$PROFILE/airootfs/usr/share/applications/tiny-games-$game.desktop"
        echo "file_permissions[\"/usr/local/bin/$game\"]=\"0:0:755\"" >> "$PROFILE/profiledef.sh"
        echo "   + $name"
    done
else
    echo "!! Could not fetch $GAMES_REPO (private: needs your GitHub login). Building without games." >&2
fi

# Networking: NetworkManager instead of releng's iwd + systemd-networkd.
UNITS="$PROFILE/airootfs/etc/systemd/system"
find "$UNITS" \( -name 'iwd.service' -o -name 'systemd-networkd*' \) -type l -delete
mkdir -p "$UNITS/multi-user.target.wants"
ln -sf /usr/lib/systemd/system/NetworkManager.service "$UNITS/multi-user.target.wants/NetworkManager.service"
ln -sf /etc/systemd/system/live-user.service          "$UNITS/multi-user.target.wants/live-user.service"

# Name and permissions (profiledef.sh is plain bash, later assignments win).
cat >> "$PROFILE/profiledef.sh" <<EOF

# --- mbp overrides ---
iso_name="mbp-$FLAVOUR"
iso_publisher="mbp-$FLAVOUR <local build>"
iso_application="Arch Linux + $FLAVOUR (MacBook Pro 2011, ThinkPad T460s)"
file_permissions["/usr/local/bin/mbp-install"]="0:0:755"
file_permissions["/usr/local/bin/live-user-setup"]="0:0:755"
file_permissions["/etc/sudoers.d/live"]="0:0:440"
EOF

echo 'file_permissions["/usr/lib/mbp-settings/mbp-settings-helper"]="0:0:755"' >> "$PROFILE/profiledef.sh"
# Every helper in /usr/local/bin is executable.
for f in "$HERE"/overlay/usr/local/bin/* "$FLAVOUR_DIR"/overlay/usr/local/bin/*; do
    [[ -e $f ]] || continue
    echo "file_permissions[\"/usr/local/bin/$(basename "$f")\"]=\"0:0:755\"" >> "$PROFILE/profiledef.sh"
done

# Bluetooth in the live session too.
ln -sf /usr/lib/systemd/system/bluetooth.service "$UNITS/multi-user.target.wants/bluetooth.service"

echo ":: Building ISO (this takes a while)"
mkdir -p "$OUT"
# Watch for the case described at release_work: once package installation is
# over (no pacstrap/arch-chroot running) nothing may stay mounted in the image.
# The few steps between it and mksquashfs give the watcher time to step in.
sudo -v     # one root watcher for the whole build, so it never asks for a password
watch_image() {
    while sleep 1; do
        pgrep -x mksquashfs >/dev/null && break
        { pgrep -x pacstrap || pgrep -x arch-chroot; } >/dev/null && continue
        [[ -n $(mounts_below "$1") ]] && release_work "$1"
    done
}
sudo bash -c "$(declare -f mounts_below release_work watch_image); watch_image \"\$1\"" _ "$WORK/tmp" &
watcher=$!
trap 'sudo kill "$watcher" 2>/dev/null' EXIT
sudo mkarchiso -v -w "$WORK/tmp" -o "$OUT" "$PROFILE"
sudo kill "$watcher" 2>/dev/null
clean_work

echo
echo ":: Done:"
ls -1 "$OUT"/*.iso
