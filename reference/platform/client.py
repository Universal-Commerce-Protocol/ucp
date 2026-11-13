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

"""The Platform: discover a Business, then shop there over REST or MCP.

`Platform.call` sends one operation: a request built from a generated
model goes out, and the response comes back parsed into one. `shop`
strings eight calls into the shopping funnel: search, cart, checkout, pay.
The same `shop` runs unchanged over either transport.

This directory has no `__init__.py` on purpose. A regular package named
`platform` on the import path would shadow the standard library module of
that name.
"""

import argparse
import asyncio
import json
import sys
import uuid
from contextlib import AsyncExitStack

import httpx2
from mcp import Client, MCPError
from mcp.client.streamable_http import streamable_http_client

from reference import build
from reference.business.negotiation import negotiate

DISCOUNT = "dev.ucp.shopping.discount"
SERVICE = "dev.ucp.shopping"


class OutcomeError(Exception):
  """The operation ran and ended in an error response, such as not found."""

  def __init__(self, response):
    """Keep the parsed error response; its `messages` say what went wrong."""
    super().__init__(response.messages[0].content)
    self.response = response


class RejectedError(Exception):
  """The Business rejected a request before running the operation."""

  def __init__(self, body: dict):
    """Keep the `{code, content}` body the Business sent."""
    super().__init__(body.get("content"))
    self.body = body


class Platform:
  """A Platform shopping at one Business."""

  def __init__(
    self,
    http: httpx2.AsyncClient,
    name: str,
    profile_url: str,
    transport: str = "mcp",
  ):
    """Shop as the sample profile `name`, which is served at `profile_url`."""
    self.http, self.profile_url, self.transport = http, profile_url, transport
    self.profile = build.platform_profiles()[name]
    self._stack = AsyncExitStack()

  async def connect(self, business_url: str) -> "Platform":
    """Read the Business profile and open the chosen transport."""
    response = await self.http.get(f"{business_url}/.well-known/ucp")
    response.raise_for_status()
    self.business = response.json()
    # What the Business will compute on every request, computed here too, so
    # the Platform knows which extension fields it may send.
    self.active = set(negotiate(self.business, self.profile))
    # The routes and models generated for that negotiated set.
    variant = build.variant(self.business, self.active)
    self.models = build.models(variant)
    openapi = json.loads((build.OUT / variant / "openapi.json").read_text())
    self.operations = {
      operation["operationId"]: (method, path, operation)
      for method, path, operation in build.operations(openapi)
    }
    self.endpoint = next(
      service["endpoint"]
      for service in self.business["ucp"]["services"][SERVICE]
      if service["transport"] == self.transport
    )
    if self.transport == "mcp":
      transport = streamable_http_client(self.endpoint, http_client=self.http)
      self.mcp = await self._stack.enter_async_context(Client(transport))
      listed = await self.mcp.list_tools()
      self.tools = {tool.name: tool for tool in listed.tools}
    return self

  async def close(self) -> None:
    """Close the transport."""
    await self._stack.aclose()

  def _uuid(self, purpose: str) -> str:
    """Return a fresh UUID for a request id or an idempotency key."""
    return str(uuid.uuid4())

  async def call(self, operation: str, request=None, id: str | None = None):
    """Send a typed request and return the typed response.

    Raises `OutcomeError` when the Business answers with an error response.
    """
    reply = await self.send(operation, request and build.wire(request), id)
    name = build.response_type(self.operations[operation][2], reply)
    response = getattr(self.models, name).model_validate(reply)
    if name == "ErrorResponse":
      raise OutcomeError(response)
    return response

  async def send(
    self,
    operation: str,
    body: dict | None = None,
    id: str | None = None,
    key: str | None = None,
  ) -> dict:
    """Send one operation as JSON and return the JSON that came back.

    State-changing calls carry an idempotency key. Pass `key` to retry a
    call with the key it was first sent with.
    """
    method, path, described = self.operations[operation]
    # The service definition says which operations take an idempotency key.
    keyed = any(
      parameter.get("$ref", "").endswith("/idempotency_key")
      for parameter in described.get("parameters", [])
    )
    key = (key or self._uuid("idempotency")) if keyed else None
    send = self._mcp if self.transport == "mcp" else self._rest
    return await send(operation, method, path, key, body, id)

  async def _rest(self, operation, method, path, key, body, id) -> dict:
    """REST: profile and key in headers, id in the path, payload as body."""
    headers = {
      "UCP-Agent": f'profile="{self.profile_url}"',
      "Request-Id": self._uuid("request"),
    }
    if key:
      headers["Idempotency-Key"] = key
    response = await self.http.request(
      method,
      self.endpoint + path.replace("{id}", id or ""),
      headers=headers,
      json=None if method == "GET" else body or {},
    )
    if response.status_code >= 400:
      raise RejectedError(response.json())
    return response.json()

  async def _mcp(self, operation, method, path, key, body, id) -> dict:
    """MCP: profile and key in `meta`, id and payload as tool arguments."""
    meta = {"ucp-agent": {"profile": self.profile_url}}
    if key:
      meta["idempotency-key"] = key
    arguments = {"meta": meta}
    for name in self.tools[operation].input_schema["properties"]:
      if name == "id":
        arguments["id"] = id
      elif name != "meta":
        arguments[name] = body  # the one payload argument, e.g. `checkout`
    try:
      result = await self.mcp.call_tool(operation, arguments)
    except MCPError as error:
      body = error.error.data or {"content": error.error.message}
      raise RejectedError(body) from error
    return result.structured_content


async def shop(platform: Platform, query: str, code: str = "WELCOME10"):
  """Search, fill a cart, check out and pay. Return the completed checkout."""
  m = platform.models
  # Locality: provisional hints, not authoritative data.
  context = m.Context(address_country="US", address_region="CA")
  found = await platform.call(
    "search_catalog", m.CatalogSearchRequest(query=query, context=context)
  )
  variant = found.products[0].variants[0]

  # A variant id from the catalog is the item id of a line item.
  item = m.ItemCreateRequest(id=variant.id)
  cart = await platform.call(
    "create_cart",
    m.CartCreateRequest(
      line_items=[m.LineItemCreateRequest(item=item, quantity=1)],
      context=context,
    ),
  )

  # Updates replace the whole resource, so resend everything worth keeping.
  # Send a discount code only if the discount extension was negotiated.
  item = m.ItemUpdateRequest(id=variant.id)
  update = m.CartUpdateRequest(
    line_items=[m.LineItemUpdateRequest(item=item, quantity=2)],
    context=context,
  )
  if DISCOUNT in platform.active:
    update.discounts = m.DiscountsObjectUpdateRequest(codes=[code])
  await platform.call("update_cart", update, id=cart.id)
  cart = await platform.call("get_cart", id=cart.id)

  # The cart's lines and discount codes carry over into the checkout.
  checkout = await platform.call(
    "create_checkout", m.CheckoutCreateRequestCartId(cart_id=cart.id)
  )

  # The Business reports what is missing in `messages`. Here it wants the
  # Buyer's email before the checkout is ready to complete.
  update = m.CheckoutUpdateRequest(
    line_items=[
      m.LineItemUpdateRequest(
        item=m.ItemUpdateRequest(id=line.item.id), quantity=line.quantity
      )
      for line in checkout.line_items
    ],
    buyer=m.Buyer(
      first_name="Ada", last_name="Lovelace", email="ada@example.com"
    ),
    context=context,
  )
  if DISCOUNT in platform.active:
    codes = checkout.discounts.codes
    update.discounts = m.DiscountsObjectUpdateRequest(codes=codes)
  await platform.call("update_checkout", update, id=checkout.id)
  checkout = await platform.call("get_checkout", id=checkout.id)
  if checkout.status != "ready_for_complete":
    return checkout

  # Pay with a payment handler the Business offered in this checkout.
  handler = next(iter(checkout.ucp.payment_handlers.values()))[0]
  instrument = m.SelectedPaymentInstrument(
    id="instrument_1",
    handler_id=handler.id,
    type=handler.available_instruments[0].type,
    credential=m.PaymentCredential(type="token", token="mock_token"),
  )
  payment = m.Payment(instruments=[instrument])
  return await platform.call(
    "complete_checkout",
    m.CheckoutCompleteRequest(payment=payment),
    id=checkout.id,
  )


async def main() -> None:
  """Shop at a Business started with `make serve`."""
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument("--business", default="http://localhost:8182")
  parser.add_argument("--profile", default="discount", help="core or discount")
  parser.add_argument("--transport", default="mcp", choices=["mcp", "rest"])
  parser.add_argument("--query", default="field guide")
  args = parser.parse_args()
  async with httpx2.AsyncClient() as http:
    # `make serve` also hosts the sample Platform profiles, for convenience.
    profile_url = f"{args.business}/platform/{args.profile}.json"
    platform = Platform(http, args.profile, profile_url, args.transport)
    try:
      checkout = await shop(await platform.connect(args.business), args.query)
    except httpx2.ConnectError:
      sys.exit(
        f"Cannot reach a Business at {args.business}.\n"
        "Start one in another terminal with `make serve`, then try again."
      )
    except (RejectedError, OutcomeError) as error:
      sys.exit(f"The Business did not complete the purchase: {error}")
    finally:
      await platform.close()
  print(checkout.model_dump_json(indent=2, exclude_unset=True))


if __name__ == "__main__":
  asyncio.run(main())
