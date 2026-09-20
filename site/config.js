// Public, non-secret site configuration. Safe to commit.
// The Meta Pixel ID is public by design (it ships in every page's HTML).
window.DDS_CONFIG = {
  companyName: "Debt Direct Solutions",
  metaPixelId: "",              // e.g. "1234567890123456". Empty = pixel disabled (server events still work).
  trackEndpoint: "/api/track",  // Netlify function: netlify/functions/track.js
  leadEndpoint: "/api/lead",    // Netlify function: netlify/functions/lead.js
  phoneDisplay: "",             // optional, e.g. "(800) 555-0100" — shown in header if set
  debug: false                  // true = log every event to the browser console
};
