#!/usr/bin/env python3
"""veadotube mini WebSocket controller for Gemi.

Controls Nova's avatar talking/idle state and mouth movement through the
veadotube mini WebSocket API, using the `nodes` channel.

Protocol reference:
- https://veado.tube/docs/tech/api/
- https://veado.tube/docs/tech/api/nodes/

WebSocket address format: ws://<host>:<port>/?n=<client name>
Nodes channel messages are prefixed with `nodes: ` and carry JSON.

Nodes used:
- boolean node `mini` (push-to-talk): controls microphone on/off.
- stateEvents node `mini` (avatar state): controls the avatar's mouth state
  (open/closed). Set states via {"event": "set", "state": "<state id>"}.
  State ids depend on the loaded avatar — check them in veadotube mini and
  adjust the defaults below if yours differ.

Audio capture:
- PyAudioWPatch (pyaudiowpatch) WASAPI loopback captures Windows system
  output audio, including Discord voice and other speaker audio.
"""

import argparse
import array
import json
import sys
import time

import websocket  # pip install websocket-client


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 50200
CLIENT_NAME = "GemiController"

NODE_CHANNEL = "nodes"
BOOLEAN_NODE_TYPE = "boolean"
BOOLEAN_NODE_ID = "mini"
STATEEVENTS_NODE_TYPE = "stateEvents"
STATEEVENTS_NODE_ID = "mini"

# Default avatar state ids for veadotube mini. These depend on the loaded
# avatar; check them in veadotube mini (or via the nodes channel `list`
# event) and adjust as needed, or pass --open-state / --closed-state.
DEFAULT_OPEN_STATE = "talking"
DEFAULT_CLOSED_STATE = "idle"


class VeadotubeController:
    """A little controller for veadotube mini's WebSocket API."""

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, client_name=CLIENT_NAME):
        self.host = host
        self.port = port
        self.client_name = client_name
        self.ws = None
        self.connected = False

    @property
    def address(self):
        return f"{self.host}:{self.port}"

    @property
    def url(self):
        return f"ws://{self.address}/?n={self.client_name}"

    def connect(self):
        """Open the WebSocket connection to veadotube mini."""
        print(f"[connect] Connecting to {self.url} ...")
        try:
            self.ws = websocket.create_connection(self.url, timeout=10)
            self.connected = True
            print(
                f"[connect] Connected to veadotube mini at {self.address} "
                f"as '{self.client_name}'."
            )
            return True
        except Exception as exc:  # noqa: BLE001 - report any connection failure
            self.connected = False
            print(f"[connect] Failed to connect to {self.address}: {exc}")
            return False

    def _send_nodes_message(self, message):
        """Send a JSON message on the `nodes` channel."""
        if not self.connected or self.ws is None:
            raise RuntimeError("Not connected to veadotube mini.")
        payload = f"nodes: {json.dumps(message)}"
        self.ws.send(payload)

    def set_talking(self, talking: bool):
        """Set the push-to-talk boolean node `mini` to talking or idle."""
        value = bool(talking)
        message = {
            "event": "payload",
            "type": BOOLEAN_NODE_TYPE,
            "id": BOOLEAN_NODE_ID,
            "payload": {"event": "set", "value": value},
        }
        state_word = "TALKING" if value else "IDLE"
        print(f"[state] Setting push-to-talk (node 'mini') to {state_word} ...")
        self._send_nodes_message(message)
        print(f"[state] Push-to-talk is now {state_word}.")

    def set_mouth(self, open_: bool, open_state=DEFAULT_OPEN_STATE, closed_state=DEFAULT_CLOSED_STATE):
        """Set the avatar mouth state via the stateEvents node `mini`.

        open_=True pushes the open-mouth state; open_=False pushes the
        closed-mouth state. State ids depend on the loaded avatar — adjust
        the defaults or pass explicit ids if yours differ.
        """
        state = open_state if open_ else closed_state
        message = {
            "event": "payload",
            "type": STATEEVENTS_NODE_TYPE,
            "id": STATEEVENTS_NODE_ID,
            "payload": {"event": "set", "state": state},
        }
        state_word = "OPEN" if open_ else "CLOSED"
        print(f"[mouth] Setting mouth state (node 'mini') to {state_word} ('{state}') ...")
        self._send_nodes_message(message)
        print(f"[mouth] Mouth is now {state_word} ('{state}').")

    def reset_mouth_closed(self, closed_state=DEFAULT_CLOSED_STATE):
        """Force the mouth back to the closed state."""
        if self.connected:
            self.set_mouth(False, closed_state=closed_state)

    def reset_talking_off(self):
        """Force push-to-talk back to OFF (idle)."""
        if self.connected:
            self.set_talking(False)

    def disconnect(self):
        """Close the WebSocket, making sure talking is OFF and mouth closed first."""
        try:
            self.reset_talking_off()
        except Exception as exc:
            print(f"[disconnect] Could not reset talking to OFF: {exc}")
        try:
            self.reset_mouth_closed()
        except Exception as exc:
            print(f"[disconnect] Could not reset mouth to closed: {exc}")
        if self.ws is not None:
            try:
                self.ws.close()
            except Exception as exc:
                print(f"[disconnect] Error closing WebSocket: {exc}")
            self.ws = None
        self.connected = False
        print("[disconnect] Disconnected from veadotube mini.")


class AudioMouth:
    """Captures Windows system audio (WASAPI loopback) and drives mouth open/closed."""

    def __init__(
        self,
        controller: VeadotubeController,
        threshold: float = 0.02,
        decay: float = 0.85,
        min_open_ms: int = 150,
        check_interval_ms: int = 50,
        open_state=DEFAULT_OPEN_STATE,
        closed_state=DEFAULT_CLOSED_STATE,
    ):
        self.controller = controller
        self.threshold = threshold
        self.decay = decay
        self.min_open_ms = min_open_ms
        self.check_interval_ms = check_interval_ms
        self.open_state = open_state
        self.closed_state = closed_state
        self._running = False
        self._mouth_open = False
        self._last_change_time = 0.0
        self._smoothed = 0.0

    def _rms(self, data: bytes) -> float:
        """Root-mean-square of 16-bit PCM samples, normalized to 0..1."""
        count = len(data) // 2
        if count == 0:
            return 0.0
        shorts = array.array("h")
        shorts.frombytes(data[: count * 2])
        mean_square = sum(s * s for s in shorts) / count
        return (mean_square ** 0.5) / 32768.0

    def run(self):
        """Open the loopback stream and drive the mouth until stopped."""
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            print("[audio] pyaudiowpatch is not installed. Run: pip install pyaudiowpatch")
            return 1

        self._running = True
        self._mouth_open = False
        self._smoothed = 0.0
        self._last_change_time = time.monotonic()

        with pyaudio.PyAudio() as p:
            try:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            except OSError:
                print("[audio] WASAPI is not available on this system.")
                return 1

            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            loopback_device = None
            if not default_speakers["isLoopbackDevice"]:
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        loopback_device = loopback
                        break
            if loopback_device is None:
                loopback_device = default_speakers

            print(
                f"[audio] Capturing from: ({loopback_device['index']}) {loopback_device['name']}"
            )
            print(f"[audio] Threshold: {self.threshold}, decay: {self.decay}")
            print("[audio] Press Ctrl+C to stop.")

            chunk_size = 512
            channels = loopback_device["maxInputChannels"]
            rate = int(loopback_device["defaultSampleRate"])

            with p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                frames_per_buffer=chunk_size,
                input=True,
                input_device_index=loopback_device["index"],
            ) as stream:
                while self._running:
                    try:
                        data = stream.read(chunk_size, exception_on_overflow=False)
                    except OSError:
                        break

                    level = self._rms(data)
                    # Smoothing with decay: level rises instantly, fades slowly.
                    if level > self._smoothed:
                        self._smoothed = level
                    else:
                        self._smoothed *= self.decay

                    want_open = self._smoothed > self.threshold
                    now = time.monotonic()

                    if want_open and not self._mouth_open:
                        if now - self._last_change_time >= self.min_open_ms / 1000.0:
                            self._set_mouth(True)
                            self._mouth_open = True
                            self._last_change_time = now
                    elif not want_open and self._mouth_open:
                        if now - self._last_change_time >= self.min_open_ms / 1000.0:
                            self._set_mouth(False)
                            self._mouth_open = False
                            self._last_change_time = now

        return 0

    def _set_mouth(self, open_: bool):
        try:
            self.controller.set_mouth(
                open_, open_state=self.open_state, closed_state=self.closed_state
            )
        except Exception as exc:
            print(f"[audio] Failed to set mouth state: {exc}")

    def stop(self):
        self._running = False


def run_three_second_test(controller: VeadotubeController):
    """Original test: TALKING for 3 seconds, then IDLE, then disconnect."""
    if not controller.connect():
        sys.exit(1)

    try:
        controller.set_talking(True)
        print("[test] Holding TALKING for 3 seconds ...")
        time.sleep(3)
        controller.set_talking(False)
        print("[test] Test complete. Nova's avatar should be back to idle.")
    except KeyboardInterrupt:
        print("\n[test] Interrupted by user.")
    except Exception as exc:  # noqa: BLE001
        print(f"[test] Error during test: {exc}")
    finally:
        controller.disconnect()


def run_audio_mode(controller: VeadotubeController, **kwargs):
    """Audio-reactive mouth movement mode."""
    if not controller.connect():
        sys.exit(1)

    mouth = AudioMouth(controller, **kwargs)
    try:
        mouth.run()
    except KeyboardInterrupt:
        print("\n[audio] Interrupted by user.")
    finally:
        mouth.stop()
        controller.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="veadotube mini controller for Gemi — talking/idle and audio-reactive mouth movement."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="WebSocket host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="WebSocket port (default: 50200)")
    parser.add_argument("--client-name", default=CLIENT_NAME, help="WebSocket client name (default: GemiController)")
    parser.add_argument("--threshold", type=float, default=0.02, help="Audio volume threshold (default: 0.02)")
    parser.add_argument("--decay", type=float, default=0.85, help="Smoothing decay factor (default: 0.85)")
    parser.add_argument("--min-open-ms", type=int, default=150, help="Minimum mouth-open duration in ms (default: 150)")
    parser.add_argument("--open-state", default=DEFAULT_OPEN_STATE, help="Open-mouth avatar state id (default: talking)")
    parser.add_argument("--closed-state", default=DEFAULT_CLOSED_STATE, help="Closed-mouth avatar state id (default: idle)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--test", action="store_true", help="Run the 3-second talking test (default if no mode given)")
    mode.add_argument("--audio", action="store_true", help="Run audio-reactive mouth movement mode")
    args = parser.parse_args()

    controller = VeadotubeController(host=args.host, port=args.port, client_name=args.client_name)

    if args.audio:
        run_audio_mode(
            controller,
            threshold=args.threshold,
            decay=args.decay,
            min_open_ms=args.min_open_ms,
            open_state=args.open_state,
            closed_state=args.closed_state,
        )
    else:
        run_three_second_test(controller)


if __name__ == "__main__":
    main()
