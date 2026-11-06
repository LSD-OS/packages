"""Network manager backend for LSD-Welcome.

Handles wired Ethernet detection, Wi-Fi access point scanning,
and network connection via libnm (gi.repository.NM) with safe fallback to nmcli.
Designed to gracefully handle environments without Wi-Fi cards (such as VMs)
and when NetworkManager daemon is offline.
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# Check for gi.repository.NM
HAS_NM = False
try:
    import gi
    gi.require_version("NM", "1.0")
    from gi.repository import NM
    HAS_NM = True
except Exception:
    HAS_NM = False


class NetworkService:
    """Service to inspect and configure network connections."""

    def __init__(self) -> None:
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily initialize and return active NM.Client instance, or None if unavailable."""
        if not HAS_NM:
            return None
        if self._client is not None:
            try:
                if self._client.get_nm_running():
                    return self._client
            except Exception:
                self._client = None
        try:
            client = NM.Client.new(None)
            if client and client.get_nm_running():
                self._client = client
                return client
        except Exception:
            self._client = None
        return None

    def has_wired_connection(self) -> bool:
        """Detect if an active wired (Ethernet) connection exists."""
        client = self._get_client()
        if client is not None:
            try:
                devices = client.get_devices() or []
                has_eth = False
                for dev in devices:
                    dev_type = getattr(dev, "get_device_type", lambda: -1)()
                    # NM.DeviceType.ETHERNET == 1
                    if dev_type == 1:
                        has_eth = True
                        state = getattr(dev, "get_state", lambda: -1)()
                        # NM.DeviceState.ACTIVATED == 100
                        if state == 100:
                            return True
                if has_eth:
                    return False
            except Exception as e:
                logger.debug("NM.Client error in has_wired_connection: %s", e)

        # Fallback to nmcli
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE,STATE", "dev"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.strip().splitlines():
                    parts = line.strip().split(":")
                    if len(parts) >= 2:
                        dev_type = parts[0].strip().lower()
                        state = parts[1].strip().lower()
                        if dev_type == "ethernet" and state.startswith("connected"):
                            return True
        except Exception as e:
            logger.debug("nmcli error in has_wired_connection: %s", e)

        return False

    def scan_wifi_networks(self) -> list[dict[str, Any]]:
        """Scan and list Wi-Fi access points.

        Returns list of dicts with:
            ssid (str): Network SSID
            signal (int): Signal strength 0-100
            security (str): Security mode (e.g. WPA2, WPA3, --)
            active (bool): True if currently connected
        """
        try:
            raw_list = self._query_nm()
        except Exception as e:
            logger.debug("Error querying networks: %s", e)
            raw_list = []

        results: list[dict[str, Any]] = []
        for item in raw_list:
            results.append({
                "ssid": str(item.get("ssid", "")),
                "signal": int(item.get("signal", 0)),
                "security": str(item.get("security", "")),
                "active": bool(item.get("active", False)),
            })
        return results

    def get_wifi_list(self) -> list[dict[str, Any]]:
        """Alias for scan_wifi_networks."""
        return self.scan_wifi_networks()

    def _query_nm(self) -> list[dict[str, Any]]:
        """Query NetworkManager for available Wi-Fi access points.

        Tries libnm D-Bus client first, then falls back to nmcli.
        """
        client = self._get_client()
        if client is not None:
            try:
                return self._scan_gi(client)
            except Exception as e:
                logger.debug("NM.Client _scan_gi error: %s", e)

        return self._scan_nmcli()

    def _scan_gi(self, client: Any) -> list[dict[str, Any]]:
        """Scan Wi-Fi access points using libnm client."""
        try:
            devices = client.get_devices() or []
        except Exception:
            return []

        wifi_devices = [
            d for d in devices
            if getattr(d, "get_device_type", lambda: -1)() == 2  # NM.DeviceType.WIFI == 2
        ]
        if not wifi_devices:
            return []

        networks: list[dict[str, Any]] = []
        for dev in wifi_devices:
            try:
                dev.request_scan(None)
            except Exception:
                pass

            active_bssid = None
            try:
                active_ap = dev.get_active_access_point()
                if active_ap:
                    active_bssid = active_ap.get_bssid()
            except Exception:
                pass

            try:
                aps = dev.get_access_points() or []
            except Exception:
                aps = []

            for ap in aps:
                try:
                    raw_ssid = ap.get_ssid()
                    if not raw_ssid:
                        continue
                    data = raw_ssid.get_data()
                    if HAS_NM and hasattr(NM, "utils_ssid_to_utf8"):
                        try:
                            ssid = NM.utils_ssid_to_utf8(data)
                        except Exception:
                            ssid = data.decode("utf-8", errors="replace")
                    else:
                        ssid = data.decode("utf-8", errors="replace")
                except Exception:
                    continue

                if not ssid:
                    continue

                try:
                    signal = int(ap.get_strength())
                except Exception:
                    signal = 0

                try:
                    bssid = ap.get_bssid()
                except Exception:
                    bssid = None

                is_active = bool(active_bssid and bssid and active_bssid == bssid)

                security = "--"
                try:
                    rsn_flags = ap.get_rsn_flags()
                    wpa_flags = ap.get_wpa_flags()
                    flags = ap.get_flags()
                    if HAS_NM and hasattr(NM, "80211ApSecurityFlags"):
                        sec_flags = getattr(NM, "80211ApSecurityFlags")
                        if rsn_flags:
                            if hasattr(sec_flags, "KEY_MGMT_SAE") and (rsn_flags & sec_flags.KEY_MGMT_SAE):
                                security = "WPA3"
                            elif hasattr(sec_flags, "KEY_MGMT_802_1X") and (rsn_flags & sec_flags.KEY_MGMT_802_1X):
                                security = "WPA2 802.1X"
                            else:
                                security = "WPA2"
                        elif wpa_flags:
                            if hasattr(sec_flags, "KEY_MGMT_802_1X") and (wpa_flags & sec_flags.KEY_MGMT_802_1X):
                                security = "WPA 802.1X"
                            else:
                                security = "WPA"
                        elif flags:
                            security = "WEP"
                        else:
                            security = "--"
                    else:
                        if rsn_flags:
                            security = "WPA2"
                        elif wpa_flags:
                            security = "WPA"
                        elif flags:
                            security = "WEP"
                        else:
                            security = "--"
                except Exception:
                    security = "--"

                networks.append({
                    "ssid": ssid,
                    "signal": signal,
                    "security": security,
                    "active": is_active,
                })

        # Deduplicate by SSID, preferring active status and higher signal
        deduped: dict[str, dict[str, Any]] = {}
        for net in networks:
            ssid = net["ssid"]
            if ssid not in deduped:
                deduped[ssid] = net
            else:
                existing = deduped[ssid]
                if net["active"]:
                    existing["active"] = True
                if net["signal"] > existing["signal"]:
                    existing["signal"] = net["signal"]
                    existing["security"] = net["security"]

        return sorted(deduped.values(), key=lambda x: (not x["active"], -x["signal"]))

    def _scan_nmcli(self) -> list[dict[str, Any]]:
        """Fallback Wi-Fi scan using nmcli command line tool."""
        try:
            subprocess.run(
                ["nmcli", "dev", "wifi", "rescan"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        except Exception:
            pass

        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if res.returncode != 0 or not res.stdout:
                return []

            networks: list[dict[str, Any]] = []
            pattern = re.compile(r"(?<!\\):")
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [p.replace(r"\:", ":") for p in pattern.split(line)]
                if len(parts) >= 4:
                    in_use = parts[0].strip()
                    ssid = parts[1].strip()
                    signal_str = parts[2].strip()
                    security = parts[3].strip()

                    if not ssid or ssid == "--":
                        continue

                    try:
                        signal = int(signal_str)
                    except ValueError:
                        signal = 0

                    active = (in_use == "*")
                    networks.append({
                        "ssid": ssid,
                        "signal": signal,
                        "security": security,
                        "active": active,
                    })

            deduped: dict[str, dict[str, Any]] = {}
            for net in networks:
                ssid = net["ssid"]
                if ssid not in deduped:
                    deduped[ssid] = net
                else:
                    existing = deduped[ssid]
                    if net["active"]:
                        existing["active"] = True
                    if net["signal"] > existing["signal"]:
                        existing["signal"] = net["signal"]
                        existing["security"] = net["security"]

            return sorted(deduped.values(), key=lambda x: (not x["active"], -x["signal"]))
        except Exception as e:
            logger.debug("Error in _scan_nmcli: %s", e)
            return []

    def connect_wifi(self, ssid: str, password: str | None = None) -> bool:
        """Connect to a Wi-Fi network specified by SSID.

        Args:
            ssid: Name of the Wi-Fi network.
            password: Passphrase if network is protected, or None if open.

        Returns:
            True if connected successfully, False otherwise.
        """
        if not ssid:
            return False
        try:
            cmd = ["nmcli", "dev", "wifi", "connect", ssid]
            if password:
                cmd.extend(["password", str(password)])

            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if res.returncode == 0:
                return True

            combined_output = (res.stderr or "") + (res.stdout or "")
            if "already exists" in combined_output.lower():
                up_res = subprocess.run(
                    ["nmcli", "con", "up", "id", ssid],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                return up_res.returncode == 0

            return False
        except Exception as e:
            logger.debug("Error connecting to Wi-Fi '%s': %s", ssid, e)
            return False
