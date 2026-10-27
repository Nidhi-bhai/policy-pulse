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
      if (note) note.textContent = "This form posts your digest request.";
    } else if (!badMailto(mailto)) {
      form.action = mailto;
      if (note) note.textContent = "Submitting opens an email draft to request the free daily digest.";
    } else if (badMailto(form.getAttribute("action"))) {
      form.hidden = true;
      if (note) note.textContent = "The daily digest signup is not configured.";
    }
  }

  var STORAGE_KEY = "policypulse-pro-order";
  var OFFER = "a link to the unlisted weekly Pro brief page, updated every Monday; no renewal, no account";

  function readReceipt() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || !parsed.orderId || !parsed.link) return null;
      return parsed;
    } catch (err) {
      return null;
    }
  }

  function showReceipt(record) {
    var box = document.getElementById("pro-receipt");
    if (!box || !record || !record.orderId || !record.link) return;
    box.hidden = false;
    box.innerHTML = "<p>Your unlisted weekly brief: <a href=\"" + escapeHtml(record.link) + "\">open the brief</a>. PayPal order id " + escapeHtml(record.orderId) + ". The page is updated every Monday. Bookmark the link.</p>";
  }

  function saveReceipt(orderId) {
    var record = { orderId: String(orderId || ""), link: cfg.PRO_BRIEF_PATH || "" };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
    } catch (err) {
      /* The link still has to appear for this visit if storage is blocked. */
    }
    showReceipt(record);
    var status = document.getElementById("paypal-status");
    if (status) status.textContent = "PayPal captured the $9 payment. Bookmark the unlisted link above.";
  }

  showReceipt(readReceipt());

  var slot = document.getElementById("paypal-button");
  if (!slot) return;
  if (readReceipt()) return;
  if (!cfg.PAYPAL_CLIENT_ID) {
    slot.textContent = "Checkout is unavailable right now.";
    return;
  }

  var script = document.createElement("script");
  script.src = "https://www.paypal.com/sdk/js?client-id=" + encodeURIComponent(cfg.PAYPAL_CLIENT_ID) + "&currency=USD&intent=capture";
  script.onload = function () {
    if (!window.paypal) return;
    window.paypal.Buttons({
      style: { shape: "rect", label: "pay", color: "gold" },
      createOrder: function (data, actions) {
        return actions.order.create({
          intent: "CAPTURE",
          purchase_units: [{
            description: "PolicyPulse Pro: " + OFFER,
            amount: { currency_code: "USD", value: "9.00" }
          }]
        });
      },
      onApprove: function (data, actions) {
        return actions.order.capture().then(function () {
          saveReceipt(data.orderID);
        });
      }
    }).render("#paypal-button");
  };
  document.head.appendChild(script);
})();
