# ============================================================
# secretaire/context_processors.py
# ============================================================
#
# Injecte automatiquement dans tous les templates le nombre de messages
# non encore lus par leur destinataire — utilisé par la cloche de
# notifications de la topbar (rôles "admin" et "secretaire").
#
# À ajouter dans settings.py, dans TEMPLATES[0]['OPTIONS']['context_processors'] :
#   'secretaire.context_processors.notifications_topbar',
# ============================================================

from eleve.models import Message
from .models import eleves_en_retard


def notifications_topbar(request):
    if not request.user.is_authenticated:
        return {}

    role = getattr(request.user, 'role', None)

    if role == 'secretaire':
        return {
            'secretaire_non_lus': Message.objects.filter(
                expediteur=request.user, lu=False
            ).count(),
            'secretaire_retard_count': len(eleves_en_retard()),
        }

    if role == 'admin':
        return {
            'admin_non_lus': Message.objects.filter(
                expediteur=request.user, lu=False
            ).count(),
            'admin_retard_count': len(eleves_en_retard()),
        }

    return {}