# ============================================================
# administrateur/templatetags/dict_filters.py
# ============================================================
#
# Filtre de template pour récupérer une valeur d'un dictionnaire
# par sa clé (Django ne le permet pas nativement avec une variable
# dynamique : {{ mon_dict.ma_cle }} ne marche que si ma_cle est fixe).
#
# Usage dans un template :
#   {% load dict_filters %}
#   {{ mon_dict|get_item:ma_cle_variable }}
# ============================================================

from django import template

register = template.Library()


@register.filter
def get_item(dictionnaire, cle):
    """Renvoie dictionnaire.get(cle) en toute sécurité (None si absent)."""
    if not dictionnaire:
        return None
    return dictionnaire.get(cle)