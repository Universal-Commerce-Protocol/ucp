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

"""The Business: what happens to a call whichever transport carried it.

`Business.call` is the whole protocol in order: resolve the Platform's
profile, negotiate, check the operation is available, validate and parse
the request, honor the idempotency key, run the handler, and serialize
its response. The REST and MCP bindings only translate to and from this
one function.
"""

import json
import os
from dataclasses import dataclass

import httpx2
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from pydantic import RootModel, ValidationError
from starlette.responses import JSONResponse
from starlette.routing import Route as HttpRoute

from reference import build
from reference.business import mcp, negotiation, rest
from reference.business.handlers import CHECKOUT, OPERATIONS, Call, OutcomeError
from reference.business.negotiation import ProtocolError
from reference.business.store import Store

TEMPLATE_URL = "https://business.example"  # as written in profile.json


@dataclass
class Route:
  """One operation, as bound by the generated OpenAPI document."""

  name: str  # operationId, which is also the MCP tool name
  summary: str
  method: str
  path: str
  status: int  # HTTP status of a successful response
  request: str | None  # name of the request type, if the operation has a body
  response: dict  # schema of the response body
  headers: list[str]  # request headers the service definition requires


def _routes(openapi: dict) -> list[Route]:
  """Read every operation out of an OpenAPI document."""
  routes = []
  declared = openapi["components"]["parameters"]
  for method, path, operation in build.operations(openapi):
    status, response = next(iter(operation["responses"].items()))
    body = operation.get("requestBody")
    request = body and body["content"]["application/json"]["schema"]["$ref"]
    parameters = [
      declared[parameter["$ref"].rsplit("/", 1)[-1]]
      for parameter in operation.get("parameters", [])
    ]
    routes.append(
      Route(
        name=operation["operationId"],
        summary=operation["summary"],
        method=method,
        path=path,
        status=int(status),
        request=request and request.rsplit("/", 1)[-1],
        response=response["content"]["application/json"]["schema"],
        headers=[
          parameter["name"]
          for parameter in parameters
          if parameter["in"] == "header" and parameter.get("required")
        ],
      )
    )
  return routes


class Business:
  """A UCP Business serving the capabilities named in its profile."""

  def __init__(
    self,
    http: httpx2.AsyncClient,
    base_url: str = TEMPLATE_URL,
    resolver=negotiation.resolve,
    local: bool = False,
  ):
    """Load the profile and the routes and types generated from it."""
    template = build.ROOT / "business" / "profile.json"
    self.base_url = base_url
    self.profile = json.loads(
      json.dumps(build.load(template)).replace(TEMPLATE_URL, base_url)
    )
    self.version = self.profile["ucp"]["version"]
    # One type bundle per combination of extensions; see reference/build.py.
    self.bundles = {
      path.parent.name: json.loads(path.read_text())["$defs"]
      for path in sorted(build.OUT.glob("*/types.json"))
    }
    self.types = self.bundles["full"]
    # The same types as Pydantic models, to parse requests and build
    # responses with.
    self.models = {variant: build.models(variant) for variant in self.bundles}
    openapi = json.loads((build.OUT / "full" / "openapi.json").read_text())
    self.routes = {route.name: route for route in _routes(openapi)}
    unhandled = sorted(set(self.routes) - set(OPERATIONS))
    if unhandled:
      raise RuntimeError(
        f"The profile exposes operations that have no handler: {unhandled}"
      )
    self._validators: dict[tuple[str, str], Draft202012Validator] = {}
    self.profiles = negotiation.Profiles(
      http, self._validator("full", "ProfilePlatformSchema"), resolver, local
    )
    self.store = Store()

  def _validator(self, variant: str, type_name: str) -> Draft202012Validator:
    """Return a validator for a generated type of one extension set."""
    if (variant, type_name) not in self._validators:
      schema = {"$ref": f"#/$defs/{type_name}", "$defs": self.bundles[variant]}
      self._validators[variant, type_name] = Draft202012Validator(schema)
    return self._validators[variant, type_name]

  def check(self, variant: str, type_name: str, payload) -> None:
    """Reject a payload that does not match a generated type."""
    validator = self._validator(variant, type_name)
    error = best_match(validator.iter_errors(payload))
    if error:
      where = "/".join(str(part) for part in error.absolute_path) or "body"
      raise ProtocolError(f"{where}: {error.message}", status=400, rpc=-32602)

  async def call(
    self,
    name: str,
    profile_url: str,
    *,
    key: str | None = None,
    id: str | None = None,
    body: dict | None = None,
    digest: str = "",
  ) -> dict:
    """Run one operation for the Platform whose profile is at `profile_url`.

    `key` is the idempotency key and `digest` identifies the request it
    came with. Returns the response body. Raises `ProtocolError` when the
    request fails before a handler runs.
    """
    capability, handler = OPERATIONS[name]
    route = self.routes[name]

    # 1. Negotiate. Every request is negotiated; nothing is remembered
    #    between requests except the cached profile.
    platform = await self.profiles.get(profile_url)
    active = negotiation.negotiate(self.profile, platform)
    handlers = negotiation.payment_handlers(self.profile, platform)
    # The types for the extensions that were negotiated, and no others.
    variant = build.variant(self.profile, active)
    models = self.models[variant]
    ucp = {
      "version": self.version,
      "status": "success",
      "capabilities": negotiation.relevant(active, capability),
    }
    if capability == CHECKOUT:
      ucp["payment_handlers"] = handlers

    # 2. The operation's capability must be in the negotiated set.
    if capability not in active:
      missing = OutcomeError(
        "capabilities_incompatible",
        f"{name} needs {capability}, which was not negotiated.",
      )
      return self._error_response(models, ucp, missing)

    # 3. Validate the request against the schema, then parse it into its
    #    model. A field of an extension that was not negotiated is just an
    #    unknown property here: it passes validation, and no handler reads it.
    request = None
    if route.request:
      self.check(variant, route.request, body)
      try:
        request = getattr(models, route.request).model_validate(body)
      except ValidationError as error:
        fault = error.errors()[0]
        where = "/".join(str(part) for part in fault["loc"]) or "body"
        raise ProtocolError(
          f"{where}: {fault['msg']}", status=400, rpc=-32602
        ) from error
      if isinstance(request, RootModel):
        request = request.root  # a union: use whichever form was sent

    # 4. Idempotency: the same key with the same request replays the reply;
    #    with a different request it is a conflict. Keys are scoped to the
    #    Platform and the operation.
    remembered = (profile_url, name, key)
    fingerprint = (id, digest)
    if key and remembered in self.store.replies:
      seen, reply = self.store.replies[remembered]
      if seen != fingerprint:
        raise ProtocolError(
          "Idempotency key was already used with a different request.",
          status=409,
          rpc=-32000,
        )
      return reply

    # 5. Run the handler and serialize the model it returns.
    call = Call(
      store=self.store,
      models=models,
      ucp=ucp,
      active=set(active),
      base_url=self.base_url,
      id=id,
      body=request,
    )
    try:
      reply = build.wire(handler(call))
    except OutcomeError as outcome:
      reply = self._error_response(models, ucp, outcome)
    if key:
      self.store.replies[remembered] = (fingerprint, reply)
    return reply

  def _error_response(self, models, ucp: dict, outcome: OutcomeError) -> dict:
    """Build the error response for an outcome that has no resource."""
    envelope = {k: v for k, v in ucp.items() if k != "payment_handlers"}
    message = models.MessageError(
      type="error",
      code=outcome.code,
      content=str(outcome),
      severity="unrecoverable",
    )
    response = models.ErrorResponse(
      ucp={**envelope, "status": "error"},
      messages=[message],
      continue_url=self.base_url,
    )
    return build.wire(response)

  def asgi(self, extra_routes=()):
    """Return the ASGI application serving discovery, REST and MCP."""
    return mcp.app(self, [*rest.routes(self), *extra_routes])


def serve():
  """Build the application for `make serve`: local development only.

  The specification requires HTTPS for endpoints and for profile URLs. This
  entry point relaxes that for loopback addresses so the Business can be
  tried from a terminal. Do not deploy it.
  """
  base_url = os.environ.get("REFERENCE_BASE_URL", "http://localhost:8182")
  profiles = build.platform_profiles()

  async def platform_profile(request):
    # A Platform hosts its own profile. Serving the samples here saves
    # running a second server while trying things out.
    return JSONResponse(profiles[request.path_params["name"]])

  hosted = HttpRoute("/platform/{name}.json", platform_profile)
  return Business(httpx2.AsyncClient(), base_url, local=True).asgi([hosted])
