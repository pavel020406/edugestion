# ============================================================
# eleve/urls.py
# Inclus depuis manager/urls.py avec le préfixe 'eleve/'
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',                         views.dashboard_eleve,        name='dashboard_eleve'),
    path('profil/',                            views.eleve_profil,           name='eleve_profil'),
    path('notes/',                             views.eleve_notes,            name='eleve_notes'),
    path('emploi/',                            views.eleve_emploi,           name='eleve_emploi'),
    path('presences/',                         views.eleve_presences,        name='eleve_presences'),
    path('messages/',                          views.eleve_messages,         name='eleve_messages'),
    path('messages/<int:message_id>/',         views.eleve_message_detail,   name='eleve_message_detail'),
    path('messages/<int:message_id>/pdf/',     views.eleve_message_pdf,      name='eleve_message_pdf'),
]