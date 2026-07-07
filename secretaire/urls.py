# ============================================================
# secretaire/urls.py
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_secretaire, name='dashboard_secretaire'),

    # Frais par niveau (montants + tranches + PDF)
    path('frais/', views.frais_niveaux, name='frais_niveaux'),
    path('frais/<str:niveau>/', views.frais_niveau_detail, name='frais_niveau_detail'),
    path('frais/<str:niveau>/supprimer-pdf/', views.frais_niveau_supprimer_pdf, name='frais_niveau_supprimer_pdf'),
    path('frais/<str:niveau>/tranches/ajouter/', views.frais_tranche_ajouter, name='frais_tranche_ajouter'),
    path('frais/tranches/<int:tranche_id>/modifier/', views.frais_tranche_modifier, name='frais_tranche_modifier'),
    path('frais/tranches/<int:tranche_id>/supprimer/', views.frais_tranche_supprimer, name='frais_tranche_supprimer'),

    # Élèves (CRUD)
    path('eleves/', views.secretaire_list_eleve, name='secretaire_list_eleve'),
    path('eleves/inscrire/', views.secretaire_add_eleve, name='secretaire_add_eleve'),
    path('eleves/<int:eleve_id>/modifier/', views.secretaire_add_eleve, name='secretaire_edit_eleve'),
    path('eleves/<int:eleve_id>/', views.secretaire_detail_eleve, name='secretaire_detail_eleve'),
    path('eleves/<int:eleve_id>/recu/', views.secretaire_recu_inscription, name='secretaire_recu_inscription'),
    path('eleves/<int:eleve_id>/recu/pdf/', views.secretaire_recu_inscription_pdf, name='secretaire_recu_inscription_pdf'),
    path('eleves/<int:eleve_id>/supprimer/', views.secretaire_delete_eleve, name='secretaire_delete_eleve'),

    # Paiements
    path('eleves/<int:eleve_id>/paiement/ajouter/', views.secretaire_paiement_ajouter, name='secretaire_paiement_ajouter'),
    path('paiements/<int:paiement_id>/recu/', views.secretaire_recu_paiement, name='secretaire_recu_paiement'),
    path('paiements/<int:paiement_id>/recu/pdf/', views.secretaire_recu_paiement_pdf, name='secretaire_recu_paiement_pdf'),
    path('paiements/retard/', views.secretaire_paiements_retard, name='secretaire_paiements_retard'),

    # Messages vers élève + parent
    path('messages/', views.secretaire_messages, name='secretaire_messages'),
    path('messages/envoyer/', views.secretaire_envoyer_message, name='secretaire_envoyer_message'),
    path('messages/envoyer/<int:eleve_id>/', views.secretaire_envoyer_message, name='secretaire_envoyer_message_eleve'),

    # Profil
    path('profil/', views.secretaire_profil, name='secretaire_profil'),
]