from administrateur.models import Enseignant


def enseignant_connecte(request):
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'enseignant':
        return {
            'enseignant_connecte': request.user
        }

    return {
        'enseignant_connecte': None
    }