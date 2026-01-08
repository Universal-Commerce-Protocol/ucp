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

# Google's Implementation

<style>
  .hero-section-h1 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 3rem;
    padding: 2rem 0 3rem 0;
    /* Flex-wrap is allowed, but the sizing below ensures it fits on desktop */
    flex-wrap: wrap;
  }

  .hero-section-h1-text {
    /* Changed from 55% to flex: 1 to fill available space */
    flex: 1;
    min-width: 300px;
  }

  .hero-section-h1-video {
    /* Changed to fixed width so it doesn't force a wrap */
    flex: 0 0 280px;
    text-align: center;
  }

  .hero-section-h1-video img {
    width: 280px;
    max-width: 100%;
    height: auto;
    display: block; /* Changed to block to remove inline spacing issues */
    border-radius: 24px;
    box-shadow: 0 4px 8px rgba(0,0,0,.05), 0 1px 3px rgba(0,0,0,.08);
    border: 1px solid rgba(128,128,128,.1);
  }

  .hero-section-h1-text h1 {
    font-family: "Google Sans", sans-serif;
    font-size: 2.5rem;
    font-weight: 500;
    line-height: 1.3;
    margin-top: 0;
    margin-bottom: 1rem;
    color: #202124;
  }

  .hero-section-h1-text p {
    font-size: 1rem;
    line-height: 1.6;
    margin-bottom: 1.5rem;
    color: #5f6368;
  }

  .hero-section-h1-buttons {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
  }

  .hero-section-h1-buttons a {
    font-family: "Google Sans", sans-serif;
    text-decoration: none;
    padding: 0.5rem 1.2rem;
    border-radius: 100px;
    font-weight: 500;
    font-size: .875rem;
    border: 1px solid #dadce0;
    display: inline-block;
    text-align: center;
    transition: all 0.2s ease;
    white-space: nowrap;
  }

  /* --- UPDATED COLORS FOR BLACK & WHITE THEME --- */
  a.button-primary {
    background-color: #202124; /* Black background */
    border-color: #202124;
    color: white !important;
  }

  a.button-secondary {
    background-color: transparent;
    color: #202124 !important; /* Black text */
    border-color: #dadce0;
  }

  a.button-primary:hover {
    background-color: #3c4043; /* Lighter black/grey on hover */
    border-color: #3c4043;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
  }

  a.button-secondary:hover {
    background-color: #f8f9fa; /* Very light grey on hover */
    border-color: #202124; /* Darker border on hover */
  }

  /* Mobile Layout */
  @media screen and (max-width: 768px) {
    .hero-section-h1 {
      flex-direction: column;
      text-align: center;
      gap: 2rem;
    }
    .hero-section-h1-buttons {
      justify-content: center;
    }
    .hero-section-h1-text {
        width: 100%;
    }
    .hero-section-h1-video {
        flex: 1;
        width: 100%;
    }
  }
</style>

<div class="hero-section-h1">
  <div class="hero-section-h1-text">
    <h2>Sell everywhere your customers are with UCP</h2>
    <p>The Universal Commerce Protocol (UCP) empowers you to turn AI interactions into instant sales. Enable users to buy your products directly on Google AI-Mode and Gemini with a new open standard designed for the future of commerce.</p>
    <div class="hero-section-h1-buttons">
      <a href="https://developers.google.com/merchant/ucp" class="button-primary">Learn more about this launch</a>
      <a href="https://developers.google.com/merchant/ucp/guides" class="button-secondary">Read the documentation</a>
      <a href="https://support.google.com/merchants/contact/ucp_integration_interest" class="button-secondary">Join the waitlist</a>
    </div>
  </div>
  <div class="hero-section-h1-video">
    <img src="../../assets/Suitcase_PhoneFrame_v17.gif" alt="Demo video">
  </div>
</div>
