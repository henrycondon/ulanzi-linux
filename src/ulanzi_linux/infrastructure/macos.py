"""macOS stand-ins for the host tools the Linux build shells out to.

Linux sends shortcuts with ``xdotool``/``wtype``. macOS has neither, so a
shortcut written in the same xdotool syntax (``ctrl+alt+t``, ``Super+A``,
``XF86AudioMute``) is turned into an ``osascript`` call here:

* volume and mute keys set the system volume directly (no permission needed);
* play/pause, next and previous post the hardware media key;
* everything else is typed through System Events.

The last two need the process that runs the daemon to be allowed under
System Settings > Privacy & Security > Accessibility.
"""

from __future__ import annotations

import sys

OSASCRIPT = "/usr/bin/osascript"
VOLUME_STEP = 6

_MODIFIERS = {
    "ctrl": "control down",
    "control": "control down",
    "alt": "option down",
    "option": "option down",
    "shift": "shift down",
    "super": "command down",
    "meta": "command down",
    "cmd": "command down",
    "command": "command down",
    "win": "command down",
}

# Virtual key codes (ANSI layout) for keys that are not a single character.
_KEY_CODES = {
    "return": 36,
    "enter": 36,
    "tab": 48,
    "space": 49,
    "backspace": 51,
    "escape": 53,
    "esc": 53,
    "delete": 117,
    "home": 115,
    "end": 119,
    "page_up": 116,
    "prior": 116,
    "page_down": 121,
    "next": 121,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
    "f1": 122,
    "f2": 120,
    "f3": 99,
    "f4": 118,
    "f5": 96,
    "f6": 97,
    "f7": 98,
    "f8": 100,
    "f9": 101,
    "f10": 109,
    "f11": 103,
    "f12": 111,
}

# NX_KEYTYPE_* codes of the hardware media keys.
_MEDIA_KEYS = {
    "xf86audioplay": 16,
    "xf86audiopause": 16,
    "xf86audionext": 17,
    "xf86audioprev": 18,
}

_MEDIA_KEY_JXA = (
    "ObjC.import('Cocoa');"
    "function run(argv){var key=parseInt(argv[0]);[0xa,0xb].forEach(function(state){"
    "var ev=$.NSEvent.otherEventWithTypeLocationModifierFlagsTimestampWindowNumber"
    "ContextSubtypeData1Data2(14,$.NSMakePoint(0,0),state<<8,0,0,$(),8,"
    "(key<<16)|(state<<8),-1);"
    "$.CGEventPost(0,ev.CGEvent);});}"
)

_VOLUME_SCRIPTS: dict[str, tuple[str, ...]] = {
    "xf86audiomute": (
        "set volume output muted (not (output muted of (get volume settings)))",
    ),
    "xf86audioraisevolume": (
        f"set v to (output volume of (get volume settings)) + {VOLUME_STEP}",
        "if v > 100 then set v to 100",
        "set volume output volume v",
    ),
    "xf86audiolowervolume": (
        f"set v to (output volume of (get volume settings)) - {VOLUME_STEP}",
        "if v < 0 then set v to 0",
        "set volume output volume v",
    ),
    # macOS has no microphone mute; the input level goes to 0 and back to 75.
    "xf86audiomicmute": (
        "if (input volume of (get volume settings)) > 0 then",
        "set volume input volume 0",
        "else",
        "set volume input volume 75",
        "end if",
    ),
}

_FONT_DIR = "/System/Library/Fonts/Supplemental"
_FONT_STYLE_SUFFIX = {
    (False, False): "",
    (True, False): " Bold",
    (False, True): " Italic",
    (True, True): " Bold Italic",
}
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"


def font_fallbacks(family: str, *, bold: bool = False, italic: bool = False) -> tuple[str, ...]:
    """System fonts that stand in for the DejaVu/Liberation families on macOS."""
    if "Mono" in family:
        base = "Courier New"
    elif "Serif" in family:
        base = "Times New Roman"
    else:
        base = "Arial"
    return (f"{_FONT_DIR}/{base}{_FONT_STYLE_SUFFIX[(bold, italic)]}.ttf",)


def is_macos() -> bool:
    return sys.platform == "darwin"


def _applescript(lines: tuple[str, ...]) -> list[str]:
    argv = [OSASCRIPT]
    for line in lines:
        argv += ["-e", line]
    return argv


def shortcut_argv(keys: str) -> list[str] | None:
    """The ``osascript`` command that performs an xdotool-style shortcut.

    Returns ``None`` for a shortcut that cannot be expressed (empty, an
    unknown key name, or more than one non-modifier key).
    """
    parts = [part.strip() for part in keys.split("+") if part.strip()]
    if not parts:
        return None
    key = parts[-1]
    lowered = key.lower()
    if len(parts) == 1:
        if lowered in _VOLUME_SCRIPTS:
            return _applescript(_VOLUME_SCRIPTS[lowered])
        if lowered in _MEDIA_KEYS:
            return [OSASCRIPT, "-l", "JavaScript", "-e", _MEDIA_KEY_JXA, str(_MEDIA_KEYS[lowered])]

    modifiers: list[str] = []
    for part in parts[:-1]:
        modifier = _MODIFIERS.get(part.lower())
        if modifier is None:
            return None
        if modifier not in modifiers:
            modifiers.append(modifier)
    using = f" using {{{', '.join(modifiers)}}}" if modifiers else ""

    if lowered in _KEY_CODES:
        stroke = f"key code {_KEY_CODES[lowered]}"
    elif len(key) == 1 and key not in '"\\':
        stroke = f'keystroke "{key.lower()}"'
    else:
        return None
    return _applescript((f'tell application "System Events" to {stroke}{using}',))


__all__ = ["EMOJI_FONT", "font_fallbacks", "is_macos", "shortcut_argv"]
