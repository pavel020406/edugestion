# ============================================================
# accueil/urls.py
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('parametres/etablissement/', views.admin_modifier_etablissement, name='admin_modifier_etablissement'),
    path('', views.accueil, name='accueil'),
    path('setup/etablissement/', views.setup_etablissement, name='setup_etablissement'),
    path('setup/admin/',         views.setup_admin,         name='setup_admin'),
    path('setup/secretaire/',    views.setup_secretaire,     name='setup_secretaire'),
    # Authentification
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),

    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profil/', views.admin_profil, name='admin_profil'),
    

    # Élèves
    path('eleves/', views.list_eleve, name='list_eleve'),
    path('eleves/ajouter/', views.add_eleve, name='add_eleve'),
    path('eleves/<int:eleve_id>/', views.detail_eleve, name='detail_eleve'),
    path('eleves/<int:eleve_id>/modifier/', views.add_eleve, name='edit_eleve'),
    path('eleves/<int:eleve_id>/supprimer/', views.delete_eleve, name='delete_eleve'),

    # Matières
    path('matieres/', views.list_matiere, name='list_matiere'),
    path('matieres/ajouter/', views.add_matiere, name='add_matiere'),
    path('matieres/<int:matiere_id>/', views.detail_matiere, name='detail_matiere'),
    path('matieres/<int:matiere_id>/modifier/', views.add_matiere, name='edit_matiere'),
    path('matieres/<int:matiere_id>/supprimer/', views.delete_matiere, name='delete_matiere'),

    # Classes
    path('classes/', views.list_classe, name='list_classe'),
    path('classes/ajouter/', views.add_classe, name='add_classe'),
    path('classes/<int:classe_id>/', views.detail_classe, name='detail_classe'),
    path('classes/<int:classe_id>/modifier/', views.add_classe, name='edit_classe'),
    path('classes/<int:classe_id>/supprimer/', views.delete_classe, name='delete_classe'),

    # Salles
    path('salles/', views.list_salle, name='list_salle'),
    path('salles/ajouter/', views.add_salle, name='add_salle'),
    path('salles/<int:salle_id>/', views.detail_salle, name='detail_salle'),
    path('salles/<int:salle_id>/modifier/', views.add_salle, name='edit_salle'),
    path('salles/<int:salle_id>/supprimer/', views.delete_salle, name='delete_salle'),

    # Notes (parcours Niveau → Classes → Matières → Saisie)
    path('notes/', views.notes_niveaux, name='notes_niveaux'),
    path('notes/<str:niveau>/', views.notes_classes, name='notes_classes'),
    path('notes/classe/<int:classe_id>/', views.notes_matieres, name='notes_matieres'),
    path('notes/classe/<int:classe_id>/matiere/<int:matiere_id>/', views.notes_saisie, name='notes_saisie'),
    path('classes/<int:classe_id>/notes/partager/',
     views.notes_partager_classe,
     name='notes_partager_classe'),
    # Enseignants (gestion admin)
    path('enseignants/', views.list_enseignant, name='list_enseignant'),
    path('enseignants/ajouter/', views.add_enseignant, name='add_enseignant'),
    path('enseignants/<int:enseignant_id>/', views.detail_enseignant, name='detail_enseignant'),
    path('enseignants/<int:enseignant_id>/modifier/', views.add_enseignant, name='edit_enseignant'),
    path('enseignants/<int:enseignant_id>/supprimer/', views.delete_enseignant, name='delete_enseignant'),

    # Bulletins
    path('bulletins/', views.bulletin_classes, name='bulletin_classes'),
    path('bulletins/<int:classe_id>/', views.bulletin_eleves, name='bulletin_eleves'),
    path('bulletins/<int:classe_id>/<int:eleve_id>/', views.bulletin_generer, name='bulletin_generer'),
    path('bulletins/<int:classe_id>/<int:eleve_id>/pdf/', views.bulletin_pdf, name='bulletin_pdf'),
    # Créneaux horaires
    path('creneaux/', views.list_creneau, name='list_creneau'),
    path('creneaux/ajouter/', views.add_creneau, name='add_creneau'),
    path('creneaux/<int:creneau_id>/modifier/', views.add_creneau, name='edit_creneau'),
    path('creneaux/<int:creneau_id>/supprimer/', views.delete_creneau, name='delete_creneau'),

     path('appels/', views.appel_classes, name='appel_classes'),
    path('appels/<int:classe_id>/', views.appel_creneaux, name='appel_creneaux'),
    path('appels/<int:classe_id>/creneau/<int:creneau_id>/', views.appel_saisie, name='appel_saisie'),
    path('appels/<int:classe_id>/historique/', views.appel_historique, name='appel_historique'),
 
   
    path('emploi/<int:classe_id>/appel/<int:creneau_id>/', views.appel_depuis_grille, name='appel_depuis_grille'),
    path('emploi/', views.emploi_du_temps_classes, name='emploi_du_temps_classes'),
    path('emploi/<int:classe_id>/', views.emploi_du_temps_grille, name='emploi_du_temps_grille'),
    path('parametres/trimestres/', views.admin_periodes_trimestres, name='admin_periodes_trimestres'),
    path('emploi/semaines/historique/',         views.historique_semaines, name='historique_semaines'),
    path('emploi/semaines/<int:semaine_id>/cloturer/', views.cloturer_semaine, name='cloturer_semaine'),
    path('messages/',                                views.admin_messages,           name='admin_messages'),
    path('messages/envoyer/',                        views.admin_envoyer_message,    name='admin_envoyer_message'),
    path('messages/envoyer/<int:eleve_id>/',         views.admin_envoyer_message,    name='admin_envoyer_message_eleve'),
    path('messages/<int:message_id>/supprimer/',     views.admin_supprimer_message,  name='admin_supprimer_message'),
    path('eleves/<int:eleve_id>/acces/',          views.admin_gestion_acces,  name='admin_gestion_acces'),
    path('eleves/<int:eleve_id>/acces/publier/',  views.admin_publier_acces,  name='admin_publier_acces'),
  
    path(
    'messages/<int:message_id>/repondre/',
    views.admin_repondre_message,
    name='admin_repondre_message'
),
     path('paiements/historique/', views.secretaire_historique_paiements, name='secretaire_historique_paiements'),
     path('historiques/', views.admin_historiques, name='admin_historiques'),
     path('classes/<int:classe_id>/acces/', views.admin_acces_classe, name='admin_acces_classe'),
]
