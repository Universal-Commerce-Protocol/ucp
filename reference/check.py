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

"""The integration test: `make check`.

Runs the sample Platform against the sample Business, in one process, over
REST and MCP, with and without the discount extension, and checks that the
specification's schemas, service definitions and tooling agree with what
went over the wire.

Nothing here opens a socket. Requests to `https://business.example` and
`https://platform.example` are routed to the two applications in memory,
which keeps runs identical and lets both sides use the HTTPS origins the
specification requires.
"""

import asyncio
import copy
import difflib
import json
import re
import subprocess
import sys
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx2
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from reference import build
from reference.business.app import Business
from reference.business.negotiation import ProtocolError, negotiate, relevant
from reference.platform.client import Platform, RejectedError, shop

VERSION = build.ucp_version()
BUSINESS = "https://business.example"
PLATFORM = "https://platform.example"
TRANSCRIPTS = build.ROOT / "transcripts"

SEARCH = "dev.ucp.shopping.catalog.search"
CART = "dev.ucp.shopping.cart"
CHECKOUT = "dev.ucp.shopping.checkout"
DISCOUNT = "dev.ucp.shopping.discount"
BUYER = {
  "first_name": "Ada",
  "last_name": "Lovelace",
  "email": "ada@example.com",
}

# The capabilities each sample Platform must see in responses, by kind of
# operation. Written out by hand so the check does not lean on the
# negotiation code it is checking.
EXPECTED = {
  "core": {"catalog": [SEARCH], "cart": [CART], "checkout": [CHECKOUT]},
  "discount": {
    "catalog": [SEARCH],
    "cart": [CART, DISCOUNT],
    "checkout": [CHECKOUT, DISCOUNT],
  },
}


def expect(condition, message: str) -> None:
  """Fail the check with a message that says what the wire got wrong."""
  if not condition:
    raise AssertionError(message)


# --- an in-process network --------------------------------------------------


class Network(httpx2.AsyncBaseTransport):
  """Routes each request to an application by host name, and records it."""

  def __init__(self):
    """Start with no hosts."""
    self.hosts: dict[str, httpx2.ASGITransport] = {}
    self.log: list[tuple[httpx2.Request, httpx2.Response]] = []

  async def handle_async_request(self, request):
    """Deliver a request to the application registered for its host."""
    transport = self.hosts.get(request.url.host)
    if transport is None:
      raise httpx2.ConnectError(f"No such host: {request.url.host}")
    response = await transport.handle_async_request(request)
    await response.aread()
    self.log.append((request, response))
    return response


def platform_host() -> Starlette:
  """Serve the sample Platform profiles, and a few broken ones."""
  profiles = build.platform_profiles()
  old = copy.deepcopy(profiles["core"])
  old["ucp"]["version"] = "2025-01-01"
  stranger = copy.deepcopy(profiles["core"])
  stranger["ucp"]["capabilities"] = {}
  profiles |= {"old": old, "stranger": stranger, "malformed": {"hello": 1}}

  async def profile(request):
    found = profiles.get(request.path_params["name"])
    return JSONResponse(found) if found else Response(status_code=404)

  return Starlette(routes=[Route("/profiles/{name}.json", profile)])


class Traced(Platform):
  """A Platform that remembers every call it made."""

  def __init__(self, network: Network, *args):
    """Record calls made through `network`."""
    super().__init__(*args)
    self.network, self.calls, self.statuses = network, [], []
    self._sent = 0

  def _uuid(self, purpose: str) -> str:
    """Return the same UUID on every run, so transcripts do not change."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{purpose}-{self._sent}"))

  async def send(self, operation, body=None, id=None, key=None):
    """Send the call, then record what was sent and what came back."""
    self._sent += 1
    # Copies, so that later changes to a body cannot rewrite the record.
    record = {"operation": operation, "id": id, "body": copy.deepcopy(body)}
    try:
      reply = await super().send(operation, body, id, key)
      record["reply"] = copy.deepcopy(reply)
      return reply
    except RejectedError as rejection:
      record["rejected"] = rejection.body
      raise
    finally:
      self.status = self.network.log[-1][1].status_code
      self.statuses.append(self.status)
      self.calls.append(record)


@asynccontextmanager
async def world(transport: str, name: str, profile: str | None = None):
  """Start a fresh Business and connect one Platform to it."""
  network = Network()
  http_client = httpx2.AsyncClient(transport=network)
  business = Business(http_client, BUSINESS, resolver=None).app()
  network.hosts = {
    "business.example": httpx2.ASGITransport(app=business),
    "platform.example": httpx2.ASGITransport(app=platform_host()),
  }
  url = f"{PLATFORM}/profiles/{profile or name}.json"
  platform = Traced(network, http_client, name, url, transport)
  failure = None
  async with business.lifespan():
    try:
      yield await platform.connect(BUSINESS)
    except AssertionError as error:
      # Raised again below: inside the SDK's task group it would be wrapped
      # in an exception group and lose its message.
      failure = error
    finally:
      await platform.close()
  if failure:
    raise failure


# --- what must hold for every response --------------------------------------


class Bundle:
  """The routes and types `ucp-schema` generated for one profile."""

  def __init__(self, directory: Path):
    """Load `openapi.json` and `types.json` from a generated directory."""
    self.openapi = json.loads((directory / "openapi.json").read_text())
    self.types = json.loads((directory / "types.json").read_text())["$defs"]
    self.models = build.models(directory.name)
    self.operations = {
      operation["operationId"]: operation
      for _, _, operation in build.operations(self.openapi)
    }

  def validate(self, schema: dict, payload, what: str) -> None:
    """Check a payload against a schema that refers into the bundle."""
    text = json.dumps(schema).replace("#/components/schemas/", "#/$defs/")
    validator = Draft202012Validator({**json.loads(text), "$defs": self.types})
    error = best_match(validator.iter_errors(payload))
    where = error and "/".join(str(part) for part in error.absolute_path)
    expect(error is None, f"{what}: /{where}: {error and error.message}")

  def check_call(self, call: dict, what: str) -> None:
    """Validate the request and the response of one recorded call."""
    operation = self.operations[call["operation"]]
    if "requestBody" in operation:
      schema = operation["requestBody"]["content"]["application/json"]["schema"]
      self.validate(schema, call["body"], f"{what} request")
    response = next(iter(operation["responses"].values()))
    schema = response["content"]["application/json"]["schema"]
    self.validate(schema, call["reply"], f"{what} response")

  def check_models(self, call: dict, what: str) -> None:
    """Check that payloads survive a trip through the generated models.

    Each request and response is parsed into its Pydantic model and
    serialized again. What comes out must be what went in.
    """
    operation = self.operations[call["operation"]]
    payloads = [(build.response_type(operation, call["reply"]), call["reply"])]
    if "requestBody" in operation:
      schema = operation["requestBody"]["content"]["application/json"]["schema"]
      payloads.append((schema["$ref"].rsplit("/", 1)[-1], call["body"]))
    for name, payload in payloads:
      model = getattr(self.models, name).model_validate(payload)
      same = build.wire(model) == payload
      expect(same, f"{what}: {name} changed in a round trip")

  def check_consistent(self, what: str) -> None:
    """Check that the OpenAPI components and the bundle hold the same types."""
    for name, schema in self.openapi["components"]["schemas"].items():
      text = json.dumps(schema).replace("#/components/schemas/", "#/$defs/")
      same = json.loads(text) == self.types.get(name)
      expect(
        same, f"{what}: {name} differs between openapi.json and types.json"
      )


def kind(operation: str) -> str:
  """Return `catalog`, `cart` or `checkout` for an operation name."""
  return operation.rsplit("_", 1)[-1]


def check_envelope(call: dict, name: str, what: str) -> None:
  """Check the `ucp` envelope and the negotiated shape of a response."""
  reply, ucp = call["reply"], call["reply"]["ucp"]
  expect(ucp["version"] == VERSION, f"{what}: version is {ucp['version']}")
  wanted = {
    capability: [{"version": VERSION}]
    for capability in EXPECTED[name][kind(call["operation"])]
  }
  expect(
    ucp.get("capabilities") == wanted,
    f"{what}: ucp.capabilities is {ucp.get('capabilities')}, not {wanted}",
  )
  # Schemas allow additional properties, so validation alone would let an
  # extension field through when the extension was not negotiated.
  if DISCOUNT not in wanted:
    expect("discounts" not in reply, f"{what}: discounts without the extension")
  if kind(call["operation"]) == "checkout" and ucp["status"] == "success":
    expect("payment_handlers" in ucp, f"{what}: no ucp.payment_handlers")
    expect("cart_id" not in reply, f"{what}: cart_id must not be returned")


def check_totals(call: dict, what: str) -> None:
  """Totals must add up: lines to the resource, and parts to the total."""
  reply = call["reply"]
  if "totals" not in reply:
    return

  def amounts(totals: list[dict]) -> dict[str, int]:
    return {total["type"]: total["amount"] for total in totals}

  resource = amounts(reply["totals"])
  parts = sum(v for k, v in resource.items() if k != "total")
  expect(parts == resource["total"], f"{what}: totals do not sum to total")
  for part in resource:
    lines = sum(
      amounts(line["totals"]).get(part, 0) for line in reply["line_items"]
    )
    expect(lines == resource[part], f"{what}: line {part}s do not sum up")


def check_resolver(call: dict, business: dict, what: str) -> None:
  """Validate a response a second way: the `ucp-schema validate` command.

  The bundle comes from the code generator and this from the resolver, two
  separate paths through `ucp-schema`. They must agree. The resolver finds
  schemas through `schema` URLs on the capabilities, which responses do not
  carry, so a copy of the response is annotated from the Business profile.
  """
  reply = copy.deepcopy(call["reply"])
  if kind(call["operation"]) == "catalog" or reply["ucp"]["status"] == "error":
    return
  for capability, entries in reply["ucp"]["capabilities"].items():
    declared = business["ucp"]["capabilities"][capability][0]
    for entry in entries:
      entry |= {k: declared[k] for k in ("schema", "extends") if k in declared}
  with tempfile.NamedTemporaryFile("w", suffix=".json") as payload:
    json.dump(reply, payload)
    payload.flush()
    result = subprocess.run(
      [build.ucp_schema(), "validate", payload.name, "--response", "--json"]
      + ["--op", "read", "--schema-local-base", build.REPO / "source/schemas"]
      + ["--schema-remote-base", f"https://ucp.dev/{VERSION}/schemas"],
      capture_output=True,
      text=True,
    )
  expect(
    result.returncode == 0, f"{what}: ucp-schema validate: {result.stdout}"
  )


# --- the checks -------------------------------------------------------------


def check_generated() -> dict[str, Bundle]:
  """Check the generated artifacts and the profiles they came from."""
  generated = {path.name: Bundle(path) for path in sorted(build.OUT.iterdir())}
  for variant, bundle in generated.items():
    bundle.check_consistent(variant)
  # The types each sample Platform works with: `core` negotiates no
  # extension, `discount` negotiates the only one the Business declares.
  bundles = {"core": generated["base"], "discount": generated["full"]}

  # Profiles are checked by the released validator against profile.json.
  served = {
    "business_schema": [build.load(build.ROOT / "business/profile.json")]
  }
  served["platform_schema"] = list(build.platform_profiles().values())
  for definition, profiles in served.items():
    for profile in profiles:
      with tempfile.NamedTemporaryFile("w", suffix=".json") as payload:
        json.dump(profile, payload)
        payload.flush()
        schema = build.REPO / "source/schemas/profile.json"
        result = subprocess.run(
          [build.ucp_schema(), "validate", payload.name, "--schema", schema]
          + ["--def", definition, "--op", "read", "--response", "--json"],
          capture_output=True,
          text=True,
        )
      expect(result.returncode == 0, f"{definition}: {result.stdout}")
  return bundles


def check_negotiation() -> None:
  """Check the intersection algorithm against cases worked out by hand."""
  business = build.load(build.ROOT / "business/profile.json")

  def platform(capabilities: dict, version: str = VERSION) -> dict:
    entries = {
      name: [{"version": v} for v in versions]
      for name, versions in capabilities.items()
    }
    return {"ucp": {"version": version, "capabilities": entries}}

  def active(capabilities: dict) -> set[str]:
    return set(negotiate(business, platform(capabilities)))

  everything = [SEARCH, CART, CHECKOUT, DISCOUNT]
  cases = {
    "all four": ({c: [VERSION] for c in everything}, set(everything)),
    "no discount": (
      {c: [VERSION] for c in everything[:3]},
      set(everything[:3]),
    ),
    # The extension extends cart and checkout. One parent is enough.
    "one parent": (
      {CHECKOUT: [VERSION], DISCOUNT: [VERSION]},
      {CHECKOUT, DISCOUNT},
    ),
    # With neither parent the extension is an orphan and is pruned.
    "orphan": ({SEARCH: [VERSION], DISCOUNT: [VERSION]}, {SEARCH}),
    # A capability with no version in common is left out.
    "no common version": (
      {CART: ["2025-01-01"], CHECKOUT: [VERSION]},
      {CHECKOUT},
    ),
    "highest common": ({CART: ["2025-01-01", VERSION]}, {CART}),
    "nothing shared": ({"com.example.loyalty": [VERSION]}, set()),
  }
  for label, (offered, wanted) in cases.items():
    got = active(offered)
    expect(got == wanted, f"negotiation, {label}: {sorted(got)}")

  try:
    negotiate(business, platform({}, version="2025-01-01"))
    expect(False, "negotiation: an unsupported protocol version was accepted")
  except ProtocolError as error:
    expect(error.code == "version_unsupported", f"negotiation: {error.code}")

  # A response lists the operation's own capability and its extensions only.
  full = negotiate(business, platform({c: [VERSION] for c in everything}))
  expect(set(relevant(full, CART)) == {CART, DISCOUNT}, "relevance: cart")
  expect(set(relevant(full, SEARCH)) == {SEARCH}, "relevance: catalog")


async def funnel(transport: str, name: str, bundle: Bundle):
  """Run the shopping funnel and check every call it made."""
  async with world(transport, name) as platform:
    business = platform.business
    await shop(platform, "field guide")
    log = platform.network.log
  done = platform.calls[-1]["reply"]

  what = f"{transport}/{name}"
  expect(done["status"] == "completed", f"{what}: ended {done['status']}")
  expect("order" in done, f"{what}: completed without an order")
  # Two copies at 18.00, and 10% off with the extension: worked out by hand.
  wanted = [("subtotal", 3600), ("total", 3600)]
  if name == "discount":
    wanted.insert(1, ("items_discount", -360))
    wanted[-1] = ("total", 3240)
  totals = [(total["type"], total["amount"]) for total in done["totals"]]
  expect(totals == wanted, f"{what}: totals are {totals}, not {wanted}")
  for index, call in enumerate(platform.calls, 1):
    label = f"{what} #{index} {call['operation']}"
    bundle.check_call(call, label)
    bundle.check_models(call, label)
    check_envelope(call, name, label)
    check_totals(call, label)
    check_resolver(call, business, label)
    # REST answers with the status the service definition gives; MCP
    # results are always 200.
    responses = bundle.operations[call["operation"]]["responses"]
    status = int(next(iter(responses))) if transport == "rest" else 200
    got = platform.statuses[index - 1]
    expect(got == status, f"{label}: HTTP {got}, not {status}")
    if call["operation"] == "create_checkout" and name == "discount":
      applied = call["reply"].get("discounts", {}).get("applied")
      expect(applied, f"{label}: the cart's discount did not carry forward")
  check_wire(log, what)
  return platform.calls, log


def check_wire(log, what: str) -> None:
  """Check the things that only show at the HTTP level."""
  for request, response in log:
    if request.url.path == "/.well-known/ucp":
      # Profiles must be cacheable for at least a minute.
      cache = response.headers.get("cache-control", "")
      age = re.search(r"max-age=(\d+)", cache)
      cacheable = "public" in cache and age and int(age.group(1)) >= 60
      expect(cacheable, f"{what}: profile Cache-Control is '{cache}'")
    result = response.content and json.loads(response.content)
    result = result.get("result", {}) if isinstance(result, dict) else {}
    if "structuredContent" in result:
      # MCP: the text content must repeat the structured payload.
      text = json.loads(result["content"][0]["text"])
      expect(text == result["structuredContent"], f"{what}: content differs")


async def rejected(
  platform: Traced, status: int, code: str | None, *call
) -> None:
  """Expect a call to be rejected at the protocol level."""
  try:
    await platform.send(*call)
  except RejectedError as rejection:
    got = (platform.status, rejection.body.get("code"))
    expect(got == (status, code), f"{call[0]}: rejected with {got}")
    return
  expect(False, f"{call[0]}: expected HTTP {status} {code}, but it succeeded")


def first_message(reply: dict) -> tuple[str, str]:
  """Return the type and code of the first message in a response."""
  message = reply["messages"][0]
  return message["type"], message["code"]


async def edges(transport: str, bundles: dict[str, Bundle]):
  """Exercise protocol errors, error responses and the remaining operations."""
  line = {"item": {"id": "var_poster_pack_digital"}, "quantity": 1}
  calls, log = [], []

  def keep(platform: Traced, name: str, last: bool = True) -> None:
    for index, call in enumerate(platform.calls, 1):
      if "reply" in call:
        label = f"{transport}/errors/{name} #{index} {call['operation']}"
        bundles[name].check_call(call, label)
        bundles[name].check_models(call, label)
    calls.extend(platform.calls)
    if last:
      log.extend(platform.network.log)

  # --- protocol errors: the request never reaches a handler ---------------
  search = ("search_catalog", {"query": "poster"})
  async with world(transport, "core", "missing") as platform:
    await rejected(platform, 424, "profile_unreachable", *search)
    keep(platform, "core")
  async with world(transport, "core", "malformed") as platform:
    await rejected(platform, 422, "profile_malformed", *search)
    keep(platform, "core")
  async with world(transport, "core", "old") as platform:
    await rejected(platform, 422, "version_unsupported", *search)
    keep(platform, "core")
  async with world(transport, "core") as platform:
    platform.profile_url = "http://platform.example/profiles/core.json"
    await rejected(platform, 400, "invalid_profile_url", *search)
    keep(platform, "core")

  # --- no capability in common: a business outcome, HTTP 200 ---------------
  async with world(transport, "core", "stranger") as platform:
    reply = await platform.send("create_cart", {"line_items": [line]})
    expect(platform.status == 200, "incompatible: not HTTP 200")
    expect(reply["ucp"]["status"] == "error", "incompatible: status")
    expect(
      first_message(reply) == ("error", "capabilities_incompatible"),
      f"incompatible: {reply['messages']}",
    )
    keep(platform, "core")

  # --- the core Platform: no discount extension ----------------------------
  async with world(transport, "core") as platform:
    # A request that does not match the generated type is rejected.
    await rejected(platform, 400, None, "create_cart", {"line_items": "none"})

    # `discounts` means nothing without the extension, whatever its shape.
    # It is not validated, not applied and not echoed.
    body = {"line_items": [line], "discounts": {"codes": "WELCOME10"}}
    cart = await platform.send("create_cart", body)
    expect("discounts" not in cart, "core: discounts without the extension")
    expect(cart["totals"][-1]["amount"] == 900, "core: a discount was applied")

    # An update that cannot be applied leaves the cart as it was and says
    # why. The cart still exists, so this is not an error response.
    unknown = {"line_items": [{"item": {"id": "var_none"}, "quantity": 1}]}
    reply = await platform.send("update_cart", unknown, cart["id"])
    expect(reply["ucp"]["status"] == "success", "update: error response")
    expect(first_message(reply) == ("error", "item_unavailable"), "update")
    expect(reply["line_items"] == cart["line_items"], "update: cart changed")

    # Repeating a call with its idempotency key replays the first reply.
    key = "0e3c0b5e-7f9a-4d55-9d2e-3c1a5b7d9f10"
    new_cart = ("create_cart", {"line_items": [line]}, None, key)
    first = await platform.send(*new_cart)
    again = await platform.send(*new_cart)
    expect(first == again, "idempotency: the replay differs")
    other = {"line_items": [{**line, "quantity": 3}]}
    await rejected(platform, 409, None, "create_cart", other, None, key)

    # Cancel returns the cart as it was; afterwards the cart is gone.
    gone = await platform.send("cancel_cart", None, first["id"])
    expect(gone["id"] == first["id"], "cancel_cart: wrong cart returned")
    reply = await platform.send("get_cart", None, first["id"])
    expect(platform.status == 200, "not_found: not HTTP 200")
    expect(first_message(reply) == ("error", "not_found"), "get after cancel")

    # A checkout without a Buyer email is incomplete, and stays so when the
    # Platform tries to complete it anyway.
    checkout = await platform.send("create_checkout", {"line_items": [line]})
    expect(checkout["status"] == "incomplete", "checkout: not incomplete")
    expect(first_message(checkout) == ("error", "missing"), "checkout: message")
    paid = {"id": "i1", "handler_id": "mock_pay", "type": "mock_instrument"}
    payment = {"payment": {"instruments": [paid]}}
    reply = await platform.send("complete_checkout", payment, checkout["id"])
    expect(reply["status"] == "incomplete", "complete: accepted too early")

    # Once ready, payment fails with two instruments, and with an
    # instrument type the checkout did not offer. Both can be retried.
    ready = {"line_items": [line], "buyer": BUYER}
    reply = await platform.send("update_checkout", ready, checkout["id"])
    expect(reply["status"] == "ready_for_complete", "checkout: not ready")
    for wrong in ([paid, {**paid, "id": "i2"}], [{**paid, "type": "other"}]):
      attempt = {"payment": {"instruments": wrong}}
      reply = await platform.send("complete_checkout", attempt, checkout["id"])
      expect(first_message(reply) == ("error", "payment_failed"), "payment")

    # Cancel works once.
    reply = await platform.send("cancel_checkout", None, checkout["id"])
    expect(reply["status"] == "canceled", "cancel_checkout: not canceled")
    reply = await platform.send("cancel_checkout", None, checkout["id"])
    expect(first_message(reply) == ("error", "not_allowed"), "second cancel")

    # A search with no query, and a search paged one product at a time.
    reply = await platform.send("search_catalog", {})
    expect(first_message(reply) == ("error", "missing"), "empty search")
    paged = {"query": "of", "pagination": {"limit": 1}}
    page = await platform.send("search_catalog", paged)
    expect(page["pagination"]["has_next_page"], "search: no second page")
    cursor = {"limit": 1, "cursor": page["pagination"]["cursor"]}
    following = await platform.send(
      "search_catalog", {"query": "of", "pagination": cursor}
    )
    expect(following["products"] != page["products"], "search: same page twice")
    keep(platform, "core")

  # --- the discount Platform ------------------------------------------------
  async with world(transport, "discount") as platform:
    # An unknown code is reported and not applied.
    body = {"line_items": [line], "discounts": {"codes": ["FREE"]}}
    cart = await platform.send("create_cart", body)
    expect(
      first_message(cart) == ("warning", "discount_code_invalid"),
      f"unknown code: {cart.get('messages')}",
    )
    expect("applied" not in cart["discounts"], "unknown code was applied")

    # Converting the same cart twice returns the one open checkout.
    once = await platform.send("create_checkout", {"cart_id": cart["id"]})
    twice = await platform.send("create_checkout", {"cart_id": cart["id"]})
    expect(once["id"] == twice["id"], "a cart became two checkouts")

    # Idempotency keys belong to one Platform. Another Platform that sends
    # the same key and request gets its own cart, shaped by what it
    # negotiated.
    key = "7d1f4c2a-9b3e-4a61-8c5d-2e6f8a0b4c13"
    body = {"line_items": [line], "discounts": {"codes": ["WELCOME10"]}}
    mine = await platform.send("create_cart", body, None, key)
    url = f"{PLATFORM}/profiles/core.json"
    other = Traced(platform.network, platform.http, "core", url, transport)
    try:
      theirs = await (await other.connect(BUSINESS)).send(
        "create_cart", body, None, key
      )
    finally:
      await other.close()
    expect(mine["id"] != theirs["id"], "an idempotency key crossed Platforms")
    expect("discounts" not in theirs, "a reply crossed Platforms")
    keep(other, "core", last=False)
    keep(platform, "discount")
  return calls, log


# --- transcripts ------------------------------------------------------------


def pretty(value, indent: int = 0, width: int = 96) -> str:
  """Format JSON so that small objects and arrays stay on one line."""
  flat = json.dumps(value)
  if not isinstance(value, (dict, list)) or len(flat) + indent <= width:
    return flat
  pad = " " * (indent + 2)
  if isinstance(value, dict):
    items = [
      f"{pad}{json.dumps(k)}: {pretty(v, indent + 2, width)}"
      for k, v in value.items()
    ]
    return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"
  items = [f"{pad}{pretty(v, indent + 2, width)}" for v in value]
  return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"


def _tidy(body: bytes):
  """Parse a body for display, dropping what would only add noise."""
  if not body:
    return None
  payload = json.loads(body)
  if isinstance(payload, dict) and "jsonrpc" in payload:
    # MCP's own request metadata names the SDK and its version.
    for part in ("params", "result"):
      if isinstance(payload.get(part), dict):
        payload[part].pop("_meta", None)
    for tool in payload.get("result", {}).get("tools", []):
      tool["inputSchema"] = tool["outputSchema"] = "(schema omitted)"
    for block in payload.get("result", {}).get("content", []):
      block["text"] = "(the structuredContent below, as a JSON string)"
  return payload


def _title(request: httpx2.Request, routes: dict) -> str:
  """Name an exchange for its transcript heading."""
  path = request.url.path
  if path == "/.well-known/ucp":
    return "The Platform reads the Business profile"
  if request.url.host == "platform.example":
    return "The Business fetches the Platform profile"
  if path == "/mcp":
    body = json.loads(request.content)
    tool = body.get("params", {}).get("name")
    return f"`{tool}`" if tool else f"MCP `{body['method']}`"
  for name, route in routes.items():
    pattern = route.path.replace("{id}", "[^/]+")
    if route.method == request.method and re.fullmatch(pattern, path):
      return f"`{name}`"
  return f"{request.method} {path}"


# Reason phrases as RFC 9110 names them. Python's own table renamed 422
# between versions, and a transcript must not depend on the interpreter.
REASONS = {
  200: "OK",
  201: "Created",
  202: "Accepted",
  400: "Bad Request",
  404: "Not Found",
  409: "Conflict",
  422: "Unprocessable Content",
  424: "Failed Dependency",
}


def render(title: str, intro: str, log, routes: dict, keep=None) -> str:
  """Render recorded exchanges as a Markdown transcript.

  `keep(heading, request, response)` selects which exchanges to show.
  """
  out = [f"# {title}", "", intro, ""]
  out += ["Generated by `make check`. Do not edit; run `make update`.", ""]
  index, seen = 0, set()
  for request, response in log:
    heading = _title(request, routes)
    # Each fresh Business is discovered again. Show a repeat only once.
    setup = (heading, str(request.url), response.content)
    if not heading.startswith("`") and setup in seen:
      continue
    seen.add(setup)
    if keep and not keep(heading, request, response):
      continue
    index += 1
    out += [f"## {index}. {heading}", "", "```http"]
    out += [f"{request.method} {request.url.raw_path.decode()} HTTP/1.1"]
    out += [f"Host: {request.url.host}"]
    for header in ("UCP-Agent", "Idempotency-Key", "Request-Id"):
      if header in request.headers:
        out += [f"{header}: {request.headers[header]}"]
    body = _tidy(request.content)
    if body is not None:
      out += ["Content-Type: application/json", "", pretty(body)]
    out += ["```", "", "```http"]
    out += [f"HTTP/1.1 {response.status_code} {REASONS[response.status_code]}"]
    if "cache-control" in response.headers:
      out += [f"Cache-Control: {response.headers['cache-control']}"]
    body = _tidy(response.content)
    if body is not None:
      out += ["Content-Type: application/json", "", pretty(body)]
    out += ["```", ""]
  text = "\n".join(out).replace(VERSION, "{{ ucp_version }}")
  return text.rstrip("\n") + "\n"


def _is_setup(request: httpx2.Request) -> bool:
  """Tell whether an exchange fetched one of the sample profiles."""
  return request.url.path == "/.well-known/ucp" or request.url.path.endswith(
    ("/core.json", "/discount.json")
  )


def _mcp_sample(heading, request, response) -> bool:
  """Keep MCP's own exchanges and one tool call of each argument shape."""
  shown = ("`search_catalog`", "`update_cart`", "`complete_checkout`")
  return heading.startswith("MCP") or heading in shown


def _went_wrong(heading, request, response) -> bool:
  """Keep exchanges that ended in an error or carried a message."""
  if _is_setup(request) or heading.startswith("MCP"):
    return False
  body = json.loads(response.content) if response.content else {}
  body = body.get("result", {}).get("structuredContent", body)
  return response.status_code >= 400 or "messages" in body


def _protocol_error(heading, request, response) -> bool:
  """Keep tool calls that were answered with a JSON-RPC error."""
  return heading.startswith("`") and b'"error"' in response.content[:40]


def transcripts(logs: dict, routes: dict) -> dict[str, str]:
  """Render every committed transcript: file name to text."""
  funnel_title = "The funnel over REST"
  with_discount, without = (
    render(funnel_title, "", logs[run], routes)
    for run in ("rest-discount", "rest-core")
  )
  difference = difflib.unified_diff(
    without.splitlines(),
    with_discount.splitlines(),
    "without the discount extension (platform/profiles/core.json)",
    "with the discount extension (platform/profiles/discount.json)",
  )
  return {
    "rest.md": render(
      funnel_title,
      "Search, cart, checkout and payment, for a Platform whose profile "
      "declares the discount extension.",
      logs["rest-discount"],
      routes,
    ),
    # Blank context lines lose their leading space, so that whitespace
    # hooks leave the file alone. It is for reading, not for `patch`.
    "discount-extension.diff": "".join(
      line.rstrip() + "\n" for line in difference
    ),
    "mcp.md": render(
      "The funnel over MCP",
      "The same run as `rest.md`, over MCP. Shown here: MCP's own exchanges "
      "and one tool call of each argument shape. The run made all eight "
      "calls, and each `structuredContent` equals the matching REST body.",
      logs["mcp-discount"],
      routes,
      _mcp_sample,
    ),
    "errors-rest.md": render(
      "Protocol errors and business outcomes over REST",
      "Protocol errors never reach a handler and carry an HTTP error "
      "status. Business outcomes are HTTP 200 and explain themselves in "
      "`messages`. Only exchanges that failed or carried a message are "
      "shown.",
      logs["rest-errors"],
      routes,
      _went_wrong,
    ),
    "errors-mcp.md": render(
      "Protocol errors over MCP",
      "A protocol error is a JSON-RPC error that carries the UCP body in "
      "`data`, with the same HTTP status as on REST. Business outcomes "
      "arrive in `structuredContent` exactly as in `errors-rest.md`.",
      logs["mcp-errors"],
      routes,
      _protocol_error,
    ),
  }


def check_transcripts(logs: dict, routes: dict, update: bool) -> None:
  """Compare the committed transcripts with this run, or rewrite them."""
  rendered = transcripts(logs, routes)
  if update:
    for stale in TRANSCRIPTS.iterdir():
      stale.unlink()
  for name, text in rendered.items():
    path = TRANSCRIPTS / name
    if update:
      path.write_text(text)
      continue
    current = path.read_text() if path.exists() else ""
    expect(
      current == text,
      f"{path.relative_to(build.REPO)} is out of date: the wire changed. "
      "Run `make update` and review the result with `git diff`.",
    )


def check_readme() -> None:
  """Check that the code the README quotes is still in the source.

  Each python, json and diff block must appear in one file under
  `reference/`, indentation aside. A line of `...` marks an omission.
  """

  def squash(text: str) -> str:
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)

  sources = [
    squash(path.read_text())
    for path in sorted(build.ROOT.rglob("*"))
    if path.suffix in (".py", ".json", ".diff")
    and build.OUT not in path.parents
  ]
  readme = (build.ROOT / "README.md").read_text()
  for block in re.findall(r"```(?:python|json|diff)\n(.*?)```", readme, re.S):
    parts = [squash(part) for part in re.split(r"(?m)^\s*\.\.\.\s*$", block)]
    quoted = any(all(part in source for part in parts) for source in sources)
    expect(quoted, f"README.md quotes code that is not in the source:\n{block}")


async def main(update: bool) -> None:
  """Run every check; `update` rewrites the transcripts instead."""
  bundles = check_generated()
  print("ok  generated routes and types are consistent; profiles are valid")
  check_negotiation()
  print("ok  negotiation matches the cases worked out by hand")

  calls, logs = {}, {}
  for transport in ("rest", "mcp"):
    for name in ("core", "discount"):
      run = f"{transport}-{name}"
      calls[run], logs[run] = await funnel(transport, name, bundles[name])
      print(f"ok  {run}: funnel completed, {len(calls[run])} calls valid")
    calls[f"{transport}-errors"], logs[f"{transport}-errors"] = await edges(
      transport, bundles
    )
    print(f"ok  {transport}-errors: protocol errors and error responses")

  for name in ("core", "discount", "errors"):
    same = calls[f"rest-{name}"] == calls[f"mcp-{name}"]
    expect(same, f"{name}: REST and MCP carried different payloads")
  print("ok  REST and MCP carried identical payloads")

  business = Business(httpx2.AsyncClient(), BUSINESS, resolver=None)
  made = {call["operation"] for run in calls.values() for call in run}
  unused = sorted(set(business.routes) - made)
  expect(not unused, f"operations never called: {unused}")
  print(f"ok  all {len(business.routes)} operations were called")

  check_transcripts(logs, business.routes, update)
  print("ok  transcripts " + ("rewritten" if update else "are up to date"))
  check_readme()
  print("ok  the README quotes code that is in the source")


if __name__ == "__main__":
  try:
    asyncio.run(main("--update" in sys.argv))
  except AssertionError as failure:
    sys.exit(f"FAILED  {failure}")
