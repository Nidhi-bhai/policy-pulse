(function () {
  var cfg = window.POLICY_PULSE_CONFIG || {};

  document.querySelectorAll("[data-filter]").forEach(function (button) {
    button.addEventListener("click", function () {
      var filter = button.getAttribute("data-filter");
      document.querySelectorAll("[data-filter]").forEach(function (other) {
        other.classList.toggle("is-on", other === button);
      });
      document.querySelectorAll("[data-source]").forEach(function (card) {
        var show = filter === "all" || card.getAttribute("data-source") === filter;
        card.hidden = !show;
      });
    });
  });

  var form = document.getElementById("digest-form");
  if (form) {
    var note = document.getElementById("digest-mode");
    if (cfg.DIGEST_FORM_ACTION) {
      form.action = cfg.DIGEST_FORM_ACTION;
      form.method = "post";
      form.removeAttribute("enctype");
      if (note) note.textContent = "This form posts to the endpoint in config.js.";
    } else if (cfg.DIGEST_MAILTO) {
      form.action = cfg.DIGEST_MAILTO;
      if (note) note.textContent = "Placeholder mode: submitting opens a mail draft. Set DIGEST_FORM_ACTION in config.js to use a Google Form or other static form.";
    }
  }

  var slot = document.getElementById("paypal-button");
  if (!slot) return;
  if (!cfg.PAYPAL_CLIENT_ID || !cfg.PLAN_ID) {
    slot.innerHTML = "<p class=\"note\">Add <code>PAYPAL_CLIENT_ID</code> and <code>PLAN_ID</code> in <code>config.js</code> to turn on the $9/month PayPal subscription button. No secret belongs in that file.</p>";
    return;
  }
  var script = document.createElement("script");
  script.src = "https://www.paypal.com/sdk/js?client-id=" + encodeURIComponent(cfg.PAYPAL_CLIENT_ID) + "&vault=true&intent=subscription";
  script.onload = function () {
    if (!window.paypal) return;
    window.paypal.Buttons({
      style: { shape: "rect", label: "subscribe", color: "gold" },
      createSubscription: function (data, actions) {
        return actions.subscription.create({ plan_id: cfg.PLAN_ID });
      },
      onApprove: function (data) {
        var status = document.getElementById("paypal-status");
        if (status) {
          status.textContent = "PayPal accepted the subscription. Reference " + data.subscriptionID + ".";
        }
      }
    }).render("#paypal-button");
  };
  document.head.appendChild(script);
})();
