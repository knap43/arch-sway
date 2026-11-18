#!/usr/bin/env bash
# Builds the MacBook Pro sway ISO on top of Arch's official "releng" profile.
# Usage: ./build.sh          (needs the 'archiso' package; asks for sudo)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELENG=/usr/share/archiso/configs/releng
WORK="$HERE/work"
PROFILE="$WORK/profile"
OUT="$HERE/out"

[[ -d $RELENG ]] || { echo "archiso is not installed: sudo pacman -S archiso" >&2; exit 1; }

echo ":: Preparing profile from releng"
sudo rm -rf "$WORK"
mkdir -p "$WORK"
cp -a "$RELENG" "$PROFILE"

# Packages: releng's list + ours, deduplicated.
# (releng still lists the prebuilt broadcom-wl, which Arch has dropped
#  in favour of broadcom-wl-dkms, so filter it out.)
grep -vhE '^\s*(#|$)' "$PROFILE/packages.x86_64" "$HERE/packages.system" \
    | grep -vx 'broadcom-wl' | sort -u > "$WORK/pkgs"
mv "$WORK/pkgs" "$PROFILE/packages.x86_64"

# Overlay our files onto the live root filesystem.
cp -a "$HERE/overlay/." "$PROFILE/airootfs/"
install -Dm644 "$HERE/packages.system" "$PROFILE/airootfs/usr/local/share/mbp/packages.system"

# Networking: NetworkManager instead of releng's iwd + systemd-networkd.
UNITS="$PROFILE/airootfs/etc/systemd/system"
find "$UNITS" \( -name 'iwd.service' -o -name 'systemd-networkd*' \) -type l -delete
mkdir -p "$UNITS/multi-user.target.wants"
ln -sf /usr/lib/systemd/system/NetworkManager.service "$UNITS/multi-user.target.wants/NetworkManager.service"
ln -sf /etc/systemd/system/live-user.service          "$UNITS/multi-user.target.wants/live-user.service"

# Name and permissions (profiledef.sh is plain bash, later assignments win).
cat >> "$PROFILE/profiledef.sh" <<'EOF'

# --- mbp-sway overrides ---
iso_name="mbp-sway"
iso_publisher="mbp-sway <local build>"
iso_application="Arch Linux + sway for MacBookPro8,1"
file_permissions["/usr/local/bin/mbp-install"]="0:0:755"
file_permissions["/usr/local/bin/live-user-setup"]="0:0:755"
file_permissions["/etc/sudoers.d/live"]="0:0:440"
EOF

# Every helper in /usr/local/bin is executable.
for f in "$HERE"/overlay/usr/local/bin/*; do
    echo "file_permissions[\"/usr/local/bin/$(basename "$f")\"]=\"0:0:755\"" >> "$PROFILE/profiledef.sh"
done

# Bluetooth in the live session too.
ln -sf /usr/lib/systemd/system/bluetooth.service "$UNITS/multi-user.target.wants/bluetooth.service"

echo ":: Building ISO (this takes a while)"
mkdir -p "$OUT"
sudo mkarchiso -v -w "$WORK/tmp" -o "$OUT" "$PROFILE"
sudo rm -rf "$WORK"

echo
echo ":: Done:"
ls -1 "$OUT"/*.iso
