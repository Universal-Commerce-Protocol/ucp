#   Copyright 2026 UCP Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Capability negotiation: what every Business does before it handles a call.

The Platform names its profile on each request. The Business fetches that
profile, checks the protocol version, and intersects the two capability
sets. The result decides which operations are available and which
extension fields may appear on the wire.

Specification: overview, "Negotiation Protocol" and "Protocol Version".
"""

import ipaddress
import json
import re
import socket
import time
from urllib.parse import urlsplit

from jsonschema.exceptions import best_match

PROFILE_TTL = 60  # seconds; the specification sets this as the floor
MAX_PROFILE_BYTES = 1_000_000
MAX_CACHED_PROFILES = 256
_UCP_AGENT = re.compile(r'(?:^|[,;\s])profile="([^"]+)"')
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


# The specification's negotiation errors: UCP code -> HTTP status.
NEGOTIATION_ERRORS = {
  "invalid_profile_url": 400,
  "profile_unreachable": 424,
  "profile_malformed": 422,
  "version_unsupported": 422,
}


class ProtocolError(Exception):
  """The request failed before any handler ran.

  REST answers with `status` and the `body()`. MCP answers with a JSON-RPC
  error that carries the same body as its `data`, and the same HTTP status.
  """

  def __init__(
    self,
    content: str,
    code: str | None = None,
    status: int | None = None,
    rpc: int = -32001,
  ):
    """Take a negotiation error `code`, or a bare `status` for other errors."""
    super().__init__(content)
    self.content, self.code, self.rpc = content, code, rpc
    self.status = status or NEGOTIATION_ERRORS[code]

  def body(self) -> dict:
    """Return the wire body shared by both transports."""
    code = {"code": self.code} if self.code else {}
    return {**code, "content": self.content}


def profile_url(ucp_agent: str | None) -> str:
  """Read the Platform profile URL out of a `UCP-Agent` header value."""
  match = _UCP_AGENT.search(ucp_agent or "")
  if not match:
    raise ProtocolError(
      'UCP-Agent must carry profile="<https URL>"', "invalid_profile_url"
    )
  return match.group(1)


def resolve(host: str) -> list[str]:
  """Resolve a host name to the addresses a fetch would connect to."""
  return [info[4][0] for info in socket.getaddrinfo(host, 443)]


class Profiles:
  """Fetches and caches Platform profiles under the specification's rules."""

  def __init__(self, http, validator, resolver=resolve, local: bool = False):
    """Fetch through `http` and accept what `validator` finds no fault with.

    `validator` checks a document against the Platform profile schema.
    `local` relaxes HTTPS for loopback development. Pass `resolver=None`
    only when `http` cannot reach a network, as in the in-process check,
    where there are no addresses to vet.
    """
    self.http, self.validator = http, validator
    self.resolver, self.local = resolver, local
    self._cache: dict[str, tuple[float, dict]] = {}

  def _vet(self, url: str) -> None:
    """Reject URLs the Business must not dereference.

    This vets the addresses a host name resolves to, but the fetch resolves
    the name again. A production fetcher must connect to the address it
    vetted, or a hostile DNS server can answer differently the second time.
    """
    parts = urlsplit(url)
    loopback = self.local and parts.hostname in _LOOPBACK_HOSTS
    if not parts.hostname or parts.username or parts.password:
      raise ProtocolError(f"Malformed URL: {url}", "invalid_profile_url")
    if parts.scheme != "https" and not loopback:
      raise ProtocolError(
        f"Profile URL must use https: {url}", "invalid_profile_url"
      )
    if self.resolver is None or loopback:
      return
    try:
      addresses = self.resolver(parts.hostname)
    except OSError as error:
      raise ProtocolError(
        f"Cannot resolve {parts.hostname}", "profile_unreachable"
      ) from error
    if not all(ipaddress.ip_address(a).is_global for a in addresses):
      raise ProtocolError(
        f"{parts.hostname} is not a public host", "invalid_profile_url"
      )

  async def _fetch(self, url: str) -> bytes:
    """Fetch a profile: no redirects, and no more than the size limit."""
    body = b""
    try:
      request = self.http.stream("GET", url, follow_redirects=False)
      async with request as response:
        if response.status_code != 200:
          raise ProtocolError(
            f"{url} answered {response.status_code}", "profile_unreachable"
          )
        async for chunk in response.aiter_bytes():
          body += chunk
          if len(body) > MAX_PROFILE_BYTES:
            raise ProtocolError(f"{url} is too large", "profile_malformed")
    except ProtocolError:
      raise
    except Exception as error:
      raise ProtocolError(
        f"Cannot fetch {url}", "profile_unreachable"
      ) from error
    return body

  async def get(self, url: str) -> dict:
    """Return the profile at `url`, fetching it at most once per TTL."""
    cached = self._cache.get(url)
    if cached and time.monotonic() - cached[0] < PROFILE_TTL:
      return cached[1]
    self._vet(url)
    try:
      profile = json.loads(await self._fetch(url))
    except ValueError as error:
      raise ProtocolError(f"{url} is not JSON", "profile_malformed") from error
    fault = best_match(self.validator.iter_errors(profile))
    if fault:
      raise ProtocolError(
        f"{url} is not a Platform profile: {fault.message}", "profile_malformed"
      )
    if len(self._cache) >= MAX_CACHED_PROFILES:
      del self._cache[next(iter(self._cache))]  # forget the oldest
    self._cache[url] = (time.monotonic(), profile)
    return profile


def _parents(entry: dict) -> list[str]:
  """Return the capabilities an entry extends, as a list."""
  extends = entry.get("extends", [])
  return [extends] if isinstance(extends, str) else list(extends)


def negotiate(business: dict, platform: dict) -> dict[str, dict]:
  """Return the active capabilities: name to the Business's chosen entry.

  Follows the four steps of the Intersection Algorithm, after the protocol
  version check that precedes it.
  """
  ours, theirs = business["ucp"], platform["ucp"]
  if theirs["version"] != ours["version"]:
    raise ProtocolError(
      f"Protocol version {theirs['version']} is not supported. "
      f"This business supports {ours['version']}.",
      "version_unsupported",
    )

  active: dict[str, dict] = {}
  offered = theirs.get("capabilities", {})
  for name, entries in ours.get("capabilities", {}).items():
    # Steps 1 and 2: same name, then the highest version both sides list.
    mutual = {e["version"] for e in entries} & {
      e["version"] for e in offered.get(name, [])
    }
    if mutual:
      best = max(mutual)  # versions are ISO dates, so text order is date order
      active[name] = next(e for e in entries if e["version"] == best)

  # Steps 3 and 4: drop extensions left without any parent, until stable.
  pruned = True
  while pruned:
    orphans = [
      name
      for name, entry in active.items()
      if _parents(entry) and not any(p in active for p in _parents(entry))
    ]
    for name in orphans:
      del active[name]
    pruned = bool(orphans)
  return active


def relevant(active: dict[str, dict], root: str) -> dict[str, list[dict]]:
  """Select the `ucp.capabilities` of a response to a `root` operation.

  A response lists the root capability and the active extensions of it,
  and nothing else from the negotiated set.
  """
  return {
    name: [{"version": entry["version"]}]
    for name, entry in active.items()
    if name == root or root in _parents(entry)
  }


def payment_handlers(business: dict, platform: dict) -> dict[str, list[dict]]:
  """Resolve the payment handlers and instruments offered to a Platform.

  A payment handler is offered when both profiles declare it. Its
  instruments are the Business's, narrowed to the types the Platform also
  lists; a Platform entry that lists none accepts them all. This sample's
  instruments carry no constraints, so there are none to intersect.
  """
  theirs = platform["ucp"].get("payment_handlers", {})
  resolved = {}
  for name, entries in business["ucp"].get("payment_handlers", {}).items():
    if name not in theirs:
      continue
    accepts_all = any("available_instruments" not in e for e in theirs[name])
    types = {
      instrument["type"]
      for entry in theirs[name]
      for instrument in entry.get("available_instruments", [])
    }
    offered = []
    for entry in entries:
      if "available_instruments" not in entry:
        offered.append(entry)  # the Business takes any instrument
        continue
      instruments = [
        instrument
        for instrument in entry.get("available_instruments", [])
        if accepts_all or instrument["type"] in types
      ]
      if instruments:
        offered.append({**entry, "available_instruments": instruments})
    if offered:
      resolved[name] = offered
  return resolved
