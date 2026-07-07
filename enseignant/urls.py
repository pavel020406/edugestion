# ============================================================
# enseignant/urls.py — COMPLET
# Remplace ton fichier urls.py existant par celui-ci
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard_enseignant, name='dashboard_enseignant'),

    # Mes classes
    path('classes/', views.enseignant_mes_classes, name='enseignant_mes_classes'),

    # Notes
    path('notes/', views.enseignant_notes_classes, name='enseignant_notes_classes'),
    path('notes/<int:classe_id>/', views.enseignant_notes_matieres, name='enseignant_notes_matieres'),
    path('notes/<int:classe_id>/<int:matiere_id>/', views.enseignant_notes_saisie, name='enseignant_notes_saisie'),

    # Appels / Présences
    path('presences/', views.enseignant_presences_classes, name='enseignant_presences_classes'),
    path('presences/<int:classe_id>/', views.enseignant_presences_creneaux, name='enseignant_presences_creneaux'),
    path('presences/<int:classe_id>/creneau/<int:creneau_id>/', views.enseignant_presences_appel, name='enseignant_presences_appel'),
    path('presences/<int:classe_id>/historique/', views.enseignant_presences_historique, name='enseignant_presences_historique'),

    # Profil
    path('profil/', views.enseignant_profil, name='enseignant_profil'),
]