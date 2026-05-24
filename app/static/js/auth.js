/**
 * Módulo de autenticación - Control de Facturación
 * Sin auth: elementos se ven normales pero no funcionan (clase is-disabled)
 * Con auth: todo habilitado
 *
 * Escucha el evento 'ce-auth-change' del sistema moderno (base.html).
 * No usa localStorage.
 */
function initAuthUI(authenticated) {
  // ----- .require-auth (botón Agregar Error) -----
  document.querySelectorAll('.require-auth').forEach(function(el) {
    if (!authenticated) {
      el.classList.add('is-disabled');
    } else {
      el.classList.remove('is-disabled');
    }
  });

  // ----- .action-icon--delete (botones eliminar) -----
  document.querySelectorAll('.action-icon--delete').forEach(function(btn) {
    if (!authenticated) {
      btn.classList.add('is-disabled');
    } else {
      btn.classList.remove('is-disabled');
    }
  });

  // ----- .editable-cell (EXCEPTO data-field="estado") -----
  document.querySelectorAll('.editable-cell').forEach(function(cell) {
    var field = cell.dataset.field;
    if (field === 'estado') return; // NO tocar columna estado

    if (!authenticated) {
      cell.classList.add('is-disabled');
    } else {
      cell.classList.remove('is-disabled');
    }
  });

  // ----- ÁREAS EN HOME -----
  var areasSection = document.getElementById('areas-section');
  if (areasSection) {
    areasSection.style.display = authenticated ? 'block' : 'none';
  }
}

// Escuchar evento moderno ce-auth-change (disparado por base.html)
document.addEventListener('ce-auth-change', function(e) {
  var authed = e.detail && e.detail.auth;
  initAuthUI(!!authed);
});

// Fallback: inicializar con false si el evento nunca se disparó
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    initAuthUI(false);
  });
} else {
  initAuthUI(false);
}
