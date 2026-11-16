/**
 * Curated notes about platforms that have published how UCP works for their
 * merchants. The UCP documentation does not cover platform-specific setup,
 * so without these the assistant can only say "check with the platform".
 *
 * Every entry is a claim about another company, shown to visitors as fact.
 * Keep each one conservative, attributed to what the platform itself has
 * said, and review it when that platform's guidance changes. Keys are the
 * platform name in lower case, as it appears in the partner lists.
 */

export interface PlatformNote {
  /** Shown when someone asks whether the platform uses or supports UCP. */
  adoption: string;
  /** Shown first when someone asks how to set UCP up on the platform. */
  setup: string;
}

export const PLATFORM_NOTES: Record<string, PlatformNote> = {
  shopify: {
    adoption:
      "Shopify stores are integrated with UCP by default. Shopify has said it is switched on for eligible stores through its agentic storefronts, so merchants are reachable over UCP without building anything. It can be turned off in the Shopify admin, and what is supported can vary by store, so check your admin or Shopify's developer documentation to confirm for yours.",
    setup:
      "Shopify stores are integrated with UCP by default, so you most likely do not need to implement anything yourself. Shopify has said it is switched on for eligible stores through its agentic storefronts. Check your Shopify admin to confirm it is on for your store, and see Shopify's developer documentation for what is supported.",
  },
};

export function platformNote(name: string): PlatformNote | undefined {
  return PLATFORM_NOTES[name.toLowerCase()];
}
