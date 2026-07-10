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