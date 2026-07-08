// ============================================================
// responsive.js — à inclure juste avant </body>,
// sur index.html ET sur base_dashboard.html
// ============================================================

document.addEventListener('DOMContentLoaded', function () {

  // ── Site public : menu hamburger dans le header ──
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks  = document.querySelector('.nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function () {
      navLinks.classList.toggle('mobile-open');
    });
  }

  // ── Dashboard : sidebar en tiroir sur mobile ──
  const sidebar = document.querySelector('.sidebar');
  const main    = document.querySelector('.dashboard-main');
  if (sidebar && main) {

    // Bouton hamburger (créé dynamiquement, pas besoin de toucher au HTML)
    const menuBtn = document.createElement('button');
    menuBtn.className = 'dashboard-menu-toggle';
    menuBtn.setAttribute('aria-label', 'Ouvrir le menu');
    menuBtn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 6h18M3 12h18M3 18h18" stroke-linecap="round"/>
      </svg>`;
    document.body.appendChild(menuBtn);

    // Overlay sombre
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);

    function ouvrirSidebar() {
      sidebar.classList.add('sidebar-open');
      overlay.classList.add('active');
    }
    function fermerSidebar() {
      sidebar.classList.remove('sidebar-open');
      overlay.classList.remove('active');
    }

    menuBtn.addEventListener('click', ouvrirSidebar);
    overlay.addEventListener('click', fermerSidebar);

    // Ferme la sidebar automatiquement si on clique un lien (mobile)
    sidebar.querySelectorAll('.sidebar-link').forEach(function (link) {
      link.addEventListener('click', fermerSidebar);
    });
  }
});