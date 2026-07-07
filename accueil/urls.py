# ============================================================
# accueil/urls.py
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.accueil, name='accueil'),

    # Authentification
    path('connexion/', views.connexion, name='connexion'),
   

   
]