(function () {
  var cfg = window.POLICY_PULSE_CONFIG || {};

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function badMailto(value) {
    return !value || /example\.com/i.test(value);
  }

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
    var mailto = cfg.DIGEST_MAILTO || "";
    if (cfg.DIGEST_FORM_ACTION) {
      form.action = cfg.DIGEST_FORM_ACTION;
      form.method = "post";
      form.removeAttribute("enctype");
      if (note) note.textContent = "This form posts to the digest endpoint in config.js.";
    } else if (!badMailto(mailto)) {
      form.action = mailto;
      if (note) note.textContent = "Submitting opens an email draft to request the free daily digest.";
    } else if (badMailto(form.getAttribute("action"))) {
      form.hidden = true;
      if (note) note.textContent = "The daily digest signup is not configured.";
    }
  }

  var slot = document.getElementById("paypal-button");
  if (!slot) return;
  if (!cfg.PAYPAL_CLIENT_ID || !cfg.PLAN_ID) {
    slot.innerHTML = "<p class=\"note\">Add <code>PAYPAL_CLIENT_ID</code> and <code>PLAN_ID</code> in <code>config.js</code> to turn on the $9/month PayPal subscription button. No secret belongs in that file.</p>";
    return;
  }

  function revealBrief(subscriptionId) {
    var status = document.getElementById("paypal-status");
    var emailInput = document.getElementById("pro-email");
    var email = emailInput ? String(emailInput.value || "").trim() : "";
    var subscription = String(subscriptionId || "");
    if (cfg.PRO_FORM_ACTION) {
      try {
        var body = new FormData();
        body.append(cfg.PRO_FORM_EMAIL_FIELD || "email", email);
        body.append(cfg.PRO_FORM_SUBSCRIPTION_FIELD || "subscription_id", subscription);
        fetch(cfg.PRO_FORM_ACTION, { method: "POST", mode: "no-cors", body: body });
      } catch (err) {
        /* The bookmark still has to show if the optional form is unreachable. */
      }
    }
    if (!status) return;
    var path = cfg.PRO_BRIEF_PATH || "";
    if (path && !/example\.com/i.test(path)) {
      status.innerHTML = "PayPal accepted the subscription. Reference " + escapeHtml(subscription) + ". Bookmark <a href=\"" + escapeHtml(path) + "\">your private weekly brief</a>. A new edition is at that link every Monday.";
    } else {
      status.textContent = "PayPal accepted the subscription. Reference " + subscription + ". The private brief link is not in config.js yet.";
    }
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
        revealBrief(data.subscriptionID);
      }
    }).render("#paypal-button");
  };
  document.head.appendChild(script);
})();
