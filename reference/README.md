# UCP reference implementation

This is a UCP reference implementation of an example Business and an example
Platform. The Platform discovers the Business, negotiates capabilities with
it, and completes a purchase: catalog search, cart, checkout, payment. Both
sides support the REST and MCP transports, and the same purchase runs with
and without a negotiated extension.

It is built from one input, the Business's profile, and you can build yours
the same way. Read it as an example, copy it as a starting point, and rely on
it as a test: every pull request to the specification runs it against that
commit's schemas.

## From a profile to a working Business

### 1. Write a profile

[`business/profile.json`](business/profile.json) is the document the Business
serves at `/.well-known/ucp`. It declares catalog search, cart, checkout, and
the discount extension, which extends both cart and checkout:

```json
"dev.ucp.shopping.discount": [
  {
    "version": "{{ ucp_version }}",
    "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/discount",
    "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/discount.json",
    "extends": [
      "dev.ucp.shopping.cart",
      "dev.ucp.shopping.checkout"
    ]
  }
]
```

Everything else follows from this file. (`{{ ucp_version }}` is filled in with
the protocol version when the profile is loaded.)

### 2. Generate routes and types from it

`make generate` runs `ucp-schema` on the profile, then a stock generator on
the result:

```sh
ucp-schema generate-openapi --profile profile.json -o openapi.json  # operations
ucp-schema generate-types   --profile profile.json -o types.json    # types
datamodel-codegen --input types.json --output models.py             # models
```

You get the ten operations the profile's capabilities expose, each bound to
its request and response type, and those types as Pydantic models with the
profile's extensions composed in. `Cart` has `discounts` because the profile
says so. The models are used exactly as generated;
[`build.py`](build.py) has the full commands.

The shape of a payload depends on which extensions were negotiated, so this
is repeated for each smaller combination of extensions. Here that gives two
directories: `generated/full/` and `generated/base/`, with no extension.
Generated files are not committed.

### 3. Write one function per operation

[`business/handlers.py`](business/handlers.py) has one function for each
generated operation. A handler works in typed objects from end to end: the
request arrives as its generated model, the response is built from generated
models, and what the Business keeps between calls is typed too. There is no
HTTP, no MCP and no negotiation in it, only what the Business decides. This
one takes payment:

```python
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
```

The comment marks where your own logic goes. The store's rules read the same
way. A checkout is ready once the Buyer's email is known:

```python
    if not (checkout.buyer and checkout.buyer.email):
      errors.append(
        _error(call, "missing", "Buyer email is required.", "$.buyer.email")
      )
    status = "incomplete" if errors else "ready_for_complete"
```

And a response is assembled from typed parts, so a missing field or a wrong
type fails where the object is built:

```python
    line_items.append(
      m.LineItem(
        id=f"li_{index + 1}",
        item=m.Item(id=item.id, title=item.title, price=item.price),
        quantity=line.quantity,
        totals=_totals(m.Total, line_subtotal, line_discount),
      )
    )
```

Pricing lives in `_priced`, over a three-product catalog in
[`business/store.py`](business/store.py). Replace both with your catalog,
your prices and your rules.

Add a capability to the profile and regenerate, and the Business refuses to
start until the new operations have handlers. Here "handler" always means one
of these functions; payment handlers are written out in full.

### 4. Serve REST and MCP from the same handlers

The bindings contain no operation-specific code.
[`business/rest.py`](business/rest.py) reads its routes from the generated
OpenAPI document. [`business/mcp.py`](business/mcp.py) builds one tool per
operation from the same document and serves them with the official MCP SDK.

The Platform, [`platform/client.py`](platform/client.py), uses the same
generated types: it builds a request object, sends it, and gets a response
object back. Its code does not change with the transport:

```python
  item = m.ItemCreateRequest(id=variant.id)
  cart = await platform.call(
    "create_cart",
    m.CartCreateRequest(
      line_items=[m.LineItemCreateRequest(item=item, quantity=1)],
      context=context,
    ),
  )
  ...
  checkout = await platform.call(
    "create_checkout", m.CheckoutCreateRequestCartId(cart_id=cart.id)
  )
```

### 5. See what negotiation changes

A Platform whose profile does not declare the discount extension gets a
different wire shape from the same Business.
[`transcripts/discount-extension.diff`](transcripts/discount-extension.diff)
records the difference:

```diff
-    "capabilities": {"dev.ucp.shopping.cart": [{"version": "{{ ucp_version }}"}]}
+    "capabilities": {
+      "dev.ucp.shopping.cart": [{"version": "{{ ucp_version }}"}],
+      "dev.ucp.shopping.discount": [{"version": "{{ ucp_version }}"}]
+    }
...
-  "totals": [{"type": "subtotal", "amount": 3600}, {"type": "total", "amount": 3600}],
+  "totals": [
+    {"type": "subtotal", "amount": 3600},
+    {"type": "items_discount", "amount": -360},
+    {"type": "total", "amount": 3240}
+  ],
```

The other transcripts show the whole exchange:

| File | Shows |
| :--- | :--- |
| [`rest.md`](transcripts/rest.md) | The purchase over REST, with the discount extension. |
| [`mcp.md`](transcripts/mcp.md) | The same purchase over MCP. |
| [`errors-rest.md`](transcripts/errors-rest.md) | Protocol errors and business outcomes (error responses, messages) over REST. |
| [`errors-mcp.md`](transcripts/errors-mcp.md) | Protocol errors over MCP. |

## Run it

You need [uv](https://docs.astral.sh/uv/) and a Rust toolchain. From
`reference/`, install the revision of `ucp-schema` this repository is pinned
to, then run the check:

```sh
cargo install --locked \
  --git https://github.com/Universal-Commerce-Protocol/ucp-schema \
  --rev "$(cat ../.ucp-schema-rev)"

make check
```

`make check` opens no sockets. To try the Business from a terminal, start it
and shop from a second terminal:

```sh
make serve                  # the Business on http://localhost:8182
make shop                   # over MCP; TRANSPORT=rest for REST
```

`make serve` is for local development only. The specification requires HTTPS
for endpoints and for profile URLs; this target relaxes that for loopback
addresses and hosts the example Platform profiles itself.

### Use any MCP client

The Business is an ordinary MCP server at `http://localhost:8182/mcp`, so
other MCP clients can talk to it. With `make serve` running, the
[MCP Inspector](https://github.com/modelcontextprotocol/inspector) lists its
tools:

```sh
npx @modelcontextprotocol/inspector --cli http://localhost:8182/mcp \
  --method tools/list
```

Every UCP tool call names the Platform's profile in `meta`. `make serve`
hosts the two example profiles at `/platform/core.json` and
`/platform/discount.json`:

```sh
npx @modelcontextprotocol/inspector --cli http://localhost:8182/mcp \
  --method tools/call --tool-name search_catalog \
  --tool-arg 'meta={"ucp-agent":{"profile":"http://localhost:8182/platform/discount.json"}}' \
             'catalog={"query":"field guide"}'
```

The response is the UCP payload in `structuredContent`. Two things to know:

- Use `localhost`, not `127.0.0.1`. The server only answers to the host name
  it was started with.
- A call without `meta` is a protocol error: HTTP 400 with a JSON-RPC error
  in the body. Some clients, the Inspector among them, report that as a
  failed request, not as a tool error.

## What happens to a call

Both bindings hand every call to one function, `Business.call` in
[`business/app.py`](business/app.py). In order, it:

1. **Negotiates.** It fetches the Platform profile named in the request,
   checks the protocol version, and intersects the two capability sets
   ([`business/negotiation.py`](business/negotiation.py)).
2. **Checks the operation is available.** The capability that owns the
   operation must be in the negotiated set.
3. **Validates the request** against the schema composed for the extensions
   that were negotiated, and parses it into its model.
4. **Honors the idempotency key.** The same key with the same request replays
   the first response; with a different request it is a conflict. Keys belong
   to one Platform and one operation.
5. **Runs the handler** and serializes the model it returns. The `ucp`
   envelope it carries lists only the capabilities relevant to that
   operation.

## What `make check` proves

It runs the purchase four ways (REST and MCP, each with the `core` and the
`discount` Platform profile), then a set of error cases on both transports,
all in one process. It fails unless:

- **Generation is consistent.** Every type in the generated OpenAPI document
  equals the type of the same name in the bundle, and the profiles are valid
  against the profile schema.
- **Negotiation is correct.** The intersection algorithm matches cases worked
  out by hand, and each response lists exactly the capabilities that were
  negotiated. No discount field appears without the extension.
- **Every request and response is valid** against the types generated for
  what was negotiated. Cart and checkout responses are checked a second way,
  by `ucp-schema validate`, and the two must agree.
- **The generated models are faithful.** Every request and response is parsed
  into its model and serialized again, and comes out unchanged. The models
  are a little more lenient than the schemas (they accept `null` for an
  optional field, and a boolean for an integer), which is why the Business
  validates against the schema first.
- **REST and MCP carry identical payloads**, including the bodies of protocol
  errors.
- **Every operation the profile exposes is called**, and amounts come out to
  totals worked out by hand.
- **The wire has not changed.** The run must match `transcripts/`. After a
  deliberate change, run `make update` and review the result with `git diff`.
- **This page quotes real code.** The examples above must still be in the
  source.

## Layout

```text
reference/
├── Makefile                generate, check, update, serve, shop
├── build.py                the generate step
├── check.py                the integration test
├── business/
│   ├── profile.json        the single input; served at /.well-known/ucp
│   ├── handlers.py         one function per operation
│   ├── store.py            an in-memory digital-goods store
│   ├── negotiation.py      profile fetch and the intersection algorithm
│   ├── app.py              Business.call: the path every call takes
│   ├── rest.py             REST binding
│   └── mcp.py              MCP binding
├── platform/
│   ├── profiles/           core.json, and discount.json with the extension
│   └── client.py           the Platform and the purchase it makes
├── transcripts/            what went over the wire; committed
└── generated/              written by `make generate`; not committed
```

## What it leaves out

It is deliberately small. Not included:

- **Order, webhooks and message signatures.** Declaring the order capability
  obliges a Business to send signed webhooks.
- **Authentication** of any kind.
- **Fulfillment.** The store sells downloads, so a checkout needs the Buyer's
  email and no shipping address.
- **Other capabilities and bindings:** catalog lookup and get-product,
  identity linking, the A2A binding and the Embedded Protocol.
- **Some rules around what it does implement:** the confirmation email after
  completion, constraints on payment instruments, carrying checkout changes
  back to the cart, the authority binding check on `schema` URLs in a fetched
  profile, and more than one protocol version.
- **What production needs:** persistence (state lives in memory), and a
  hardened profile fetcher (it vets the addresses a profile host resolves to,
  but does not pin the connection to them).
