# administrateur/context_processors.py

from .models import Etablissement


def etablissement_context(request):
    """
    Une seule école pour tout le site (pas de multi-établissement).
    Visible par tout le monde, connecté ou non — ce n'est pas une donnée
    privée, c'est juste "l'école qui utilise cette installation".
    """
    return {
        'etablissement': Etablissement.objects.first()
    }