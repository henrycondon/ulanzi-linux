"""macOS support: shortcut translation, predefined commands, metrics, fonts."""

from __future__ import annotations

import sys
import types

import pytest

from ulanzi_linux.application import predefined_commands
from ulanzi_linux.application.action_runner import ActionRunner
from ulanzi_linux.domain.button_config import ShellAction, ShortcutAction
from ulanzi_linux.infrastructure import macos, system_metrics


def _script(argv: list[str]) -> str:
    assert argv[0] == macos.OSASCRIPT
    return "\n".join(argv[i + 1] for i, arg in enumerate(argv) if arg == "-e")


def test_modifier_shortcut_becomes_a_system_events_keystroke() -> None:
    assert _script(macos.shortcut_argv("ctrl+alt+t")) == (
        'tell application "System Events" to keystroke "t" using {control down, option down}'
    )
    assert _script(macos.shortcut_argv("Super+A")) == (
        'tell application "System Events" to keystroke "a" using {command down}'
    )


def test_named_key_uses_its_key_code() -> None:
    assert _script(macos.shortcut_argv("shift+F5")) == (
        'tell application "System Events" to key code 96 using {shift down}'
    )
    assert _script(macos.shortcut_argv("Escape")) == (
        'tell application "System Events" to key code 53'
    )


def test_volume_keys_set_the_system_volume() -> None:
    assert "output muted" in _script(macos.shortcut_argv("XF86AudioMute"))
    assert "+ 6" in _script(macos.shortcut_argv("XF86AudioRaiseVolume"))
    assert "- 6" in _script(macos.shortcut_argv("XF86AudioLowerVolume"))
    assert "input volume" in _script(macos.shortcut_argv("XF86AudioMicMute"))


def test_media_keys_post_the_hardware_key() -> None:
    argv = macos.shortcut_argv("XF86AudioPlay")
    assert argv[:3] == [macos.OSASCRIPT, "-l", "JavaScript"]
    assert argv[-1] == "16"
    assert macos.shortcut_argv("XF86AudioNext")[-1] == "17"
    assert macos.shortcut_argv("XF86AudioPrev")[-1] == "18"


@pytest.mark.parametrize("keys", ["", "hyper+a", "ctrl+NoSuchKey", 'ctrl+"'])
def test_unsupported_shortcuts_return_none(keys: str) -> None:
    assert macos.shortcut_argv(keys) is None


def test_predefined_commands_swap_gnome_tools_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(macos, "is_macos", lambda: True)
    terminal = predefined_commands.resolve_predefined_command("gnome_terminal")
    assert terminal.action == ShellAction(type="shell", cmd="open -a Terminal")
    shot = predefined_commands.resolve_predefined_command("gnome_screenshot")  # an alias
    assert shot.command_id == "display_screenshot_selection"
    assert shot.action.cmd.startswith("screencapture -i ")
    mute = predefined_commands.resolve_predefined_command("audio_mute")
    assert mute.action == ShortcutAction(type="shortcut", keys="XF86AudioMute")


def test_predefined_commands_unchanged_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(macos, "is_macos", lambda: False)
    terminal = predefined_commands.resolve_predefined_command("gnome_terminal")
    assert terminal.action == ShellAction(type="shell", cmd="gnome-terminal")


async def test_runner_sends_shortcuts_through_osascript_on_macos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ActionRunner, "_login_shell_path", lambda self: None)
    monkeypatch.setattr(macos, "is_macos", lambda: True)
    runner = ActionRunner()
    calls: list[list[str]] = []

    async def fake_try_exec(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr(runner, "_try_exec", fake_try_exec)
    monkeypatch.setattr(runner, "_which", lambda _exe: None)  # no xdotool, no wtype
    await runner._run_shortcut(ShortcutAction(type="shortcut", keys="cmd+space"))
    assert calls == [macos.shortcut_argv("cmd+space")]


class _FakePsutil(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("psutil")
        self.battery: object | None = types.SimpleNamespace(percent=81.4)

    def cpu_percent(self, interval: float | None = None) -> float:
        return 37.6

    def virtual_memory(self) -> object:
        return types.SimpleNamespace(percent=62.2)

    def net_io_counters(self, pernic: bool = False) -> dict[str, object]:
        return {
            "lo0": types.SimpleNamespace(bytes_recv=999, bytes_sent=999),
            "en0": types.SimpleNamespace(bytes_recv=1000, bytes_sent=500),
        }

    def sensors_battery(self) -> object | None:
        return self.battery


def test_darwin_metrics_read_from_psutil(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakePsutil()
    monkeypatch.setitem(sys.modules, "psutil", fake)
    reader = system_metrics.DarwinSystemMetrics()
    assert reader.read_cpu_percent() == 38
    assert reader.read_memory_percent() == 62
    assert reader._read_network_total_bytes() == 1500
    assert reader.read_metric_value("battery") == "81%"
    assert reader.read_metric_value("gpu") == "n/a"
    fake.battery = None
    assert reader.read_metric_value("battery") == "n/a"


def test_default_reader_follows_the_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "psutil", _FakePsutil())
    monkeypatch.setattr(system_metrics.sys, "platform", "darwin")
    assert isinstance(system_metrics.default_metrics_reader(), system_metrics.DarwinSystemMetrics)
    monkeypatch.setattr(system_metrics.sys, "platform", "linux")
    assert type(system_metrics.default_metrics_reader()) is system_metrics.ProcSystemMetrics


def test_default_reader_survives_missing_psutil(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "psutil", None)  # import raises ImportError
    monkeypatch.setattr(system_metrics.sys, "platform", "darwin")
    assert type(system_metrics.default_metrics_reader()) is system_metrics.ProcSystemMetrics


def test_font_fallbacks_pick_the_matching_system_face() -> None:
    assert macos.font_fallbacks("DejaVu Sans", bold=True) == (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    )
    assert macos.font_fallbacks("Liberation Serif", italic=True) == (
        "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
    )
    assert macos.font_fallbacks("DejaVu Sans Mono", bold=True, italic=True) == (
        "/System/Library/Fonts/Supplemental/Courier New Bold Italic.ttf",
    )
