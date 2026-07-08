# administrateur/context_processors.py

def etablissement_context(request):
    """
    Injecte `etablissement` dans les templates — mais UNIQUEMENT
    celui de l'utilisateur connecté. Un visiteur anonyme (page
    d'accueil publique, page de connexion) ne voit JAMAIS
    d'établissement, peu importe combien il en existe en base.
    """
    if request.user.is_authenticated and getattr(request.user, 'etablissement', None):
        return {'etablissement': request.user.etablissement}
    return {'etablissement': None}