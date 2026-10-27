// Public site config. Do not put secrets in this file.
// PayPal subscription buttons read PAYPAL_CLIENT_ID and PLAN_ID at runtime.
// Live $9/month plan (PolicyPulse Pro). Client id is public; the secret never goes here.
window.POLICY_PULSE_CONFIG = {
  PAYPAL_CLIENT_ID: "BAAb5cq2I0Xx3lFhRJNBjnuGCVT5VDtWfWHgAuSasCoaA_F4cFzLmDWcDmYhsXG6panQVSaRPR3gvrgE9w",
  PLAN_ID: "P-7U340289BA306012CNLQF4BI",
  // Optional static form endpoint (Google Form action URL, Formspree, etc.).
  // Leave blank to keep the mailto placeholder on the digest page.
  DIGEST_FORM_ACTION: "",
  DIGEST_MAILTO: "mailto:you@example.com?subject=PolicyPulse%20daily%20digest%20signup"
};
