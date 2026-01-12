<!--
   Copyright 2026 UCP Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
-->

# Cart Capability

* **Capability Name:** `dev.ucp.shopping.cart`
* **Version:** `2026-01-11`

## Overview

The Cart capability provides a first-class basket for multi-item shopping before
checkout. It allows platforms to build, validate, and update carts without
collecting payment details.

A cart can be converted into a checkout session by sending the cart's
`line_items` to the Checkout create endpoint.

## Endpoints

### Create Cart

{{ method_fields('create_cart', 'rest.openapi.json', 'cart') }}

### Get Cart

{{ method_fields('get_cart', 'rest.openapi.json', 'cart') }}

### Update Cart

{{ method_fields('update_cart', 'rest.openapi.json', 'cart') }}

## Schema

{{ schema_fields('cart_resp', 'cart') }}

## Related Specs

* [Checkout Capability](checkout.md)
* [HTTP/REST Binding](checkout-rest.md)
