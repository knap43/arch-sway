# Make Flatpak apps visible to the launcher. Runs before 10-session.fish
# starts sway, so sway and fuzzel inherit it.
set -q XDG_DATA_DIRS; or set -gx --path XDG_DATA_DIRS /usr/local/share /usr/share
for dir in /var/lib/flatpak/exports/share $HOME/.local/share/flatpak/exports/share
    contains -- $dir $XDG_DATA_DIRS; or set -gx --path XDG_DATA_DIRS $dir $XDG_DATA_DIRS
end
