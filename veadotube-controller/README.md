# veadotube-controller

Small Python controller that switches Nova's veadotube mini avatar between
talking and idle over the official WebSocket API.

## What it does

- Connects to veadotube mini's WebSocket server as client `GemiController`.
- Uses the `nodes` channel and the `boolean` node `mini` (push-to-talk).
- Provides a reusable `set_talking(True/False)` function.
- On first run: connects, activates TALKING for 3 seconds, deactivates it,
  then disconnects.
- Prints connection status and state changes to the terminal.
- On failure or disconnect, attempts to reset TALKING to OFF first.

## Requirements

- Python 3
- [`websocket-client`](https://pypi.org/project/websocket-client/) (single dependency)

## Windows installation

1. Open PowerShell (or Command Prompt) in this folder.
2. Install the dependency:

   ```powershell
   pip install websocket-client
   ```

   If you don't have `pip` on `PATH`, use:

   ```powershell
   python -m pip install websocket-client
   ```

## Execution

Make sure veadotube mini is running on your Windows PC with its WebSocket
server enabled, listening on `127.0.0.1:50200`, then run:

```powershell
python controller.py
```

The address is configurable. Edit `DEFAULT_HOST` / `DEFAULT_PORT` in
`controller.py`, or pass them to `VeadotubeController(host=..., port=...)`.

## Protocol notes

- WebSocket URL: `ws://127.0.0.1:50200/?n=GemiController`
- Messages are sent on the `nodes` channel, prefixed with `nodes: `.
- Push-to-talk is the `boolean` node with id `mini`; setting it to `true`
  activates TALKING, `false` returns to idle.

Docs: https://veado.tube/docs/tech/api/ and https://veado.tube/docs/tech/api/nodes/
