// Public site config. Do not put secrets in this file.
// PayPal subscription buttons read PAYPAL_CLIENT_ID and PLAN_ID at runtime.
// Leave them empty until you create a $9/month plan in PayPal.
window.POLICY_PULSE_CONFIG = {
  PAYPAL_CLIENT_ID: "",
  PLAN_ID: "",
  // Optional static form endpoint (Google Form action URL, Formspree, etc.).
  // Leave blank to keep the mailto placeholder on the digest page.
  DIGEST_FORM_ACTION: "",
  DIGEST_MAILTO: "mailto:you@example.com?subject=PolicyPulse%20daily%20digest%20signup"
};
