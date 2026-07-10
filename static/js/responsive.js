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

    // Réutilise le bouton et l'overlay déjà présents dans le HTML.
    // Ne les crée dynamiquement QUE s'ils n'existent pas déjà (sécurité).
    let menuBtn = document.querySelector('.dashboard-menu-toggle');
    if (!menuBtn) {
      menuBtn = document.createElement('button');
      menuBtn.className = 'dashboard-menu-toggle';
      menuBtn.setAttribute('aria-label', 'Ouvrir le menu');
      menuBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 6h18M3 12h18M3 18h18" stroke-linecap="round"/>
        </svg>`;
      document.body.appendChild(menuBtn);
    }

    let overlay = document.querySelector('.sidebar-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'sidebar-overlay';
      document.body.appendChild(overlay);
    }

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

// ============================================================
// theme-switcher.js
// Deux parties :
// 1. Un petit script à mettre TOUT EN HAUT du <head> (avant tout CSS)
//    pour appliquer le thème sauvegardé AVANT que la page ne s'affiche
//    (évite le flash "bleu puis orange").
// 2. Le gestionnaire du bouton, à charger avant </body>.
// ============================================================

// ── Partie 2 : gestion du bouton (ce fichier) ──
document.addEventListener('DOMContentLoaded', function () {
  const bouton = document.getElementById('theme-toggle-btn');
  if (!bouton) return;

  function themeActuel() {
    return document.documentElement.getAttribute('data-theme') || 'bleu';
  }

  function majLabel() {
    const t = themeActuel();
    bouton.querySelector('.theme-toggle-label').textContent =
      t === 'orange' ? 'Noir & Orange' : 'Bleu & Blanc';
    bouton.querySelector('.theme-toggle-dot').style.background =
      t === 'orange' ? '#EA580C' : '#1D4ED8';
  }

  majLabel();

  bouton.addEventListener('click', function () {
    const nouveauTheme = themeActuel() === 'orange' ? 'bleu' : 'orange';
    document.documentElement.setAttribute('data-theme', nouveauTheme);
    localStorage.setItem('edugestion-theme', nouveauTheme);
    majLabel();
  });
});