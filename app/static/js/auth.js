/**
 * Módulo de autenticación - Control de Facturación
 * Sin auth: elementos se ven normales pero no funcionan (clase is-disabled)
 * Con auth: todo habilitado
 */

const AUTH_KEY = 'admin_authenticated';

function isAuthenticated() {
  return localStorage.getItem(AUTH_KEY) === 'true';
}

function initAuthUI() {
  const authenticated = isAuthenticated();

  // ----- .require-auth (botón Agregar Error) -----
  document.querySelectorAll('.require-auth').forEach(el => {
    if (!authenticated) {
      el.classList.add('is-disabled');
    } else {
      el.classList.remove('is-disabled');
    }
  });

  // ----- .action-icon--delete (botones eliminar) -----
  document.querySelectorAll('.action-icon--delete').forEach(btn => {
    if (!authenticated) {
      btn.classList.add('is-disabled');
    } else {
      btn.classList.remove('is-disabled');
    }
  });

  // ----- .editable-cell (EXCEPTO data-field="estado") -----
  document.querySelectorAll('.editable-cell').forEach(cell => {
    const field = cell.dataset.field;
    if (field === 'estado') return; // NO tocar columna estado
    
    if (!authenticated) {
      cell.classList.add('is-disabled');
    } else {
      cell.classList.remove('is-disabled');
    }
  });

  // ----- ÁREAS EN HOME -----
  const areasSection = document.getElementById('areas-section');
  if (areasSection) {
    areasSection.style.display = authenticated ? 'block' : 'none';
  }
}

// Inicializar
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAuthUI);
} else {
  initAuthUI();
}

// Escuchar cambios en localStorage (si se loguea en otra pestaña)
window.addEventListener('storage', function(e) {
  if (e.key === AUTH_KEY) {
    initAuthUI();
  }
});