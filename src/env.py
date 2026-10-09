"""Mocked enterprise environment: the 'world' agents act on.

Five systems, in-memory (no network, fully reproducible):
  - ticketing  : service-desk tickets
  - identity   : users, licenses, access flags
  - devices    : laptops/phones inventory
  - knowledge  : KB articles (for search_kb)
  - network    : zone status (for outage triage)

Every mutating tool appends to `audit_log` so verifiers can check
*what* was done, *in what order*, and whether side-effects are complete.
This mirrors the ITSMBench finding that agents often fix the main issue
but leave records/follow-ups incomplete.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field


@dataclass
class EnterpriseEnv:
    users: dict = field(default_factory=dict)
    devices: dict = field(default_factory=dict)
    tickets: dict = field(default_factory=dict)
    kb: list = field(default_factory=list)
    network: dict = field(default_factory=dict)
    audit_log: list = field(default_factory=list)

    # ------------------------------------------------------------------ seed
    @classmethod
    def seed(cls) -> "EnterpriseEnv":
        env = cls()
        env.users = {
            "u_ava": {"id": "u_ava", "name": "Ava Chen", "email": "ava@acme.com",
                      "active": True, "mfa_verified": True, "licenses": ["slack", "github"],
                      "access": ["vpn", "hr-portal"], "password_reset": False},
            "u_ben": {"id": "u_ben", "name": "Ben Rao", "email": "ben@acme.com",
                      "active": True, "mfa_verified": False, "licenses": ["slack"],
                      "access": ["vpn"], "password_reset": False},
            "u_cara": {"id": "u_cara", "name": "Cara Lee", "email": "cara@acme.com",
                       "active": True, "mfa_verified": True, "licenses": ["o365", "slack"],
                       "access": ["vpn", "prod-db"], "password_reset": False},
            "u_dev": {"id": "u_dev", "name": "Dev Patel", "email": "dev@acme.com",
                      "active": True, "mfa_verified": True, "licenses": ["github"],
                      "access": ["vpn"], "password_reset": False},
            "u_ella": {"id": "u_ella", "name": "Ella Kim", "email": "ella@acme.com",
                       "active": False, "mfa_verified": True, "licenses": ["slack", "o365"],
                       "access": ["vpn"], "password_reset": False},  # already offboarded (distractor)
            "u_finn": {"id": "u_finn", "name": "Finn Das", "email": "finn@acme.com",
                       "active": True, "mfa_verified": True, "licenses": ["o365"],
                       "access": [], "password_reset": False},
        }
        env.devices = {
            "d_ava1": {"id": "d_ava1", "owner": "u_ava", "model": "MacBook Pro 14",
                       "status": "active", "encrypted": True, "reported_lost": False},
            "d_ben1": {"id": "d_ben1", "owner": "u_ben", "model": "ThinkPad X1",
                       "status": "active", "encrypted": False, "reported_lost": True},
            "d_cara1": {"id": "d_cara1", "owner": "u_cara", "model": "MacBook Air",
                        "status": "active", "encrypted": True, "reported_lost": False},
            "d_pool1": {"id": "d_pool1", "owner": None, "model": "MacBook Air",
                        "status": "pool", "encrypted": True, "reported_lost": False},
            "d_pool2": {"id": "d_pool2", "owner": None, "model": "ThinkPad X1",
                        "status": "pool", "encrypted": True, "reported_lost": False},
        }
        env.tickets = {
            f"T-{100+i}": {"id": f"T-{100+i}", "status": "open", "notes": [],
                            "assignee": None, "escalated_to": None}
            for i in range(40)
        }
        env.kb = [
            {"id": "kb01", "title": "Password reset SOP",
             "body": "Verify MFA first, then reset_password with verified=true. Update ticket with note."},
            {"id": "kb02", "title": "Offboarding SOP",
             "body": "Disable account, revoke ALL licenses, remove VPN access, update ticket."},
            {"id": "kb03", "title": "Lost device SOP",
             "body": "If device unencrypted and lost: wipe_device with confirmed=true, then reissue_device from pool, update ticket."},
            {"id": "kb04", "title": "VPN outage triage",
             "body": "Check get_network_status for the zone. If degraded, escalate to netops with reason. Do not reset passwords."},
            {"id": "kb05", "title": "Phishing triage",
             "body": "Security incident: disable account temporarily, escalate to secops, do NOT grant access."},
            {"id": "kb06", "title": "Access request policy",
             "body": "prod-db access requires manager approval note in ticket. Never grant without approval evidence."},
        ]
        env.network = {
            "blr-office": {"zone": "blr-office", "status": "healthy", "latency_ms": 22},
            "vpn-east": {"zone": "vpn-east", "status": "degraded", "latency_ms": 1400},
            "vpn-west": {"zone": "vpn-west", "status": "healthy", "latency_ms": 60},
        }
        env.audit_log = []
        return env

    # ---------------------------------------------------------------- helpers
    def clone(self) -> "EnterpriseEnv":
        return copy.deepcopy(self)

    def log(self, tool: str, args: dict, result: str):
        self.audit_log.append({"tool": tool, "args": args, "result": result})

    def ticket(self, tid: str) -> dict:
        if tid not in self.tickets:
            raise KeyError(f"unknown ticket {tid}")
        return self.tickets[tid]
