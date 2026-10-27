// Public site config. Do not put secrets in this file.
// PayPal subscription buttons read PAYPAL_CLIENT_ID and PLAN_ID at runtime.
// The client id is public. The PayPal secret never goes here.
window.POLICY_PULSE_CONFIG = {
  PAYPAL_CLIENT_ID: "BAAb5cq2I0Xx3lFhRJNBjnuGCVT5VDtWfWHgAuSasCoaA_F4cFzLmDWcDmYhsXG6panQVSaRPR3gvrgE9w",
  PLAN_ID: "P-7U340289BA306012CNLQF4BI",
  // Optional. When set, the daily digest form posts here instead of opening mail.
  DIGEST_FORM_ACTION: "",
  DIGEST_MAILTO: "mailto:nidhi69n@gmail.com?subject=PolicyPulse%20digest",
  // Unlisted weekly brief. Revealed after PayPal approves. Kept out of the sitemap.
  PRO_BRIEF_PATH: "pro/e31e1b36d2727e090f84fe9c60ab2c15/",
  // Optional Google Form action. Empty skips the subscription email post.
  PRO_FORM_ACTION: "",
  PRO_FORM_EMAIL_FIELD: "email",
  PRO_FORM_SUBSCRIPTION_FIELD: "subscription_id"
};
