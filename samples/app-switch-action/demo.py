#!/usr/bin/env python3
"""Sample (non-normative): an app switch UCP Action.

The Business asks the Platform to launch a deep link (app switch) and await
the Buyer's return before the Platform observes Checkout again.

Stdlib only. Simulates a Business and a Platform in-process::

  python3 demo.py --scenario happy
  python3 demo.py --scenario not_installed
  python3 demo.py --scenario timeout
  python3 demo.py --scenario forged_return
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlparse

ACTION = "com.example.app_switch.launch"
EXT = "com.example.app_switch"
UCP = {"version": "2026-01-11", "status": "success"}
WALLET = "https://wallet.example.com"
SCENARIOS = ["happy", "not_installed", "timeout", "forged_return"]


def log(who, msg, obj=None):
  """Print one step of the interaction, optionally with a JSON body."""
  print(f"\n[{who}] {msg}")
  if obj is not None:
    print(json.dumps(obj, indent=2))


@dataclass
class Business:
  """Simulated Business that emits the app switch Action."""

  checkouts: dict = field(default_factory=dict)
  provider_state: dict = field(default_factory=dict)

  def create(self):
    """Create a Checkout that is ready for completion."""
    cid = "chk_" + secrets.token_hex(4)
    self.checkouts[cid] = {
      "id": cid,
      "status": "ready_for_complete",
      "expires_at": time.time() + 900,
      "actions": None,
      "continue_url": f"https://shop.example.com/checkout/{cid}",
    }
    return self._view(cid)

  def complete(self, cid, req):
    """Accept Complete Checkout and emit the app switch Action."""
    co = self.checkouts[cid]
    ret = (req.get(EXT) or {}).get("return_url")
    if not ret:
      msg = {
        "type": "error",
        "code": "missing_return_url",
        "severity": "recoverable",
        "content": "App switch requires return_url.",
      }
      return self._view(cid, messages=[msg])
    aid = "app-switch-" + secrets.token_hex(3)
    state = secrets.token_urlsafe(24)
    query = urlencode({"session": "ps_789", "state": state})
    co["status"] = "complete_in_progress"
    co["actions"] = {
      ACTION: [
        {
          "id": aid,
          "config": {
            "url": f"{WALLET}/approve?{query}",
            "fallback_url": f"{WALLET}/web/approve?session=ps_789",
            "state": state,
            "return_url": ret,
            "app_hint": {"name": "Example Wallet"},
            "timeout_seconds": 300,
          },
        }
      ]
    }
    self.provider_state[aid] = "pending"
    msg = {
      "type": "info",
      "code": "app_approval_required",
      "content": "Approve the payment in Example Wallet.",
      "path": f"$.actions['{ACTION}'][0]",
    }
    return self._view(cid, messages=[msg])

  def provider_webhook(self, aid, outcome):
    """Record the authoritative out-of-band provider outcome."""
    self.provider_state[aid] = outcome

  def get(self, cid):
    """Return the current Checkout, reflecting provider state."""
    co = self.checkouts[cid]
    for inst in (co.get("actions") or {}).get(ACTION, []):
      if self.provider_state.get(inst["id"]) == "approved":
        co["status"] = "completed"
        co["actions"] = None
        co["order"] = {"id": "ord_" + secrets.token_hex(3)}
    return self._view(cid)

  def _view(self, cid, messages=None):
    co = {
      k: v
      for k, v in self.checkouts[cid].items()
      if not k.startswith("_") and v is not None
    }
    out = {"ucp": UCP, **co}
    if messages:
      out["messages"] = messages
    return out


class Device:
  """Simulated OS: opens links and delivers the return link."""

  def __init__(self, scenario, business):
    """Bind the device to a scenario and the Business backend."""
    self.scenario = scenario
    self.business = business
    self.inbox = []

  def open_url(self, url):
    """Open a universal link; False if no installed app claims it."""
    return not (self.scenario == "not_installed" and f"{WALLET}/approve" in url)

  def run_external_app(self, inst):
    """Approve in the wallet, notify its backend, return the Buyer."""
    cfg = inst["config"]
    if self.scenario == "timeout":
      return
    self.business.provider_webhook(inst["id"], "approved")
    state = cfg["state"]
    if self.scenario == "forged_return":
      state = "attacker-guess"
    query = urlencode({"state": state, "action_id": inst["id"]})
    self.inbox.append(f"{cfg['return_url']}?{query}")


class Platform:
  """Simulated Platform that processes the app switch Action."""

  RETURN_URL = "https://agent.example.com/ucp/return"
  ALLOWED_HOSTS = frozenset({"wallet.example.com"})

  def __init__(self, business, device):
    """Bind the Platform to a Business and a device."""
    self.b = business
    self.dev = device
    self.pending = {}
    self.processed = set()

  def run(self):
    """Drive Create -> Complete -> Action -> Get Checkout."""
    co = self.b.create()
    log("Platform", "Create Checkout ->", co)
    req = {EXT: {"return_url": self.RETURN_URL}}
    co = self.b.complete(co["id"], req)
    log("Platform", "Complete Checkout ->", co)
    while co["status"] == "complete_in_progress":
      for inst in (co.get("actions") or {}).get(ACTION, []):
        if (ACTION, inst["id"]) in self.processed:
          continue
        self.processed.add((ACTION, inst["id"]))
        if self.process(co, inst) == "handoff":
          self.handoff(co)
          return
      co = self.observe(co["id"], co["expires_at"])
      acts = (co.get("actions") or {}).get(ACTION, [])
      still = [i for i in acts if (ACTION, i["id"]) in self.processed]
      if co["status"] == "complete_in_progress" and still:
        log("Platform", f"{still[0]['id']} still outstanding; no relaunch")
        self.handoff(co)
        return
    log("Platform", f"Final Checkout status: {co['status']}", co)

  def handoff(self, co):
    """Hand off to the Buyer; never Cancel while handoff can continue."""
    log("Platform", f"Hand off via continue_url {co['continue_url']}")

  def process(self, co, inst):
    """Validate, launch the deep link, and await the return."""
    cfg = inst["config"]
    if not self.validate(cfg):
      return "handoff"
    self.pending[cfg["state"]] = inst["id"]
    log("Platform", f"Launching deep link: {cfg['url']}")
    if not self.dev.open_url(cfg["url"]):
      fb = cfg.get("fallback_url")
      if not fb or urlparse(fb).hostname not in self.ALLOWED_HOSTS:
        return "handoff"
      log("Platform", f"App not installed; opening fallback {fb}")
    self.dev.run_external_app(inst)
    return self.await_return()

  def validate(self, cfg):
    """Check HTTPS, allow-listed host, return_url echo, and state."""
    u = urlparse(cfg["url"])
    ok = (
      u.scheme == "https"
      and u.hostname in self.ALLOWED_HOSTS
      and cfg["return_url"] == self.RETURN_URL
      and len(cfg["state"]) >= 16
    )
    log("Platform", f"Validate Action config: {ok}")
    return ok

  def await_return(self):
    """Correlate the return link; it signals observe, not an outcome."""
    log("Platform", "Awaiting return to platform ...")
    while self.dev.inbox:
      q = parse_qs(urlparse(self.dev.inbox.pop(0)).query)
      st = q.get("state", [""])[0]
      if st not in self.pending:
        log("Platform", f"Ignoring uncorrelated return state={st!r}")
        continue
      self.pending.pop(st)
      log("Platform", "Return correlated (not an outcome); Get Checkout")
      return "returned"
    log("Platform", "Deadline elapsed; abandoned, but still observe")
    return "abandoned"

  def observe(self, cid, expires_at, tries=4):
    """Get Checkout with bounded backoff, stopping at expires_at."""
    delay = 0.1
    co = self.b.get(cid)
    for _ in range(tries):
      log("Platform", "Get Checkout ->", co)
      done = co["status"] != "complete_in_progress"
      if done or not co.get("actions") or time.time() >= expires_at:
        break
      time.sleep(delay)
      delay *= 2
      co = self.b.get(cid)
    return co


if __name__ == "__main__":
  ap = argparse.ArgumentParser()
  ap.add_argument("--scenario", default="happy", choices=SCENARIOS)
  s = ap.parse_args().scenario
  biz = Business()
  Platform(biz, Device(s, biz)).run()
