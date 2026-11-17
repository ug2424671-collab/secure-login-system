/* Secure Login System - small progressive-enhancement helpers. */
(function () {
  "use strict";

  // Show / hide password fields.
  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    button.addEventListener("click", function () {
      var input = document.getElementById(button.getAttribute("data-toggle-password"));
      if (!input) return;
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });

  // Keep the OTP field numeric and limited to six characters.
  document.querySelectorAll("[data-otp-input]").forEach(function (input) {
    input.addEventListener("input", function () {
      var cleaned = input.value.replace(/\D/g, "").slice(0, 6);
      if (input.value !== cleaned) input.value = cleaned;
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && input.value.length === 6) {
        input.form.submit();
      }
    });
  });

  // Live expiry countdown for login and password-reset codes.
  function formatDuration(totalSeconds) {
    var minutes = Math.floor(totalSeconds / 60);
    var seconds = totalSeconds % 60;
    return String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
  }

  document.querySelectorAll("[data-expires-at]").forEach(function (node) {
    var expiresAt = Number(node.getAttribute("data-expires-at"));
    if (!expiresAt || Number.isNaN(expiresAt)) return;

    function tick() {
      var remaining = expiresAt - Math.floor(Date.now() / 1000);
      if (remaining <= 0) {
        node.textContent = "This code has expired. Request a new one.";
        node.classList.add("is-expired");
        return false;
      }
      node.textContent = "Code expires in " + formatDuration(remaining);
      node.classList.remove("is-expired");
      return true;
    }

    if (tick()) {
      var timer = window.setInterval(function () {
        if (!tick()) window.clearInterval(timer);
      }, 1000);
    }
  });

  // Cooldown on the resend-code button.
  document.querySelectorAll("[data-resend-button]").forEach(function (button) {
    var remaining = Number(button.getAttribute("data-cooldown")) || 0;
    if (remaining <= 0) return;

    button.disabled = true;

    function update() {
      if (remaining <= 0) {
        button.disabled = false;
        button.textContent = "Resend code";
        return false;
      }
      button.textContent = "Resend in " + remaining + "s";
      remaining -= 1;
      return true;
    }

    update();
    var interval = window.setInterval(function () {
      if (!update()) window.clearInterval(interval);
    }, 1000);
  });
})();
