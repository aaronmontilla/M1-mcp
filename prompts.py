"""
5G-MAG M1 Interface MCP Prompts
================================
Reusable prompt templates for the M1 interface workflow, registered with the
FastMCP instance via @mcp.prompt().

Prompt catalogue
----------------
  complete_m1_setup              Full 3-step setup in one shot
  create_provisioning_session    Step 1 — create a provisioning session
  create_content_hosting         Step 2 — attach a content hosting configuration
  create_consumption_reporting   Step 3 — attach a consumption reporting configuration
  add_metrics_reporting          Optional — add a QoE metrics reporting configuration
  inspect_session                Retrieve and display all resources for a session
  enumerate_sessions             List all provisioning sessions via the MAF API
  teardown_session               Delete all resources for a session (cascade)
"""

from mcp_instance import mcp


@mcp.prompt()
def complete_m1_setup(
    m1_url: str,
    asp_id: str,
    app_id: str,
    ingest_base_url: str,
    entry_point_path: str,
    stream_name: str,
) -> str:
    """Run the complete 3-step M1 setup: provisioning session → content hosting → consumption reporting."""
    return (
        f"Please run the complete 5GMS M1 interface setup in order:\n\n"
        f"1. Create a provisioning session at {m1_url} with ASP ID '{asp_id}' "
        f"and application ID '{app_id}'.\n"
        f"2. Create a content hosting configuration named '{stream_name}' "
        f"that ingests from {ingest_base_url} with entry point '{entry_point_path}' using DASH format.\n"
        f"3. Create a consumption reporting configuration with a 10-second reporting interval, "
        f"100% sample percentage, and both location and access reporting enabled.\n\n"
        f"After each step, confirm success and show the key identifiers before proceeding. "
        f"At the end, retrieve all configurations and display a summary."
    )


@mcp.prompt()
def create_provisioning_session(
    m1_url: str,
    asp_id: str,
    app_id: str,
    session_type: str = "DOWNLINK",
) -> str:
    """Step 1 — Create a new 5GMS provisioning session."""
    return (
        f"Create a new 5GMS provisioning session on the M1 interface.\n\n"
        f"Parameters:\n"
        f"- M1 URL: {m1_url}\n"
        f"- ASP ID: {asp_id}\n"
        f"- Application ID: {app_id}\n"
        f"- Session type: {session_type}\n\n"
        f"After success, display the provisioning session ID and remind me that the next step "
        f"is to create a content hosting configuration."
    )


@mcp.prompt()
def create_content_hosting(
    ingest_base_url: str,
    entry_point_path: str,
    stream_name: str,
    content_type: str = "application/dash+xml",
) -> str:
    """Step 2 — Attach a content hosting configuration to the current provisioning session."""
    return (
        f"Create a content hosting configuration for the current provisioning session.\n\n"
        f"Parameters:\n"
        f"- Name: {stream_name}\n"
        f"- Ingest base URL: {ingest_base_url}\n"
        f"- Entry point path: {entry_point_path}\n"
        f"- Content type: {content_type}\n\n"
        f"Use the provisioning session ID already stored in state. "
        f"After success, display the configuration and remind me that the next step "
        f"is to create a consumption reporting configuration."
    )


@mcp.prompt()
def create_consumption_reporting(
    reporting_interval: int = 10,
    sample_percentage: float = 100.0,
    location_reporting: bool = True,
    access_reporting: bool = True,
) -> str:
    """Step 3 — Attach a consumption reporting configuration to the current provisioning session."""
    return (
        f"Create a consumption reporting configuration for the current provisioning session.\n\n"
        f"Parameters:\n"
        f"- Reporting interval: {reporting_interval} seconds\n"
        f"- Sample percentage: {sample_percentage}%\n"
        f"- Location reporting: {location_reporting}\n"
        f"- Access reporting: {access_reporting}\n\n"
        f"Use the provisioning session ID already stored in state. "
        f"After success, display the full configuration and confirm that the mandatory "
        f"3-step M1 setup is now complete."
    )


@mcp.prompt()
def add_metrics_reporting(
    sampling_period: int,
    reporting_interval: int = 10,
    sample_percentage: float = 100.0,
) -> str:
    """Optional — Add a QoE metrics reporting configuration to the current provisioning session."""
    return (
        f"Add a metrics reporting configuration to the current provisioning session.\n\n"
        f"Parameters:\n"
        f"- Sampling period: {sampling_period} seconds\n"
        f"- Reporting interval: {reporting_interval} seconds\n"
        f"- Sample percentage: {sample_percentage}%\n"
        f"- Metrics to collect: HTTP list, buffer level, representation switch list, MPD information\n\n"
        f"Use the provisioning session ID already stored in state. "
        f"After success, display the assigned metrics reporting configuration ID — "
        f"I will need it to retrieve or delete this configuration later."
    )


@mcp.prompt()
def inspect_session(provisioning_session_id: str = "") -> str:
    """Retrieve and display all resources for a provisioning session."""
    session_ref = (
        f"provisioning session '{provisioning_session_id}'"
        if provisioning_session_id
        else "the provisioning session currently stored in state"
    )
    return (
        f"Retrieve and display all resources for {session_ref}:\n\n"
        f"1. Get the provisioning session details.\n"
        f"2. Get the content hosting configuration.\n"
        f"3. Get the consumption reporting configuration.\n\n"
        f"Present the results as a structured summary, highlighting the key fields "
        f"(IDs, URLs, reporting intervals). Note any resources that are missing or "
        f"not yet configured."
    )


@mcp.prompt()
def enumerate_sessions(maf_url: str) -> str:
    """List all provisioning sessions known to the Application Function via the MAF API."""
    return (
        f"List all provisioning sessions from the 5G-MAG management API at {maf_url}.\n\n"
        f"Display each session's ID, type, ASP ID, and application ID in a clear table. "
        f"If there are no sessions, say so explicitly."
    )


@mcp.prompt()
def teardown_session(provisioning_session_id: str = "") -> str:
    """Delete all resources for a provisioning session (cascade delete)."""
    session_ref = (
        f"provisioning session '{provisioning_session_id}'"
        if provisioning_session_id
        else "the provisioning session currently stored in state"
    )
    return (
        f"Delete all resources for {session_ref} in the correct order:\n\n"
        f"1. Delete the consumption reporting configuration (if present).\n"
        f"2. Delete the content hosting configuration (if present).\n"
        f"3. Delete the provisioning session itself.\n\n"
        f"Confirm each deletion before proceeding to the next step. "
        f"If any step fails because the resource does not exist, skip it and continue. "
        f"At the end, confirm that the session has been fully removed."
    )
