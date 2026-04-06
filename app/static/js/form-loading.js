/**
 * form-loading.js — Loading state for form submit buttons.
 *
 * Any <button> with [data-loading-text] inside a <form> gets:
 *   1. btn--loading class (shows spinner, blocks re-click)
 *   2. Label swapped to data-loading-text value
 *   3. Auto-restore after 15 s (safety net for navigation/download)
 */
(function () {
  "use strict";

  var RESTORE_TIMEOUT_MS = 15000;

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || form.tagName !== "FORM") return;

    // Find the button that triggered the submit
    var activeBtn = document.activeElement;
    if (!activeBtn || activeBtn.tagName !== "BUTTON" || !activeBtn.form) {
      // Fallback: find first submit button with loading text
      activeBtn = form.querySelector("button[data-loading-text]");
    }
    if (!activeBtn || !activeBtn.dataset.loadingText) return;

    var label = activeBtn.querySelector(".btn__label");
    var originalText = label ? label.textContent : "";

    // Apply loading state
    activeBtn.classList.add("btn--loading");
    if (label) {
      label.textContent = activeBtn.dataset.loadingText;
    }

    // Safety restore — covers file downloads where the page doesn't navigate
    setTimeout(function () {
      activeBtn.classList.remove("btn--loading");
      if (label) {
        label.textContent = originalText;
      }
    }, RESTORE_TIMEOUT_MS);
  });
})();
