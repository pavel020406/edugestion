# ============================================================
# parent/urls.py
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_parent, name='dashboard_parent'),
    path('choisir-enfant/<int:eleve_id>/', views.parent_choisir_enfant, name='parent_choisir_enfant'),
    path('frais/', views.parent_frais_niveaux, name='parent_frais_niveaux'),
    path('notes/', views.parent_notes, name='parent_notes'),
    path('bulletins/', views.parent_bulletins, name='parent_bulletins'),
    path('bulletins/<str:trimestre>/pdf/', views.parent_bulletin_pdf, name='parent_bulletin_pdf'),
    path('emploi-du-temps/', views.parent_emploi_du_temps, name='parent_emploi_du_temps'),
    path('messages/', views.parent_messages, name='parent_messages'),
    path('messages/envoyer/', views.parent_envoyer_message, name='parent_envoyer_message'),
]