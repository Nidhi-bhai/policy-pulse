// Public site config. Do not put secrets in this file.
// The PayPal button reads PAYPAL_CLIENT_ID at runtime and captures a one-time $9 order.
// The client id is public. The PayPal secret never goes here.
window.POLICY_PULSE_CONFIG = {
  PAYPAL_CLIENT_ID: "BAAb5cq2I0Xx3lFhRJNBjnuGCVT5VDtWfWHgAuSasCoaA_F4cFzLmDWcDmYhsXG6panQVSaRPR3gvrgE9w",
  // Optional. When set, the daily digest form posts here instead of opening mail.
  DIGEST_FORM_ACTION: "",
  DIGEST_MAILTO: "mailto:nidhi69n@gmail.com?subject=PolicyPulse%20digest",
  // Unlisted weekly brief. Shown after PayPal captures the order. Kept out of the sitemap.
  PRO_BRIEF_PATH: "pro/e31e1b36d2727e090f84fe9c60ab2c15/"
};
