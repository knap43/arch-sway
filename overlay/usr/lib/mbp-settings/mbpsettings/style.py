"""The desktop's look for GTK 4 apps: flat, square corners, greys and the accent colour.

Plain Python with no GTK import, so mbp-conf can load it too: Settings applies
it to its own windows, and mbp-conf writes it to ~/.config/tether/style.css so
Tether looks the same.
"""

# name: (background, the text colour that reads on it); mbp-conf has the same.
ACCENTS = {"blue": ("#5e81ac", "#ffffff"), "teal": ("#88c0d0", "#1e1e1e"), "green": ("#a3be8c", "#1e1e1e"),
           "yellow": ("#ebcb8b", "#1e1e1e"), "orange": ("#d08770", "#1e1e1e"), "red": ("#bf616a", "#ffffff"),
           "purple": ("#b48ead", "#1e1e1e"), "grey": ("#6b6b6b", "#ffffff"),
           "everforest": ("#a7c080", "#2d353b")}

# Each theme names libadwaita's colours plus the few of our own (mbp_*) that
# the rules below use, so the two themes differ only here.
DARK_COLOURS = """
@define-color window_bg_color #1e1e1e;
@define-color window_fg_color #dddddd;
@define-color view_bg_color #1e1e1e;
@define-color view_fg_color #dddddd;
@define-color headerbar_bg_color #2a2a2a;
@define-color headerbar_fg_color #dddddd;
@define-color sidebar_bg_color #232323;
@define-color card_bg_color #2a2a2a;
@define-color popover_bg_color #2a2a2a;
@define-color dialog_bg_color #2a2a2a;
@define-color mbp_sidebar #232323;
@define-color mbp_raised #2a2a2a;
@define-color mbp_hover #303030;
@define-color mbp_button #3b3b3b;
@define-color mbp_border #333333;
"""
LIGHT_COLOURS = """
@define-color window_bg_color #f2f2f2;
@define-color window_fg_color #1e1e1e;
@define-color view_bg_color #f2f2f2;
@define-color view_fg_color #1e1e1e;
@define-color headerbar_bg_color #e4e4e4;
@define-color headerbar_fg_color #1e1e1e;
@define-color sidebar_bg_color #e9e9e9;
@define-color card_bg_color #fbfbfb;
@define-color popover_bg_color #fbfbfb;
@define-color dialog_bg_color #fbfbfb;
@define-color mbp_sidebar #e9e9e9;
@define-color mbp_raised #fbfbfb;
@define-color mbp_hover #e6e6e6;
@define-color mbp_button #dcdcdc;
@define-color mbp_border #cfcfcf;
"""

BASE_CSS = """
* { border-radius: 0; }
window, .background, .view, preferencespage, scrolledwindow { background-color: @window_bg_color; }
headerbar { background-color: @mbp_raised; box-shadow: none; border-bottom: 1px solid @mbp_border; min-height: 38px; }
.navigation-sidebar { background-color: @mbp_sidebar; padding: 6px 0; }
.navigation-sidebar row { padding: 8px 12px; margin: 0; }
.navigation-sidebar row:selected { background-color: @accent_bg_color; color: @accent_fg_color; }
.navigation-sidebar row:selected image { color: @accent_fg_color; }
.boxed-list, list.boxed-list, .card { background-color: @mbp_raised; box-shadow: none; border: 1px solid @mbp_border; }
row.activatable:hover { background-color: @mbp_hover; }
row separator, list.boxed-list > row { border-color: @mbp_border; }
button { box-shadow: none; }
button:not(.flat) { background-color: @mbp_button; }
button.suggested-action { background-color: @accent_bg_color; color: @accent_fg_color; }
switch { border-radius: 0; }
switch slider { border-radius: 0; }
scale trough, scale highlight, scale slider { border-radius: 0; }
toast { border-radius: 0; background-color: @mbp_raised; border: 1px solid @accent_bg_color; }
dialog-host > dialog, dialog .dialog-contents, window.dialog, alertdialog sheet, sheet { border-radius: 0; }
popover contents, popover > arrow { border-radius: 0; }
"""

# Tether's window has a few widgets Settings doesn't: content lists, entries,
# tabs and a view switcher. Square and flat to match.
TETHER_CSS = """
list.content { background-color: @mbp_raised; border: 1px solid @mbp_border; }
entry, spinbutton, dropdown > button, popover > contents { border: 1px solid @mbp_border; box-shadow: none; }
tabbar tab, viewswitcher button { border: 1px solid transparent; }
tabbar tab:selected, viewswitcher button:checked { border-color: @mbp_border; background-color: @mbp_raised; }
"""


def colours(theme):
    return LIGHT_COLOURS if theme == "light" else DARK_COLOURS


def accent_css(name):
    bg, fg = ACCENTS.get(name, ACCENTS["blue"])
    return f"@define-color accent_bg_color {bg}; @define-color accent_fg_color {fg}; @define-color accent_color {bg};\n"


def tether_css(theme, accent):
    return colours(theme) + accent_css(accent) + BASE_CSS + TETHER_CSS
