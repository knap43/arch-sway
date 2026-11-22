# Start Mango automatically after logging in on tty1.
if status is-login; and test -z "$WAYLAND_DISPLAY"; and test (tty) = /dev/tty1
    # This machine's keyboard options (Alt and Win trade places on a PC keyboard)
    mkdir -p ~/.cache/mbp
    echo "xkb_rules_options="(mbp-xkb-options) > ~/.cache/mbp/mango-keyboard.conf
    mango; and exit
end
