# veadotube-controller

Small Python controller that switches Nova's veadotube mini avatar between
talking and idle over the official WebSocket API, with an optional
audio-reactive mouth movement mode.

## What it does

- Connects to veadotube mini's WebSocket server as client `GemiController`.
- Uses the `nodes` channel and the `boolean` node `mini` (push-to-talk).
- Provides a reusable `set_talking(True/False)` function.
- On first run (`--test`): connects, activates TALKING for 3 seconds,
  deactivates it, then disconnects.
- Audio-reactive mode (`--audio`): captures Windows system-output audio
  (WASAPI loopback, including Discord voice) and drives Nova's talking/idle
  state via the `boolean` node `mini`. Nova's mouth opens and closes in
  response to system audio volume — this is the approach Tessa confirmed works.
- Prints connection status and state changes to the terminal.
- On failure or disconnect, attempts to reset TALKING to OFF and mouth to
  closed first.

## Requirements

- Python 3
- [`websocket-client`](https://pypi.org/project/websocket-client/) (base dependency)
- [`pyaudiowpatch`](https://pypi.org/project/PyAudioWPatch/) (audio-reactive mode only)

## Windows installation

1. Open PowerShell (or Command Prompt) in this folder.
2. Install the base dependency:

   ```powershell
   pip install websocket-client
   ```

   If you don't have `pip` on `PATH`, use:

   ```powershell
   python -m pip install websocket-client
   ```

3. For audio-reactive mode, also install PyAudioWPatch:

   ```powershell
   pip install pyaudiowpatch
   ```

## Execution

Make sure veadotube mini is running on your Windows PC with its WebSocket
server enabled, then run:

**Three-second talking test (the original behavior):**

```powershell
python controller.py --test
```

**Audio-reactive mouth movement:**

```powershell
python controller.py --audio
```

The WebSocket address is configurable. By default the script will attempt to
discover the port from veadotube mini's instance data folder (`%USERPROFILE%\.veadotube\instances`). If discovery succeeds, the discovered port is used; otherwise the default `50200` is used, or you can pass `--port <port>` manually.

```powershell
python controller.py --audio
```

You can still override the port manually:

```powershell
python controller.py --audio --port 51959
```

Other audio options:

```powershell
python controller.py --audio --threshold 0.03 --decay 0.8 --min-open-ms 100
```

Avatar state ids depend on your loaded avatar. Adjust them if needed:

```powershell
python controller.py --audio --open-state talking --closed-state idle
```

## veadotube mini configuration

- **WebSocket server:** enable it in veadotube mini and note the port (the
  working test used `51959`; the default here is `50200`).
- **Port discovery:** on startup, if `--port` is not explicitly set, the script
  reads `%USERPROFILE%\.veadotube\instances` to find the running veadotube mini
  instance's server port automatically. If no instance data is found, the
  default `50200` is used and a message is printed.
- **Mouth states:** the audio-reactive mode now drives the `boolean` node
  `mini` (push-to-talk) via `set_talking()`, not the `stateEvents` node.
  Nova's mouth opens and closes in response to system audio volume — this is
  the approach Tessa confirmed works. The default talking/idle state ids are
  `talking` and `idle`, but check your avatar's actual state ids and pass
  `--open-state` / `--closed-state` if they differ (these are now mainly for
  reference).
- **Audio device:** PyAudioWPatch captures the default speakers' loopback
  device. Make sure the audio you want Nova to react to is playing through
  those speakers.

## Protocol notes

- WebSocket URL: `ws://127.0.0.1:50200/?n=GemiController`
- Messages are sent on the `nodes` channel, prefixed with `nodes: `.
- Push-to-talk is the `boolean` node with id `mini`; setting it to `true`
  activates TALKING, `false` returns to idle.
- Mouth movement in audio-reactive mode is driven by toggling the
  `boolean` node `mini` on/off with `set_talking()`. This is the approach
  Tessa confirmed works: Nova's mouth opens and closes in response to system
  audio volume.
- State ids `talking` and `idle` are the default avatar state names; they
  are mainly kept for reference and the three-second test mode.

Docs: https://veado.tube/docs/tech/api/ and https://veado.tube/docs/tech/api/nodes/

## Protocol notes

- WebSocket URL: `ws://127.0.0.1:50200/?n=GemiController`
- Messages are sent on the `nodes` channel, prefixed with `nodes: `.
- Push-to-talk is the `boolean` node with id `mini`; setting it to `true`
  activates TALKING, `false` returns to idle.
- Mouth state is the `stateEvents` node with id `mini`; setting a state via
  `{"event": "set", "state": "<state id>"}` switches the avatar's mouth image.

Docs: https://veado.tube/docs/tech/api/ and https://veado.tube/docs/tech/api/nodes/
