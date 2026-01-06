---
hide:
  - toc
---

<div class="hero-wrapper">
  <div class="hero-content">
    <h1>Universal Commerce<br>Protocol</h1>
    <p class="hero-subheading">
      The common language for consumers, agents and businesses.
    </p>
    <p class="hero-description">
      Discover products, Negotiate capabilities, Complete transactions. UCP defines the primitives for agentic commerce so platforms, businesses, and payment providers can interoperate through one standard, without custom builds.
    </p>
  </div>
  <div class="hero-image">
    <img src="assets/updated-icon.svg" alt="Hero image for Universal Commerce Protocol" class="hero-logo-crisp">
  </div>
</div>

<div class="promo-card-wrapper">

  <div class="promo-card">
    <h3>Learn</h3>
    <p>Protocol overview, core concepts, and design principles</p>
    <a href="specification/overview/" class="promo-button">
      Read the docs
    </a>
  </div>

  <div class="promo-card">
    <h3>Implement</h3>
    <p>GitHub repo, technical spec, SDKs, and reference implementations</p>
    <a href="https://github.com/Universal-Commerce-Protocol/ucp" class="promo-button">
      View on GitHub
    </a>
  </div>

</div>

<div style="text-align: center; padding: 60px 0; max-width: 1200px; margin: 0 auto;">
  <h2 style="font-size: 2.5rem; font-weight: 500; color: #202124; margin-bottom: 20px;">
    Created and adopted by industry partners
  </h2>

  <p style="color: #5f6368; font-size: 1.1rem; line-height: 1.6; max-width: 800px; margin: 0 auto 50px auto;">
    UCP is co-developed with foundational partners like Shopify, Target, Walmart, Etsy, and Wayfair to ensure it solves real-world retail pain points, not just tech theory.
  </p>

  <div style="display: flex; justify-content: center; align-items: center; gap: 60px; margin-bottom: 40px; flex-wrap: wrap;">
    <img src="assets/Google_Logo.svg" alt="Google" style="height: 38px; width: auto; opacity: 0.9;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
    <span style="display:none; font-weight: 700; color: #202124; font-size: 1.4rem;">Google</span>

    <img src="assets/shopify_monotone_black.svg" alt="Shopify" style="height: 35px; width: auto; opacity: 0.9;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
    <span style="display:none; font-weight: 700; color: #202124; font-size: 1.4rem;">Shopify</span>

    <img src="assets/Wayfair_Logo.svg" alt="Wayfair" style="height: 35px; width: auto; opacity: 0.9;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
    <span style="display:none; font-weight: 700; color: #202124; font-size: 1.4rem;">Wayfair</span>
  </div>

  <div style="display: flex; justify-content: center; align-items: center; gap: 60px; flex-wrap: wrap;">
    <img src="assets/Etsy.svg" alt="Etsy" style="height: 38px; width: auto; opacity: 0.9;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
    <span style="display:none; font-weight: 700; color: #202124; font-size: 1.4rem;">Etsy</span>

    <img src="assets/Target.svg" alt="Target" style="height: 38px; width: auto; opacity: 0.9;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
    <span style="display:none; font-weight: 700; color: #202124; font-size: 1.4rem;">Target</span>

    <img src="assets/walmart.svg" alt="Walmart" style="height: 38px; width: auto; opacity: 0.9;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
    <span style="display:none; font-weight: 700; color: #202124; font-size: 1.4rem;">Walmart</span>
  </div>
</div>

<section class="action-carousel-section">
  <h2>See it in action</h2>

  <div class="carousel-tabs">
    <button class="tab-btn active" onclick="openTab(event, 'tab-checkout')">Checkout</button>
    <button class="tab-btn" onclick="openTab(event, 'tab-identity')">Identity Linking</button>
    <button class="tab-btn" onclick="openTab(event, 'tab-order')">Order</button>
  </div>

  <div class="carousel-content">

    <div id="tab-checkout" class="tab-pane active">
      <div class="pane-text">
        <div class="icon-placeholder">
           <img src="assets/updated-icon.svg" alt="UCP Icon">
        </div>
        <div style="text-transform: uppercase; color: #5f6368; font-size: 0.7rem; font-weight: 700; letter-spacing: 1.2px; margin-bottom: 15px;">SEE IT IN ACTION</div>
        <h3>Checkout</h3>
        <p>Support complex cart logic, dynamic pricing, and tax calculations across millions of merchants through unified checkout sessions.</p>
        <a href="specification/checkout-rest/" class="learn-more-btn">Learn more</a>
      </div>
      <div class="pane-visuals">
        <div class="image-container">
           <img src="assets/Paysheet_with_address.svg" alt="Checkout UI" class="phone-mockup" onerror="this.src='https://placehold.co/260x500/EEE/31343C?text=Checkout+UI'">
        </div>
        <div class="code-block-placeholder">
           <code>// Code snippet space...</code>
        </div>
      </div>
    </div>

    <div id="tab-identity" class="tab-pane">
      <div class="pane-text">
        <div class="icon-placeholder">
           <img src="assets/updated-icon.svg" alt="UCP Icon">
        </div>
        <div style="text-transform: uppercase; color: #5f6368; font-size: 0.7rem; font-weight: 700; letter-spacing: 1.2px; margin-bottom: 15px;">SEE IT IN ACTION</div>
        <h3>Identity Linking</h3>
        <p>OAuth 2.0 standard enables agents to maintain secure, authorized relationships without sharing credentials.</p>
        <a href="specification/identity-linking/" class="learn-more-btn">Learn more</a>
      </div>
      <div class="pane-visuals">
        <div class="image-container">
           <img src="assets/Duo_branding.svg" alt="Identity UI" class="phone-mockup" onerror="this.src='https://placehold.co/260x500/EEE/31343C?text=Identity+UI'">
        </div>
        <div class="code-block-placeholder">
           <code>// Code snippet space...</code>
        </div>
      </div>
    </div>

    <div id="tab-order" class="tab-pane">
      <div class="pane-text">
          <div class="icon-placeholder">
            <img src="assets/updated-icon.svg" alt="UCP Icon">
        </div>
        <div style="text-transform: uppercase; color: #5f6368; font-size: 0.7rem; font-weight: 700; letter-spacing: 1.2px; margin-bottom: 15px;">SEE IT IN ACTION</div>
        <h3>Order</h3>
        <p>From purchase confirmation to delivery. Real-time web-hooks power status updates, shipment tracking, and return processing across every channel.</p>
        <a href="specification/order/" class="learn-more-btn">Learn more</a>
      </div>
      <div class="pane-visuals">
        <div class="image-container">
           <img src="assets/Confirmation.svg" alt="Order UI" class="phone-mockup" onerror="this.src='https://placehold.co/260x500/EEE/31343C?text=Order+UI'">
        </div>
        <div class="code-block-placeholder">
           <code>// Code snippet space...</code>
        </div>
      </div>
    </div>

</section>

<script>
function openTab(evt, tabName) {
  var i, tabContent, tabBtns;
  tabContent = document.getElementsByClassName("tab-pane");
  for (i = 0; i < tabContent.length; i++) {
    tabContent[i].classList.remove("active");
  }
  tabBtns = document.getElementsByClassName("tab-btn");
  for (i = 0; i < tabBtns.length; i++) {
    tabBtns[i].classList.remove("active");
  }
  document.getElementById(tabName).classList.add("active");
  evt.currentTarget.classList.add("active");
}
</script>

<div style="display: flex; gap: 30px; flex-wrap: wrap; justify-content: center;">

  <div style="flex: 1; min-width: 300px; background: #f8f9fa; border-radius: 16px; padding: 40px; display: flex; flex-direction: column; align-items: flex-start;">
    <div style="margin-bottom: 20px;">
      <img src="assets/Icon=Native_Checkout.svg" alt="Native Checkout feature icon" width="96" style="display: block;">
    </div>
    <h3 style="font-size: 1.5rem; margin: 0 0 15px 0; font-weight: 500; color: #202124;">Power native checkout UI</h3>
    <p style="color: #5f6368; font-size: 0.95rem; line-height: 1.6; margin-bottom: 30px; flex-grow: 1;">
      Integrate and negotiate directly with the merchant checkout API to power native UI and workflows for your platform.
    </p>
    <a href="specification/native/" class="md-button" style="background: #fff; border-radius: 24px; padding: 0.6rem 2rem; border: 1px solid #dadce0; color: #3c4043; font-weight: 500; text-transform: none;">See how it works</a>
  </div>

  <div style="flex: 1; min-width: 300px; background: #f8f9fa; border-radius: 16px; padding: 40px; display: flex; flex-direction: column; align-items: flex-start;">
    <div style="margin-bottom: 20px;">
      <img src="assets/Icon=Embedded_Option.svg" alt="Embedded Option feature icon" width="96" style="display: block;">
    </div>
    <h3 style="font-size: 1.5rem; margin: 0 0 15px 0; font-weight: 500; color: #202124;">Embed business checkout UI</h3>
    <p style="color: #5f6368; font-size: 0.95rem; line-height: 1.6; margin-bottom: 30px; flex-grow: 1;">
      Embed your checkout UI within an iframe to support more complex checkout flows, with advanced capabilities like bidirectional communication, payments and shipping address handoffs.
    </p>
    <a href="specification/embedded-checkout/" class="md-button" style="background: #fff; border-radius: 24px; padding: 0.6rem 2rem; border: 1px solid #dadce0; color: #3c4043; font-weight: 500; text-transform: none;">Learn more</a>
  </div>

</div>

<div style="text-align: center; margin: 100px 0 60px;">
  <h2 style="font-size: 2.5rem; font-weight: 500; color: #202124;">UCP Principles</h2>
</div>

<div style="max-width: 900px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px;">

  <div style="display: flex; align-items: center; gap: 30px; padding: 30px; background: #fff; border: 1px solid #e0e0e0; border-radius: 16px;">
    <div style="flex-shrink: 0;">
      <img src="assets/Icon=Extensible.svg" alt="Scalable" width="72">
    </div>
    <div>
      <h3 style="font-size: 1.2rem; font-weight: 500; margin: 0 0 8px 0; color: #202124;">Scalable and universal</h3>
      <p style="margin: 0; color: #5f6368; line-height: 1.5; font-size: 0.95rem;">
        Surface-agnostic design that can scale to support any commerce entity (from small merchants to enterprise builders) and all modalities (chat, visual commerce, voice, etc).
      </p>
    </div>
  </div>

  <div style="display: flex; align-items: center; gap: 30px; padding: 30px; background: #fff; border: 1px solid #e0e0e0; border-radius: 16px;">
    <div style="flex-shrink: 0;">
      <img src="assets/Icon=Open_Source.svg" alt="Simple" width="72">
    </div>
    <div>
      <h3 style="font-size: 1.2rem; font-weight: 500; margin: 0 0 8px 0; color: #202124;">Open and extensible</h3>
      <p style="margin: 0; color: #5f6368; line-height: 1.5; font-size: 0.95rem;">
        Open and extensible by design, enabling development of community-driven capabilities and extensions. Model your commerce, your way.
      </p>
    </div>
  </div>

  <div style="display: flex; align-items: center; gap: 30px; padding: 30px; background: #fff; border: 1px solid #e0e0e0; border-radius: 16px;">
    <div style="flex-shrink: 0;">
      <img src="assets/Icon=Merchant_at_the_Center.svg" alt="Merchants" width="72">
    </div>
    <div>
      <h3 style="font-size: 1.2rem; font-weight: 500; margin: 0 0 8px 0; color: #202124;">Businesses at the center</h3>
      <p style="margin: 0; color: #5f6368; line-height: 1.5; font-size: 0.95rem;">
        Built to facilitate commerce, ensuring retailers retain control of their business rules and remains the Merchant of Record with full ownership of customer relationship.
      </p>
    </div>
  </div>

  <div style="display: flex; align-items: center; gap: 30px; padding: 30px; background: #fff; border: 1px solid #e0e0e0; border-radius: 16px;">
    <div style="flex-shrink: 0;">
      <img src="assets/Icon=Secure_and_Private.svg" alt="Secure" width="72">
    </div>
    <div>
      <h3 style="font-size: 1.2rem; font-weight: 500; margin: 0 0 8px 0; color: #202124;">Secure and private</h3>
      <p style="margin: 0; color: #5f6368; line-height: 1.5; font-size: 0.95rem;">
        Built-on proven security standards for account linking (OAuth 2.0) and secure payment(Ap2) via payment mandates and verifiable credentials.
      </p>
    </div>
  </div>

  <div style="display: flex; align-items: center; gap: 30px; padding: 30px; background: #fff; border: 1px solid #e0e0e0; border-radius: 16px;">
    <div style="flex-shrink: 0;">
      <img src="assets/Icon=Frictionless_Payments.svg" alt="Frictionless" width="72">
    </div>
    <div>
      <h3 style="font-size: 1.2rem; font-weight: 500; margin: 0 0 8px 0; color: #202124;">Frictionless payments</h3>
      <p style="margin: 0; color: #5f6368; line-height: 1.5; font-size: 0.95rem;">
        Open wallet ecosystem with interoperability between providers to ensure buyers can pay with their preferred payment methods.
      </p>
    </div>
  </div>

</div>

<div class="lifecycle-container" style="padding: 80px 0; text-align: center; max-width: 1200px; margin: 0 auto;">

  <h2 style="font-size: 2.5rem; font-weight: 500; color: #202124; margin-bottom: 60px; line-height: 1.2; max-width: 800px; margin-left: auto; margin-right: auto;">
    The foundational open-source standard for the end-to-end commerce lifecycle
  </h2>

  <div style="display: flex; gap: 24px; flex-wrap: wrap; justify-content: center; margin-bottom: 24px;">

    <div style="flex: 1; min-width: 300px; max-width: 360px; border: 1px solid #dadce0; border-radius: 32px; padding: 40px 30px; display: flex; flex-direction: column; align-items: center;">
      <div style="height: 120px; margin-bottom: 30px; display: flex; align-items: center; justify-content: center;">
        <img src="assets/Content=Developers.svg" alt="Content illustration for Developers" style="max-height: 100%; width: auto;">
      </div>
      <h3 style="font-size: 1.4rem; margin: 0 0 15px 0; font-weight: 500; color: #202124;">For Developers</h3>
      <p style="color: #5f6368; font-size: 0.95rem; line-height: 1.6; margin-bottom: 30px; flex-grow: 1;">
        Build the future of commerce on an open foundation. Join our community in evolving an open-source standard designed for the next generation of digital trade.
      </p>
      <a href="specification/overview/" style="color: #1a73e8; text-decoration: none; font-weight: 500; font-size: 0.95rem;">View the technical spec</a>
    </div>

    <div style="flex: 1; min-width: 300px; max-width: 360px; border: 1px solid #dadce0; border-radius: 32px; padding: 40px 30px; display: flex; flex-direction: column; align-items: center;">
      <div style="height: 120px; margin-bottom: 30px; display: flex; align-items: center; justify-content: center;">
        <img src="assets/Content=Retailers.svg" alt="Content illustration for Businesses" style="max-height: 100%; width: auto;">
      </div>
      <h3 style="font-size: 1.4rem; margin: 0 0 15px 0; font-weight: 500; color: #202124;">For Businesses</h3>
      <p style="color: #5f6368; font-size: 0.95rem; line-height: 1.6; margin-bottom: 30px; flex-grow: 1;">
        UCP lets you meet customers wherever they are—AI assistants, shopping agents, embedded experiences—without rebuilding your checkout for each. Your existing payment stack stays intact.
      </p>
      <a href="#" style="color: #1a73e8; text-decoration: none; font-weight: 500; font-size: 0.95rem;">Integrate with UCP</a>
    </div>

    <div style="flex: 1; min-width: 300px; max-width: 360px; border: 1px solid #dadce0; border-radius: 32px; padding: 40px 30px; display: flex; flex-direction: column; align-items: center;">
      <div style="height: 120px; margin-bottom: 30px; display: flex; align-items: center; justify-content: center;">
        <img src="assets/Content=AI_Platforms.svg" alt="Content illustration for AI Platforms" style="max-height: 100%; width: auto;">
      </div>
      <h3 style="font-size: 1.4rem; margin: 0 0 15px 0; font-weight: 500; color: #202124;">For AI Platforms</h3>
      <p style="color: #5f6368; font-size: 0.95rem; line-height: 1.6; margin-bottom: 30px; flex-grow: 1;">
        Simplify merchant onboarding with standardized APIs and provide your audience with an integrated shopping experience. Compatible with MCP, A2A, and existing agent frameworks.
      </p>
      <a href="documentation/core-concepts/" style="color: #1a73e8; text-decoration: none; font-weight: 500; font-size: 0.95rem;">Learn more UCP core concepts</a>
    </div>

  </div>

  <div style="display: flex; gap: 24px; flex-wrap: wrap; justify-content: center;">

    <div style="flex: 1; min-width: 300px; max-width: 360px; border: 1px solid #dadce0; border-radius: 32px; padding: 40px 30px; display: flex; flex-direction: column; align-items: center;">
      <div style="height: 120px; margin-bottom: 30px; display: flex; align-items: center; justify-content: center;">
        <img src="assets/Content=Payment_Providers.svg" alt="Content illustration for Payment Providers" style="max-height: 100%; width: auto;">
      </div>
      <h3 style="font-size: 1.4rem; margin: 0 0 15px 0; font-weight: 500; color: #202124;">For Payment Providers</h3>
      <p style="color: #5f6368; font-size: 0.95rem; line-height: 1.6; margin-bottom: 30px; flex-grow: 1;">
        Universal payments that are provable—every authorization backed by cryptographic proof of user consent. Open, modular payment handler design enables open interoperability.
      </p>
      <a href="documentation/ucp-and-ap2/" style="color: #1a73e8; text-decoration: none; font-weight: 500; font-size: 0.95rem;">Learn more about UCP and AP2</a>
    </div>

    <div style="flex: 1; min-width: 300px; max-width: 360px; border: 1px solid #dadce0; border-radius: 32px; padding: 40px 30px; display: flex; flex-direction: column; align-items: center;">
      <div style="height: 120px; margin-bottom: 30px; display: flex; align-items: center; justify-content: center;">
        <img src="assets/Content=Shoppers.svg" alt="Content illustration for Shoppers" style="max-height: 100%; width: auto;">
      </div>
      <h3 style="font-size: 1.4rem; margin: 0 0 15px 0; font-weight: 500; color: #202124;">For Shoppers</h3>
      <p style="color: #5f6368; font-size: 0.95rem; line-height: 1.6; margin-bottom: 30px; flex-grow: 1;">
        Shop with absolute confidence. UCP ensures your preferred payment methods work across every agent and app, with a consistent checkout experience no matter where you buy.
      </p>
      <a href="tutotials.md" style="color: #1a73e8; text-decoration: none; font-weight: 500; font-size: 0.95rem;">Learn more about the launch on Google's AI Mode in Search</a>
    </div>

  </div>
</div>

<div class="partner-carousel">
  <h2>Trusted by market leaders</h2>

  <div class="partner-track">
    <div class="partner-logo">
      <img src="assets/Adyen_Logo.svg" alt="Adyen" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Adyen</span>
    </div>
    <div class="partner-logo">
      <img src="assets/AntInternational_Logo.svg" alt="Ant International" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Ant International</span>
    </div>
    <div class="partner-logo">
      <img src="assets/BestBuy_Logo.svg" alt="Best Buy" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Best Buy</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Carrefour_Logo.svg" alt="Carrefour" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Carrefour</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Chewy_Logo.svg" alt="Chewy" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Chewy</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Commerce_Logo_Black_RGB.png" alt="Commerce" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Commerce</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Etsy.svg" alt="Etsy" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Etsy</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Flipkart_Logo.svg" alt="Flipkart" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Flipkart</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Gap_Logo.svg" alt="Gap" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Gap</span>
    </div>
    <div class="partner-logo">
      <img src="assets/HomeDepot_Logo.svg" alt="The Home Depot" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>The Home Depot</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Kroger_Logo.svg" alt="Kroger" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Kroger</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Lowes_Logo.svg" alt="Lowe's" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Lowe's</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Macys_Logo.svg" alt="Macy's" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Macy's</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Sephora_Logo.svg" alt="Sephora" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Sephora</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Shopee_Logo.svg" alt="Shopee" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Shopee</span>
    </div>
    <div class="partner-logo">
      <img src="assets/shopify_monotone_black.svg" alt="Shopify" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Shopify</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Target.svg" alt="Target" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Target</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Ulta_Logo.svg" alt="Ulta" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Ulta</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Worldpay_Logo.svg" alt="Worldpay" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Worldpay</span>
    </div>
    <div class="partner-logo">
      <img src="assets/Zalando_Logo.svg" alt="Zalando" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
      <span>Zalando</span>
    </div>
  </div>
</div>

<div class="get-started-container" style="max-width: 1200px; margin: 0 auto; padding: 100px 20px 80px; text-align: center;">

  <div style="margin-bottom: 60px;">
    <h2 style="font-size: 2.5rem; font-weight: 500; color: #202124; margin-bottom: 30px; line-height: 1.2;">Get started today</h2>

    <p style="color: #3c4043; font-size: 1.1rem; line-height: 1.6; margin-bottom: 15px; max-width: 900px; margin-left: auto; margin-right: auto;">
      UCP is an open standard designed to let AI agents, apps, merchants, and payment providers interact seamlessly without needing custom, one-off integrations for every connection. We actively seek your feedback and contributions to help build the future of commerce.
    </p>
    <p style="color: #3c4043; font-size: 1.1rem; line-height: 1.6; max-width: 900px; margin-left: auto; margin-right: auto;">
      The complete technical specification, documentation, and reference implementations are hosted in our public GitHub repository.
    </p>
  </div>

  <div style="display: flex; justify-content: center; gap: 60px; flex-wrap: wrap; text-align: center;">

    <div style="flex: 1; min-width: 250px; max-width: 350px; display: flex; flex-direction: column; align-items: center;">
      <div style="height: 60px; margin-bottom: 20px;">
        <img src="assets/Icon=Download.svg" alt="Download" style="height: 48px; width: auto; opacity: 0.8;">
      </div>
      <h3 style="font-size: 1.4rem; font-weight: 400; color: #202124; margin: 0 0 15px 0;">Download</h3>
      <p style="color: #5f6368; font-size: 1rem; line-height: 1.5;">Download and run our code samples</p>
    </div>

    <div style="flex: 1; min-width: 250px; max-width: 350px; display: flex; flex-direction: column; align-items: center;">
      <div style="height: 60px; margin-bottom: 20px;">
        <img src="assets/Icon=Experiment.svg" alt="Experiment" style="height: 48px; width: auto; opacity: 0.8;">
      </div>
      <h3 style="font-size: 1.4rem; font-weight: 400; color: #202124; margin: 0 0 15px 0;">Experiment</h3>
      <p style="color: #5f6368; font-size: 1rem; line-height: 1.5;">Experiment with the protocol and its different agent roles</p>
    </div>

    <div style="flex: 1; min-width: 250px; max-width: 350px; display: flex; flex-direction: column; align-items: center;">
      <div style="height: 60px; margin-bottom: 20px;">
        <img src="assets/Icon=Contribute.svg" alt="Contribute" style="height: 48px; width: auto; opacity: 0.8;">
      </div>
      <h3 style="font-size: 1.4rem; font-weight: 400; color: #202124; margin: 0 0 15px 0;">Contribute</h3>
      <p style="color: #5f6368; font-size: 1rem; line-height: 1.5;">Contribute your feedback and code to the public repository</p>
    </div>

  </div>

  <div style="text-align: center; margin-top: 60px;">
    <a href="https://github.com/Universal-Commerce-Protocol/ucp" style="display: inline-flex; align-items: center; gap: 12px; padding: 14px 32px; border: 1px solid #dadce0; border-radius: 50px; text-decoration: none; color: #3c4043; font-weight: 500; font-size: 1rem; transition: all 0.2s; background: #fff;">
      <svg height="24" width="24" viewBox="0 0 16 16" version="1.1" fill="#3c4043">
        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
      </svg>
      Visit the Github repository
    </a>
  </div>

</div>

<div style="background: #f8f9fa; padding: 60px 20px; text-align: center; border-top: 1px solid #e0e0e0;">
  <div style="display: flex; justify-content: center; align-items: center; gap: 15px; opacity: 0.9;">
    <img src="assets/updated-icon.svg" alt="UCP" style="height: 28px; width: auto;">
    <span style="font-size: 1.2rem; color: #5f6368; font-weight: 400; letter-spacing: -0.5px; font-family: 'Google Sans', sans-serif;">Universal Commerce Protocol</span>
  </div>
</div>
