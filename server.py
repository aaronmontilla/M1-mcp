#!/usr/bin/env python3
"""
5G-MAG M1 Interface MCP Server

Provides tools to configure 5G Media Streaming (5GMS) sessions through
the 3GPP M1 interface (TS 26.512), following the standard 3-step workflow:

  1. create_provisioning_session      → Creates the top-level session container
  2. create_content_hosting_configuration → Defines media ingest & distribution
  3. create_consumption_reporting_configuration → Enables viewer analytics
"""

import json
import httpx
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Session state — persisted across tool calls within a single MCP session
# ---------------------------------------------------------------------------
_state: dict = {
    "m1_url": None,
    "provisioning_session_id": None,
}

TEMPLATE_PATH = Path(__file__).parent / "content_hosting_config_template.json"

# ---------------------------------------------------------------------------
# MCP server definition
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="5G-MAG M1 Interface",
    instructions=(
        "You help users configure 5G Media Streaming (5GMS) sessions via the 3GPP M1 interface. "
        "Always guide users through the 3-step workflow in order:\n"
        "  Step 1 → create_provisioning_session\n"
        "  Step 2 → create_content_hosting_configuration\n"
        "  Step 3 → create_consumption_reporting_configuration\n"
        "Explain each parameter in plain language and suggest the next step after every success."
    ),
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _extract_session_id(response: httpx.Response) -> str | None:
    """Extract provisioningSessionId from JSON body or Location header."""
    try:
        data = response.json()
        if isinstance(data, dict) and data.get("provisioningSessionId"):
            return data["provisioningSessionId"]
    except Exception:
        pass
    # Fallback: Location header (some AF implementations use this)
    location = response.headers.get("Location", "")
    if location:
        return location.rstrip("/").split("/")[-1]
    return None


# ---------------------------------------------------------------------------
# Tool 1 — Create Provisioning Session
# ---------------------------------------------------------------------------
@mcp.tool()
async def create_provisioning_session(
    asp_id: str,
    app_id: str,
    provisioning_session_type: str = "DOWNLINK",
    m1_url: str = None,
) -> str:
    """
    STEP 1 OF 3 — Create a 5GMS Provisioning Session.

    A Provisioning Session is the top-level container that groups all media streaming
    configurations. It must be created before any other configuration can be added.

    PARAMETERS
    ----------
    asp_id (REQUIRED)
        Application Service Provider ID. Identifies your organisation or service.
        Example: "myCompany", "bbc-rd", "my-streaming-provider"

    app_id (REQUIRED)
        Application ID. Uniquely identifies the streaming application within your
        organisation. Example: "live-stream-1", "vod-service", "sports-channel"

    provisioning_session_type (OPTIONAL, default: "DOWNLINK")
        Direction of the media stream:
        - "DOWNLINK"  Server → device. Use for video-on-demand, live TV, IPTV.
                      This is the most common type.
        - "UPLINK"    Device → server. Use for user-generated content uploads.

    m1_url (OPTIONAL if already provided)
        Base URL of the 5GMS Application Function M1 interface.
        Format: http://<host>:<port>
        Example: "http://192.168.1.100:7778"
        Once provided it is remembered for subsequent tool calls in this session.

    RETURNS
    -------
    The Provisioning Session ID, which is stored automatically for the next steps.

    NEXT STEP
    ---------
    Call create_content_hosting_configuration to define how media will be ingested
    and distributed.
    """
    # --- Resolve m1_url ---
    if m1_url:
        _state["m1_url"] = m1_url.rstrip("/")
    if not _state["m1_url"]:
        return (
            "ERROR: No M1 URL provided.\n"
            "Please supply the m1_url parameter with the base URL of your 5GMS Application "
            "Function M1 interface.\n"
            "Example: m1_url='http://192.168.1.100:7778'"
        )

    # --- Validate provisioning_session_type ---
    pst = provisioning_session_type.upper().strip()
    if pst not in {"DOWNLINK", "UPLINK"}:
        return (
            f"ERROR: Invalid provisioning_session_type '{provisioning_session_type}'.\n"
            "Accepted values:\n"
            "  DOWNLINK — server-to-device streaming (video, live TV, VOD)\n"
            "  UPLINK   — device-to-server streaming (uploads, UGC)"
        )

    payload = {
        "aspId": asp_id,
        "appId": app_id,
        "provisioningSessionType": pst,
    }
    url = f"{_state['m1_url']}/3gpp-m1/v2/provisioning-sessions"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        if response.status_code in (200, 201):
            session_id = _extract_session_id(response)
            if session_id:
                _state["provisioning_session_id"] = session_id
                return (
                    f"SUCCESS: Provisioning Session created.\n"
                    f"\n"
                    f"  Session ID : {session_id}\n"
                    f"  ASP ID     : {asp_id}\n"
                    f"  App ID     : {app_id}\n"
                    f"  Type       : {pst}\n"
                    f"  M1 URL     : {_state['m1_url']}\n"
                    f"\n"
                    f"NEXT STEP → Call create_content_hosting_configuration\n"
                    f"  You will need to provide:\n"
                    f"    - name              : a friendly label for this stream\n"
                    f"    - ingest_base_url   : the origin server URL (e.g. https://cdn.example.com/)\n"
                    f"    - entry_point_relative_path : path to the DASH/HLS manifest on that server\n"
                )
            else:
                return (
                    f"WARNING: HTTP {response.status_code} received but could not extract "
                    f"provisioningSessionId from the response.\n"
                    f"Response body: {response.text[:500]}\n"
                    f"Response headers: {dict(response.headers)}"
                )
        else:
            return (
                f"ERROR: HTTP {response.status_code} {response.reason_phrase}\n"
                f"  URL: {url}\n"
                f"  Body sent: {json.dumps(payload, indent=2)}\n"
                f"  Server response: {response.text[:600]}"
            )

    except httpx.ConnectError:
        return (
            f"ERROR: Could not connect to '{_state['m1_url']}'.\n"
            "Please check:\n"
            "  1. The m1_url is correct (format: http://host:port)\n"
            "  2. The 5GMS Application Function is running\n"
            "  3. Network/firewall allows access to that host and port"
        )
    except httpx.TimeoutException:
        return (
            f"ERROR: Request timed out while connecting to '{_state['m1_url']}'.\n"
            "The server may be unreachable or overloaded. Try again or check the URL."
        )
    except Exception as exc:
        return f"ERROR: Unexpected error — {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Tool 2 — Create Content Hosting Configuration
# ---------------------------------------------------------------------------
@mcp.tool()
async def create_content_hosting_configuration(
    name: str,
    ingest_base_url: str,
    entry_point_relative_path: str,
    entry_point_content_type: str = "application/dash+xml",
    domain_name_alias: str = None,
    dash_profiles: list[str] = None,
    ingest_pull: bool = True,
    ingest_protocol: str = "urn:3gpp:5gms:content-protocol:http-pull-ingest",
) -> str:
    """
    STEP 2 OF 3 — Create a Content Hosting Configuration.

    Defines WHERE the media content comes from (ingest origin server) and HOW it will
    be distributed to end-user devices (entry point manifest). Must be called AFTER
    create_provisioning_session.

    MANDATORY PARAMETERS
    --------------------
    name (REQUIRED)
        Human-readable label for this content hosting configuration.
        Example: "My Live Stream", "VOD Library", "Sports Channel HD"

    ingest_base_url (REQUIRED)
        Base URL of the origin server from which the 5GMS AF will pull media content.
        Must end with '/' or one will be added automatically.
        Example: "https://rdmedia.bbc.co.uk/"
                 "http://192.168.1.50:8080/media/"

    entry_point_relative_path (REQUIRED)
        Path to the media manifest file, relative to ingest_base_url.
        For DASH streams this is the .mpd file; for HLS it is the .m3u8 playlist.
        Example (DASH): "elephants_dream/1/client_manifest-all.mpd"
        Example (HLS):  "live/channel1/index.m3u8"

    OPTIONAL PARAMETERS
    -------------------
    entry_point_content_type (default: "application/dash+xml")
        MIME type of the entry point manifest:
        - DASH (most common) : "application/dash+xml"
        - HLS                : "application/vnd.apple.mpegurl"

    domain_name_alias (default: none)
        Alternate hostname or IP address that clients use to reach the CDN/distribution
        point. Useful when the AF's public address differs from its internal address.
        Example: "cdn.example.com"  or  "192.168.1.100"

    dash_profiles (default: ["urn:mpeg:dash:profile:isoff-live:2011"])
        List of DASH profile URNs that describe the stream format.
        Common profiles:
        - "urn:mpeg:dash:profile:isoff-live:2011"      → DASH live streaming
        - "urn:mpeg:dash:profile:isoff-on-demand:2011" → DASH on-demand / VOD

    ingest_pull (default: true)
        true  → AF pulls content from the origin (standard, almost always correct)
        false → Content is pushed TO the AF from the origin

    ingest_protocol (default: "urn:3gpp:5gms:content-protocol:http-pull-ingest")
        Protocol URN for the ingest method. Only change this if your AF uses a
        non-standard protocol.

    NEXT STEP
    ---------
    Call create_consumption_reporting_configuration to enable viewer analytics.
    All parameters have sensible defaults, so you can run it with no arguments.
    """
    if not _state["m1_url"]:
        return (
            "ERROR: No M1 URL configured. Please run create_provisioning_session first "
            "(providing the m1_url parameter)."
        )
    if not _state["provisioning_session_id"]:
        return (
            "ERROR: No Provisioning Session ID found.\n"
            "You must successfully call create_provisioning_session before creating a "
            "Content Hosting Configuration."
        )

    base_url = _state["m1_url"]
    session_id = _state["provisioning_session_id"]

    # --- Load template, fall back to built-in skeleton ---
    try:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {
            "name": "",
            "ingestConfiguration": {
                "pull": True,
                "protocol": "urn:3gpp:5gms:content-protocol:http-pull-ingest",
                "baseURL": "",
            },
            "distributionConfigurations": [
                {
                    "entryPoint": {
                        "relativePath": "",
                        "contentType": "application/dash+xml",
                        "profiles": ["urn:mpeg:dash:profile:isoff-live:2011"],
                    }
                }
            ],
        }

    # --- Populate with user-supplied values ---
    config["name"] = name
    config["ingestConfiguration"]["pull"] = ingest_pull
    config["ingestConfiguration"]["protocol"] = ingest_protocol
    config["ingestConfiguration"]["baseURL"] = (
        ingest_base_url if ingest_base_url.endswith("/") else ingest_base_url + "/"
    )

    profiles = dash_profiles if dash_profiles else ["urn:mpeg:dash:profile:isoff-live:2011"]

    dist = {
        "entryPoint": {
            "relativePath": entry_point_relative_path.lstrip("/"),
            "contentType": entry_point_content_type,
            "profiles": profiles,
        }
    }
    if domain_name_alias:
        dist["domainNameAlias"] = domain_name_alias

    config["distributionConfigurations"] = [dist]

    url = (
        f"{base_url}/3gpp-m1/v2/provisioning-sessions/"
        f"{session_id}/content-hosting-configuration"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=config,
                headers={"Content-Type": "application/json"},
            )

        if response.status_code in (200, 201, 204):
            return (
                f"SUCCESS: Content Hosting Configuration created.\n"
                f"\n"
                f"  Session ID   : {session_id}\n"
                f"  Name         : {name}\n"
                f"  Ingest URL   : {config['ingestConfiguration']['baseURL']}\n"
                f"  Entry Point  : {entry_point_relative_path}\n"
                f"  Content Type : {entry_point_content_type}\n"
                + (f"  Domain Alias : {domain_name_alias}\n" if domain_name_alias else "")
                + f"\n"
                f"NEXT STEP → Call create_consumption_reporting_configuration\n"
                f"  All parameters are optional — defaults are pre-configured:\n"
                f"    - reporting_interval  : 10 seconds\n"
                f"    - sample_percentage   : 100% of clients\n"
                f"    - location_reporting  : enabled\n"
                f"    - access_reporting    : enabled\n"
                f"  You can call it as-is or customise any of the above values."
            )
        else:
            return (
                f"ERROR: HTTP {response.status_code} {response.reason_phrase}\n"
                f"  URL: {url}\n"
                f"  Body sent:\n{json.dumps(config, indent=2)}\n"
                f"  Server response: {response.text[:600]}"
            )

    except httpx.ConnectError:
        return f"ERROR: Could not connect to '{base_url}'. Is the 5GMS AF running?"
    except httpx.TimeoutException:
        return f"ERROR: Request timed out to '{base_url}'."
    except Exception as exc:
        return f"ERROR: Unexpected error — {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Tool 3 — Create Consumption Reporting Configuration
# ---------------------------------------------------------------------------
@mcp.tool()
async def create_consumption_reporting_configuration(
    reporting_interval: int = 10,
    sample_percentage: float = 100.0,
    location_reporting: bool = True,
    access_reporting: bool = True,
) -> str:
    """
    STEP 3 OF 3 — Create a Consumption Reporting Configuration.

    Configures how the 5GMS system collects analytics about how viewers consume
    the media stream. Must be called AFTER create_provisioning_session.
    Ideally also after create_content_hosting_configuration.

    ALL PARAMETERS ARE OPTIONAL — sensible defaults are provided.

    PARAMETERS
    ----------
    reporting_interval (default: 10, unit: seconds)
        How often clients send consumption reports to the reporting server.
        A lower value gives more frequent updates but generates more network traffic.

        Recommended values:
          5  → Near real-time monitoring (testing / small deployments)
         10  → Balanced — good default for most deployments
         30  → Low overhead — suitable for medium deployments
         60  → Minimal traffic — large-scale production

        Must be a positive integer.

    sample_percentage (default: 100.0, range: 0.0–100.0)
        Percentage of connected clients that will send consumption reports.
        Reduce this in large deployments to limit reporting traffic.

          100.0 → All clients report (recommended for testing / small deployments)
           50.0 → Half of clients report (medium deployments)
           10.0 → 10% of clients report (large production environments)

    location_reporting (default: true)
        Whether to include the viewer's geographic location in the report.
        Useful for geographic analytics (coverage maps, regional QoE).

          true  → Location data included (requires device permission)
          false → No location data collected

    access_reporting (default: true)
        Whether to include access network information in the report, such as
        whether the device is on WiFi or cellular, and signal quality.

          true  → Network access info included (useful for QoE analysis)
          false → No access network data collected

    RETURNS
    -------
    A confirmation summary. If all 3 steps are complete, a full workflow summary
    is displayed.
    """
    if not _state["m1_url"]:
        return (
            "ERROR: No M1 URL configured.\n"
            "Please run create_provisioning_session first (providing the m1_url parameter)."
        )
    if not _state["provisioning_session_id"]:
        return (
            "ERROR: No Provisioning Session ID found.\n"
            "You must successfully call create_provisioning_session before creating a "
            "Consumption Reporting Configuration."
        )

    # --- Validate ---
    if reporting_interval <= 0:
        return (
            f"ERROR: reporting_interval must be a positive integer (received {reporting_interval}).\n"
            "Example valid values: 5, 10, 30, 60"
        )
    if not (0.0 <= sample_percentage <= 100.0):
        return (
            f"ERROR: sample_percentage must be between 0.0 and 100.0 "
            f"(received {sample_percentage})."
        )

    base_url = _state["m1_url"]
    session_id = _state["provisioning_session_id"]

    payload = {
        "reportingInterval": reporting_interval,
        "samplePercentage": sample_percentage,
        "locationReporting": location_reporting,
        "accessReporting": access_reporting,
    }

    url = (
        f"{base_url}/3gpp-m1/v2/provisioning-sessions/"
        f"{session_id}/consumption-reporting-configuration"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        if response.status_code in (200, 201, 204):
            return (
                f"SUCCESS: Consumption Reporting Configuration created.\n"
                f"\n"
                f"  Session ID          : {session_id}\n"
                f"  Reporting Interval  : every {reporting_interval} second(s)\n"
                f"  Sample Percentage   : {sample_percentage}%\n"
                f"  Location Reporting  : {'enabled' if location_reporting else 'disabled'}\n"
                f"  Access Reporting    : {'enabled' if access_reporting else 'disabled'}\n"
                f"\n"
                f"All 3 steps completed! Your 5GMS session is fully configured:\n"
                f"  [1] Provisioning Session              : {session_id}\n"
                f"  [2] Content Hosting Configuration     : created\n"
                f"  [3] Consumption Reporting             : configured\n"
                f"\n"
                f"The 5GMS Application Function is now ready to serve media to clients."
            )
        else:
            return (
                f"ERROR: HTTP {response.status_code} {response.reason_phrase}\n"
                f"  URL: {url}\n"
                f"  Body sent: {json.dumps(payload, indent=2)}\n"
                f"  Server response: {response.text[:600]}"
            )

    except httpx.ConnectError:
        return f"ERROR: Could not connect to '{base_url}'. Is the 5GMS AF running?"
    except httpx.TimeoutException:
        return f"ERROR: Request timed out to '{base_url}'."
    except Exception as exc:
        return f"ERROR: Unexpected error — {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
