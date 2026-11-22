# Start Mango automatically after logging in on tty1.
if status is-login; and test -z "$WAYLAND_DISPLAY"; and test (tty) = /dev/tty1
    # This machine's keyboard options (Alt and Win trade places on a PC keyboard)
    mkdir -p ~/.cache/mbp
    echo "xkb_rules_options="(mbp-xkb-options) > ~/.cache/mbp/mango-keyboard.conf
    # Displays 1080p or taller: 1.5x scaling
    begin
        echo "# written at login by 10-session.fish from mbp-display-scale"
        mbp-display-scale | while read -l out scale
            echo "monitor_rule=name:^$out\$,scale:$scale"
        end
    end > ~/.cache/mbp/mango-display.conf
    mango; and exit
end
