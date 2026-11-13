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

"""MCP binding: one tool per operation, served by the official MCP SDK.

The specification defines the binding as a transform of the OpenRPC
service definition: a method becomes a tool name and its params become
the tool arguments. `meta["ucp-agent"].profile` carries the Platform
profile, `meta["idempotency-key"]` the idempotency key, `id` the resource,
and one more argument the payload.

Tool schemas come from the type bundle generated for the Business's
profile, so they describe everything the Business offers. What a given
Platform negotiated is decided per call, as on REST.
"""

import copy
import hashlib
import json
from urllib.parse import urlsplit

import mcp.types as types
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from mcp import MCPError
from mcp.server import Server
from mcp.server.transport_security import TransportSecuritySettings
from starlette.routing import Route

from reference import build
from reference.business.negotiation import NEGOTIATION_ERRORS, ProtocolError

OPENRPC = build.REPO / "source" / "services" / "shopping" / "mcp.openrpc.json"
PATH = "/mcp"
# HTTP status for the JSON-RPC errors this Business raises without a UCP
# code: invalid arguments, and an idempotency conflict. A Business that
# also raised -32000 for authentication or rate limiting would have to
# carry the status some other way.
RPC_STATUS = {-32700: 400, -32602: 400, -32000: 409}


def _closure(defs: dict, schema) -> dict:
  """Return the `$defs` entries that `schema` reaches through `$ref`."""
  found: dict = {}
  pending = [schema]
  while pending:
    node = pending.pop()
    if isinstance(node, dict):
      ref = node.get("$ref", "")
      name = ref.removeprefix("#/$defs/")
      if ref.startswith("#/$defs/") and name not in found:
        found[name] = defs[name]
        pending.append(defs[name])
      pending.extend(node.values())
    elif isinstance(node, list):
      pending.extend(node)
  return dict(sorted(found.items()))


def _local(schema: dict) -> dict:
  """Rewrite OpenAPI and OpenRPC component references to `#/$defs/`."""
  return json.loads(
    json.dumps(schema).replace("#/components/schemas/", "#/$defs/")
  )


def tools(business) -> dict[str, tuple[types.Tool, str | None]]:
  """Build one tool per operation: name to (tool, payload argument name)."""
  openrpc = json.loads(OPENRPC.read_text())
  defs = {**business.types, "meta": openrpc["components"]["schemas"]["meta"]}
  built = {}
  for method in openrpc["methods"]:
    route = business.routes.get(method["name"])
    if route is None:
      continue  # an operation of a capability this profile does not declare
    properties, required, payload = {}, [], None
    for param in method["params"]:
      if param["name"] in ("meta", "id"):
        properties[param["name"]] = _local(param["schema"])
      else:
        # The OpenRPC schema here is a pointer to the base capability. Use
        # the request type composed for this Business's profile instead.
        payload = param["name"]
        properties[payload] = {"$ref": f"#/$defs/{route.request}"}
      if param.get("required"):
        required.append(param["name"])
    arguments = {
      "type": "object",
      "properties": properties,
      "required": required,
    }
    result = {"type": "object", **_local(route.response)}
    tool = types.Tool(
      name=route.name,
      description=route.summary,
      input_schema={**arguments, "$defs": _closure(defs, arguments)},
      output_schema={**result, "$defs": _closure(defs, result)},
    )
    built[route.name] = (tool, payload)
  return built


def app(business, rest_routes: list[Route]):
  """Return the ASGI application: the MCP endpoint plus the REST routes."""
  offered = tools(business)
  # The payload is validated in `Business.call`, against the types for what
  # was negotiated. Here only the arguments around it are checked.
  envelopes = {}
  for name, (tool, payload) in offered.items():
    schema = copy.deepcopy(tool.input_schema)
    if payload:
      schema["properties"][payload] = {}
    envelopes[name] = Draft202012Validator(schema)

  async def list_tools(context, params) -> types.ListToolsResult:
    return types.ListToolsResult(tools=[tool for tool, _ in offered.values()])

  async def call_tool(context, params) -> types.CallToolResult:
    arguments = params.arguments or {}
    if params.name not in offered:
      raise MCPError(code=-32602, message=f"Unknown tool: {params.name}")
    payload = offered[params.name][1]
    try:
      meta = arguments.get("meta")
      agent = meta.get("ucp-agent") if isinstance(meta, dict) else None
      profile = agent.get("profile") if isinstance(agent, dict) else None
      if not isinstance(profile, str):
        raise ProtocolError(
          'meta["ucp-agent"].profile is required', "invalid_profile_url"
        )
      fault = best_match(envelopes[params.name].iter_errors(arguments))
      if fault:
        raise ProtocolError(
          f"Invalid arguments: {fault.message}", status=400, rpc=-32602
        )
      # MCP has no request body of its own, so the arguments other than
      # `meta` stand in for it when two requests are compared.
      rest = {k: v for k, v in arguments.items() if k != "meta"}
      reply = await business.call(
        params.name,
        profile,
        key=meta.get("idempotency-key"),
        id=arguments.get("id"),
        body=arguments.get(payload) if payload else None,
        digest=hashlib.sha256(
          json.dumps(rest, sort_keys=True).encode()
        ).hexdigest(),
      )
    except ProtocolError as error:
      data = error.body() if error.code else None
      raise MCPError(
        code=error.rpc, message=error.content, data=data
      ) from error
    # The payload goes in structuredContent; content repeats it as text for
    # clients that predate structured results.
    return types.CallToolResult(
      content=[types.TextContent(type="text", text=json.dumps(reply))],
      structured_content=reply,
    )

  server = Server(
    "ucp-reference-business",
    version=business.version,
    on_list_tools=list_tools,
    on_call_tool=call_tool,
  )
  inner = server.streamable_http_app(
    streamable_http_path=PATH,
    json_response=True,
    stateless_http=True,
    transport_security=TransportSecuritySettings(
      allowed_hosts=[urlsplit(business.base_url).netloc]
    ),
    custom_starlette_routes=rest_routes,
  )
  return _StatusCodes(inner)


class _StatusCodes:
  """Give JSON-RPC errors the HTTP status the specification requires.

  Over Streamable HTTP a UCP server returns the matching HTTP status
  alongside a JSON-RPC error. The SDK answers 200, so this wrapper sets
  the status from the error it finds in the response body.
  """

  def __init__(self, inner):
    """Wrap the SDK's Starlette application."""
    self.inner = inner
    self.lifespan = lambda: inner.router.lifespan_context(inner)

  async def __call__(self, scope, receive, send):
    """Pass everything through, buffering MCP responses to set the status."""
    if scope["type"] != "http" or scope["path"] != PATH:
      return await self.inner(scope, receive, send)
    start, chunks = {}, []

    async def buffered(message):
      if message["type"] == "http.response.start":
        start.update(message)
        return
      chunks.append(message.get("body", b""))
      if message.get("more_body"):
        return
      body = b"".join(chunks)
      start["status"] = _status(body, start["status"])
      await send(start)
      await send({"type": "http.response.body", "body": body})

    await self.inner(scope, receive, buffered)


def _status(body: bytes, default: int) -> int:
  """Return the HTTP status for a JSON-RPC response body."""
  try:
    error = json.loads(body)["error"]
  except (ValueError, KeyError, TypeError):
    return default
  code = (error.get("data") or {}).get("code")
  return NEGOTIATION_ERRORS.get(code) or RPC_STATUS.get(error["code"], default)
