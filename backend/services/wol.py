import re
import socket

from shared.config import WOL_TARGET_MAC, WOL_BROADCAST_IP, WOL_PORT

_MAC_RE = re.compile(r"^[0-9A-Fa-f]{2}([:-]?[0-9A-Fa-f]{2}){5}$")

def _normalize_mac(mac: str) -> bytes:
    mac = mac.strip().replace("-", "").replace(":", "")
    if len(mac) != 12 or not all(c in "0123456789abcdefABCDEF" for c in mac):
        raise ValueError("Invalid MAC address format")
    return bytes.fromhex(mac)

def send_magic_packet(mac: str | None = None) -> dict:
    target_mac = (mac or WOL_TARGET_MAC).strip()
    if not target_mac:
        raise ValueError("WOL_TARGET_MAC is not configured")

    if not _MAC_RE.match(target_mac):
        raise ValueError("Invalid MAC address format")

    mac_bytes = _normalize_mac(target_mac)
    payload = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(payload, (WOL_BROADCAST_IP, WOL_PORT))

    return {
        "success": True,
        "message": f"Wake packet sent to {target_mac} via {WOL_BROADCAST_IP}:{WOL_PORT}",
    }