"""
Metrics Reporting Configuration tools — 3GPP M1 Interface
Endpoints:
  GET    /3gpp-m1/v2/provisioning-sessions/{id}/metrics-reporting-configurations/{metrics_id}
  DELETE /3gpp-m1/v2/provisioning-sessions/{id}/metrics-reporting-configurations/{metrics_id}
"""

import json
import httpx

from mcp_instance import mcp
import state


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _build_url(session_id: str, metrics_id: str) -> str:
    return (
        f"{state.get_m1_url()}/3gpp-m1/v2/provisioning-sessions/"
        f"{session_id}/metrics-reporting-configurations/{metrics_id}"
    )


def _connect_error(url: str) -> str:
    return f"ERROR: Could not connect to '{url}'. Is the 5GMS AF running?"


# ---------------------------------------------------------------------------
# Tool — Get Metrics Reporting Configuration
# ---------------------------------------------------------------------------
@mcp.tool()
async def get_metrics_reporting_configuration(
    metrics_reporting_configuration_id: str,
    provisioning_session_id: str = None,
    m1_url: str = None,
) -> str:
    """
    Retrieve a Metrics Reporting Configuration from a Provisioning Session.

    PARAMETERS
    ----------
    metrics_reporting_configuration_id (REQUIRED)
        The ID of the metrics reporting configuration to retrieve.
        This ID is returned in the Location header when creating a metrics
        reporting configuration (create_metrics_reporting_configuration).

    provisioning_session_id (OPTIONAL)
        The provisioning session that owns this configuration.
        Defaults to the current session stored in state.

    m1_url (OPTIONAL if already provided)
        Base URL of the 5GMS Application Function M1 interface.
        Example: "http://192.168.1.100:7778"

    RETURNS
    -------
    Full JSON representation of the Metrics Reporting Configuration, including
    scheme, reporting interval, sample percentage, metrics URNs, and URL filters.
    """
    if m1_url:
        state.set_m1_url(m1_url)
    if not state.get_m1_url():
        return "ERROR: No M1 URL configured. Provide m1_url parameter."

    session_id = provisioning_session_id or state.get_session_id()
    if not session_id:
        return "ERROR: No provisioning_session_id provided or stored in state."

    url = _build_url(session_id, metrics_reporting_configuration_id)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)

        if response.status_code == 200:
            try:
                data = response.json()
                pretty = json.dumps(data, indent=2)
            except Exception:
                pretty = response.text
            return (
                f"SUCCESS: Metrics Reporting Configuration '{metrics_reporting_configuration_id}'\n"
                f"  Session: {session_id}\n\n{pretty}"
            )
        elif response.status_code == 404:
            return (
                f"NOT FOUND: Metrics Reporting Configuration '{metrics_reporting_configuration_id}' "
                f"does not exist for session '{session_id}' (HTTP 404)."
            )
        return (
            f"ERROR: HTTP {response.status_code} {response.reason_phrase}\n"
            f"  URL: {url}\n  Response: {response.text[:600]}"
        )

    except httpx.ConnectError:
        return _connect_error(state.get_m1_url())
    except httpx.TimeoutException:
        return f"ERROR: Request timed out to '{state.get_m1_url()}'."
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Tool — Delete Metrics Reporting Configuration
# ---------------------------------------------------------------------------
@mcp.tool()
async def delete_metrics_reporting_configuration(
    metrics_reporting_configuration_id: str,
    provisioning_session_id: str = None,
    m1_url: str = None,
) -> str:
    """
    Delete a Metrics Reporting Configuration from a Provisioning Session.

    Removes the specified metrics reporting configuration. The Provisioning Session
    and other configurations are NOT affected.

    PARAMETERS
    ----------
    metrics_reporting_configuration_id (REQUIRED)
        The ID of the metrics reporting configuration to delete.

    provisioning_session_id (OPTIONAL)
        The provisioning session that owns this configuration.
        Defaults to the current session stored in state.

    m1_url (OPTIONAL if already provided)
        Base URL of the 5GMS Application Function M1 interface.
        Example: "http://192.168.1.100:7778"

    RETURNS
    -------
    Confirmation of deletion or an error message.
    """
    if m1_url:
        state.set_m1_url(m1_url)
    if not state.get_m1_url():
        return "ERROR: No M1 URL configured. Provide m1_url parameter."

    session_id = provisioning_session_id or state.get_session_id()
    if not session_id:
        return "ERROR: No provisioning_session_id provided or stored in state."

    url = _build_url(session_id, metrics_reporting_configuration_id)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url)

        if response.status_code in (200, 204):
            return (
                f"SUCCESS: Metrics Reporting Configuration '{metrics_reporting_configuration_id}' "
                f"deleted from session '{session_id}'."
            )
        elif response.status_code == 404:
            return (
                f"ERROR: Metrics Reporting Configuration '{metrics_reporting_configuration_id}' "
                f"not found for session '{session_id}' (HTTP 404)."
            )
        return (
            f"ERROR: HTTP {response.status_code} {response.reason_phrase}\n"
            f"  URL: {url}\n  Response: {response.text[:600]}"
        )

    except httpx.ConnectError:
        return _connect_error(state.get_m1_url())
    except httpx.TimeoutException:
        return f"ERROR: Request timed out to '{state.get_m1_url()}'."
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"
