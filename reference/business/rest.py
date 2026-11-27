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

"""REST binding: HTTP routes read from the generated OpenAPI document.

The Platform profile arrives in the `UCP-Agent` header, the idempotency
key in `Idempotency-Key`, the resource id in the path and the payload in
the body.
"""

import hashlib
import json

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from reference.business.negotiation import ProtocolError, profile_url


def routes(business) -> list[Route]:
  """Return the discovery route and one route per generated operation."""

  async def discover(request: Request) -> JSONResponse:
    # Profiles must be cacheable: public, with max-age of at least 60s.
    headers = {"Cache-Control": "public, max-age=3600"}
    return JSONResponse(business.profile, headers=headers)

  def bind(route) -> Route:
    async def endpoint(request: Request) -> JSONResponse:
      try:
        for header in route.headers:
          if header != "UCP-Agent" and header not in request.headers:
            raise ProtocolError(f"Missing header: {header}", status=400)
        raw = await request.body()
        reply = await business.call(
          route.name,
          profile_url(request.headers.get("UCP-Agent")),
          key=request.headers.get("Idempotency-Key"),
          id=request.path_params.get("id"),
          body=_json(raw) if route.request else None,
          # For idempotency, two requests match when their bodies are the
          # same bytes.
          digest=hashlib.sha256(raw).hexdigest(),
        )
      except ProtocolError as error:
        return JSONResponse(error.body(), status_code=error.status)
      # A business outcome is always 200, even when it is an error response.
      # Only a success uses the operation's own status (201 for creates).
      succeeded = reply["ucp"]["status"] == "success"
      return JSONResponse(reply, status_code=route.status if succeeded else 200)

    return Route(route.path, endpoint, methods=[route.method])

  return [
    Route("/.well-known/ucp", discover, methods=["GET"]),
    *(bind(route) for route in business.routes.values()),
  ]


def _json(raw: bytes) -> dict:
  """Parse a JSON request body."""
  try:
    return json.loads(raw)
  except ValueError as error:
    raise ProtocolError(
      "Request body is not JSON.", status=400, rpc=-32700
    ) from error
