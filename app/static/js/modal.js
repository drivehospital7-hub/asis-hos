/* ──────── Modal.confirm() / Modal.alert() — Promise-based helpers ────────
 *
 * window.Modal.confirm(message)  → Promise<boolean>
 *   - Shows overlay + modal with Cancel / Aceptar buttons
 *   - Aceptar → resolve(true), Cancel/Escape/click-outside → resolve(false)
 *
 * window.Modal.alert(message)    → Promise<void>
 *   - Shows overlay + modal with OK button only
 *   - OK / Escape / click-outside → resolve()
 *
 * Both auto-cleanup the overlay after resolution.
 * Design classes are defined in /static/css/modal.css.
 * ────────────────────────────────────────────────────────────────────────
 */
(function () {
  "use strict";

  var overlay = null;

  function createOverlay() {
    var el = document.createElement("div");
    el.className = "confirm-overlay";
    return el;
  }

  function createModal(html) {
    var el = document.createElement("div");
    el.className = "confirm-modal";
    el.innerHTML = html;
    return el;
  }

  function destroyOverlay() {
    if (overlay && overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
    overlay = null;
  }

  function onEscape(e) {
    if (e.key === "Escape" && overlay) {
      // Click-outside handler on overlay will resolve(false)
      overlay.click();
    }
  }

  /**
   * Modal.confirm(message) → Promise<boolean>
   * Shows Cancel / Aceptar. Aceptar = true, otherwise false.
   */
  window.Modal = window.Modal || {};
  window.Modal.confirm = function confirm(msg) {
    return new Promise(function (resolve) {
      if (overlay) destroyOverlay();

      overlay = createOverlay();

      var box = createModal(
        '<p class="confirm-modal__message">' + escapeHtml(msg) + '</p>' +
        '<div class="confirm-modal__buttons">' +
          '<button class="confirm-button confirm-button--secondary" data-action="cancel">Cancelar</button>' +
          '<button class="confirm-button confirm-button--primary" data-action="confirm">Aceptar</button>' +
        '</div>'
      );

      overlay.appendChild(box);
      document.body.appendChild(overlay);

      // Click outside → cancel
      overlay.addEventListener("click", function onClickOverlay(e) {
        if (e.target === overlay) {
          cleanup();
          resolve(false);
        }
      });

      // Button clicks
      box.addEventListener("click", function onClickBox(e) {
        var btn = e.target.closest("[data-action]");
        if (!btn) return;
        var action = btn.getAttribute("data-action");
        cleanup();
        resolve(action === "confirm");
      });

      // Escape key
      document.addEventListener("keydown", onEscape);

      function cleanup() {
        document.removeEventListener("keydown", onEscape);
        destroyOverlay();
      }
    });
  };

  /**
   * Modal.alert(message) → Promise<void>
   * Shows OK button only. Resolves on OK / Escape.
   */
  window.Modal.alert = function modalAlert(msg) {
    return new Promise(function (resolve) {
      if (overlay) destroyOverlay();

      overlay = createOverlay();

      var box = createModal(
        '<p class="confirm-modal__message">' + escapeHtml(msg) + '</p>' +
        '<div class="confirm-modal__buttons">' +
          '<button class="confirm-button confirm-button--primary" data-action="ok">Aceptar</button>' +
        '</div>'
      );

      overlay.appendChild(box);
      document.body.appendChild(overlay);

      // Click outside → dismiss
      overlay.addEventListener("click", function onClickOverlay(e) {
        if (e.target === overlay) {
          cleanup();
          resolve();
        }
      });

      // Button click
      box.addEventListener("click", function onClickBox(e) {
        var btn = e.target.closest("[data-action]");
        if (!btn) return;
        cleanup();
        resolve();
      });

      // Escape key
      document.addEventListener("keydown", onEscape);

      function cleanup() {
        document.removeEventListener("keydown", onEscape);
        destroyOverlay();
      }
    });
  };

  /**
   * Modal.toast(message, duration?) → Promise<void>
   * Non-blocking toast at bottom-right. Auto-dismisses after duration ms.
   * Use this for success confirmations that don't need a blocking dialog.
   */
  window.Modal.toast = function modalToast(msg, duration) {
    duration = duration || 3500;
    return new Promise(function (resolve) {
      var toast = document.createElement("div");
      toast.className = "toast-notification";
      toast.textContent = msg;
      document.body.appendChild(toast);

      // Trigger enter animation
      requestAnimationFrame(function () {
        toast.classList.add("toast-notification--visible");
      });

      // Auto-dismiss
      var timer = setTimeout(function () {
        dismiss();
      }, duration);

      // Click to dismiss early
      toast.addEventListener("click", function () {
        clearTimeout(timer);
        dismiss();
      });

      function dismiss() {
        toast.classList.remove("toast-notification--visible");
        toast.classList.add("toast-notification--exit");
        setTimeout(function () {
          if (toast.parentNode) toast.parentNode.removeChild(toast);
          resolve();
        }, 300);
      }
    });
  };

  /**
   * Minimal HTML-escaper for message content.
   * Using textContent would strip the message — we need innerHTML for
   * pre-wrap formatting but MUST escape user-facing strings.
   */
  function escapeHtml(t) {
    if (t == null) return "";
    var d = document.createElement("div");
    d.textContent = t;
    return d.innerHTML;
  }
})();
