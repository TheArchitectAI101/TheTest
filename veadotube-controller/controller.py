#!/usr/bin/env python3
"""veadotube mini WebSocket controller for Gemi.

Controls Nova's avatar talking/idle state through the veadotube mini
WebSocket API, using the `nodes` channel and the `boolean` node `mini`
(push-to-talk).

Protocol reference:
- https://veado.tube/docs/tech/api/
- https://veado.tube/docs/tech/api/nodes/

WebSocket address format: ws://<host>:<port>/?n=<client name>
Nodes channel messages are prefixed with `nodes: ` and carry JSON.
"""

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
        return f"ws://{self.address}?n={self.client_name}"

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

    def reset_talking_off(self):
        """Force push-to-talk back to OFF (idle)."""
        if self.connected:
            self.set_talking(False)

    def disconnect(self):
        """Close the WebSocket, making sure talking is OFF first."""
        try:
            self.reset_talking_off()
        except Exception as exc:
            print(f"[disconnect] Could not reset talking to OFF: {exc}")
        if self.ws is not None:
            try:
                self.ws.close()
            except Exception as exc:
                print(f"[disconnect] Error closing WebSocket: {exc}")
            self.ws = None
        self.connected = False
        print("[disconnect] Disconnected from veadotube mini.")


def main():
    controller = VeadotubeController()
    try:
        if not controller.connect():
            sys.exit(1)

        controller.set_talking(True)
        print("[test] Holding TALKING for 3 seconds ...")
        time.sleep(3)

        controller.set_talking(False)
        print("[test] Test complete. Nova's avatar should be back to idle.")
    except KeyboardInterrupt:
        print("\n[test] Interrupted by user.")
    except Exception as exc:  # noqa: BLE001 - surface runtime errors clearly
        print(f"[test] Error during test: {exc}")
    finally:
        controller.disconnect()


if __name__ == "__main__":
    main()
