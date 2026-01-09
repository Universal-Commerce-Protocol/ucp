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

# UCP playground

<div class="playgroundHero">
  <p>
    Walk through a complete UCP checkout flow step-by-step. This interactive demo runs entirely in the browser, simulating payloads and validating against real UCP schemas at each stage.
  </p>
</div>

<div class="page">
  <!-- Step Navigation -->
  <div class="stepper" id="stepper">
    <button class="step isActive" data-step="profiles">
      <span class="stepNumber">1</span>Profiles
    </button>
    <button class="step" data-step="discovery">
      <span class="stepNumber">2</span>Discovery
    </button>
    <button class="step" data-step="negotiation">
      <span class="stepNumber">3</span>Negotiation
    </button>
    <button class="step" data-step="createCheckout">
      <span class="stepNumber">4</span>Create checkout
    </button>
    <button class="step" data-step="mintInstrument">
      <span class="stepNumber">5</span>Mint instrument
    </button>
    <button class="step" data-step="updateCheckout">
      <span class="stepNumber">6</span>Update checkout
    </button>
    <button class="step" data-step="completeCheckout">
      <span class="stepNumber">7</span>Complete checkout
    </button>
    <button class="step" data-step="order">
      <span class="stepNumber">8</span>Order events
    </button>
  </div>

  <!-- Step Content -->
  <div id="playground-content">
    <!-- Profiles Step -->
    <section class="playgroundSection" id="step-profiles">
      <h2 class="sectionTitle">Choose an agent profile</h2>
      <p class="sectionDescription">
        In the real spec, agents advertise a profile URI and merchants fetch/cache it. Here we model it directly so you can see how the negotiated capability set changes.
      </p>
      <div class="twoCol">
        <div class="card">
          <h3 class="cardTitle">Agent profile</h3>
          <label>
            Select agent type
            <select id="agent-select">
              <option value="basic">Basic agent (core only)</option>
              <option value="full">Full agent (extensions enabled)</option>
            </select>
          </label>
          <p class="cardBody" id="agent-description">Checkout + Order only. No extensions.</p>
        </div>
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Agent capabilities</span>
            <button class="chip chipCopy" onclick="copyJson('agent-capabilities', this)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="agent-capabilities"></pre>
        </div>
      </div>
      <div class="stepperActions">
        <button class="button buttonDark" onclick="goToStep('discovery')">Continue to Discovery →</button>
      </div>
    </section>

    <!-- Discovery Step -->
    <section class="playgroundSection hidden" id="step-discovery">
      <h2 class="sectionTitle">Discovery</h2>
      <p class="sectionDescription">
        In the protocol, this would be <code>GET /.well-known/ucp</code>. In the static playground, we generate the merchant profile locally.
      </p>
      <div class="playgroundGrid">
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Request</span>
            <button class="chip chipCopy" onclick="copyJson('discovery-request', this)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="discovery-request"></pre>
        </div>
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Response</span>
            <button class="chip chipCopy" onclick="copyJson('discovery-response', this)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="discovery-response"></pre>
        </div>
      </div>
      <div class="stepperActions">
        <button class="button buttonGhost" onclick="goToStep('profiles')">← Back</button>
        <button class="button buttonDark" onclick="goToStep('negotiation')">Continue to Negotiation →</button>
      </div>
    </section>

    <!-- Negotiation Step -->
    <section class="playgroundSection hidden" id="step-negotiation">
      <h2 class="sectionTitle">Capability negotiation</h2>
      <p class="sectionDescription">
        The merchant activates only capabilities supported by both sides and prunes orphaned extensions (those whose <code>extends</code> parent is not active).
      </p>
      <div class="twoCol">
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Merchant capabilities</span>
            <button class="chip chipCopy" onclick="copyJson('merchant-capabilities', this)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="merchant-capabilities"></pre>
        </div>
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Active capabilities (intersection)</span>
            <button class="chip chipCopy" onclick="copyJson('active-capabilities', this)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="active-capabilities"></pre>
        </div>
      </div>
      <div class="stepperActions">
        <button class="button buttonGhost" onclick="goToStep('discovery')">← Back</button>
        <button class="button buttonDark" onclick="doCreateCheckout()">Create Checkout →</button>
      </div>
    </section>

    <!-- Create Checkout Step -->
    <section class="playgroundSection hidden" id="step-createCheckout">
      <h2 class="sectionTitle">Create checkout</h2>
      <p class="sectionDescription">
        The platform creates a checkout session. The merchant responds with the canonical checkout representation and messages indicating what's missing (e.g., payment instruments).
      </p>
      <div class="playgroundGrid">
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Create request</span>
            <div class="jsonPanelActions">
              <button class="chip chipCopy" onclick="copyJson('create-request', this)">Copy</button>
              <button class="chip chipRun" id="btn-create-run" onclick="runWithFeedback('btn-create-run', doCreateCheckout)">▶ Run</button>
            </div>
          </div>
          <pre class="jsonPanelBody" id="create-request"></pre>
        </div>
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Create response</span>
            <div class="jsonPanelActions">
              <button class="chip chipCopy" onclick="copyJson('create-response', this)">Copy</button>
            </div>
          </div>
          <pre class="jsonPanelBody" id="create-response"></pre>
        </div>
      </div>
      <div class="playgroundGrid playgroundGrid--top hidden" style="margin-top: 16px;" id="create-validation-row">
        <div class="jsonPanel jsonPanel--collapsed" id="create-req-validation-panel">
          <div class="jsonPanelHeader validationPanelHeader">
            <span class="jsonPanelTitle"><span class="md-nav__icon md-icon toggleIcon"></span> Schema validation: request</span>
            <button class="chip chipGhost buttonCompact" onclick="copyValidation(this, 'create-req-validation', event)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="create-req-validation"></pre>
        </div>
        <div class="jsonPanel jsonPanel--collapsed" id="create-resp-validation-panel">
          <div class="jsonPanelHeader validationPanelHeader">
            <span class="jsonPanelTitle"><span class="md-nav__icon md-icon toggleIcon"></span> Schema validation: response</span>
            <button class="chip chipGhost buttonCompact" onclick="copyValidation(this, 'create-resp-validation', event)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="create-resp-validation"></pre>
        </div>
      </div>
      <div class="stepperActions">
        <button class="button buttonGhost" onclick="goToStep('negotiation')">← Back</button>
        <button class="button buttonDark" id="btn-to-mint" disabled onclick="goToStep('mintInstrument')">Next: Mint instrument →</button>
      </div>
    </section>

    <!-- Mint Instrument Step -->
    <section class="playgroundSection hidden" id="step-mintInstrument">
      <h2 class="sectionTitle">Mint a payment instrument</h2>
      <p class="sectionDescription">
        Choose a payment handler and mint an instrument that conforms to that handler's instrument schema. This step simulates CP/PSP token acquisition.
      </p>
      <div class="twoCol">
        <div class="card">
          <h3 class="cardTitle">Handler selection</h3>
          <label>
            Payment handler
            <select id="handler-select">
              <option value="shop_pay">shop_pay (com.shopify.shop_pay)</option>
            </select>
          </label>
          <p class="cardBody">Instrument schema: <code>https://shopify.dev/ucp/handlers/shop_pay/instrument.json</code></p>
          <button class="button buttonPrimary buttonCompact" style="margin-top: 16px;" onclick="doMintInstrument()">▶ Run</button>
        </div>
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Minted instrument</span>
            <button class="chip chipCopy" onclick="copyJson('minted-instrument', this)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="minted-instrument"></pre>
        </div>
      </div>
      <div class="twoCol twoCol--top hidden" style="margin-top: 16px;" id="instrument-validation-row">
        <div class="jsonPanel jsonPanel--collapsed" id="instrument-validation-panel">
          <div class="jsonPanelHeader validationPanelHeader">
            <span class="jsonPanelTitle"><span class="md-nav__icon md-icon toggleIcon"></span> Schema validation: instrument</span>
            <button class="chip chipGhost buttonCompact" onclick="copyValidation(this, 'instrument-validation', event)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="instrument-validation"></pre>
        </div>
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Checkout ID</span>
            <button class="chip chipCopy" onclick="copyJson('checkout-id-display', this)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="checkout-id-display"></pre>
        </div>
      </div>
      <div class="stepperActions">
        <button class="button buttonGhost" onclick="goToStep('createCheckout')">← Back</button>
        <button class="button buttonDark" id="btn-to-update" disabled onclick="doUpdateCheckout()">Update checkout →</button>
      </div>
    </section>

    <!-- Update Checkout Step -->
    <section class="playgroundSection hidden" id="step-updateCheckout">
      <h2 class="sectionTitle">Update checkout</h2>
      <p class="sectionDescription">
        Update replaces the checkout resource. Here we attach <code>payment.instruments</code> and set <code>payment.selected_instrument_id</code>.
      </p>
      <div class="playgroundGrid">
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Update request</span>
            <div class="jsonPanelActions">
              <button class="chip chipCopy" onclick="copyJson('update-request', this)">Copy</button>
              <button class="chip chipRun" id="btn-run-update" onclick="runWithFeedback('btn-run-update', doUpdateCheckout)">▶ Run</button>
            </div>
          </div>
          <pre class="jsonPanelBody" id="update-request"></pre>
        </div>
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Update response</span>
            <div class="jsonPanelActions">
              <button class="chip chipCopy" onclick="copyJson('update-response', this)">Copy</button>
            </div>
          </div>
          <pre class="jsonPanelBody" id="update-response"></pre>
        </div>
      </div>
      <div class="playgroundGrid playgroundGrid--top hidden" style="margin-top: 16px;" id="update-validation-row">
        <div class="jsonPanel jsonPanel--collapsed" id="update-req-validation-panel">
          <div class="jsonPanelHeader validationPanelHeader">
            <span class="jsonPanelTitle"><span class="md-nav__icon md-icon toggleIcon"></span> Schema validation: request</span>
            <button class="chip chipGhost buttonCompact" onclick="copyValidation(this, 'update-req-validation', event)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="update-req-validation"></pre>
        </div>
        <div class="jsonPanel jsonPanel--collapsed" id="update-resp-validation-panel">
          <div class="jsonPanelHeader validationPanelHeader">
            <span class="jsonPanelTitle"><span class="md-nav__icon md-icon toggleIcon"></span> Schema validation: response</span>
            <button class="chip chipGhost buttonCompact" onclick="copyValidation(this, 'update-resp-validation', event)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="update-resp-validation"></pre>
        </div>
      </div>
      <div class="stepperActions">
        <button class="button buttonGhost" onclick="goToStep('mintInstrument')">← Back</button>
        <button class="button buttonDark" id="btn-to-complete" disabled onclick="doCompleteCheckout()">Complete checkout →</button>
      </div>
    </section>

    <!-- Complete Checkout Step -->
    <section class="playgroundSection hidden" id="step-completeCheckout">
      <h2 class="sectionTitle">Complete checkout</h2>
      <p class="sectionDescription">
        Completion submits the selected instrument for processing. In this static demo, we validate the instrument shape and then create an order locally.
      </p>
      <div class="playgroundGrid">
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Complete request</span>
            <div class="jsonPanelActions">
              <button class="chip chipCopy" onclick="copyJson('complete-request', this)">Copy</button>
              <button class="chip chipRun" id="btn-run-complete" onclick="runWithFeedback('btn-run-complete', doCompleteCheckout)">▶ Run</button>
            </div>
          </div>
          <pre class="jsonPanelBody" id="complete-request"></pre>
        </div>
        <div class="jsonPanel">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Complete response</span>
            <div class="jsonPanelActions">
              <button class="chip chipCopy" onclick="copyJson('complete-response', this)">Copy</button>
            </div>
          </div>
          <pre class="jsonPanelBody" id="complete-response"></pre>
        </div>
      </div>
      <div class="callout callout--tip">
        <div class="calloutTitle">Next step</div>
        <div class="calloutBody">When you have an <code>order_id</code>, inspect the order representation and simulate lifecycle events (shipped/delivered).</div>
      </div>
      <div class="stepperActions">
        <button class="button buttonGhost" onclick="goToStep('updateCheckout')">← Back</button>
        <button class="button buttonDark" id="btn-to-order" disabled onclick="goToStep('order')">View order →</button>
      </div>
    </section>

    <!-- Order Events Step -->
    <section class="playgroundSection hidden" id="step-order">
      <h2 class="sectionTitle">Order events</h2>
      <p class="sectionDescription">
        Post-purchase updates are communicated as events/webhooks. Here we simulate a few representative events and update the order representation.
      </p>
      <div class="playgroundGrid playgroundGrid--top">
        <div class="jsonPanel" style="max-height: 600px;">
          <div class="jsonPanelHeader">
            <span class="jsonPanelTitle">Order (with events)</span>
            <button class="chip chipGhost buttonCompact" onclick="copyToClipboard(this, 'order-display', event)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="order-display" style="max-height: 540px;"></pre>
        </div>
        <div class="jsonPanel jsonPanel--collapsed hidden" id="order-validation-panel">
          <div class="jsonPanelHeader validationPanelHeader">
            <span class="jsonPanelTitle"><span class="md-nav__icon md-icon toggleIcon"></span> Schema validation: order</span>
            <button class="chip chipGhost buttonCompact" onclick="copyValidation(this, 'order-validation', event)">Copy</button>
          </div>
          <pre class="jsonPanelBody" id="order-validation"></pre>
        </div>
      </div>
      <div class="stepperActions">
        <button class="button buttonGhost" onclick="goToStep('completeCheckout')">← Back</button>
        <button class="button buttonDark" onclick="simulateEvent('shipped')">Simulate shipped</button>
        <button class="button buttonDark" onclick="simulateEvent('delivered')">Simulate delivered</button>
      </div>
    </section>
  </div>

  <!-- About callout -->
  <div class="callout" style="margin-top: 48px;">
    <div class="calloutTitle">About this demo</div>
    <div class="calloutBody">This playground runs entirely client-side. The "merchant" logic is simulated locally, demonstrating the UCP protocol flow without requiring a live backend.</div>
  </div>
</div>

<script>
(function() {
  // Agent profiles
  const AGENTS = {
    basic: {
      label: "Basic agent (core only)",
      description: "Checkout + Order only. No extensions.",
      capabilities: [
        { name: "dev.ucp.shopping.checkout", version: "2026-01-11" },
        { name: "dev.ucp.shopping.order", version: "2026-01-11" }
      ]
    },
    full: {
      label: "Full agent (extensions enabled)",
      description: "Checkout + Order + common shopping extensions (fulfillment/discount/buyer consent/refund/return/dispute).",
      capabilities: [
        { name: "dev.ucp.shopping.checkout", version: "2026-01-11" },
        { name: "dev.ucp.shopping.order", version: "2026-01-11" },
        { name: "dev.ucp.shopping.fulfillment", version: "2026-01-11", extends: "dev.ucp.shopping.checkout" },
        { name: "dev.ucp.shopping.discount", version: "2026-01-11", extends: "dev.ucp.shopping.checkout" },
        { name: "dev.ucp.shopping.buyer_consent", version: "2026-01-11", extends: "dev.ucp.shopping.checkout" },
        { name: "dev.ucp.shopping.refund", version: "2026-01-11", extends: "dev.ucp.shopping.order" },
        { name: "dev.ucp.shopping.return", version: "2026-01-11", extends: "dev.ucp.shopping.order" },
        { name: "dev.ucp.shopping.dispute", version: "2026-01-11", extends: "dev.ucp.shopping.order" }
      ]
    }
  };

  // Merchant profile
  const VERSION = "2026-01-11";
  function buildMerchantProfile() {
    const origin = window.location.origin;
    return {
      ucp: {
        version: VERSION,
        services: {
          "dev.ucp.shopping": {
            version: VERSION,
            spec: "https://ucp.dev/specs/shopping",
            rest: { schema: "https://ucp.dev/services/shopping/openapi.json", endpoint: origin + "/ucp/v1" },
            mcp: { schema: "https://ucp.dev/services/shopping/openrpc.json", endpoint: origin + "/ucp/mcp" }
          }
        },
        capabilities: [
          { name: "dev.ucp.shopping.checkout", version: VERSION },
          { name: "dev.ucp.shopping.order", version: VERSION },
          { name: "dev.ucp.shopping.fulfillment", version: VERSION, extends: "dev.ucp.shopping.checkout" },
          { name: "dev.ucp.shopping.discount", version: VERSION, extends: "dev.ucp.shopping.checkout" },
          { name: "dev.ucp.shopping.buyer_consent", version: VERSION, extends: "dev.ucp.shopping.checkout" },
          { name: "dev.ucp.shopping.refund", version: VERSION, extends: "dev.ucp.shopping.order" },
          { name: "dev.ucp.shopping.return", version: VERSION, extends: "dev.ucp.shopping.order" },
          { name: "dev.ucp.shopping.dispute", version: VERSION, extends: "dev.ucp.shopping.order" }
        ]
      },
      payment: {
        handlers: [{
          id: "shop_pay",
          name: "com.shopify.shop_pay",
          version: "2025-12-08",
          spec: "https://shopify.dev/ucp/shop_pay",
          config_schema: "https://shopify.dev/ucp/handlers/shop_pay/config.json",
          instrument_schemas: ["https://shopify.dev/ucp/handlers/shop_pay/instrument.json"],
          config: { shop_id: "shopify-559128571" }
        }]
      }
    };
  }

  // State
  let currentStep = 'profiles';
  let selectedAgentId = 'basic';
  let merchantProfile = buildMerchantProfile();
  let activeCaps = [];
  let checkoutId = null;
  let checkoutResp = null;
  let instrument = null;
  let updateResp = null;
  let orderId = null;
  let orderState = null;

  // Track whether Run has been clicked for each step
  let createRunClicked = false;
  let mintRunClicked = false;
  let updateRunClicked = false;

  // Helpers
  function uuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  function nowIso() { return new Date().toISOString(); }
  function in6HoursIso() { const d = new Date(); d.setHours(d.getHours() + 6); return d.toISOString(); }

  function formatJson(obj) {
    return JSON.stringify(obj, null, 2);
  }

  function setJson(id, obj) {
    const el = document.getElementById(id);
    if (el) el.textContent = formatJson(obj);
  }

  // Capability negotiation
  function negotiate(agentCaps, merchantCaps) {
    let active = merchantCaps.filter(m => agentCaps.some(a => a.name === m.name));
    let changed = true;
    while (changed) {
      changed = false;
      const names = new Set(active.map(c => c.name));
      const next = active.filter(c => !c.extends || names.has(c.extends));
      if (next.length !== active.length) changed = true;
      active = next;
    }
    return active;
  }

  // Copy JSON to clipboard
  window.copyJson = function(elementId, btn) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.textContent;
    navigator.clipboard.writeText(text).then(() => {
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      btn.classList.add('chipCopied');
      setTimeout(() => {
        btn.textContent = originalText;
        btn.classList.remove('chipCopied');
      }, 1500);
    });
  };

  // Copy to clipboard (generic, stops propagation)
  window.copyToClipboard = function(btn, elementId, event) {
    if (event) event.stopPropagation();
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.textContent;
    navigator.clipboard.writeText(text).then(() => {
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      btn.classList.add('chipCopied');
      setTimeout(() => {
        btn.textContent = originalText;
        btn.classList.remove('chipCopied');
      }, 1500);
    });
  };

  // Copy validation panel content (stops propagation to avoid toggling panel)
  window.copyValidation = function(btn, elementId, event) {
    if (event) event.stopPropagation();
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.textContent;
    navigator.clipboard.writeText(text).then(() => {
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      btn.classList.add('chipCopied');
      setTimeout(() => {
        btn.textContent = originalText;
        btn.classList.remove('chipCopied');
      }, 1500);
    });
  };

  // Run with "Running..." feedback
  window.runWithFeedback = function(btnId, action) {
    const btn = document.getElementById(btnId);
    if (!btn) {
      action();
      return;
    }
    const originalText = btn.textContent;
    btn.textContent = '▶ Running...';
    btn.disabled = true;
    setTimeout(() => {
      action();
      btn.textContent = originalText;
      btn.disabled = false;
    }, 400);
  };

  // Simulate validation (in real impl, this would use AJV against UCP schemas)
  function simulateValidation(schemaId, data) {
    // For this demo, we simulate successful validation
    return { ok: true, schemaId: schemaId };
  }

  // Show/hide element helpers
  function showElement(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
  }

  function hideElement(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  }

  // Step navigation
  window.goToStep = function(step, fromRunAction) {
    document.querySelectorAll('.playgroundSection').forEach(s => s.classList.add('hidden'));
    document.querySelectorAll('.step').forEach(s => s.classList.remove('isActive'));

    const section = document.getElementById('step-' + step);
    const btn = document.querySelector('[data-step="' + step + '"]');
    if (section) section.classList.remove('hidden');
    if (btn) btn.classList.add('isActive');

    // Reset run flags when navigating (unless coming from Run action)
    if (!fromRunAction) {
      if (step === 'createCheckout') createRunClicked = false;
      if (step === 'mintInstrument') mintRunClicked = false;
      if (step === 'updateCheckout') updateRunClicked = false;
    }

    currentStep = step;
    updateUI();
  };

  // Update UI based on state
  function updateUI() {
    const agent = AGENTS[selectedAgentId];
    activeCaps = negotiate(agent.capabilities, merchantProfile.ucp.capabilities);

    // Profiles
    setJson('agent-capabilities', { ucp: { version: VERSION, capabilities: agent.capabilities } });
    const descEl = document.getElementById('agent-description');
    if (descEl) descEl.textContent = agent.description;

    // Discovery
    setJson('discovery-request', { method: "GET", url: "/.well-known/ucp" });
    setJson('discovery-response', { profile: merchantProfile });

    // Negotiation
    setJson('merchant-capabilities', merchantProfile.ucp.capabilities);
    setJson('active-capabilities', activeCaps);

    // Create checkout
    const suggestedCreate = {
      line_items: [
        { item: { id: "sku_stickers", title: "UCP Demo Sticker Pack", price: 599 }, quantity: 2 },
        { item: { id: "sku_mug", title: "UCP Demo Mug", price: 1999 }, quantity: 1 }
      ],
      currency: "USD",
      payment: {}
    };
    setJson('create-request', suggestedCreate);
    if (checkoutResp) {
      setJson('create-response', checkoutResp);
      setJson('create-req-validation', simulateValidation("https://ucp.dev/schemas/shopping/checkout.create_req.json", suggestedCreate));
      setJson('create-resp-validation', simulateValidation("https://ucp.dev/schemas/shopping/checkout_resp.json", checkoutResp));
      if (createRunClicked) {
        showElement('create-validation-row');
      }
      const btnMint = document.getElementById('btn-to-mint');
      if (btnMint) btnMint.disabled = false;
    } else {
      setJson('create-response', { hint: "Click 'Run' to generate a session." });
      hideElement('create-validation-row');
    }

    // Mint instrument
    if (instrument) {
      setJson('minted-instrument', instrument);
      setJson('instrument-validation', simulateValidation("https://shopify.dev/ucp/handlers/shop_pay/instrument.json", instrument));
      setJson('checkout-id-display', { checkoutId: checkoutId });
      if (mintRunClicked) {
        showElement('instrument-validation-row');
      }
      const btnUpdate = document.getElementById('btn-to-update');
      if (btnUpdate) btnUpdate.disabled = false;
    } else {
      setJson('minted-instrument', { hint: "Click 'Run' to mint an instrument." });
      hideElement('instrument-validation-row');
    }

    // Update checkout
    if (checkoutResp && instrument) {
      const updateReq = {
        id: checkoutResp.id,
        line_items: suggestedCreate.line_items.map(li => ({ item: { id: li.item.id, title: li.item.title }, quantity: li.quantity })),
        currency: suggestedCreate.currency,
        payment: { selected_instrument_id: instrument.id, instruments: [instrument] }
      };
      setJson('update-request', updateReq);
    } else {
      setJson('update-request', { hint: "Complete previous steps to see request." });
    }
    if (updateResp) {
      setJson('update-response', updateResp);
      setJson('update-req-validation', simulateValidation("https://ucp.dev/schemas/shopping/checkout.update_req.json", updateResp));
      setJson('update-resp-validation', simulateValidation("https://ucp.dev/schemas/shopping/checkout_resp.json", updateResp));
      if (updateRunClicked) {
        showElement('update-validation-row');
      }
      const btnComplete = document.getElementById('btn-to-complete');
      if (btnComplete) btnComplete.disabled = false;
    } else {
      setJson('update-response', { hint: "No response yet." });
      hideElement('update-validation-row');
    }

    // Complete checkout
    if (instrument) {
      setJson('complete-request', { payment: { selected_instrument_id: instrument.id, instruments: [instrument] } });
    } else {
      setJson('complete-request', { hint: "Complete previous steps to see request." });
    }
    if (orderId && orderState) {
      setJson('complete-response', { ...checkoutResp, status: "completed", order_id: orderId, order_permalink_url: "https://merchant.example.com/orders/" + orderId });
      const btnOrder = document.getElementById('btn-to-order');
      if (btnOrder) btnOrder.disabled = false;
    } else {
      setJson('complete-response', { hint: "No response yet." });
    }

    // Order
    if (orderState) {
      setJson('order-display', { ...orderState.order, events: orderState.events });
      setJson('order-validation', simulateValidation("https://ucp.dev/schemas/shopping/order.json", orderState.order));
      showElement('order-validation-panel');
    } else {
      setJson('order-display', { hint: "No order yet." });
      hideElement('order-validation-panel');
    }
  }

  // Build checkout response
  function buildCheckoutResponse(opts) {
    const line_items = opts.lineItems.map((li, idx) => {
      const price = li.item.price || 2599;
      const quantity = Math.max(1, Math.floor(li.quantity || 1));
      return {
        id: "li_" + (idx + 1),
        item: { id: li.item.id, title: li.item.title, price },
        quantity,
        base_amount: price * quantity,
        subtotal: price * quantity,
        total: price * quantity
      };
    });
    const itemsBase = line_items.reduce((sum, li) => sum + li.base_amount, 0);

    return {
      ucp: { version: VERSION, capabilities: opts.activeCapabilities.map(c => ({ name: c.name, version: c.version })) },
      id: opts.checkoutId,
      line_items,
      status: opts.status,
      currency: opts.currency,
      totals: [
        { type: "items_base_amount", amount: itemsBase },
        { type: "subtotal", amount: itemsBase },
        { type: "total", amount: itemsBase }
      ],
      links: [
        { type: "privacy_policy", url: "https://merchant.example.com/privacy", title: "Privacy Policy" },
        { type: "terms_of_service", url: "https://merchant.example.com/terms", title: "Terms of Service" }
      ],
      expires_at: in6HoursIso(),
      payment: {
        handlers: merchantProfile.payment.handlers,
        selected_instrument_id: opts.selectedInstrumentId,
        instruments: opts.instruments || []
      },
      ...(opts.messages?.length ? { messages: opts.messages } : {}),
      ...(opts.orderId ? { order_id: opts.orderId, order_permalink_url: opts.orderPermalinkUrl } : {})
    };
  }

  // Actions
  window.doCreateCheckout = function() {
    createRunClicked = true;
    const suggestedCreate = {
      line_items: [
        { item: { id: "sku_stickers", title: "UCP Demo Sticker Pack", price: 599 }, quantity: 2 },
        { item: { id: "sku_mug", title: "UCP Demo Mug", price: 1999 }, quantity: 1 }
      ],
      currency: "USD",
      payment: {}
    };

    checkoutId = "checkout_" + uuid();
    checkoutResp = buildCheckoutResponse({
      activeCapabilities: activeCaps,
      checkoutId,
      currency: suggestedCreate.currency,
      lineItems: suggestedCreate.line_items,
      status: "recoverable_errors",
      messages: [{
        type: "error",
        code: "missing",
        path: "$.payment.instruments",
        content_type: "plain",
        content: "Add a payment instrument to complete checkout.",
        severity: "recoverable"
      }]
    });

    goToStep('createCheckout', true);
  };

  window.doMintInstrument = function() {
    mintRunClicked = true;
    const token = "shptok_" + uuid();
    instrument = {
      id: "instr_1",
      handler_id: "shop_pay",
      type: "shop_pay",
      email: "buyer@example.com",
      credential: { type: "shop_token", token }
    };
    goToStep('mintInstrument', true);
  };

  window.doUpdateCheckout = function() {
    updateRunClicked = true;
    if (!checkoutResp || !instrument) return;

    const suggestedCreate = {
      line_items: [
        { item: { id: "sku_stickers", title: "UCP Demo Sticker Pack", price: 599 }, quantity: 2 },
        { item: { id: "sku_mug", title: "UCP Demo Mug", price: 1999 }, quantity: 1 }
      ],
      currency: "USD"
    };

    updateResp = buildCheckoutResponse({
      activeCapabilities: activeCaps,
      checkoutId: checkoutResp.id,
      currency: suggestedCreate.currency,
      lineItems: suggestedCreate.line_items,
      status: "ready_for_complete",
      messages: [],
      selectedInstrumentId: instrument.id,
      instruments: [instrument]
    });

    goToStep('updateCheckout', true);
  };

  window.doCompleteCheckout = function() {
    if (!checkoutResp || !instrument) return;

    orderId = "order_" + uuid();
    const orderPermalinkUrl = "https://merchant.example.com/orders/" + orderId;

    checkoutResp = { ...checkoutResp, status: "completed", order_id: orderId, order_permalink_url: orderPermalinkUrl };

    orderState = {
      order: {
        ucp: { version: VERSION, capabilities: activeCaps.map(c => ({ name: c.name, version: c.version })) },
        id: orderId,
        checkout_id: checkoutId,
        permalink_url: orderPermalinkUrl,
        line_items: (checkoutResp.line_items || []).map(li => ({ line_item: li, status: "processing" })),
        totals: checkoutResp.totals || [],
        fulfillment_details: [{
          id: "pkg_1",
          fulfillment_option: { id: "standard", title: "Standard", description: "Standard fulfillment", total: 0 },
          status: "processing"
        }]
      },
      status: "processing",
      events: [{ id: "evt_" + uuid(), type: "order_created", created_at: nowIso(), note: "Order created." }]
    };

    goToStep('completeCheckout');
  };

  window.simulateEvent = function(event) {
    if (!orderState) return;

    const createdAt = nowIso();
    orderState.events.push({ id: "evt_" + uuid(), type: event, created_at: createdAt });

    if (event === "shipped") {
      orderState.status = "shipped";
      orderState.order.line_items = orderState.order.line_items.map(li => ({ ...li, status: "shipped" }));
      orderState.order.fulfillment_details = orderState.order.fulfillment_details.map(fd => ({
        ...fd,
        status: "shipped",
        tracking_identifier: "TRACK123",
        fulfillment_tracking_url: "https://carrier.example.com/track/TRACK123",
        expected_fulfillment_time: createdAt
      }));
    }

    if (event === "delivered") {
      orderState.status = "delivered";
      orderState.order.line_items = orderState.order.line_items.map(li => ({ ...li, status: "delivered" }));
      orderState.order.fulfillment_details = orderState.order.fulfillment_details.map(fd => ({ ...fd, status: "delivered" }));
    }

    updateUI();
  };

  // Initialize the playground
  function init() {
    // Agent select
    const agentSelect = document.getElementById('agent-select');
    if (agentSelect) {
      agentSelect.addEventListener('change', function() {
        selectedAgentId = this.value;
        updateUI();
      });
    }

    // Stepper clicks
    document.querySelectorAll('.step').forEach(btn => {
      btn.addEventListener('click', function() {
        goToStep(this.dataset.step);
      });
    });

    // Validation panel toggle clicks
    document.querySelectorAll('.validationPanelHeader').forEach(header => {
      header.addEventListener('click', function(e) {
        e.stopPropagation();
        const panel = this.closest('.jsonPanel');
        if (panel) {
          panel.classList.toggle('jsonPanel--collapsed');
        }
      });
    });

    // Initial UI
    updateUI();
  }

  // Run init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    // DOM already loaded
    init();
  }
})();
</script>

<style>
/* UCP Playground - Google-style Design System */

@import url("https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Google+Sans+Text:wght@400;500&display=swap");

:root {
  color-scheme: light;

  /* Core colors - Google style */
  --bg: #ffffff;
  --panel: #f8f9fa;
  --panel-elevated: #ffffff;
  --text: #202124;
  --text-secondary: #3c4043;
  --muted: #5f6368;
  --border: #dadce0;
  --border-light: #e8eaed;
  --accent: #1a73e8;
  --accent-hover: #1557b0;
  --success: #1e8e3e;
  --success-bg: #e6f4ea;
  --warning: #f9ab00;
  --warning-bg: #fef7e0;
  --error: #d93025;
  --error-bg: #fce8e6;
  --shadow-sm: 0 1px 2px rgba(60, 64, 67, 0.3),
    0 1px 3px 1px rgba(60, 64, 67, 0.15);
  --shadow-md: 0 1px 3px rgba(60, 64, 67, 0.3),
    0 4px 8px 3px rgba(60, 64, 67, 0.15);
  --shadow-lg: 0 1px 3px rgba(60, 64, 67, 0.3),
    0 8px 16px 4px rgba(60, 64, 67, 0.15);

  /* Radii */
  --radius: 16px;
  --radius-sm: 8px;
  --radius-lg: 24px;
  --radius-pill: 50px;

  /* Layout */
  --max: 1200px;

  /* Typography */
  font-family: "Google Sans", "Google Sans Text", -apple-system,
    BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
}

/* ============================================
   Playground Hero
   ============================================ */

.playgroundHero {
  background: linear-gradient(135deg, #f8f9fa 0%, #e8f0fe 50%, #f0f4f9 100%);
  border-radius: var(--radius-lg);
  padding: 48px 40px;
  margin-bottom: 40px;
}

.playgroundHero h1 {
  font-size: 2.5rem;
  font-weight: 500;
  color: var(--text);
  margin: 0 0 16px 0;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.playgroundHero p {
  font-size: 0.95rem;
  color: var(--muted);
  margin: 0;
  max-width: 700px;
  line-height: 1.6;
}

/* ============================================
   Stepper (Tab Pills)
   ============================================ */

.stepper {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px;
  background: var(--panel);
  border-radius: 24px;
}

.step {
  padding: 12px 20px;
  border-radius: var(--radius-pill);
  border: none;
  background: transparent;
  color: var(--muted);
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.step:hover {
  color: var(--text);
}

.step.isActive {
  background: var(--text);
  color: #fff;
  box-shadow: var(--shadow-sm);
}

.stepNumber {
  opacity: 0.5;
  margin-right: 6px;
  font-weight: 400;
}

/* ============================================
   Buttons
   ============================================ */

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  font-weight: 500;
  font-size: 14px;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.button:hover {
  text-decoration: none;
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.buttonPrimary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.buttonPrimary:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.buttonCompact {
  padding: 6px 12px;
  font-size: 12px;
  gap: 4px;
}

.buttonGhost {
  background: var(--bg);
  color: var(--text-secondary);
}

.buttonGhost:hover:not(:disabled) {
  background: var(--panel);
}

.buttonDark {
  background: #202124;
  border-color: #202124;
  color: #fff;
}

.buttonDark:hover:not(:disabled) {
  background: #3c4043;
  border-color: #3c4043;
}

.stepperActions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  flex-wrap: wrap;
}

/* ============================================
   Cards & Panels
   ============================================ */

.card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  transition: box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.cardTitle {
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--text);
  margin: 0 0 8px 0;
}

.cardBody {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

/* ============================================
   Callouts
   ============================================ */

.callout {
  border-radius: var(--radius);
  border: 1px solid var(--border);
  padding: 20px 24px;
  background: var(--panel);
  margin: 20px 0;
}

.calloutTitle {
  font-weight: 500;
  font-size: 1rem;
  color: var(--text);
  margin-bottom: 8px;
}

.calloutBody {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
}

.callout--note {
  background: var(--panel);
  border-color: var(--border);
}

.callout--tip {
  background: var(--success-bg);
  border-color: var(--success);
}

.callout--tip .calloutTitle {
  color: var(--success);
}

.callout--warning {
  background: var(--warning-bg);
  border-color: var(--warning);
}

.callout--warning .calloutTitle {
  color: #b06000;
}

/* ============================================
   JSON Panel
   ============================================ */

.jsonPanel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: #fafafa;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 450px;
}

.jsonPanel--success {
  border-color: var(--success);
}

.jsonPanel--success .jsonPanelHeader {
  background: var(--success-bg);
}

.jsonPanel--error {
  border-color: var(--error);
}

.jsonPanel--error .jsonPanelHeader {
  background: var(--error-bg);
}

.jsonPanel--collapsed .jsonPanelBody {
  display: none;
}

.jsonPanel--collapsed .jsonPanelHeader {
  border-bottom: none;
}

/* Validation panel header - clickable */
.validationPanelHeader {
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.validationPanelHeader:hover {
  background: var(--border-light);
}

/* Toggle icon for collapsible panels - uses MkDocs Material chevron */
.toggleIcon {
  display: inline-flex;
  margin-right: 4px;
  transition: transform 0.2s ease;
}

/* When collapsed, rotate the chevron to point right */
.jsonPanel--collapsed .toggleIcon {
  transform: rotate(-90deg);
}

.jsonPanelHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  min-height: 48px;
}

.jsonPanelTitle {
  border: 0;
  background: transparent;
  color: var(--text);
  font-weight: 500;
  font-size: 14px;
  padding: 0;
  text-align: left;
  font-family: inherit;
  display: flex;
  align-items: center;
}

.jsonPanelActions {
  display: flex;
  gap: 8px;
}

pre.jsonPanelBody {
  margin: 0 !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding: 12px 16px;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  font-size: 12px;
  flex: 1;
  min-height: 0;
  overflow: auto;
  font-family: "Google Sans Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  line-height: 1.6;
  background: transparent;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ============================================
   Chip / Tag
   ============================================ */

.chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.chip:hover:not(.chipRun) {
  background: var(--panel);
  border-color: var(--text-secondary);
}

.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chipRun {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.chipRun:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.chipCopy {
  background: var(--bg);
  border-color: var(--border);
  color: var(--text-secondary);
}

.chipCopy:hover {
  background: var(--panel);
  border-color: var(--text-secondary);
}

.chipCopied {
  background: var(--success-bg) !important;
  border-color: var(--success) !important;
  color: var(--success) !important;
}

/* ============================================
   Grids & Layouts
   ============================================ */

.playgroundGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.playgroundGrid--top {
  align-items: start;
}

.twoCol {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: stretch;
}

.twoCol--top {
  align-items: start;
}

.twoCol > * {
  min-width: 0;
}

/* ============================================
   Section Styling
   ============================================ */

.sectionTitle {
  font-size: 1.5625em !important;
  font-weight: 500;
  color: var(--text);
  margin: 24px 0 12px 0 !important;
  letter-spacing: -0.02em;
}

.sectionDescription {
  font-size: 0.95rem !important;
  color: var(--text);
  line-height: 1.6;
  margin: 0 0 24px 0;
  max-width: 800px;
}

/* ============================================
   Playground Section
   ============================================ */

.playgroundSection {
  animation: fadeIn 0.3s ease;
}

/* Hidden utility class */
.hidden,
.playgroundSection.hidden {
  display: none !important;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ============================================
   Form Elements
   ============================================ */

select {
  display: block;
  width: 100%;
  padding: 12px 40px 12px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%235f6368' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' xmlns='http://www.w3.org/2000/svg'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  background-size: 18px;
}

select:hover {
  border-color: var(--text-secondary);
}

select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
}

label {
  display: block;
  font-weight: 500;
  color: var(--text);
  font-size: 14px;
  margin-bottom: 8px;
}

/* ============================================
   Responsive
   ============================================ */

@media (max-width: 1024px) {
  .playgroundGrid,
  .twoCol {
    grid-template-columns: 1fr;
  }

  .playgroundHero {
    padding: 32px 24px;
  }

  .playgroundHero h1 {
    font-size: 2rem;
  }

  .stepper {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 8px;
  }

  .step {
    flex-shrink: 0;
    padding: 10px 16px;
    font-size: 13px;
  }
}

@media (max-width: 640px) {
  .playgroundHero h1 {
    font-size: 1.75rem;
  }

  .playgroundHero p {
    font-size: 1rem;
  }
}

/* Bottom padding for the page */
.page {
  padding-bottom: 80px;
}
</style>
