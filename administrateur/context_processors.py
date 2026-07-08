# ============================================================
# administrateur/context_processors.py  (nouveau fichier)
# ============================================================

from .models import Etablissement





from .models import Etablissement


def etablissement_context(request):
    return {
        'etablissement': Etablissement.objects.first()
    }