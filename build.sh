#!/usr/bin/env bash
# Builds the ISO on top of Arch's official "releng" profile.
# Usage: ./build.sh [sway|hyprland|mango]     (default: sway)
#        needs the 'archiso' package; asks for sudo
#
#        ./build.sh --stage DIR [flavour]
#        no ISO: puts our files and the bundled apps (Tether, RetroHub, toofan,
#        the emulators, tiny-games, Zen's extensions) into DIR, laid out as on
#        the live system. mbp-update uses it to update an installed machine;
#        it needs no archiso and no root.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE=""
if [[ ${1-} == --stage ]]; then
    STAGE=${2:?"--stage needs a directory"}
    shift 2
fi
FLAVOUR=${1:-sway}
FLAVOUR_DIR="$HERE/compositors/$FLAVOUR"
[[ -d $FLAVOUR_DIR ]] || { echo "Unknown flavour '$FLAVOUR'. Choose one of: $(ls "$HERE/compositors" | tr '\n' ' ')" >&2; exit 1; }
RELENG=/usr/share/archiso/configs/releng
if [[ -n $STAGE ]]; then
    WORK=$(mktemp -d)
    trap 'rm -rf "$WORK"' EXIT
    ROOT=$STAGE
    mkdir -p "$ROOT"
else
    WORK="$HERE/work"
    PROFILE="$WORK/profile"
    ROOT="$ROOT"       # the live system's files
    OUT="$HERE/out"
    [[ -d $RELENG ]] || { echo "archiso is not installed: sudo pacman -S archiso" >&2; exit 1; }
fi
iso() { [[ -z $STAGE ]]; }

command -v git >/dev/null || { echo "git is needed to fetch Tether: sudo pacman -S git" >&2; exit 1; }
TETHER_REPO=${TETHER_REPO:-https://github.com/knap43/tether}
GAMES_REPO=${GAMES_REPO:-https://github.com/knap43/tiny-games}
RETROHUB_REPO=${RETROHUB_REPO:-https://github.com/knap43/retrohub}


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

if iso; then
    echo ":: Preparing the $FLAVOUR profile from releng"
    clean_work
    mkdir -p "$WORK"
    cp -a "$RELENG" "$PROFILE"
    # multilib, for umu-launcher and the 32-bit Vulkan driver it needs (RetroHub)
    sed -i '/^#\[multilib\]$/{s/^#//;n;s/^#//}' "$PROFILE/pacman.conf"
    grep -q '^\[multilib\]' "$PROFILE/pacman.conf" || printf '\n[multilib]\nInclude = /etc/pacman.d/mirrorlist\n' >> "$PROFILE/pacman.conf"

    # The installed system's packages: shared ones + this flavour's.
    # One name per line; '#' starts a comment, also after a name.
    sed -E 's/#.*//; s/[[:space:]]+$//; s/^[[:space:]]+//; /^$/d' "$HERE/packages.system" "$FLAVOUR_DIR/packages" > "$WORK/system-pkgs"

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
    REPO="$ROOT/var/lib/mbp/repo"
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
fi

# Overlay our files onto the live root filesystem.
cp -a "$HERE/overlay/." "$ROOT/"
cp -a "$FLAVOUR_DIR/overlay/." "$ROOT/"
sed -E 's/#.*//; s/[[:space:]]+$//; s/^[[:space:]]+//; /^$/d' "$HERE/packages.system" "$FLAVOUR_DIR/packages" \
    | install -Dm644 /dev/stdin "$ROOT/usr/local/share/mbp/packages.system"
# Marks the live system (the installer doesn't copy it); holds the flavour.
iso && echo "$FLAVOUR" > "$ROOT/etc/mbp-live"
install -Dm644 "$HERE/README.md" "$ROOT/usr/local/share/mbp/README.md"
# What was installed, for mbp-update: the flavour, and the repo's commit.
echo "$FLAVOUR" > "$ROOT/usr/local/share/mbp/flavour"
git -C "$HERE" rev-parse HEAD > "$ROOT/usr/local/share/mbp/version" 2>/dev/null \
    || date -u +%Y-%m-%dT%H:%M:%SZ > "$ROOT/usr/local/share/mbp/version"

# Tether (clipboard + file sharing with the phone and other computers).
echo ":: Fetching Tether from $TETHER_REPO"
git clone -q --depth 1 "$TETHER_REPO" "$WORK/tether"
install -d "$ROOT/usr/lib/tether"
cp -r "$WORK/tether/linux/tether" "$ROOT/usr/lib/tether/"
find "$ROOT/usr/lib/tether" -name __pycache__ -prune -exec rm -rf {} +
install -Dm644 "$WORK/tether/linux/desktop/dev.tether.Tether.svg" \
    "$ROOT/usr/share/icons/hicolor/scalable/apps/dev.tether.Tether.svg"

# RetroHub (terminal game launcher: Proton through umu-launcher, Wine, native).
echo ":: Fetching RetroHub from $RETROHUB_REPO"
git clone -q --depth 1 "$RETROHUB_REPO" "$WORK/retrohub"
install -d "$ROOT/usr/lib/retrohub"
cp -r "$WORK/retrohub/src/retrohub" "$ROOT/usr/lib/retrohub/"
find "$ROOT/usr/lib/retrohub" -name __pycache__ -prune -exec rm -rf {} +
install -Dm644 "$WORK/retrohub/packaging/retrohub.fish" \
    "$ROOT/usr/share/fish/vendor_completions.d/retrohub.fish"

# toofan (github.com/vyrx-dev/toofan): a typing-speed test for the terminal.
# Its latest release's static binary, checked against the release's
# checksums.txt; cached per version in ./cache. Optional: if GitHub can't be
# reached, the ISO is built without it. TOOFAN_VERSION=2.4.2 pins a release.
toofan_repo=https://github.com/vyrx-dev/toofan
toofan_ver=${TOOFAN_VERSION:-$(git ls-remote --tags --refs "$toofan_repo" 2>/dev/null \
    | awk -F/ '{print $3}' | sed 's/^v//' | grep -E '^[0-9]+(\.[0-9]+)*$' | sort -V | tail -1 || true)}
toofan_ok=""
if [[ -n $toofan_ver ]]; then
    toofan_tar="toofan_${toofan_ver}_linux_amd64.tar.gz"
    toofan_dl="$toofan_repo/releases/download/v$toofan_ver"
    mkdir -p "$HERE/cache"
    if [[ ! -f $HERE/cache/$toofan_tar ]]; then
        echo ":: Downloading toofan $toofan_ver"
        curl -fsSL -o "$HERE/cache/$toofan_tar.part" "$toofan_dl/$toofan_tar" \
            && mv "$HERE/cache/$toofan_tar.part" "$HERE/cache/$toofan_tar"
    fi
    toofan_sum=$(curl -fsSL "$toofan_dl/toofan_${toofan_ver}_checksums.txt" 2>/dev/null \
        | awk -v f="$toofan_tar" '$2 == f {print $1}' || true)
    if [[ -f $HERE/cache/$toofan_tar && -n $toofan_sum ]] \
        && echo "$toofan_sum  $HERE/cache/$toofan_tar" | sha256sum -c --quiet - 2>/dev/null; then
        tar -xzf "$HERE/cache/$toofan_tar" -C "$WORK" toofan
        install -Dm755 "$WORK/toofan" "$ROOT/usr/local/bin/toofan"
        toofan_ok=1
        echo ":: toofan $toofan_ver added"
    else
        rm -f "$HERE/cache/$toofan_tar"
    fi
fi
[[ -n $toofan_ok ]] || echo "!! Couldn't fetch or verify toofan; building without it" >&2

# DuckStation (PS1) and PCSX2 (PS2) are only published as AppImages. Each is
# downloaded (cached in ./cache), checked against the SHA-256 GitHub records
# for the release asset, and unpacked into /opt/<name> at build time, so it
# needs no FUSE and starts quicker; the wrapper in /usr/local/bin runs its
# AppRun. The image is never executed here: its squashfs is found from the
# ELF header and opened with unsquashfs. Optional, like toofan: if one can't
# be fetched or verified, the ISO is built without it.
# Each entry: name|GitHub repo|release (latest = newest stable)|asset|title|comment|categories|mime types
EMULATORS=(
    "duckstation|stenzek/duckstation|tags/latest|DuckStation-x64.AppImage|DuckStation|PlayStation emulator|Game;Emulator;|application/x-cue;application/x-psx-rom;"
    "pcsx2|PCSX2/pcsx2|latest|pcsx2-*-linux-appimage-x64-Qt.AppImage|PCSX2|PlayStation 2 emulator|Game;Emulator;|application/x-cue;application/x-iso9660-image;application/x-ps2-rom;"
)
appimage_asset() {   # repo release pattern -> "url sha256 tag" from GitHub's API
    curl -fsSL "https://api.github.com/repos/$1/releases/$2" 2>/dev/null | python3 -c '
import fnmatch, json, sys
d = json.load(sys.stdin)
for a in d.get("assets", []):
    if fnmatch.fnmatch(a["name"], sys.argv[1]) and (a.get("digest") or "").startswith("sha256:"):
        print(a["browser_download_url"], a["digest"][7:], d.get("tag_name", "?")); break
' "$3" 2>/dev/null || true
}
squashfs_offset() {  # where the squashfs starts: the end of the runtime ELF
    python3 -c '
import struct, sys
b = open(sys.argv[1], "rb").read(64)
shoff, = struct.unpack_from("<Q", b, 0x28); shentsize, shnum = struct.unpack_from("<HH", b, 0x3A)
off = shoff + shentsize * shnum
f = open(sys.argv[1], "rb"); f.seek(off)
print(off if f.read(4) == b"hsqs" else "")
' "$1"
}
EMU_ADDED=()
for entry in "${EMULATORS[@]}"; do
    IFS='|' read -r emu repo rel pattern title comment categories mimes <<< "$entry"
    read -r emu_url emu_sum emu_tag < <(appimage_asset "$repo" "$rel" "$pattern") || true
    if [[ -z ${emu_url-} ]]; then
        echo "!! Couldn't find $title's AppImage on GitHub; building without it" >&2
        continue
    fi
    emu_file="$HERE/cache/$emu-$emu_sum.AppImage"     # per checksum: rolling releases change
    mkdir -p "$HERE/cache"
    if [[ ! -f $emu_file ]]; then
        echo ":: Downloading $title ($emu_tag)"
        curl -fsSL -o "$emu_file.part" "$emu_url" && mv "$emu_file.part" "$emu_file"
    fi
    if ! { [[ -f $emu_file ]] && echo "$emu_sum  $emu_file" | sha256sum -c --quiet - 2>/dev/null; }; then
        rm -f "$emu_file" "$emu_file.part"
        echo "!! $title's AppImage didn't download or match its checksum; building without it" >&2
        continue
    fi
    emu_off=$(squashfs_offset "$emu_file")
    rm -rf "$WORK/$emu.AppDir"
    if [[ -z $emu_off ]] || ! unsquashfs -q -n -o "$emu_off" -d "$WORK/$emu.AppDir" "$emu_file" >/dev/null; then
        echo "!! Couldn't unpack $title's AppImage; building without it" >&2
        continue
    fi
    install -d "$ROOT/opt"
    cp -a "$WORK/$emu.AppDir" "$ROOT/opt/$emu"
    chmod -R u+rwX,go+rX,go-w "$ROOT/opt/$emu"
    printf '#!/bin/sh\n# %s (%s), unpacked from its AppImage when the ISO was built.\nexec /opt/%s/AppRun "$@"\n' \
        "$title" "$emu_tag" "$emu" > "$ROOT/usr/local/bin/$emu"
    chmod 755 "$ROOT/usr/local/bin/$emu"
    # mkarchiso doesn't keep modes, so list everything that must stay executable.
    if iso; then
        echo "file_permissions[\"/usr/local/bin/$emu\"]=\"0:0:755\"" >> "$PROFILE/profiledef.sh"
        while IFS= read -r -d '' x; do
            echo "file_permissions[\"/opt/$emu/${x#"$WORK/$emu.AppDir/"}\"]=\"0:0:755\"" >> "$PROFILE/profiledef.sh"
        done < <(find "$WORK/$emu.AppDir" -type f -perm -u+x -print0)
    fi
    # The icon the AppImage itself uses (.DirIcon, followed if it's a link).
    emu_icon=$(readlink -f "$WORK/$emu.AppDir/.DirIcon" 2>/dev/null || true)
    icon_name=applications-games
    if [[ -f $emu_icon ]]; then
        ext=${emu_icon##*.}; [[ $ext == svg ]] || ext=png
        install -Dm644 "$emu_icon" "$ROOT/usr/share/pixmaps/$emu.$ext"
        icon_name=$emu
    fi
    cat > "$ROOT/usr/share/applications/mbp-$emu.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$title
Comment=$comment
Exec=/usr/local/bin/$emu %f
Icon=$icon_name
Terminal=false
Categories=$categories
MimeType=$mimes
Keywords=emulator;games;
EOF
    EMU_ADDED+=("$title $emu_tag")
done
(( ${#EMU_ADDED[@]} )) && echo ":: Emulators added: ${EMU_ADDED[*]}"

# Zen Browser, from Flathub, with the runtime and GL drivers it needs, so it
# works offline from the first boot. It's installed into a Flatpak system
# installation of its own, kept in ./cache/flatpak (updated, not re-downloaded,
# on later builds), and packed as one squashfs image: mkarchiso drops file
# modes from airootfs, and Flatpak needs them. The live system mounts the
# image on /var/lib/flatpak (mbp-flatpak-live); the installer copies it out.
# Needs flatpak on the build machine; without it, or offline, the ISO is built
# without Zen. ZEN_APP=... picks another Flathub app id.
ZEN_APP=${ZEN_APP:-app.zen_browser.zen}
FP="$HERE/cache/flatpak"
ZEN_EXTENSIONS=${ZEN_EXTENSIONS:-ublock-origin vimium-ff}

# Extensions, through Zen's system-config extension point (mounted in the
# sandbox at /app/etc/zen): the .xpi files and a policies.json that installs
# them once from those files, so they work offline from the first start;
# users can remove them, and they update from addons.mozilla.org. Zen's own
# policies (the app's distribution/policies.json, $1) are kept, merged in.
# Builds the tree in $WORK/zen-sys. ZEN_EXTENSIONS=... lists addons.mozilla.org slugs.
zen_systemconfig() {
    local dist=$1 slug xpi xpis=()
    rm -rf "$WORK/zen-sys"
    install -d "$WORK/zen-sys/extensions" "$WORK/zen-sys/policies"
    for slug in $ZEN_EXTENSIONS; do
        xpi="$WORK/zen-sys/extensions/$slug.xpi"
        if curl -fsSL -o "$xpi" "https://addons.mozilla.org/firefox/downloads/latest/$slug/latest.xpi" \
            && python3 -c 'import sys, zipfile; sys.exit(zipfile.ZipFile(sys.argv[1]).testzip() is not None)' "$xpi" 2>/dev/null; then
            chmod 644 "$xpi"
            xpis+=("/app/etc/zen/extensions/$slug.xpi")
        else
            rm -f "$xpi"
            echo "!! Couldn't download the Zen extension $slug; leaving it out" >&2
        fi
    done
    [[ -f $dist ]] || dist=""
    python3 - "$dist" "${xpis[@]}" > "$WORK/zen-sys/policies/policies.json" <<'PYEOF'
import json, sys
base = {"policies": {}}
if sys.argv[1]:
    try:
        base = json.load(open(sys.argv[1]))
    except (OSError, ValueError):
        pass
ext = base.setdefault("policies", {}).setdefault("Extensions", {})
ext["Install"] = list(dict.fromkeys(ext.get("Install", []) + sys.argv[2:]))
json.dump(base, sys.stdout, indent=2)
PYEOF
    chmod 644 "$WORK/zen-sys/policies/policies.json"
}

zen_ok=""
if [[ -n $STAGE ]]; then
    # Updating an installed system: Zen itself updates through flatpak; only its
    # extension setup comes from here, built against the installed Zen.
    if command -v flatpak >/dev/null && flatpak --system info "$ZEN_APP" >/dev/null 2>&1; then
        branch_app=$(flatpak --system info "$ZEN_APP" | awk -F': *' '/^ *Branch:/ {print $2; exit}')
        zen_systemconfig "/var/lib/flatpak/app/$ZEN_APP/current/active/files/bin/distribution/policies.json"
        install -d "$ROOT/var/lib/flatpak/extension/$ZEN_APP.systemconfig/x86_64"
        cp -a "$WORK/zen-sys" "$ROOT/var/lib/flatpak/extension/$ZEN_APP.systemconfig/x86_64/${branch_app:-stable}"
        zen_ok=1
    fi
elif command -v flatpak >/dev/null; then
    fp() { sudo env FLATPAK_SYSTEM_DIR="$FP" flatpak --system "$@"; }
    sudo mkdir -p "$FP"
    echo ":: Fetching $ZEN_APP from Flathub (cached in ./cache/flatpak)"
    if fp remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo \
        && fp install -y --noninteractive --or-update flathub "$ZEN_APP"; then
        fp update -y --noninteractive || true
        # Intel video decoding inside the sandbox (both laptops have Intel graphics).
        branch=$(fp info --show-runtime "$ZEN_APP" 2>/dev/null | awk -F/ '{print $NF}')
        [[ -n $branch ]] && fp install -y --noninteractive --or-update flathub \
            "org.freedesktop.Platform.VAAPI.Intel//$branch" || true
        fp uninstall -y --noninteractive --unused || true
        branch_app=$(fp info "$ZEN_APP" 2>/dev/null | awk -F': *' '/^ *Branch:/ {print $2; exit}')
        zen_systemconfig "$FP/app/$ZEN_APP/current/active/files/bin/distribution/policies.json"
        zen_sys="$FP/extension/$ZEN_APP.systemconfig/x86_64/${branch_app:-stable}"
        sudo rm -rf "$zen_sys"
        sudo install -d "$(dirname "$zen_sys")"
        sudo cp -a "$WORK/zen-sys" "$zen_sys"
        sudo chown -R root:root "$zen_sys"
        # Links that point into the build path would dangle on the ISO.
        sudo find "$FP" -lname "$FP/*" -print0 | while IFS= read -r -d '' l; do
            t=$(readlink "$l"); sudo ln -sfn "/var/lib/flatpak/${t#"$FP/"}" "$l"
        done
        install -d "$ROOT/usr/local/share/mbp"
        sudo mksquashfs "$FP" "$ROOT/usr/local/share/mbp/flatpak.sfs" \
            -comp zstd -noappend -quiet -no-progress
        sudo chown "$(id -u):$(id -g)" "$ROOT/usr/local/share/mbp/flatpak.sfs"
        mkdir -p "$ROOT/etc/systemd/system/multi-user.target.wants"
        ln -sf /etc/systemd/system/mbp-flatpak-live.service "$ROOT/etc/systemd/system/multi-user.target.wants/mbp-flatpak-live.service"
        zen_ok=1
        echo ":: Zen added ($(du -h "$ROOT/usr/local/share/mbp/flatpak.sfs" | cut -f1) with its runtime)"
    fi
fi
[[ -n $zen_ok || -n $STAGE ]] || echo "!! Couldn't fetch Zen from Flathub (is flatpak installed here?); building without a browser" >&2

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
        install -Dm644 "$src" "$ROOT/usr/lib/tiny-games/$game.py"
        printf '#!/bin/sh\nexec python3 /usr/lib/tiny-games/%s.py "$@"\n' "$game" \
            | install -Dm755 /dev/stdin "$ROOT/usr/local/bin/$game"
        printf '[Desktop Entry]\nType=Application\nName=%s\nComment=%s\nExec=/usr/local/bin/%s\nIcon=applications-games\nTerminal=false\nCategories=%s\n' \
            "$name" "$comment" "$game" "$categories" \
            | install -Dm644 /dev/stdin "$ROOT/usr/share/applications/tiny-games-$game.desktop"
        iso && echo "file_permissions[\"/usr/local/bin/$game\"]=\"0:0:755\"" >> "$PROFILE/profiledef.sh"
        echo "   + $name"
    done
else
    echo "!! Could not fetch $GAMES_REPO (private: needs your GitHub login). Building without games." >&2
fi

if [[ -n $STAGE ]]; then
    echo ":: Staged the $FLAVOUR files in $STAGE"
    exit 0
fi

# Networking: NetworkManager instead of releng's iwd + systemd-networkd.
UNITS="$ROOT/etc/systemd/system"
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
