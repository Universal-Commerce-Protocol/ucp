# Schema Reference

This page provides a reference for all the capability data models and types used within the UCP.

## Capability Schemas

### Checkout Create Request

| Name       | Type                                                                                          | Required | Description                           |
| ---------- | --------------------------------------------------------------------------------------------- | -------- | ------------------------------------- |
| line_items | Array\[[Line Item Create Request](/draft/specification/reference/#line-item-create-request)\] | **Yes**  | List of line items being checked out. |
| buyer      | [Buyer](/draft/specification/reference/#buyer)                                                | No       | Representation of the buyer.          |
| currency   | string                                                                                        | **Yes**  | ISO 4217 currency code.               |
| payment    | [Payment Create Request](/draft/specification/reference/#payment-create-request)              | **Yes**  |                                       |

______________________________________________________________________

### Checkout Update Request

| Name       | Type                                                                                          | Required | Description                                |
| ---------- | --------------------------------------------------------------------------------------------- | -------- | ------------------------------------------ |
| id         | string                                                                                        | **Yes**  | Unique identifier of the checkout session. |
| line_items | Array\[[Line Item Update Request](/draft/specification/reference/#line-item-update-request)\] | **Yes**  | List of line items being checked out.      |
| buyer      | [Buyer](/draft/specification/reference/#buyer)                                                | No       | Representation of the buyer.               |
| currency   | string                                                                                        | **Yes**  | ISO 4217 currency code.                    |
| payment    | [Payment Update Request](/draft/specification/reference/#payment-update-request)              | **Yes**  |                                            |

______________________________________________________________________

### Checkout Response

| Name         | Type                                                                              | Required | Description                                                                                                                                                                                                                                                     |
| ------------ | --------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Checkout](/draft/specification/reference/#ucp-response-checkout)    | **Yes**  |                                                                                                                                                                                                                                                                 |
| id           | string                                                                            | **Yes**  | Unique identifier of the checkout session.                                                                                                                                                                                                                      |
| line_items   | Array\[[Line Item Response](/draft/specification/reference/#line-item-response)\] | **Yes**  | List of line items being checked out.                                                                                                                                                                                                                           |
| buyer        | [Buyer](/draft/specification/reference/#buyer)                                    | No       | Representation of the buyer.                                                                                                                                                                                                                                    |
| status       | string                                                                            | **Yes**  | Checkout state indicating the current phase and required action. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled` |
| currency     | string                                                                            | **Yes**  | ISO 4217 currency code.                                                                                                                                                                                                                                         |
| totals       | Array\[[Total Response](/draft/specification/reference/#total-response)\]         | **Yes**  | Different cart totals.                                                                                                                                                                                                                                          |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]                       | No       | List of messages with error and info about the checkout session state.                                                                                                                                                                                          |
| links        | Array\[[Link](/draft/specification/reference/#link)\]                             | **Yes**  | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                    |
| expires_at   | string                                                                            | No       | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                    |
| continue_url | string                                                                            | No       | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                 |
| payment      | [Payment Response](/draft/specification/reference/#payment-response)              | **Yes**  |                                                                                                                                                                                                                                                                 |
| order        | [Order Confirmation](/draft/specification/reference/#order-confirmation)          | No       | Details about an order created for this checkout session.                                                                                                                                                                                                       |

______________________________________________________________________

### Order

| Name          | Type                                                                        | Required | Description                                                                                                                                  |
| ------------- | --------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp           | [UCP Response Order](/draft/specification/reference/#ucp-response-order)    | **Yes**  |                                                                                                                                              |
| id            | string                                                                      | **Yes**  | Unique order identifier.                                                                                                                     |
| checkout_id   | string                                                                      | **Yes**  | Associated checkout ID for reconciliation.                                                                                                   |
| permalink_url | string                                                                      | **Yes**  | Permalink to access the order on merchant site.                                                                                              |
| line_items    | Array\[[Order Line Item](/draft/specification/reference/#order-line-item)\] | **Yes**  | Immutable line items — source of truth for what was ordered.                                                                                 |
| fulfillment   | object                                                                      | **Yes**  | Fulfillment data: buyer expectations and what actually happened.                                                                             |
| adjustments   | Array\[[Adjustment](/draft/specification/reference/#adjustment)\]           | No       | Append-only event log of money movements (refunds, returns, credits, disputes, cancellations, etc.) that exist independently of fulfillment. |
| totals        | Array\[[Total Response](/draft/specification/reference/#total-response)\]   | **Yes**  | Different totals for the order.                                                                                                              |

______________________________________________________________________

### Payment Create Request

| Name                   | Type                                                                              | Required | Description                                                                                                                                                                                                                |
| ---------------------- | --------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| selected_instrument_id | string                                                                            | No       | The id of the currently selected payment instrument from the instruments array. Set by the agent when submitting payment, and echoed back by the merchant in finalized state.                                              |
| instruments            | Array\[[Payment Instrument](/draft/specification/reference/#payment-instrument)\] | No       | The payment instruments available for this payment. Each instrument is associated with a specific handler via the handler_id field. Handlers can extend the base payment_instrument schema to add handler-specific fields. |

______________________________________________________________________

### Payment Update Request

| Name                   | Type                                                                              | Required | Description                                                                                                                                                                                                                |
| ---------------------- | --------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| selected_instrument_id | string                                                                            | No       | The id of the currently selected payment instrument from the instruments array. Set by the agent when submitting payment, and echoed back by the merchant in finalized state.                                              |
| instruments            | Array\[[Payment Instrument](/draft/specification/reference/#payment-instrument)\] | No       | The payment instruments available for this payment. Each instrument is associated with a specific handler via the handler_id field. Handlers can extend the base payment_instrument schema to add handler-specific fields. |

______________________________________________________________________

### Payment Data

| Name         | Type                                                                     | Required | Description |
| ------------ | ------------------------------------------------------------------------ | -------- | ----------- |
| payment_data | [Payment Instrument](/draft/specification/reference/#payment-instrument) | **Yes**  |             |

______________________________________________________________________

### Payment Response

| Name                   | Type                                                                                          | Required | Description                                                                                                                                                                                                                |
| ---------------------- | --------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| handlers               | Array\[[Payment Handler Response](/draft/specification/reference/#payment-handler-response)\] | **Yes**  | Processing configurations that define how payment instruments can be collected. Each handler specifies a tokenization or payment collection strategy.                                                                      |
| selected_instrument_id | string                                                                                        | No       | The id of the currently selected payment instrument from the instruments array. Set by the agent when submitting payment, and echoed back by the merchant in finalized state.                                              |
| instruments            | Array\[[Payment Instrument](/draft/specification/reference/#payment-instrument)\]             | No       | The payment instruments available for this payment. Each instrument is associated with a specific handler via the handler_id field. Handlers can extend the base payment_instrument schema to add handler-specific fields. |

______________________________________________________________________

## Type Schemas

### Payment Account Info

| Name                      | Type   | Required | Description                                                                                                                                   |
| ------------------------- | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| payment_account_reference | string | No       | EMVCo PAR. A unique identifier linking a payment card to a specific account, enabling tracking across tokens (Apple Pay, physical card, etc). |

______________________________________________________________________

### Adjustment

| Name        | Type          | Required | Description                                                                                                                                                                                     |
| ----------- | ------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string        | **Yes**  | Adjustment event identifier.                                                                                                                                                                    |
| type        | string        | **Yes**  | Type of adjustment (open string). Typically money-related like: refund, return, credit, price_adjustment, dispute, cancellation. Can be any value that makes sense for the merchant's business. |
| occurred_at | string        | **Yes**  | RFC 3339 timestamp when this adjustment occurred.                                                                                                                                               |
| status      | string        | **Yes**  | Adjustment status. **Enum:** `pending`, `completed`, `failed`                                                                                                                                   |
| line_items  | Array[object] | No       | Which line items and quantities are affected (optional).                                                                                                                                        |
| amount      | integer       | No       | Amount in minor units (cents) for refunds, credits, price adjustments (optional).                                                                                                               |
| description | string        | No       | Human-readable reason or description (e.g., 'Defective item', 'Customer requested').                                                                                                            |

______________________________________________________________________

### Binding

| Name        | Type                                                                 | Required | Description                                                                                                                                                                                    |
| ----------- | -------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| checkout_id | string                                                               | **Yes**  | The checkout session identifier this token is bound to.                                                                                                                                        |
| identity    | [Payment Identity](/draft/specification/reference/#payment-identity) | No       | The participant this token is bound to. Required when acting on behalf of another participant (e.g., agent tokenizing for merchant). Omit when the authenticated caller is the binding target. |

______________________________________________________________________

### Buyer

| Name         | Type   | Required | Description                                                                                       |
| ------------ | ------ | -------- | ------------------------------------------------------------------------------------------------- |
| first_name   | string | No       | First name of the buyer.                                                                          |
| last_name    | string | No       | Last name of the buyer.                                                                           |
| full_name    | string | No       | Optional, buyer's full name (if first_name or last_name fields are present they take precedence). |
| email        | string | No       | Email of the buyer.                                                                               |
| phone_number | string | No       | E.164 standard.                                                                                   |

______________________________________________________________________

### Card Credential

| Name             | Type    | Required | Description                                                                                                                                            |
| ---------------- | ------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| type             | any     | **Yes**  | **Constant = card**. The credential type identifier for card credentials.                                                                              |
| card_number_type | string  | **Yes**  | The type of card number. Network tokens are preferred with fallback to FPAN. See PCI Scope for more details. **Enum:** `fpan`, `network_token`, `dpan` |
| number           | string  | No       | Card number.                                                                                                                                           |
| expiry_month     | integer | No       | The month of the card's expiration date (1-12).                                                                                                        |
| expiry_year      | integer | No       | The year of the card's expiration date.                                                                                                                |
| name             | string  | No       | Cardholder name.                                                                                                                                       |
| cvc              | string  | No       | Card CVC number.                                                                                                                                       |
| cryptogram       | string  | No       | Cryptogram provided with network tokens.                                                                                                               |
| eci_value        | string  | No       | Electronic Commerce Indicator / Security Level Indicator provided with network tokens.                                                                 |

______________________________________________________________________

### Card Payment Instrument

| Name                  | Type                                                                     | Required | Description                                                                                                                                                        |
| --------------------- | ------------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| id                    | string                                                                   | **Yes**  | A unique identifier for this instrument instance, assigned by the Agent. Used to reference this specific instrument in the 'payment.selected_instrument_id' field. |
| handler_id            | string                                                                   | **Yes**  | The unique identifier for the handler instance that produced this instrument. This corresponds to the 'id' field in the Payment Handler definition.                |
| type                  | string                                                                   | **Yes**  | The broad category of the instrument (e.g., 'card', 'tokenized_card'). Specific schemas will constrain this to a constant value.                                   |
| billing_address       | [Postal Address](/draft/specification/reference/#postal-address)         | No       | The billing address associated with this payment method.                                                                                                           |
| credential            | [Payment Credential](/draft/specification/reference/#payment-credential) | No       |                                                                                                                                                                    |
| type                  | string                                                                   | **Yes**  | **Constant = card**. Indicates this is a card payment instrument.                                                                                                  |
| brand                 | string                                                                   | **Yes**  | The card brand/network (e.g., visa, mastercard, amex).                                                                                                             |
| last_digits           | string                                                                   | **Yes**  | Last 4 digits of the card number.                                                                                                                                  |
| expiry_month          | integer                                                                  | No       | The month of the card's expiration date (1-12).                                                                                                                    |
| expiry_year           | integer                                                                  | No       | The year of the card's expiration date.                                                                                                                            |
| rich_text_description | string                                                                   | No       | An optional rich text description of the card to display to the user (e.g., 'Visa ending in 1234, expires 12/2025').                                               |
| rich_card_art         | string                                                                   | No       | An optional URI to a rich image representing the card (e.g., card art provided by the issuer).                                                                     |

______________________________________________________________________

### Expectation

| Name           | Type                                                             | Required | Description                                                                                                 |
| -------------- | ---------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------- |
| id             | string                                                           | **Yes**  | Expectation identifier.                                                                                     |
| line_items     | Array[object]                                                    | **Yes**  | Which line items and quantities are in this expectation.                                                    |
| method_type    | string                                                           | **Yes**  | Delivery method type (shipping, pickup, digital). **Enum:** `shipping`, `pickup`, `digital`                 |
| destination    | [Postal Address](/draft/specification/reference/#postal-address) | **Yes**  | Delivery destination address.                                                                               |
| description    | string                                                           | No       | Human-readable delivery description (e.g., 'Arrives in 5-8 business days').                                 |
| fulfillable_on | string                                                           | No       | When this expectation can be fulfilled: 'now' or ISO 8601 timestamp for future date (backorder, pre-order). |

______________________________________________________________________

### Fulfillment Available Method Response

| Name           | Type               | Required | Description                                                                              |
| -------------- | ------------------ | -------- | ---------------------------------------------------------------------------------------- |
| type           | string             | **Yes**  | Fulfillment method type this availability applies to. **Enum:** `shipping`, `pickup`     |
| line_item_ids  | Array[string]      | **Yes**  | Line items available for this fulfillment method.                                        |
| fulfillable_on | ['string', 'null'] | No       | 'now' for immediate availability, or ISO 8601 date for future (preorders, transfers).    |
| description    | string             | No       | Human-readable availability info (e.g., 'Available for pickup at Downtown Store today'). |

______________________________________________________________________

### Fulfillment Destination Request

This object MUST be one of the following types: [Shipping Destination Request](/draft/specification/reference/#shipping-destination-request), [Retail Location Request](/draft/specification/reference/#retail-location-request).

______________________________________________________________________

### Fulfillment Destination Response

This object MUST be one of the following types: [Shipping Destination Response](/draft/specification/reference/#shipping-destination-response), [Retail Location Response](/draft/specification/reference/#retail-location-response).

______________________________________________________________________

### Fulfillment Event

| Name            | Type          | Required | Description                                                                                                                                                                                                                                                                                                                             |
| --------------- | ------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id              | string        | **Yes**  | Fulfillment event identifier.                                                                                                                                                                                                                                                                                                           |
| occurred_at     | string        | **Yes**  | RFC 3339 timestamp when this fulfillment event occurred.                                                                                                                                                                                                                                                                                |
| type            | string        | **Yes**  | Fulfillment event type. Common values include: processing (preparing to ship), shipped (handed to carrier), in_transit (in delivery network), delivered (received by buyer), failed_attempt (delivery attempt failed), canceled (fulfillment canceled), undeliverable (cannot be delivered), returned_to_sender (returned to merchant). |
| line_items      | Array[object] | **Yes**  | Which line items and quantities are fulfilled in this event.                                                                                                                                                                                                                                                                            |
| tracking_number | string        | No       | Carrier tracking number (required if type != processing).                                                                                                                                                                                                                                                                               |
| tracking_url    | string        | No       | URL to track this shipment (required if type != processing).                                                                                                                                                                                                                                                                            |
| carrier         | string        | No       | Carrier name (e.g., 'FedEx', 'USPS').                                                                                                                                                                                                                                                                                                   |
| description     | string        | No       | Human-readable description of the shipment status or delivery information (e.g., 'Delivered to front door', 'Out for delivery').                                                                                                                                                                                                        |

______________________________________________________________________

### Fulfillment Group Create Request

| Name               | Type               | Required | Description                                           |
| ------------------ | ------------------ | -------- | ----------------------------------------------------- |
| selected_option_id | ['string', 'null'] | No       | ID of the selected fulfillment option for this group. |

______________________________________________________________________

### Fulfillment Group Update Request

| Name               | Type               | Required | Description                                                            |
| ------------------ | ------------------ | -------- | ---------------------------------------------------------------------- |
| id                 | string             | **Yes**  | Group identifier for referencing merchant-generated groups in updates. |
| selected_option_id | ['string', 'null'] | No       | ID of the selected fulfillment option for this group.                  |

______________________________________________________________________

### Fulfillment Group Response

| Name               | Type                                                                                                | Required | Description                                                            |
| ------------------ | --------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------- |
| id                 | string                                                                                              | **Yes**  | Group identifier for referencing merchant-generated groups in updates. |
| line_item_ids      | Array[string]                                                                                       | **Yes**  | Line item IDs included in this group/package.                          |
| options            | Array\[[Fulfillment Option Response](/draft/specification/reference/#fulfillment-option-response)\] | No       | Available fulfillment options for this group.                          |
| selected_option_id | ['string', 'null']                                                                                  | No       | ID of the selected fulfillment option for this group.                  |

______________________________________________________________________

### Fulfillment Method Create Request

| Name                    | Type                                                                                                          | Required | Description                                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| type                    | string                                                                                                        | **Yes**  | Fulfillment method type. **Enum:** `shipping`, `pickup`                                                      |
| line_item_ids           | Array[string]                                                                                                 | No       | Line item IDs fulfilled via this method.                                                                     |
| destinations            | Array\[[Fulfillment Destination Request](/draft/specification/reference/#fulfillment-destination-request)\]   | No       | Available destinations. For shipping: addresses. For pickup: retail locations.                               |
| selected_destination_id | ['string', 'null']                                                                                            | No       | ID of the selected destination.                                                                              |
| groups                  | Array\[[Fulfillment Group Create Request](/draft/specification/reference/#fulfillment-group-create-request)\] | No       | Fulfillment groups for selecting options. Agent sets selected_option_id on groups to choose shipping method. |

______________________________________________________________________

### Fulfillment Method Update Request

| Name                    | Type                                                                                                          | Required | Description                                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| id                      | string                                                                                                        | **Yes**  | Unique fulfillment method identifier.                                                                        |
| line_item_ids           | Array[string]                                                                                                 | **Yes**  | Line item IDs fulfilled via this method.                                                                     |
| destinations            | Array\[[Fulfillment Destination Request](/draft/specification/reference/#fulfillment-destination-request)\]   | No       | Available destinations. For shipping: addresses. For pickup: retail locations.                               |
| selected_destination_id | ['string', 'null']                                                                                            | No       | ID of the selected destination.                                                                              |
| groups                  | Array\[[Fulfillment Group Update Request](/draft/specification/reference/#fulfillment-group-update-request)\] | No       | Fulfillment groups for selecting options. Agent sets selected_option_id on groups to choose shipping method. |

______________________________________________________________________

### Fulfillment Method Response

| Name                    | Type                                                                                                          | Required | Description                                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| id                      | string                                                                                                        | **Yes**  | Unique fulfillment method identifier.                                                                        |
| type                    | string                                                                                                        | **Yes**  | Fulfillment method type. **Enum:** `shipping`, `pickup`                                                      |
| line_item_ids           | Array[string]                                                                                                 | **Yes**  | Line item IDs fulfilled via this method.                                                                     |
| destinations            | Array\[[Fulfillment Destination Response](/draft/specification/reference/#fulfillment-destination-response)\] | No       | Available destinations. For shipping: addresses. For pickup: retail locations.                               |
| selected_destination_id | ['string', 'null']                                                                                            | No       | ID of the selected destination.                                                                              |
| groups                  | Array\[[Fulfillment Group Response](/draft/specification/reference/#fulfillment-group-response)\]             | No       | Fulfillment groups for selecting options. Agent sets selected_option_id on groups to choose shipping method. |

______________________________________________________________________

### Fulfillment Option Response

| Name                      | Type                                                                      | Required | Description                                                                |
| ------------------------- | ------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------- |
| id                        | string                                                                    | **Yes**  | Unique fulfillment option identifier.                                      |
| title                     | string                                                                    | **Yes**  | Short label (e.g., 'Express Shipping', 'Curbside Pickup').                 |
| description               | string                                                                    | No       | Complete context for buyer decision (e.g., 'Arrives Dec 12-15 via FedEx'). |
| carrier                   | string                                                                    | No       | Carrier name (for shipping).                                               |
| earliest_fulfillment_time | string                                                                    | No       | Earliest fulfillment date.                                                 |
| latest_fulfillment_time   | string                                                                    | No       | Latest fulfillment date.                                                   |
| totals                    | Array\[[Total Response](/draft/specification/reference/#total-response)\] | **Yes**  | Fulfillment option totals breakdown.                                       |

______________________________________________________________________

### Fulfillment Request

| Name    | Type                                                                                                            | Required | Description                         |
| ------- | --------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------- |
| methods | Array\[[Fulfillment Method Create Request](/draft/specification/reference/#fulfillment-method-create-request)\] | No       | Fulfillment methods for cart items. |

______________________________________________________________________

### Fulfillment Response

| Name              | Type                                                                                                                    | Required | Description                         |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------- |
| methods           | Array\[[Fulfillment Method Response](/draft/specification/reference/#fulfillment-method-response)\]                     | No       | Fulfillment methods for cart items. |
| available_methods | Array\[[Fulfillment Available Method Response](/draft/specification/reference/#fulfillment-available-method-response)\] | No       | Inventory availability hints.       |

______________________________________________________________________

### Item Create Request

| Name | Type   | Required | Description                                                                                                                                    |
| ---- | ------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| id   | string | **Yes**  | Should be recognized by both the Platform, and the Business. For Google it should match the id provided in the "id" field in the product feed. |

______________________________________________________________________

### Item Update Request

| Name | Type   | Required | Description                                                                                                                                    |
| ---- | ------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| id   | string | **Yes**  | Should be recognized by both the Platform, and the Business. For Google it should match the id provided in the "id" field in the product feed. |

______________________________________________________________________

### Item Response

| Name      | Type    | Required | Description                                                                                                                                    |
| --------- | ------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string  | **Yes**  | Should be recognized by both the Platform, and the Business. For Google it should match the id provided in the "id" field in the product feed. |
| title     | string  | **Yes**  | Product title.                                                                                                                                 |
| price     | integer | **Yes**  | Unit price in minor (cents) currency units.                                                                                                    |
| image_url | string  | No       | Product image URI.                                                                                                                             |

______________________________________________________________________

### Line Item Create Request

| Name     | Type                                                                       | Required | Description                           |
| -------- | -------------------------------------------------------------------------- | -------- | ------------------------------------- |
| item     | [Item Create Request](/draft/specification/reference/#item-create-request) | **Yes**  |                                       |
| quantity | integer                                                                    | **Yes**  | Quantity of the item being purchased. |

______________________________________________________________________

### Line Item Update Request

| Name      | Type                                                                       | Required | Description                                            |
| --------- | -------------------------------------------------------------------------- | -------- | ------------------------------------------------------ |
| id        | string                                                                     | No       |                                                        |
| item      | [Item Update Request](/draft/specification/reference/#item-update-request) | **Yes**  |                                                        |
| quantity  | integer                                                                    | **Yes**  | Quantity of the item being purchased.                  |
| parent_id | string                                                                     | No       | Parent line item identifier for any nested structures. |

______________________________________________________________________

### Line Item Response

| Name      | Type                                                                      | Required | Description                                            |
| --------- | ------------------------------------------------------------------------- | -------- | ------------------------------------------------------ |
| id        | string                                                                    | **Yes**  |                                                        |
| item      | [Item Response](/draft/specification/reference/#item-response)            | **Yes**  |                                                        |
| quantity  | integer                                                                   | **Yes**  | Quantity of the item being purchased.                  |
| totals    | Array\[[Total Response](/draft/specification/reference/#total-response)\] | **Yes**  | Line item totals breakdown.                            |
| parent_id | string                                                                    | No       | Parent line item identifier for any nested structures. |

______________________________________________________________________

### Link

| Name  | Type   | Required | Description                                                                                                                                                                                                                          |
| ----- | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| type  | string | **Yes**  | Type of link. Well-known values: `privacy_policy`, `terms_of_service`, `refund_policy`, `shipping_policy`, `faq`. Consumers SHOULD handle unknown values gracefully by displaying them using the `title` field or omitting the link. |
| url   | string | **Yes**  | The actual URL pointing to the content to be displayed.                                                                                                                                                                              |
| title | string | No       | Optional display text for the link. When provided, use this instead of generating from type.                                                                                                                                         |

______________________________________________________________________

### Merchant Fulfillment Config

| Name                       | Type         | Required | Description                                    |
| -------------------------- | ------------ | -------- | ---------------------------------------------- |
| allows_multi_destination   | object       | No       | Permits multiple destinations per method type. |
| allows_method_combinations | Array[array] | No       | Allowed method type combinations.              |

______________________________________________________________________

### Message

This object MUST be one of the following types: [Message Error](/draft/specification/reference/#message-error), [Message Warning](/draft/specification/reference/#message-warning), [Message Info](/draft/specification/reference/#message-info).

______________________________________________________________________

### Message Error

| Name         | Type   | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------ | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = error**. Message type discriminator.                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| code         | string | **Yes**  | Error code. Possible values include: missing, invalid, out_of_stock, payment_declined, requires_sign_in, requires_3ds, requires_identity_linking. Freeform codes also allowed.                                                                                                                                                                                                                                                                                                                                 |
| path         | string | No       | RFC 9535 JSONPath to the component the message refers to (e.g., $.items[1]).                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| content      | string | **Yes**  | Human-readable message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| severity     | string | **Yes**  | Declares who resolves this error. 'recoverable': agent can fix via API. 'requires_buyer_input': merchant requires information their API doesn't support collecting programmatically (checkout incomplete). 'requires_buyer_review': buyer must authorize before order placement due to policy, regulatory, or entitlement rules (checkout complete). Errors with 'requires\_*' severity contribute to 'status: requires_escalation'.* *Enum:*\* `recoverable`, `requires_buyer_input`, `requires_buyer_review` |

______________________________________________________________________

### Message Info

| Name         | Type   | Required | Description                                                    |
| ------------ | ------ | -------- | -------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = info**. Message type discriminator.               |
| path         | string | No       | RFC 9535 JSONPath to the component the message refers to.      |
| code         | string | No       | Info code for programmatic handling.                           |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown` |
| content      | string | **Yes**  | Human-readable message.                                        |

______________________________________________________________________

### Message Warning

| Name         | Type   | Required | Description                                                                                                                           |
| ------------ | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string | **Yes**  | **Constant = warning**. Message type discriminator.                                                                                   |
| path         | string | No       | JSONPath (RFC 9535) to related field (e.g., $.line_items[0]).                                                                         |
| code         | string | **Yes**  | Warning code. Machine-readable identifier for the warning type (e.g., final_sale, prop65, fulfillment_changed, age_restricted, etc.). |
| content      | string | **Yes**  | Human-readable warning message that MUST be displayed.                                                                                |
| content_type | string | No       | Content format, default = plain. **Enum:** `plain`, `markdown`                                                                        |

______________________________________________________________________

### Order Confirmation

| Name          | Type   | Required | Description                                     |
| ------------- | ------ | -------- | ----------------------------------------------- |
| id            | string | **Yes**  | Unique order identifier.                        |
| permalink_url | string | **Yes**  | Permalink to access the order on merchant site. |

______________________________________________________________________

### Order Line Item

| Name      | Type                                                                      | Required | Description                                                                                                                                                                |
| --------- | ------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id        | string                                                                    | **Yes**  | Line item identifier.                                                                                                                                                      |
| item      | [Item Response](/draft/specification/reference/#item-response)            | **Yes**  | Product data (id, title, price, image_url).                                                                                                                                |
| quantity  | object                                                                    | **Yes**  | Quantity tracking. Both total and fulfilled are derived from events.                                                                                                       |
| totals    | Array\[[Total Response](/draft/specification/reference/#total-response)\] | **Yes**  | Line item totals breakdown.                                                                                                                                                |
| status    | string                                                                    | **Yes**  | Derived status: fulfilled if quantity.fulfilled == quantity.total, partial if quantity.fulfilled > 0, otherwise processing. **Enum:** `processing`, `partial`, `fulfilled` |
| parent_id | string                                                                    | No       | Parent line item identifier for any nested structures.                                                                                                                     |

______________________________________________________________________

### Payment Credential

This object MUST be one of the following types: [Token Credential Response](/draft/specification/reference/#token-credential-response), [Card Credential](/draft/specification/reference/#card-credential).

______________________________________________________________________

### Payment Handler Response

| Name               | Type          | Required | Description                                                                                                                                        |
| ------------------ | ------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| id                 | string        | **Yes**  | The unique identifier for this handler instance within the payment.handlers. Used by payment instruments to reference which handler produced them. |
| name               | string        | **Yes**  | The specification name using reverse-DNS format. For example, dev.ucp.delegate_payment.                                                            |
| version            | string        | **Yes**  | Handler version in YYYY-MM-DD format.                                                                                                              |
| spec               | string        | **Yes**  | A URI pointing to the technical specification or schema that defines how this handler operates.                                                    |
| config_schema      | string        | **Yes**  | A URI pointing to a JSON Schema used to validate the structure of the config object.                                                               |
| instrument_schemas | Array[string] | **Yes**  |                                                                                                                                                    |
| config             | object        | **Yes**  | A dictionary containing provider-specific configuration details, such as merchant IDs, supported networks, or gateway credentials.                 |

______________________________________________________________________

### Payment Identity

| Name         | Type   | Required | Description                                                                            |
| ------------ | ------ | -------- | -------------------------------------------------------------------------------------- |
| access_token | string | **Yes**  | Unique identifier for this participant, obtained during onboarding with the tokenizer. |

______________________________________________________________________

### Payment Instrument

This object MUST be one of the following types: [Card Payment Instrument](/draft/specification/reference/#card-payment-instrument).

______________________________________________________________________

### Payment Instrument Base

| Name            | Type                                                                     | Required | Description                                                                                                                                                        |
| --------------- | ------------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| id              | string                                                                   | **Yes**  | A unique identifier for this instrument instance, assigned by the Agent. Used to reference this specific instrument in the 'payment.selected_instrument_id' field. |
| handler_id      | string                                                                   | **Yes**  | The unique identifier for the handler instance that produced this instrument. This corresponds to the 'id' field in the Payment Handler definition.                |
| type            | string                                                                   | **Yes**  | The broad category of the instrument (e.g., 'card', 'tokenized_card'). Specific schemas will constrain this to a constant value.                                   |
| billing_address | [Postal Address](/draft/specification/reference/#postal-address)         | No       | The billing address associated with this payment method.                                                                                                           |
| credential      | [Payment Credential](/draft/specification/reference/#payment-credential) | No       |                                                                                                                                                                    |

______________________________________________________________________

### Platform Fulfillment Config

| Name                 | Type    | Required | Description                         |
| -------------------- | ------- | -------- | ----------------------------------- |
| supports_multi_group | boolean | No       | Enables multiple groups per method. |

______________________________________________________________________

### Postal Address

| Name             | Type   | Required | Description                                                                                                                                                                                                                               |
| ---------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| extended_address | string | No       | An address extension such as an apartment number, C/O or alternative name.                                                                                                                                                                |
| street_address   | string | No       | The street address.                                                                                                                                                                                                                       |
| address_locality | string | No       | The locality in which the street address is, and which is in the region. For example, Mountain View.                                                                                                                                      |
| address_region   | string | No       | The region in which the locality is, and which is in the country. Required for applicable countries (i.e. state in US, province in CA). For example, California or another appropriate first-level Administrative division.               |
| address_country  | string | No       | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. |
| postal_code      | string | No       | The postal code. For example, 94043.                                                                                                                                                                                                      |
| first_name       | string | No       | Optional. First name of the contact associated with the address.                                                                                                                                                                          |
| last_name        | string | No       | Optional. Last name of the contact associated with the address.                                                                                                                                                                           |
| full_name        | string | No       | Optional. Full name of the contact associated with the address (if first_name or last_name fields are present they take precedence).                                                                                                      |
| phone_number     | string | No       | Optional. Phone number of the contact associated with the address.                                                                                                                                                                        |

______________________________________________________________________

### Retail Location Request

| Name    | Type                                                             | Required | Description                       |
| ------- | ---------------------------------------------------------------- | -------- | --------------------------------- |
| name    | string                                                           | **Yes**  | Location name (e.g., store name). |
| address | [Postal Address](/draft/specification/reference/#postal-address) | No       | Physical address of the location. |

______________________________________________________________________

### Retail Location Response

| Name    | Type                                                             | Required | Description                       |
| ------- | ---------------------------------------------------------------- | -------- | --------------------------------- |
| id      | string                                                           | **Yes**  | Unique location identifier.       |
| name    | string                                                           | **Yes**  | Location name (e.g., store name). |
| address | [Postal Address](/draft/specification/reference/#postal-address) | No       | Physical address of the location. |

______________________________________________________________________

### Shipping Destination Request

| Name             | Type   | Required | Description                                                                                                                                                                                                                               |
| ---------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| extended_address | string | No       | An address extension such as an apartment number, C/O or alternative name.                                                                                                                                                                |
| street_address   | string | No       | The street address.                                                                                                                                                                                                                       |
| address_locality | string | No       | The locality in which the street address is, and which is in the region. For example, Mountain View.                                                                                                                                      |
| address_region   | string | No       | The region in which the locality is, and which is in the country. Required for applicable countries (i.e. state in US, province in CA). For example, California or another appropriate first-level Administrative division.               |
| address_country  | string | No       | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. |
| postal_code      | string | No       | The postal code. For example, 94043.                                                                                                                                                                                                      |
| first_name       | string | No       | Optional. First name of the contact associated with the address.                                                                                                                                                                          |
| last_name        | string | No       | Optional. Last name of the contact associated with the address.                                                                                                                                                                           |
| full_name        | string | No       | Optional. Full name of the contact associated with the address (if first_name or last_name fields are present they take precedence).                                                                                                      |
| phone_number     | string | No       | Optional. Phone number of the contact associated with the address.                                                                                                                                                                        |
| id               | string | No       | ID specific to this shipping destination.                                                                                                                                                                                                 |

______________________________________________________________________

### Shipping Destination Response

| Name             | Type   | Required | Description                                                                                                                                                                                                                               |
| ---------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| extended_address | string | No       | An address extension such as an apartment number, C/O or alternative name.                                                                                                                                                                |
| street_address   | string | No       | The street address.                                                                                                                                                                                                                       |
| address_locality | string | No       | The locality in which the street address is, and which is in the region. For example, Mountain View.                                                                                                                                      |
| address_region   | string | No       | The region in which the locality is, and which is in the country. Required for applicable countries (i.e. state in US, province in CA). For example, California or another appropriate first-level Administrative division.               |
| address_country  | string | No       | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. |
| postal_code      | string | No       | The postal code. For example, 94043.                                                                                                                                                                                                      |
| first_name       | string | No       | Optional. First name of the contact associated with the address.                                                                                                                                                                          |
| last_name        | string | No       | Optional. Last name of the contact associated with the address.                                                                                                                                                                           |
| full_name        | string | No       | Optional. Full name of the contact associated with the address (if first_name or last_name fields are present they take precedence).                                                                                                      |
| phone_number     | string | No       | Optional. Phone number of the contact associated with the address.                                                                                                                                                                        |
| id               | string | **Yes**  | ID specific to this shipping destination.                                                                                                                                                                                                 |

______________________________________________________________________

### Token Credential Create Request

| Name  | Type   | Required | Description                                                                |
| ----- | ------ | -------- | -------------------------------------------------------------------------- |
| type  | string | **Yes**  | The specific type of token produced by the handler (e.g., 'stripe_token'). |
| token | string | **Yes**  | The token value.                                                           |

______________________________________________________________________

### Token Credential Update Request

| Name  | Type   | Required | Description                                                                |
| ----- | ------ | -------- | -------------------------------------------------------------------------- |
| type  | string | **Yes**  | The specific type of token produced by the handler (e.g., 'stripe_token'). |
| token | string | **Yes**  | The token value.                                                           |

______________________________________________________________________

### Token Credential Response

| Name | Type   | Required | Description                                                                |
| ---- | ------ | -------- | -------------------------------------------------------------------------- |
| type | string | **Yes**  | The specific type of token produced by the handler (e.g., 'stripe_token'). |

______________________________________________________________________

### Total Response

| Name         | Type    | Required | Description                                                                                                                   |
| ------------ | ------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| type         | string  | **Yes**  | Type of total categorization. **Enum:** `items_discount`, `subtotal`, `discount`, `fulfillment`, `tax`, `fee`, `total`        |
| display_text | string  | No       | Text to display against the amount. Should reflect appropriate method (e.g., 'Shipping', 'Delivery').                         |
| amount       | integer | **Yes**  | If type == total, sums subtotal - discount + fulfillment + tax + fee. Should be >= 0. Amount in minor (cents) currency units. |

______________________________________________________________________

## Extension Schemas

### AP2 Mandate Extension

#### Merchant Authorization

JWS Detached Content signature (RFC 7515 Appendix F) over the checkout response body (excluding ap2 field). Format: `<base64url-header>..<base64url-signature>`. The header MUST contain 'alg' (ES256/ES384/ES512) and 'kid' claims. The signature covers both the header and JCS-canonicalized checkout payload.

**Pattern:** `^[A-Za-z0-9_-]+\.\.[A-Za-z0-9_-]+$`

#### Checkout Mandate

SD-JWT+kb credential in `ap2.checkout_mandate`. Proving user authorization for the checkout. Contains the full checkout including `ap2.merchant_authorization`.

**Pattern:** `^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+(~[A-Za-z0-9_-]+)*$`

#### AP2 Checkout Response Object

| Name                   | Type                                                                             | Required | Description                                                |
| ---------------------- | -------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------- |
| merchant_authorization | [Merchant Authorization](/draft/specification/reference/#merchant-authorization) | **Yes**  | Merchant's signature proving checkout terms are authentic. |

#### AP2 Complete Request Object

| Name             | Type                                                                 | Required | Description                                      |
| ---------------- | -------------------------------------------------------------------- | -------- | ------------------------------------------------ |
| checkout_mandate | [Checkout Mandate](/draft/specification/reference/#checkout-mandate) | **Yes**  | SD-JWT+kb proving user authorized this checkout. |

#### AP2 Error Code

Error codes specific to AP2 mandate verification.

**Enum:** `mandate_required`, `agent_missing_key`, `mandate_invalid_signature`, `mandate_expired`, `mandate_scope_mismatch`, `merchant_authorization_invalid`, `merchant_authorization_missing`

#### Checkout with AP2 Mandate

| Name         | Type                                                                              | Required | Description                                                                                                                                                                                                                                                     |
| ------------ | --------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Checkout](/draft/specification/reference/#ucp-response-checkout)    | **Yes**  |                                                                                                                                                                                                                                                                 |
| id           | string                                                                            | **Yes**  | Unique identifier of the checkout session.                                                                                                                                                                                                                      |
| line_items   | Array\[[Line Item Response](/draft/specification/reference/#line-item-response)\] | **Yes**  | List of line items being checked out.                                                                                                                                                                                                                           |
| buyer        | [Buyer](/draft/specification/reference/#buyer)                                    | No       | Representation of the buyer.                                                                                                                                                                                                                                    |
| status       | string                                                                            | **Yes**  | Checkout state indicating the current phase and required action. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled` |
| currency     | string                                                                            | **Yes**  | ISO 4217 currency code.                                                                                                                                                                                                                                         |
| totals       | Array\[[Total Response](/draft/specification/reference/#total-response)\]         | **Yes**  | Different cart totals.                                                                                                                                                                                                                                          |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]                       | No       | List of messages with error and info about the checkout session state.                                                                                                                                                                                          |
| links        | Array\[[Link](/draft/specification/reference/#link)\]                             | **Yes**  | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                    |
| expires_at   | string                                                                            | No       | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                    |
| continue_url | string                                                                            | No       | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                 |
| payment      | [Payment Response](/draft/specification/reference/#payment-response)              | **Yes**  |                                                                                                                                                                                                                                                                 |
| order        | [Order Confirmation](/draft/specification/reference/#order-confirmation)          | No       | Details about an order created for this checkout session.                                                                                                                                                                                                       |
| ap2          | [Ap2 Checkout Response](/draft/specification/reference/#ap2-checkout-response)    | No       | AP2 extension data including merchant authorization.                                                                                                                                                                                                            |

#### Complete Checkout Request with AP2

| Name | Type                                                                         | Required | Description                                    |
| ---- | ---------------------------------------------------------------------------- | -------- | ---------------------------------------------- |
| ap2  | [Ap2 Complete Request](/draft/specification/reference/#ap2-complete-request) | No       | AP2 extension data including checkout mandate. |

______________________________________________________________________

### Buyer Consent Extension Create Request

#### Consent

| Name         | Type    | Required | Description                                       |
| ------------ | ------- | -------- | ------------------------------------------------- |
| analytics    | boolean | No       | Consent for analytics and performance tracking.   |
| preferences  | boolean | No       | Consent for storing user preferences.             |
| marketing    | boolean | No       | Consent for marketing communications.             |
| sale_of_data | boolean | No       | Consent for selling data to third parties (CCPA). |

#### Buyer with Consent Create Request

| Name         | Type                                               | Required | Description                                                                                       |
| ------------ | -------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------- |
| first_name   | string                                             | No       | First name of the buyer.                                                                          |
| last_name    | string                                             | No       | Last name of the buyer.                                                                           |
| full_name    | string                                             | No       | Optional, buyer's full name (if first_name or last_name fields are present they take precedence). |
| email        | string                                             | No       | Email of the buyer.                                                                               |
| phone_number | string                                             | No       | E.164 standard.                                                                                   |
| consent      | [Consent](/draft/specification/reference/#consent) | No       | Consent tracking fields.                                                                          |

#### Checkout with Buyer Consent Create Request

| Name       | Type                                                                                          | Required | Description                           |
| ---------- | --------------------------------------------------------------------------------------------- | -------- | ------------------------------------- |
| line_items | Array\[[Line Item Create Request](/draft/specification/reference/#line-item-create-request)\] | **Yes**  | List of line items being checked out. |
| buyer      | [Buyer](/draft/specification/reference/#buyer)                                                | No       | Buyer with consent tracking.          |
| currency   | string                                                                                        | **Yes**  | ISO 4217 currency code.               |
| payment    | [Payment Create Request](/draft/specification/reference/#payment-create-request)              | **Yes**  |                                       |

______________________________________________________________________

### Buyer Consent Extension Update Request

#### Consent

| Name         | Type    | Required | Description                                       |
| ------------ | ------- | -------- | ------------------------------------------------- |
| analytics    | boolean | No       | Consent for analytics and performance tracking.   |
| preferences  | boolean | No       | Consent for storing user preferences.             |
| marketing    | boolean | No       | Consent for marketing communications.             |
| sale_of_data | boolean | No       | Consent for selling data to third parties (CCPA). |

#### Buyer with Consent Update Request

| Name         | Type                                               | Required | Description                                                                                       |
| ------------ | -------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------- |
| first_name   | string                                             | No       | First name of the buyer.                                                                          |
| last_name    | string                                             | No       | Last name of the buyer.                                                                           |
| full_name    | string                                             | No       | Optional, buyer's full name (if first_name or last_name fields are present they take precedence). |
| email        | string                                             | No       | Email of the buyer.                                                                               |
| phone_number | string                                             | No       | E.164 standard.                                                                                   |
| consent      | [Consent](/draft/specification/reference/#consent) | No       | Consent tracking fields.                                                                          |

#### Checkout with Buyer Consent Update Request

| Name       | Type                                                                                          | Required | Description                                |
| ---------- | --------------------------------------------------------------------------------------------- | -------- | ------------------------------------------ |
| id         | string                                                                                        | **Yes**  | Unique identifier of the checkout session. |
| line_items | Array\[[Line Item Update Request](/draft/specification/reference/#line-item-update-request)\] | **Yes**  | List of line items being checked out.      |
| buyer      | [Buyer](/draft/specification/reference/#buyer)                                                | No       | Buyer with consent tracking.               |
| currency   | string                                                                                        | **Yes**  | ISO 4217 currency code.                    |
| payment    | [Payment Update Request](/draft/specification/reference/#payment-update-request)              | **Yes**  |                                            |

______________________________________________________________________

### Buyer Consent Extension Response

#### Consent

| Name         | Type    | Required | Description                                       |
| ------------ | ------- | -------- | ------------------------------------------------- |
| analytics    | boolean | No       | Consent for analytics and performance tracking.   |
| preferences  | boolean | No       | Consent for storing user preferences.             |
| marketing    | boolean | No       | Consent for marketing communications.             |
| sale_of_data | boolean | No       | Consent for selling data to third parties (CCPA). |

#### Buyer with Consent Response

| Name         | Type                                               | Required | Description                                                                                       |
| ------------ | -------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------- |
| first_name   | string                                             | No       | First name of the buyer.                                                                          |
| last_name    | string                                             | No       | Last name of the buyer.                                                                           |
| full_name    | string                                             | No       | Optional, buyer's full name (if first_name or last_name fields are present they take precedence). |
| email        | string                                             | No       | Email of the buyer.                                                                               |
| phone_number | string                                             | No       | E.164 standard.                                                                                   |
| consent      | [Consent](/draft/specification/reference/#consent) | No       | Consent tracking fields.                                                                          |

#### Checkout with Buyer Consent Response

| Name         | Type                                                                              | Required | Description                                                                                                                                                                                                                                                     |
| ------------ | --------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Checkout](/draft/specification/reference/#ucp-response-checkout)    | **Yes**  |                                                                                                                                                                                                                                                                 |
| id           | string                                                                            | **Yes**  | Unique identifier of the checkout session.                                                                                                                                                                                                                      |
| line_items   | Array\[[Line Item Response](/draft/specification/reference/#line-item-response)\] | **Yes**  | List of line items being checked out.                                                                                                                                                                                                                           |
| buyer        | [Buyer](/draft/specification/reference/#buyer)                                    | No       | Buyer with consent tracking.                                                                                                                                                                                                                                    |
| status       | string                                                                            | **Yes**  | Checkout state indicating the current phase and required action. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled` |
| currency     | string                                                                            | **Yes**  | ISO 4217 currency code.                                                                                                                                                                                                                                         |
| totals       | Array\[[Total Response](/draft/specification/reference/#total-response)\]         | **Yes**  | Different cart totals.                                                                                                                                                                                                                                          |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]                       | No       | List of messages with error and info about the checkout session state.                                                                                                                                                                                          |
| links        | Array\[[Link](/draft/specification/reference/#link)\]                             | **Yes**  | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                    |
| expires_at   | string                                                                            | No       | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                    |
| continue_url | string                                                                            | No       | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                 |
| payment      | [Payment Response](/draft/specification/reference/#payment-response)              | **Yes**  |                                                                                                                                                                                                                                                                 |
| order        | [Order Confirmation](/draft/specification/reference/#order-confirmation)          | No       | Details about an order created for this checkout session.                                                                                                                                                                                                       |

______________________________________________________________________

### Discount Extension Create Request

#### Allocation

| Name   | Type    | Required | Description                                                                       |
| ------ | ------- | -------- | --------------------------------------------------------------------------------- |
| path   | string  | **Yes**  | JSONPath to the allocation target (e.g., '$.line_items[0]', '$.totals.shipping'). |
| amount | integer | **Yes**  | Amount allocated to this target in minor (cents) currency units.                  |

#### Applied Discount

| Name        | Type                                                              | Required | Description                                                                                                                      |
| ----------- | ----------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| code        | string                                                            | No       | The discount code. Omitted for automatic discounts.                                                                              |
| title       | string                                                            | **Yes**  | Human-readable discount name (e.g., 'Summer Sale 20% Off').                                                                      |
| amount      | integer                                                           | **Yes**  | Total discount amount in minor (cents) currency units.                                                                           |
| automatic   | boolean                                                           | No       | True if applied automatically by merchant rules (no code required).                                                              |
| method      | string                                                            | No       | Allocation method. 'each' = applied independently per item. 'across' = split proportionally by value. **Enum:** `each`, `across` |
| priority    | integer                                                           | No       | Stacking order for discount calculation. Lower numbers applied first (1 = first).                                                |
| allocations | Array\[[Allocation](/draft/specification/reference/#allocation)\] | No       | Breakdown of where this discount was allocated. Sum of allocation amounts equals total amount.                                   |

#### Discounts Object

| Name    | Type                                                                          | Required | Description                                                                                                |
| ------- | ----------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| codes   | Array[string]                                                                 | No       | Discount codes to apply. Case-insensitive. Replaces previously submitted codes. Send empty array to clear. |
| applied | Array\[[Applied Discount](/draft/specification/reference/#applied-discount)\] | No       | Discounts successfully applied (code-based and automatic).                                                 |

#### Checkout with Discount Create Request

| Name       | Type                                                                                          | Required | Description                           |
| ---------- | --------------------------------------------------------------------------------------------- | -------- | ------------------------------------- |
| line_items | Array\[[Line Item Create Request](/draft/specification/reference/#line-item-create-request)\] | **Yes**  | List of line items being checked out. |
| buyer      | [Buyer](/draft/specification/reference/#buyer)                                                | No       | Representation of the buyer.          |
| currency   | string                                                                                        | **Yes**  | ISO 4217 currency code.               |
| payment    | [Payment Create Request](/draft/specification/reference/#payment-create-request)              | **Yes**  |                                       |
| discounts  | [Discounts Object](/draft/specification/reference/#discounts-object)                          | No       |                                       |

______________________________________________________________________

### Discount Extension Update Request

#### Allocation

| Name   | Type    | Required | Description                                                                       |
| ------ | ------- | -------- | --------------------------------------------------------------------------------- |
| path   | string  | **Yes**  | JSONPath to the allocation target (e.g., '$.line_items[0]', '$.totals.shipping'). |
| amount | integer | **Yes**  | Amount allocated to this target in minor (cents) currency units.                  |

#### Applied Discount

| Name        | Type                                                              | Required | Description                                                                                                                      |
| ----------- | ----------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| code        | string                                                            | No       | The discount code. Omitted for automatic discounts.                                                                              |
| title       | string                                                            | **Yes**  | Human-readable discount name (e.g., 'Summer Sale 20% Off').                                                                      |
| amount      | integer                                                           | **Yes**  | Total discount amount in minor (cents) currency units.                                                                           |
| automatic   | boolean                                                           | No       | True if applied automatically by merchant rules (no code required).                                                              |
| method      | string                                                            | No       | Allocation method. 'each' = applied independently per item. 'across' = split proportionally by value. **Enum:** `each`, `across` |
| priority    | integer                                                           | No       | Stacking order for discount calculation. Lower numbers applied first (1 = first).                                                |
| allocations | Array\[[Allocation](/draft/specification/reference/#allocation)\] | No       | Breakdown of where this discount was allocated. Sum of allocation amounts equals total amount.                                   |

#### Discounts Object

| Name    | Type                                                                          | Required | Description                                                                                                |
| ------- | ----------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| codes   | Array[string]                                                                 | No       | Discount codes to apply. Case-insensitive. Replaces previously submitted codes. Send empty array to clear. |
| applied | Array\[[Applied Discount](/draft/specification/reference/#applied-discount)\] | No       | Discounts successfully applied (code-based and automatic).                                                 |

#### Checkout with Discount Update Request

| Name       | Type                                                                                          | Required | Description                                |
| ---------- | --------------------------------------------------------------------------------------------- | -------- | ------------------------------------------ |
| id         | string                                                                                        | **Yes**  | Unique identifier of the checkout session. |
| line_items | Array\[[Line Item Update Request](/draft/specification/reference/#line-item-update-request)\] | **Yes**  | List of line items being checked out.      |
| buyer      | [Buyer](/draft/specification/reference/#buyer)                                                | No       | Representation of the buyer.               |
| currency   | string                                                                                        | **Yes**  | ISO 4217 currency code.                    |
| payment    | [Payment Update Request](/draft/specification/reference/#payment-update-request)              | **Yes**  |                                            |
| discounts  | [Discounts Object](/draft/specification/reference/#discounts-object)                          | No       |                                            |

______________________________________________________________________

### Discount Extension Response

#### Allocation

| Name   | Type    | Required | Description                                                                       |
| ------ | ------- | -------- | --------------------------------------------------------------------------------- |
| path   | string  | **Yes**  | JSONPath to the allocation target (e.g., '$.line_items[0]', '$.totals.shipping'). |
| amount | integer | **Yes**  | Amount allocated to this target in minor (cents) currency units.                  |

#### Applied Discount

| Name        | Type                                                              | Required | Description                                                                                                                      |
| ----------- | ----------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| code        | string                                                            | No       | The discount code. Omitted for automatic discounts.                                                                              |
| title       | string                                                            | **Yes**  | Human-readable discount name (e.g., 'Summer Sale 20% Off').                                                                      |
| amount      | integer                                                           | **Yes**  | Total discount amount in minor (cents) currency units.                                                                           |
| automatic   | boolean                                                           | No       | True if applied automatically by merchant rules (no code required).                                                              |
| method      | string                                                            | No       | Allocation method. 'each' = applied independently per item. 'across' = split proportionally by value. **Enum:** `each`, `across` |
| priority    | integer                                                           | No       | Stacking order for discount calculation. Lower numbers applied first (1 = first).                                                |
| allocations | Array\[[Allocation](/draft/specification/reference/#allocation)\] | No       | Breakdown of where this discount was allocated. Sum of allocation amounts equals total amount.                                   |

#### Discounts Object

| Name    | Type                                                                          | Required | Description                                                                                                |
| ------- | ----------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| codes   | Array[string]                                                                 | No       | Discount codes to apply. Case-insensitive. Replaces previously submitted codes. Send empty array to clear. |
| applied | Array\[[Applied Discount](/draft/specification/reference/#applied-discount)\] | No       | Discounts successfully applied (code-based and automatic).                                                 |

#### Checkout with Discount Response

| Name         | Type                                                                              | Required | Description                                                                                                                                                                                                                                                     |
| ------------ | --------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Checkout](/draft/specification/reference/#ucp-response-checkout)    | **Yes**  |                                                                                                                                                                                                                                                                 |
| id           | string                                                                            | **Yes**  | Unique identifier of the checkout session.                                                                                                                                                                                                                      |
| line_items   | Array\[[Line Item Response](/draft/specification/reference/#line-item-response)\] | **Yes**  | List of line items being checked out.                                                                                                                                                                                                                           |
| buyer        | [Buyer](/draft/specification/reference/#buyer)                                    | No       | Representation of the buyer.                                                                                                                                                                                                                                    |
| status       | string                                                                            | **Yes**  | Checkout state indicating the current phase and required action. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled` |
| currency     | string                                                                            | **Yes**  | ISO 4217 currency code.                                                                                                                                                                                                                                         |
| totals       | Array\[[Total Response](/draft/specification/reference/#total-response)\]         | **Yes**  | Different cart totals.                                                                                                                                                                                                                                          |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]                       | No       | List of messages with error and info about the checkout session state.                                                                                                                                                                                          |
| links        | Array\[[Link](/draft/specification/reference/#link)\]                             | **Yes**  | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                    |
| expires_at   | string                                                                            | No       | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                    |
| continue_url | string                                                                            | No       | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                 |
| payment      | [Payment Response](/draft/specification/reference/#payment-response)              | **Yes**  |                                                                                                                                                                                                                                                                 |
| order        | [Order Confirmation](/draft/specification/reference/#order-confirmation)          | No       | Details about an order created for this checkout session.                                                                                                                                                                                                       |
| discounts    | [Discounts Object](/draft/specification/reference/#discounts-object)              | No       |                                                                                                                                                                                                                                                                 |

______________________________________________________________________

### Fulfillment Extension Create Request

#### Fulfillment Option

A fulfillment option within a group (e.g., Standard Shipping $5, Express $15).

#### Fulfillment Group

| Name               | Type               | Required | Description                                           |
| ------------------ | ------------------ | -------- | ----------------------------------------------------- |
| selected_option_id | ['string', 'null'] | No       | ID of the selected fulfillment option for this group. |

#### Fulfillment Method

| Name                    | Type                                                                                                          | Required | Description                                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| type                    | string                                                                                                        | **Yes**  | Fulfillment method type. **Enum:** `shipping`, `pickup`                                                      |
| line_item_ids           | Array[string]                                                                                                 | No       | Line item IDs fulfilled via this method.                                                                     |
| destinations            | Array\[[Fulfillment Destination Request](/draft/specification/reference/#fulfillment-destination-request)\]   | No       | Available destinations. For shipping: addresses. For pickup: retail locations.                               |
| selected_destination_id | ['string', 'null']                                                                                            | No       | ID of the selected destination.                                                                              |
| groups                  | Array\[[Fulfillment Group Create Request](/draft/specification/reference/#fulfillment-group-create-request)\] | No       | Fulfillment groups for selecting options. Agent sets selected_option_id on groups to choose shipping method. |

#### Fulfillment Available Method

Inventory availability hint for a fulfillment method type.

#### Fulfillment

| Name    | Type                                                                                                            | Required | Description                         |
| ------- | --------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------- |
| methods | Array\[[Fulfillment Method Create Request](/draft/specification/reference/#fulfillment-method-create-request)\] | No       | Fulfillment methods for cart items. |

#### Checkout with Fulfillment Create Request

| Name        | Type                                                                                          | Required | Description                           |
| ----------- | --------------------------------------------------------------------------------------------- | -------- | ------------------------------------- |
| line_items  | Array\[[Line Item Create Request](/draft/specification/reference/#line-item-create-request)\] | **Yes**  | List of line items being checked out. |
| buyer       | [Buyer](/draft/specification/reference/#buyer)                                                | No       | Representation of the buyer.          |
| currency    | string                                                                                        | **Yes**  | ISO 4217 currency code.               |
| payment     | [Payment Create Request](/draft/specification/reference/#payment-create-request)              | **Yes**  |                                       |
| fulfillment | [Fulfillment](/draft/specification/reference/#fulfillment)                                    | No       | Fulfillment details.                  |

______________________________________________________________________

### Fulfillment Extension Update Request

#### Fulfillment Option

A fulfillment option within a group (e.g., Standard Shipping $5, Express $15).

#### Fulfillment Group

| Name               | Type               | Required | Description                                                            |
| ------------------ | ------------------ | -------- | ---------------------------------------------------------------------- |
| id                 | string             | **Yes**  | Group identifier for referencing merchant-generated groups in updates. |
| selected_option_id | ['string', 'null'] | No       | ID of the selected fulfillment option for this group.                  |

#### Fulfillment Method

| Name                    | Type                                                                                                          | Required | Description                                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| id                      | string                                                                                                        | **Yes**  | Unique fulfillment method identifier.                                                                        |
| line_item_ids           | Array[string]                                                                                                 | **Yes**  | Line item IDs fulfilled via this method.                                                                     |
| destinations            | Array\[[Fulfillment Destination Request](/draft/specification/reference/#fulfillment-destination-request)\]   | No       | Available destinations. For shipping: addresses. For pickup: retail locations.                               |
| selected_destination_id | ['string', 'null']                                                                                            | No       | ID of the selected destination.                                                                              |
| groups                  | Array\[[Fulfillment Group Update Request](/draft/specification/reference/#fulfillment-group-update-request)\] | No       | Fulfillment groups for selecting options. Agent sets selected_option_id on groups to choose shipping method. |

#### Fulfillment Available Method

Inventory availability hint for a fulfillment method type.

#### Fulfillment

| Name    | Type                                                                                                            | Required | Description                         |
| ------- | --------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------- |
| methods | Array\[[Fulfillment Method Create Request](/draft/specification/reference/#fulfillment-method-create-request)\] | No       | Fulfillment methods for cart items. |

#### Checkout with Fulfillment Update Request

| Name        | Type                                                                                          | Required | Description                                |
| ----------- | --------------------------------------------------------------------------------------------- | -------- | ------------------------------------------ |
| id          | string                                                                                        | **Yes**  | Unique identifier of the checkout session. |
| line_items  | Array\[[Line Item Update Request](/draft/specification/reference/#line-item-update-request)\] | **Yes**  | List of line items being checked out.      |
| buyer       | [Buyer](/draft/specification/reference/#buyer)                                                | No       | Representation of the buyer.               |
| currency    | string                                                                                        | **Yes**  | ISO 4217 currency code.                    |
| payment     | [Payment Update Request](/draft/specification/reference/#payment-update-request)              | **Yes**  |                                            |
| fulfillment | [Fulfillment](/draft/specification/reference/#fulfillment)                                    | No       | Fulfillment details.                       |

______________________________________________________________________

### Fulfillment Extension Response

#### Fulfillment Option

| Name                      | Type                                                                      | Required | Description                                                                |
| ------------------------- | ------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------- |
| id                        | string                                                                    | **Yes**  | Unique fulfillment option identifier.                                      |
| title                     | string                                                                    | **Yes**  | Short label (e.g., 'Express Shipping', 'Curbside Pickup').                 |
| description               | string                                                                    | No       | Complete context for buyer decision (e.g., 'Arrives Dec 12-15 via FedEx'). |
| carrier                   | string                                                                    | No       | Carrier name (for shipping).                                               |
| earliest_fulfillment_time | string                                                                    | No       | Earliest fulfillment date.                                                 |
| latest_fulfillment_time   | string                                                                    | No       | Latest fulfillment date.                                                   |
| totals                    | Array\[[Total Response](/draft/specification/reference/#total-response)\] | **Yes**  | Fulfillment option totals breakdown.                                       |

#### Fulfillment Group

| Name               | Type                                                                                                | Required | Description                                                            |
| ------------------ | --------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------- |
| id                 | string                                                                                              | **Yes**  | Group identifier for referencing merchant-generated groups in updates. |
| line_item_ids      | Array[string]                                                                                       | **Yes**  | Line item IDs included in this group/package.                          |
| options            | Array\[[Fulfillment Option Response](/draft/specification/reference/#fulfillment-option-response)\] | No       | Available fulfillment options for this group.                          |
| selected_option_id | ['string', 'null']                                                                                  | No       | ID of the selected fulfillment option for this group.                  |

#### Fulfillment Method

| Name                    | Type                                                                                                          | Required | Description                                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| id                      | string                                                                                                        | **Yes**  | Unique fulfillment method identifier.                                                                        |
| type                    | string                                                                                                        | **Yes**  | Fulfillment method type. **Enum:** `shipping`, `pickup`                                                      |
| line_item_ids           | Array[string]                                                                                                 | **Yes**  | Line item IDs fulfilled via this method.                                                                     |
| destinations            | Array\[[Fulfillment Destination Response](/draft/specification/reference/#fulfillment-destination-response)\] | No       | Available destinations. For shipping: addresses. For pickup: retail locations.                               |
| selected_destination_id | ['string', 'null']                                                                                            | No       | ID of the selected destination.                                                                              |
| groups                  | Array\[[Fulfillment Group Response](/draft/specification/reference/#fulfillment-group-response)\]             | No       | Fulfillment groups for selecting options. Agent sets selected_option_id on groups to choose shipping method. |

#### Fulfillment Available Method

| Name           | Type               | Required | Description                                                                              |
| -------------- | ------------------ | -------- | ---------------------------------------------------------------------------------------- |
| type           | string             | **Yes**  | Fulfillment method type this availability applies to. **Enum:** `shipping`, `pickup`     |
| line_item_ids  | Array[string]      | **Yes**  | Line items available for this fulfillment method.                                        |
| fulfillable_on | ['string', 'null'] | No       | 'now' for immediate availability, or ISO 8601 date for future (preorders, transfers).    |
| description    | string             | No       | Human-readable availability info (e.g., 'Available for pickup at Downtown Store today'). |

#### Fulfillment

| Name              | Type                                                                                                                    | Required | Description                         |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------- |
| methods           | Array\[[Fulfillment Method Response](/draft/specification/reference/#fulfillment-method-response)\]                     | No       | Fulfillment methods for cart items. |
| available_methods | Array\[[Fulfillment Available Method Response](/draft/specification/reference/#fulfillment-available-method-response)\] | No       | Inventory availability hints.       |

#### Checkout with Fulfillment Response

| Name         | Type                                                                              | Required | Description                                                                                                                                                                                                                                                     |
| ------------ | --------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp          | [UCP Response Checkout](/draft/specification/reference/#ucp-response-checkout)    | **Yes**  |                                                                                                                                                                                                                                                                 |
| id           | string                                                                            | **Yes**  | Unique identifier of the checkout session.                                                                                                                                                                                                                      |
| line_items   | Array\[[Line Item Response](/draft/specification/reference/#line-item-response)\] | **Yes**  | List of line items being checked out.                                                                                                                                                                                                                           |
| buyer        | [Buyer](/draft/specification/reference/#buyer)                                    | No       | Representation of the buyer.                                                                                                                                                                                                                                    |
| status       | string                                                                            | **Yes**  | Checkout state indicating the current phase and required action. See Checkout Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled` |
| currency     | string                                                                            | **Yes**  | ISO 4217 currency code.                                                                                                                                                                                                                                         |
| totals       | Array\[[Total Response](/draft/specification/reference/#total-response)\]         | **Yes**  | Different cart totals.                                                                                                                                                                                                                                          |
| messages     | Array\[[Message](/draft/specification/reference/#message)\]                       | No       | List of messages with error and info about the checkout session state.                                                                                                                                                                                          |
| links        | Array\[[Link](/draft/specification/reference/#link)\]                             | **Yes**  | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                    |
| expires_at   | string                                                                            | No       | RFC 3339 expiry timestamp. Default TTL is 6 hours from creation if not sent.                                                                                                                                                                                    |
| continue_url | string                                                                            | No       | URL for checkout handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                 |
| payment      | [Payment Response](/draft/specification/reference/#payment-response)              | **Yes**  |                                                                                                                                                                                                                                                                 |
| order        | [Order Confirmation](/draft/specification/reference/#order-confirmation)          | No       | Details about an order created for this checkout session.                                                                                                                                                                                                       |
| fulfillment  | [Fulfillment](/draft/specification/reference/#fulfillment)                        | No       | Fulfillment details.                                                                                                                                                                                                                                            |

______________________________________________________________________

## UCP Metadata

The following schemas define the structure of UCP metadata used in discovery and responses.

### Discovery Profile

The top-level structure of a discovery document (`/.well-known/ucp`).

| Name         | Type                                                            | Required | Description                                |
| ------------ | --------------------------------------------------------------- | -------- | ------------------------------------------ |
| version      | string                                                          | **Yes**  | UCP protocol version in YYYY-MM-DD format. |
| services     | [Services](/draft/specification/reference/#services)            | **Yes**  |                                            |
| capabilities | Array\[[Discovery](/draft/specification/reference/#discovery)\] | **Yes**  | Supported capabilities and extensions.     |

### Checkout Response Metadata

The `ucp` object included in checkout responses.

| Name         | Type                                                          | Required | Description                                |
| ------------ | ------------------------------------------------------------- | -------- | ------------------------------------------ |
| version      | string                                                        | **Yes**  | UCP protocol version in YYYY-MM-DD format. |
| capabilities | Array\[[Response](/draft/specification/reference/#response)\] | **Yes**  | Active capabilities for this response.     |

### Order Response Metadata

The `ucp` object included in order responses or events.

| Name         | Type                                                          | Required | Description                                |
| ------------ | ------------------------------------------------------------- | -------- | ------------------------------------------ |
| version      | string                                                        | **Yes**  | UCP protocol version in YYYY-MM-DD format. |
| capabilities | Array\[[Response](/draft/specification/reference/#response)\] | **Yes**  | Active capabilities for this response.     |

### Capability

This object describes a single capability or extension. It appears in the `capabilities` array in discovery profiles and responses, with slightly different required fields in each context.

#### Capability (Discovery)

As seen in discovery profiles.

| Name    | Type   | Required | Description                                                                                                                |
| ------- | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------- |
| name    | string | **Yes**  | Stable capability identifier in reverse-domain notation (e.g., dev.ucp.shopping.checkout). Used in capability negotiation. |
| version | string | **Yes**  | Capability version in YYYY-MM-DD format.                                                                                   |
| spec    | string | **Yes**  | URL to human-readable specification document.                                                                              |
| schema  | string | **Yes**  | URL to JSON Schema for this capability's payload.                                                                          |
| extends | string | No       | Parent capability this extends. Present for extensions, absent for root capabilities.                                      |
| config  | object | No       | Capability-specific configuration (structure defined by each capability).                                                  |

#### Capability (Response)

As seen in response messages.

| Name    | Type   | Required | Description                                                                                                                |
| ------- | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------- |
| name    | string | **Yes**  | Stable capability identifier in reverse-domain notation (e.g., dev.ucp.shopping.checkout). Used in capability negotiation. |
| version | string | **Yes**  | Capability version in YYYY-MM-DD format.                                                                                   |
| spec    | string | No       | URL to human-readable specification document.                                                                              |
| schema  | string | No       | URL to JSON Schema for this capability's payload.                                                                          |
| extends | string | No       | Parent capability this extends. Present for extensions, absent for root capabilities.                                      |
| config  | object | No       | Capability-specific configuration (structure defined by each capability).                                                  |
