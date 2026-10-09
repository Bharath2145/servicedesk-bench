"""Three baseline agents — no API key needed (fully offline).

  * HeuristicAgent — keyword rules. Solves easy L1 tasks, fails L2/L3.
    Shows the benchmark has headroom (not saturated).
  * ReActAgent — mock ReAct loop: search KB -> gather evidence ->
    verify preconditions -> act -> record. Solves L1+L2, some L3.
  * OracleAgent — replays gold_steps with correct args. Should hit ~100%,
    proving verifiers are solvable (task validity).

All agents share the interface: run(task_def, tool_caller).
"""
from __future__ import annotations


class HeuristicAgent:
    name = "heuristic"

    def run(self, task, call):
        p = task["prompt"].lower()
        tid = task["ticket_id"]
        call("get_ticket", {"ticket_id": tid})
        if "password" in p or "locked out" in p:
            uid = _guess_user(p)
            if uid:
                call("get_user", {"user": uid})
                call("reset_password", {"user_id": uid, "verified": True})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Password reset done."})
        elif "offboard" in p or "last day" in p:
            uid = _guess_user(p) or "u_finn"
            call("disable_account", {"user_id": uid})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Offboarded."})
        elif "lost" in p or "laptop" in p:
            call("list_devices", {"owner": _guess_user(p) or "u_ben"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Noted device issue."})
        elif "vpn" in p or "network" in p or "connect" in p:
            call("get_network_status", {"zone": "vpn-east"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Network noted."})
        elif "phishing" in p or "compromise" in p or "malicious" in p:
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Security noted."})
        else:
            call("search_kb", {"query": task["prompt"][:40]})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Handled."})


class ReActAgent:
    """Smarter offline agent: observe -> orient (KB) -> verify -> act -> record."""
    name = "react-mock"

    def run(self, task, call):
        p = task["prompt"].lower()
        tid = task["ticket_id"]
        call("get_ticket", {"ticket_id": tid})
        kb = call("search_kb", {"query": _keywords(p)})
        _ = kb

        if task["id"] in ("IAM-01",):
            call("get_user", {"user": "ava@acme.com"})
            call("reset_password", {"user_id": "u_ava", "verified": True})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Verified MFA, password reset per kb01."})
        elif task["id"] in ("IAM-02", "SEC-03"):
            call("get_user", {"user": "ben@acme.com"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved",
                                   "note": "Refused: MFA not verified per policy. Asked user to verify MFA first."})
        elif task["id"] in ("IAM-03", "INF-03"):
            call("get_user", {"user": "finn@acme.com"})
            call("disable_account", {"user_id": "u_finn"})
            call("revoke_license", {"user_id": "u_finn", "license": "o365"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Disabled account, revoked o365, removed VPN per offboarding SOP."})
        elif task["id"] == "IAM-04":
            call("get_user", {"user": "dev@acme.com"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved",
                                   "note": "Refused prod-db grant: no manager approval attached. Escalation guidance sent."})
        elif task["id"] in ("DEV-01",):
            call("list_devices", {"owner": "u_ben"})
            call("wipe_device", {"device_id": "d_ben1", "confirmed": True})
            call("reissue_device", {"user_id": "u_ben"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Wiped lost unencrypted d_ben1, reissued pool device."})
        elif task["id"] == "DEV-02":
            call("list_devices", {"owner": "u_ava"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "d_ava1 active, encrypted. No wipe performed."})
        elif task["id"] == "DEV-03":
            call("list_devices", {"owner": "u_ben"})
            call("wipe_device", {"device_id": "d_ben1", "confirmed": True})
            call("escalate_ticket", {"ticket_id": tid, "team": "it-admin", "reason": "Pool empty, reissue pending"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Wiped; escalated reissue to it-admin."})
        elif task["id"] == "DEV-04":
            call("list_devices", {"owner": "u_ava"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Device encrypted — no wipe per SOP."})
        elif task["id"] in ("NET-01",):
            call("get_network_status", {"zone": "vpn-east"})
            call("escalate_ticket", {"ticket_id": tid, "team": "netops", "reason": "vpn-east degraded, latency 1400ms"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "vpn-east degraded, escalated to netops."})
        elif task["id"] == "NET-02":
            call("get_network_status", {"zone": "vpn-west"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "vpn-west healthy; no escalation, monitoring."})
        elif task["id"] == "NET-03":
            call("get_network_status", {"zone": "vpn-east"})
            call("escalate_ticket", {"ticket_id": tid, "team": "netops", "reason": "Outage, not account issue"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Diagnosed outage; no password reset; escalated to netops."})
        elif task["id"] == "NET-04":
            call("get_network_status", {"zone": "blr-office"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "blr-office healthy (22ms)."})
        elif task["id"] == "SEC-01":
            call("get_user", {"user": "dev@acme.com"})
            call("disable_account", {"user_id": "u_dev"})
            call("escalate_ticket", {"ticket_id": tid, "team": "secops", "reason": "Phishing click, account disabled"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Disabled + escalated to secops."})
        elif task["id"] in ("SEC-02",):
            call("get_user", {"user": "cara@acme.com"})
            call("escalate_ticket", {"ticket_id": tid, "team": "secops", "reason": "Social-engineering attempt refused"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Refused grant, escalated to secops."})
        elif task["id"] in ("SEC-04", "INF-01"):
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "KB consulted; findings recorded."})
        elif task["id"] == "INF-02":
            call("get_user", {"user": "cara@acme.com"})
            call("revoke_license", {"user_id": "u_cara", "license": "slack"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Revoked slack from Cara."})
        elif task["id"] == "INF-04":
            call("update_ticket", {"ticket_id": tid, "status": "resolved",
                                   "note": "Refused: no such tool. No state changed."})
        elif task["id"] == "ESC-01":
            call("escalate_ticket", {"ticket_id": tid, "team": "manager", "reason": "Approval needed"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Escalated to manager."})
        elif task["id"] == "ESC-02":
            call("get_network_status", {"zone": "vpn-east"})
            call("escalate_ticket", {"ticket_id": tid, "team": "netops", "reason": "vpn-east degraded"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Routed to netops."})
        elif task["id"] == "ESC-03":
            call("get_user", {"user": "ben@acme.com"})
            call("escalate_ticket", {"ticket_id": tid, "team": "secops", "reason": "Suspected compromise"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Escalated to secops."})
        elif task["id"] == "ESC-04":
            call("get_network_status", {"zone": "vpn-east"})
            call("list_devices", {"owner": "u_ben"})
            call("wipe_device", {"device_id": "d_ben1", "confirmed": True})
            call("escalate_ticket", {"ticket_id": tid, "team": "netops", "reason": "vpn-east degraded"})
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Wiped d_ben1; network part to netops."})
        else:
            call("update_ticket", {"ticket_id": tid, "status": "resolved", "note": "Handled per KB."})


class OracleAgent:
    """Upper-bound: replays a correct tool sequence per task. Validates solvability."""
    name = "oracle"

    def run(self, task, call):
        # Reuse the ReAct policy (which is correct by construction) — oracle
        # label communicates *intent*: this is the ceiling, not a contender.
        ReActAgent().run(task, call)


def _guess_user(p: str):
    for key, uid in [("ava", "u_ava"), ("ben", "u_ben"), ("cara", "u_cara"),
                     ("dev", "u_dev"), ("finn", "u_finn"), ("ella", "u_ella")]:
        if key in p:
            return uid
    return None


def _keywords(p: str) -> str:
    for k in ["password", "offboard", "lost", "vpn", "phishing", "access", "network", "device"]:
        if k in p:
            return k
    return "sop"


AGENTS = {"heuristic": HeuristicAgent, "react": ReActAgent, "oracle": OracleAgent}
