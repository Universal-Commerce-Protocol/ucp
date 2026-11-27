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

"""One function per operation: typed objects in, typed objects out.

A handler knows nothing about HTTP, MCP or negotiation. `call.body` is the
request as its generated model, and the handler returns the response as a
generated model, built from generated parts: `LineItem`, `Total`,
`MessageError` and so on. They all come from `call.models`, the models
generated for the extensions the calling Platform negotiated.

What the Business keeps between calls is typed as well. A `StoredCart` or
`StoredCheckout` holds what the Platform set, as the objects it arrived
in, so the code reads `checkout.buyer.email`. The response is built from
the stored object on every call.

The generated models accept unknown properties, as the schemas do. So it
is the code here, not the models, that keeps an extension's fields out of
a response when the extension was not negotiated; see `_priced`.

Each handler is registered under its own name, and that name is an
operationId emitted by `ucp-schema generate-openapi`. Add a capability to
the profile and the Business refuses to start until the new operations
have handlers here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from types import ModuleType
from typing import TYPE_CHECKING, Any

from reference.business.store import (
  CHECKOUT_EXPIRES_AT,
  CURRENCY,
  DISCOUNT_CODES,
  Store,
  StoredCart,
  StoredCheckout,
)

if TYPE_CHECKING:
  # Written by `make generate`; see reference/build.py. Used here for
  # annotations only: at run time the models come from `call.models`.
  from pydantic import BaseModel

  from reference.generated.full import models

CATALOG = "dev.ucp.shopping.catalog.search"
CART = "dev.ucp.shopping.cart"
CHECKOUT = "dev.ucp.shopping.checkout"
DISCOUNT = "dev.ucp.shopping.discount"


@dataclass
class Call:
  """One operation invocation, after negotiation and request validation."""

  store: Store
  models: ModuleType  # the generated models for what was negotiated
  ucp: dict  # the `ucp` envelope every response to this call carries
  active: set[str]  # names of the capabilities negotiated for this call
  base_url: str  # where the Business is served, for links it hands out
  id: str | None = None  # the cart or checkout the operation targets
  body: Any = None  # the request, as its generated model


class OutcomeError(Exception):
  """A business outcome with no resource to return, such as not found.

  `Business.call` turns it into an error response: `ucp.status` is "error"
  and `messages` says why.
  """

  def __init__(self, code: str, content: str):
    """Carry the code and text of one error message."""
    super().__init__(content)
    self.code = code


OPERATIONS: dict[str, tuple[str, Callable[[Call], BaseModel]]] = {}


def operation(capability: str):
  """Register a handler and name the capability its operation belongs to."""

  def register(handler: Callable[[Call], BaseModel]):
    OPERATIONS[handler.__name__] = (capability, handler)
    return handler

  return register


# --- shared pieces ----------------------------------------------------------


def _error(
  call: Call, code: str, content: str, path: str | None = None
) -> models.MessageError:
  """Build a recoverable error message; `path` points into the response."""
  return call.models.MessageError(
    type="error", code=code, content=content, severity="recoverable", path=path
  )


def _stored(table: dict, id: str | None, noun: str):
  """Return a stored cart or checkout, or end the call with not found."""
  if id not in table:
    raise OutcomeError("not_found", f"{noun} not found or has expired.")
  return table[id]


def _requested(call: Call, kind: type[StoredCart] = StoredCart):
  """Read what the Platform set on a cart or checkout from the request."""
  body = call.body
  requested = kind(
    line_items=body.line_items or [],
    codes=[],
    buyer=body.buyer,
    context=body.context,
  )
  # `discounts` belongs to the discount extension. Without the extension it
  # is an unknown property of any shape, so it is not read.
  if DISCOUNT in call.active and body.discounts:
    requested.codes = body.discounts.codes or []
  return requested


def _plain(model: BaseModel | None) -> dict | None:
  """Turn a stored object back into plain data for a response.

  A cart may have been stored by a Platform that negotiated different
  extensions, whose models are other classes than this call's.
  """
  return model and model.model_dump(exclude_none=True)


def _totals(kind: type, subtotal: int, discount: int) -> list:
  """Return totals of a given type: subtotal, discount if any, and total."""
  totals = [kind(type="subtotal", amount=subtotal)]
  if discount:
    totals.append(kind(type="items_discount", amount=-discount))
  return [*totals, kind(type="total", amount=subtotal - discount)]


@dataclass
class Priced:
  """A cart or checkout, priced: the parts of a response that cost money."""

  line_items: list[models.LineItem]
  totals: list[models.TotalsItem]
  discounts: models.DiscountsObject | None
  warnings: list[models.MessageWarning]


def _priced(call: Call, cart: StoredCart) -> Priced:
  """Price a stored cart or checkout for the calling Platform.

  This is the store's own logic: look up each item, price the line, apply
  a discount code. A real Business would call its catalog and pricing here.
  """
  m = call.models
  # Stored codes show only to a Platform that negotiated the extension.
  codes = cart.codes if DISCOUNT in call.active else []
  warnings, applied, offer, percent = [], None, "", 0
  for index, code in enumerate(codes):
    known = DISCOUNT_CODES.get(code.upper())  # codes match case-insensitively
    if known and not applied:
      applied, (offer, percent) = code, known
      continue
    # The store has one code, so a second valid code is the same one again.
    reason = "already_applied" if known else "invalid"
    warnings.append(
      m.MessageWarning(
        type="warning",
        code=f"discount_code_{reason}",
        path=f"$.discounts.codes[{index}]",
        content=f"Code '{code}' is {reason.replace('_', ' ')}.",
      )
    )

  line_items, allocations, subtotal, discount = [], [], 0, 0
  for index, line in enumerate(cart.line_items):
    item = call.store.item(line.item.id)
    if not item:
      raise OutcomeError(
        "item_unavailable", f"Item '{line.item.id}' is not sold here."
      )
    line_subtotal = item.price * line.quantity
    line_discount = line_subtotal * percent // 100
    line_items.append(
      m.LineItem(
        id=f"li_{index + 1}",
        item=m.Item(id=item.id, title=item.title, price=item.price),
        quantity=line.quantity,
        totals=_totals(m.Total, line_subtotal, line_discount),
      )
    )
    if line_discount:
      allocations.append(
        m.Allocation(path=f"$.line_items[{index}]", amount=line_discount)
      )
    subtotal += line_subtotal
    discount += line_discount

  discounts = None
  if codes:
    discounts = m.DiscountsObject(codes=codes)
  if discount:
    discounts.applied = [
      m.AppliedDiscount(
        code=applied,
        title=offer,
        amount=discount,
        method="each",
        allocations=allocations,
      )
    ]
  totals = _totals(m.TotalsItem, subtotal, discount)
  return Priced(line_items, totals, discounts, warnings)


# --- catalog ----------------------------------------------------------------


@operation(CATALOG)
def search_catalog(call: Call) -> models.CatalogSearchResponse:
  """Find products by text; the variant ids returned are cart item ids."""
  body: models.CatalogSearchRequest = call.body
  m = call.models
  query = (body.query or "").strip()
  if not query:
    # This store recognizes one search input, the query text.
    missing = _error(call, "missing", "Provide a search query.")
    return m.CatalogSearchResponse(
      ucp=call.ucp, products=[], messages=[missing]
    )
  found = call.store.search(query)
  page = body.pagination
  start = int(page.cursor) if page and (page.cursor or "").isdigit() else 0
  end = start + (page and page.limit or 10)
  more = end < len(found)
  return m.CatalogSearchResponse(
    ucp=call.ucp,
    products=found[start:end],
    pagination=m.PaginationResponse(
      has_next_page=more, cursor=str(end) if more else None
    ),
  )


# --- cart -------------------------------------------------------------------


def _cart(
  call: Call, cart_id: str | None, *problems: models.MessageError
) -> models.Cart:
  """Return the cart resource, priced for the calling Platform.

  `problems` are errors to report when a request changed nothing.
  """
  cart = _stored(call.store.carts, cart_id, "Cart")
  priced = _priced(call, cart)
  return call.models.Cart(
    ucp=call.ucp,
    id=cart_id,
    line_items=priced.line_items,
    currency=CURRENCY,
    totals=priced.totals,
    discounts=priced.discounts,
    buyer=_plain(cart.buyer),
    context=_plain(cart.context),
    messages=[*priced.warnings, *problems] or None,
    continue_url=f"{call.base_url}/cart/{cart_id}",
  )


@operation(CART)
def create_cart(call: Call) -> models.Cart:
  """Start a cart from line items."""
  cart = _requested(call)
  _priced(call, cart)  # raises for an unknown item; nothing is stored yet
  cart_id = call.store.new_id("cart")
  call.store.carts[cart_id] = cart
  return _cart(call, cart_id)


@operation(CART)
def get_cart(call: Call) -> models.Cart:
  """Return the current cart."""
  return _cart(call, call.id)


@operation(CART)
def update_cart(call: Call) -> models.Cart:
  """Replace the whole cart with what the Platform sent."""
  _stored(call.store.carts, call.id, "Cart")  # an unknown cart ends the call
  cart = _requested(call)
  try:
    _priced(call, cart)
  except OutcomeError as error:
    # The cart still exists, so this is a recoverable error on the cart as
    # it stands, not an error response.
    return _cart(call, call.id, _error(call, error.code, str(error)))
  call.store.carts[call.id] = cart
  return _cart(call, call.id)


@operation(CART)
def cancel_cart(call: Call) -> models.Cart:
  """Delete the cart and return its last state."""
  response = _cart(call, call.id)
  del call.store.carts[call.id]
  return response


# --- checkout ---------------------------------------------------------------


def _checkout(
  call: Call, checkout_id: str | None, *problems: models.MessageError
) -> models.Checkout:
  """Return the checkout resource, priced for the calling Platform.

  `problems` are errors to report when a request changed nothing.
  """
  m = call.models
  checkout = _stored(call.store.checkouts, checkout_id, "Checkout")
  priced = _priced(call, checkout)
  errors = list(problems)
  status, expires_at, continue_url = checkout.status, None, None
  if checkout.status == "open":
    # `ready_for_complete` is returned exactly when Complete Checkout would
    # be accepted. This store delivers by email, so with nothing else wrong
    # that is all it waits for.
    if not (checkout.buyer and checkout.buyer.email):
      errors.append(
        _error(call, "missing", "Buyer email is required.", "$.buyer.email")
      )
    status = "incomplete" if errors else "ready_for_complete"
    expires_at = CHECKOUT_EXPIRES_AT
    continue_url = f"{call.base_url}/checkout/{checkout_id}"
  return m.Checkout(
    ucp=call.ucp,
    id=checkout_id,
    status=status,
    line_items=priced.line_items,
    currency=CURRENCY,
    totals=priced.totals,
    discounts=priced.discounts,
    buyer=_plain(checkout.buyer),
    context=_plain(checkout.context),
    messages=[*priced.warnings, *errors] or None,
    links=[
      m.Link(type="terms_of_service", url=f"{call.base_url}/terms"),
      m.Link(type="privacy_policy", url=f"{call.base_url}/privacy"),
    ],
    expires_at=expires_at,
    continue_url=continue_url,
    order=_plain(checkout.order),
  )


def _open(call: Call) -> StoredCheckout:
  """Return the stored checkout if it can still change."""
  checkout = _stored(call.store.checkouts, call.id, "Checkout")
  if checkout.status != "open":
    raise OutcomeError(
      "not_allowed", f"Checkout is {checkout.status} and cannot be changed."
    )
  return checkout


def _offered(response: models.Checkout, payment: models.Payment) -> bool:
  """Tell whether a payment is exactly one instrument the checkout offers.

  The instrument must name a payment handler the checkout lists and be of
  a type that handler takes. A handler that lists no types takes any.
  """
  sent = payment.instruments or []
  handlers = [h for hs in response.ucp.payment_handlers.values() for h in hs]
  return len(sent) == 1 and any(
    handler.id == sent[0].handler_id
    and (
      handler.available_instruments is None
      or sent[0].type in [i.type for i in handler.available_instruments]
    )
    for handler in handlers
  )


@operation(CHECKOUT)
def create_checkout(call: Call) -> models.Checkout:
  """Start a checkout from line items or from a cart."""
  cart_id = call.body.cart_id  # the request has line items, a cart id, or both
  checkout = _requested(call, StoredCheckout)
  if cart_id is not None:
    if CART not in call.active:
      raise OutcomeError(
        "capabilities_incompatible",
        "cart_id needs the Cart capability, which was not negotiated.",
      )
    for checkout_id, existing in call.store.checkouts.items():
      if existing.cart_id == cart_id and existing.status == "open":
        return _checkout(call, checkout_id)  # converting twice is idempotent
    cart = _stored(call.store.carts, cart_id, "Cart")
    # The cart wins over overlapping checkout fields, and its discount codes
    # carry forward.
    checkout = replace(
      checkout,
      line_items=cart.line_items or checkout.line_items,
      codes=cart.codes or checkout.codes,
      buyer=cart.buyer or checkout.buyer,
      context=cart.context or checkout.context,
      cart_id=cart_id,
    )
  _priced(call, checkout)
  checkout_id = call.store.new_id("chk")
  call.store.checkouts[checkout_id] = checkout
  return _checkout(call, checkout_id)


@operation(CHECKOUT)
def get_checkout(call: Call) -> models.Checkout:
  """Return the current checkout."""
  return _checkout(call, call.id)


@operation(CHECKOUT)
def update_checkout(call: Call) -> models.Checkout:
  """Replace the whole checkout with what the Platform sent."""
  cart_id = _open(call).cart_id
  checkout = replace(_requested(call, StoredCheckout), cart_id=cart_id)
  try:
    _priced(call, checkout)
  except OutcomeError as error:
    return _checkout(call, call.id, _error(call, error.code, str(error)))
  call.store.checkouts[call.id] = checkout
  return _checkout(call, call.id)


@operation(CHECKOUT)
def complete_checkout(call: Call) -> models.Checkout:
  """Take payment and place the order."""
  body: models.CheckoutCompleteRequest = call.body
  checkout = _open(call)
  response = _checkout(call, call.id)
  if response.status != "ready_for_complete":
    return response  # still incomplete; its messages say what is missing

  if not _offered(response, body.payment):
    failed = _error(
      call,
      "payment_failed",
      "Send exactly one instrument that this checkout offers.",
      "$.payment.instruments",
    )
    return _checkout(call, call.id, failed)

  # A real Business would charge the instrument and email a confirmation
  # here. The mock payment handler always succeeds.
  order_id = call.store.new_id("order")
  checkout.status = "completed"
  checkout.order = call.models.OrderConfirmation(
    id=order_id, permalink_url=f"{call.base_url}/orders/{order_id}"
  )
  return _checkout(call, call.id)


@operation(CHECKOUT)
def cancel_checkout(call: Call) -> models.Checkout:
  """Cancel a checkout that has not completed."""
  _open(call).status = "canceled"
  return _checkout(call, call.id)
