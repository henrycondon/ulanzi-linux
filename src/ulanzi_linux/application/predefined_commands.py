"""Catalog of named host actions exposed as stable YAML command IDs."""

from __future__ import annotations

from dataclasses import dataclass

from ulanzi_linux.domain.button_config import (
    Action,
    PredefinedCommandAction,
    ShellAction,
    ShortcutAction,
)
from ulanzi_linux.infrastructure import macos


@dataclass(frozen=True, slots=True)
class PredefinedCommandSpec:
    """Resolved definition for a predefined command ID."""

    command_id: str
    action: Action
    aliases: tuple[str, ...] = ()


_PREDEFINED_COMMAND_SPECS = (
    PredefinedCommandSpec(
        command_id="audio_mic_mute",
        action=ShortcutAction(type="shortcut", keys="XF86AudioMicMute"),
    ),
    PredefinedCommandSpec(
        command_id="audio_mute",
        aliases=("volume_mute",),
        action=ShortcutAction(type="shortcut", keys="XF86AudioMute"),
    ),
    PredefinedCommandSpec(
        command_id="audio_volume_down",
        aliases=("volume_down",),
        action=ShortcutAction(type="shortcut", keys="XF86AudioLowerVolume"),
    ),
    PredefinedCommandSpec(
        command_id="audio_volume_up",
        aliases=("volume_up",),
        action=ShortcutAction(type="shortcut", keys="XF86AudioRaiseVolume"),
    ),
    PredefinedCommandSpec(
        command_id="display_screenshot_selection",
        aliases=("gnome_screenshot",),
        action=ShellAction(type="shell", cmd="gnome-screenshot -i"),
    ),
    PredefinedCommandSpec(
        command_id="gnome_show_applications",
        action=ShortcutAction(type="shortcut", keys="Super+A"),
    ),
    PredefinedCommandSpec(
        command_id="gnome_terminal",
        action=ShellAction(type="shell", cmd="gnome-terminal"),
    ),
    PredefinedCommandSpec(
        command_id="media_next",
        aliases=("media_next_track",),
        action=ShortcutAction(type="shortcut", keys="XF86AudioNext"),
    ),
    PredefinedCommandSpec(
        command_id="media_play_pause",
        action=ShortcutAction(type="shortcut", keys="XF86AudioPlay"),
    ),
    PredefinedCommandSpec(
        command_id="media_previous",
        aliases=("media_prev", "media_previous_track"),
        action=ShortcutAction(type="shortcut", keys="XF86AudioPrev"),
    ),
)


PREDEFINED_COMMANDS_BY_ID: dict[str, PredefinedCommandSpec] = {}
for _spec in _PREDEFINED_COMMAND_SPECS:
    PREDEFINED_COMMANDS_BY_ID[_spec.command_id] = _spec
    for _alias in _spec.aliases:
        PREDEFINED_COMMANDS_BY_ID[_alias] = _spec


# The same IDs on macOS, where the GNOME tools do not exist. IDs bound to a
# shortcut need no entry: the action runner translates those itself.
_MACOS_ACTIONS: dict[str, Action] = {
    "display_screenshot_selection": ShellAction(
        type="shell",
        cmd='screencapture -i "$HOME/Desktop/Screenshot $(date +%Y-%m-%d\\ at\\ %H.%M.%S).png"',
    ),
    # Launchpad became the Apps app in macOS 26.
    "gnome_show_applications": ShellAction(
        type="shell",
        cmd="open -a Launchpad || open -a Apps",
    ),
    "gnome_terminal": ShellAction(type="shell", cmd="open -a Terminal"),
}


def resolve_predefined_command(command_id: str) -> PredefinedCommandSpec:
    """Return the catalog entry for a YAML ``command_id``."""

    try:
        spec = PREDEFINED_COMMANDS_BY_ID[command_id]
    except KeyError as exc:
        raise ValueError(f"unknown predefined command id: {command_id!r}") from exc
    if macos.is_macos() and spec.command_id in _MACOS_ACTIONS:
        return PredefinedCommandSpec(
            command_id=spec.command_id,
            action=_MACOS_ACTIONS[spec.command_id],
            aliases=spec.aliases,
        )
    return spec


def canonical_command_id(action: PredefinedCommandAction) -> str:
    """Normalize aliases so the rest of the app sees a stable ID."""

    return resolve_predefined_command(action.command_id).command_id


__all__ = [
    "PredefinedCommandSpec",
    "canonical_command_id",
    "resolve_predefined_command",
]