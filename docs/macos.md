# macOS

The daemon, the CLI and the web editor (`ulanzi-linux gui`) run on macOS. The
`desktop` window and the session agent are Linux-only.

This port was written and unit-tested on Linux. It has not yet been run
against a D200 on a Mac, so treat the first run as a test.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[web]"
ulanzi-linux devices
```

No udev rule and no `libhidapi` package are needed: the `hidapi` wheel bundles
the library and macOS lets a user open the deck's vendor interface.

## Ulanzi Studio

Only one program can drive the deck. Quit Ulanzi Studio, and remove it from
System Settings > General > Login Items, before starting the daemon; otherwise
the two overwrite each other's pages. The deck shows its stock buttons whenever
no daemon is connected, so run the daemon at login (below) to keep your pages.

## Permissions

| Action | Needs |
|---|---|
| `shell`, `url`, `switch_page`, volume and mute keys | nothing |
| Other shortcuts (`ctrl+alt+t`, `cmd+space`), play/pause/next/previous | Accessibility |
| `display_screenshot_selection` | Screen Recording |

Grant these under System Settings > Privacy & Security to the program that
starts the daemon: your terminal app, or the venv's `python3` when launchd
starts it.

## What differs from Linux

| Linux | macOS |
|---|---|
| `xdotool key ctrl+alt+t` | System Events keystroke; `super`, `meta`, `cmd` and `win` are Command, `alt` is Option |
| `XF86AudioMute`, `XF86AudioRaiseVolume`, `XF86AudioLowerVolume` | set the output volume (6 points a press) |
| `XF86AudioMicMute` | input level to 0, and back to 75 |
| `XF86AudioPlay`, `XF86AudioNext`, `XF86AudioPrev` | the hardware media key |
| `gnome_terminal` | `open -a Terminal` |
| `gnome_show_applications` | Launchpad (the Apps app from macOS 26) |
| `display_screenshot_selection` | `screencapture -i` to the Desktop |
| `/proc` stats in the small window | `psutil`; GPU and temperature read `n/a` |
| DejaVu and Liberation fonts on text keys | Arial, Times New Roman, Courier New |

## Run at login

Save as `~/Library/LaunchAgents/com.ulanzi-linux.daemon.plist`, with the two
paths changed to yours, then run
`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ulanzi-linux.daemon.plist`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.ulanzi-linux.daemon</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/.venv/bin/ulanzi-linux</string>
    <string>daemon</string>
    <string>/path/to/deck.yaml</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>5</integer>
  <key>StandardOutPath</key><string>/tmp/ulanzi-linux.log</string>
  <key>StandardErrorPath</key><string>/tmp/ulanzi-linux.log</string>
</dict>
</plist>
```

`KeepAlive` restarts the daemon when it exits after the deck is unplugged, which
is how it recovers from a replug.
