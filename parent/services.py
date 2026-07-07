# ============================================================
# parent/services.py
# ============================================================
#
# Logique partagée de création/liaison d'un compte parent, appelée
# depuis le formulaire d'inscription élève (administrateur ET secretaire).
# ============================================================

import re

from utilisateurs.models import Utilisateur
from administrateur.models import ParentEnfant


def _generer_username_parent(nom_parent, telephone_parent):
    """
    Génère un nom d'utilisateur par défaut pour le parent, basé sur son
    numéro de téléphone (identifiant le plus fiable pour retrouver un
    parent déjà existant lors de l'inscription d'un frère/soeur).
    """
    chiffres = re.sub(r'\D', '', telephone_parent or '')
    if chiffres:
        return f"parent.{chiffres}"
    base = (nom_parent or 'parent').lower().replace(' ', '.')
    return f"parent.{base}"


def creer_ou_lier_parent(eleve, nom_parent, telephone_parent, email_parent,
                          username=None, password=None, lien='Parent/Tuteur'):
    """
    Crée le compte parent s'il n'existe pas encore (détection par nom
    d'utilisateur, dérivé du téléphone), ou réutilise le compte existant
    si un parent avec ce même numéro a déjà été enregistré (cas d'une
    fratrie). Lie ensuite ce compte à l'élève via ParentEnfant.

    Renvoie un tuple (compte_parent, cree, mot_de_passe_affiche)
    - cree : True si un nouveau compte a été créé, False s'il existait déjà
    - mot_de_passe_affiche : le mot de passe à communiquer (None si compte
      déjà existant, puisqu'on ne le change pas silencieusement)
    """
    username_final = (username or '').strip() or _generer_username_parent(nom_parent, telephone_parent)

    compte_parent = Utilisateur.objects.filter(username=username_final, role='parent').first()
    cree = False
    mot_de_passe_affiche = None

    if compte_parent is None:
        # Le username pourrait être pris par un autre rôle : on le rend unique si besoin.
        username_unique = username_final
        suffixe = 1
        while Utilisateur.objects.filter(username=username_unique).exists():
            suffixe += 1
            username_unique = f"{username_final}{suffixe}"

        mot_de_passe_final = (password or '').strip() or (re.sub(r'\D', '', telephone_parent or '') or 'parent2026')

        # Sépare grossièrement nom/prénom à partir du nom complet du parent.
        parts = (nom_parent or '').strip().split(' ', 1)
        prenom_parent = parts[0] if parts else ''
        nom_de_famille_parent = parts[1] if len(parts) > 1 else ''

        compte_parent = Utilisateur(
            username=username_unique,
            first_name=prenom_parent,
            last_name=nom_de_famille_parent,
            email=email_parent or '',
            role='parent',
        )
        compte_parent.set_password(mot_de_passe_final)
        compte_parent.save()

        cree = True
        mot_de_passe_affiche = mot_de_passe_final

    ParentEnfant.objects.get_or_create(
        parent=compte_parent, eleve=eleve,
        defaults={'lien': lien},
    )

    return compte_parent, cree, mot_de_passe_affiche