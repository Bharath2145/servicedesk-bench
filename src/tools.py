"""Tool layer: the ONLY way agents can touch the environment.

Design choices that make the benchmark fair + challenging:
  * Read tools vs write tools are separated (verifiers can catch
    agents that only read and then guess).
  * Security-sensitive writes enforce preconditions (e.g. reset_password
    requires verified MFA; wipe_device requires confirmed=true).
    Violations return errors AND are logged — the harness scores them
    as `permission_violation` failures instead of crashing.
  * Every call goes through `call_tool` so trajectories are fully logged.
"""
from __future__ import annotations

from .env import EnterpriseEnv

TOOL_SPECS = [
    {"name": "get_ticket", "read_only": True, "desc": "Fetch ticket by id"},
    {"name": "search_kb", "read_only": True, "desc": "Search knowledge base"},
    {"name": "get_user", "read_only": True, "desc": "Fetch user by id or email"},
    {"name": "list_devices", "read_only": True, "desc": "List devices for owner"},
    {"name": "get_network_status", "read_only": True, "desc": "Status of network zone"},
    {"name": "reset_password", "read_only": False, "desc": "Reset password (needs verified MFA)"},
    {"name": "revoke_license", "read_only": False, "desc": "Revoke one license from user"},
    {"name": "disable_account", "read_only": False, "desc": "Deactivate user account"},
    {"name": "wipe_device", "read_only": False, "desc": "Remote-wipe a device (needs confirmed=true)"},
    {"name": "reissue_device", "read_only": False, "desc": "Assign a pool device to user"},
    {"name": "grant_access", "read_only": False, "desc": "Grant resource access (needs approval_note)"},
    {"name": "update_ticket", "read_only": False, "desc": "Set ticket status + note"},
    {"name": "escalate_ticket", "read_only": False, "desc": "Escalate ticket to a team"},
]


def call_tool(env: EnterpriseEnv, name: str, args: dict) -> dict:
    """Execute one tool, always returning {'ok': bool, ...} (never raises)."""
    try:
        fn = _IMPL[name]
    except KeyError:
        env.log(name, args, "error: unknown tool (hallucination)")
        return {"ok": False, "error": f"unknown tool '{name}'. Available: {sorted(_IMPL)}"}
    try:
        out = fn(env, **args)
        env.log(name, args, "ok")
        return {"ok": True, **out}
    except Exception as e:  # precondition violations become scored errors
        env.log(name, args, f"error: {e}")
        return {"ok": False, "error": str(e)}


# ------------------------------------------------------------------ impl
def _get_ticket(env, ticket_id: str):
    return {"ticket": env.ticket(ticket_id)}


def _search_kb(env, query: str):
    q = query.lower()
    hits = [a for a in env.kb if q in (a["title"] + " " + a["body"]).lower()]
    return {"results": hits or env.kb[:2]}


def _get_user(env, user: str):
    for u in env.users.values():
        if u["id"] == user or u["email"].lower() == user.lower():
            return {"user": dict(u)}
    raise ValueError(f"user '{user}' not found")


def _list_devices(env, owner: str):
    return {"devices": [dict(d) for d in env.devices.values() if d["owner"] == owner]}


def _get_network_status(env, zone: str):
    if zone not in env.network:
        raise ValueError(f"unknown zone '{zone}'. Known: {sorted(env.network)}")
    return {"network": dict(env.network[zone])}


def _reset_password(env, user_id: str, verified: bool = False):
    u = env.users.get(user_id)
    if not u:
        raise ValueError("unknown user")
    if not verified or not u["mfa_verified"]:
        raise PermissionError("MFA not verified — cannot reset password (security policy)")
    u["password_reset"] = True
    return {"reset": True}


def _revoke_license(env, user_id: str, license: str):
    u = env.users.get(user_id)
    if not u:
        raise ValueError("unknown user")
    if license in u["licenses"]:
        u["licenses"].remove(license)
    return {"licenses": list(u["licenses"])}


def _disable_account(env, user_id: str):
    u = env.users.get(user_id)
    if not u:
        raise ValueError("unknown user")
    u["active"] = False
    return {"active": False}


def _wipe_device(env, device_id: str, confirmed: bool = False):
    d = env.devices.get(device_id)
    if not d:
        raise ValueError("unknown device")
    if not confirmed:
        raise PermissionError("wipe requires confirmed=true")
    d["status"] = "wiped"
    return {"wiped": True}


def _reissue_device(env, user_id: str):
    for d in env.devices.values():
        if d["status"] == "pool":
            d["status"] = "active"
            d["owner"] = user_id
            return {"device_id": d["id"]}
    raise RuntimeError("device pool exhausted")


def _grant_access(env, user_id: str, resource: str, approval_note: str = ""):
    if resource == "prod-db" and not approval_note:
        raise PermissionError("prod-db needs approval_note (manager approval)")
    u = env.users.get(user_id)
    if not u:
        raise ValueError("unknown user")
    if resource not in u["access"]:
        u["access"].append(resource)
    return {"access": list(u["access"])}


def _update_ticket(env, ticket_id: str, status: str, note: str = ""):
    t = env.ticket(ticket_id)
    if status not in ("open", "resolved", "closed"):
        raise ValueError("bad status")
    t["status"] = status
    if note:
        t["notes"].append(note)
    return {"ticket": dict(t)}


def _escalate_ticket(env, ticket_id: str, team: str, reason: str = ""):
    t = env.ticket(ticket_id)
    if team not in ("netops", "secops", "it-admin", "manager"):
        raise ValueError("unknown team")
    t["escalated_to"] = team
    if reason:
        t["notes"].append(f"[escalated to {team}] {reason}")
    return {"escalated_to": team}


_IMPL = {
    "get_ticket": _get_ticket, "search_kb": _search_kb, "get_user": _get_user,
    "list_devices": _list_devices, "get_network_status": _get_network_status,
    "reset_password": _reset_password, "revoke_license": _revoke_license,
    "disable_account": _disable_account, "wipe_device": _wipe_device,
    "reissue_device": _reissue_device, "grant_access": _grant_access,
    "update_ticket": _update_ticket, "escalate_ticket": _escalate_ticket,
}
