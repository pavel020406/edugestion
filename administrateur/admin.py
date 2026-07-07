# ============================================================
# accueil/admin.py
# ============================================================

from django.contrib import admin
from .models import (
    Salle, Matiere, Classe, Eleve, Note, ClasseMatiere, Enseignant, Presence,
    BulletinAppreciation, CreneauHoraire, EmploiDuTemps, AppelVerrouille,
)

# NOTE : Utilisateur est déjà enregistré dans votre app 'utilisateurs'
# (utilisateurs/admin.py) — on ne le réenregistre pas ici pour éviter
# l'erreur AlreadyRegistered.


@admin.register(Salle)
class SalleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'capacite')


@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ('nom_matiere', 'groupe', 'description')
    list_filter = ('groupe',)


class ClasseMatiereInline(admin.TabularInline):
    model = ClasseMatiere
    extra = 1


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ('niveau', 'salle', 'effectif')
    inlines = [ClasseMatiereInline]


@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'domaine_enseignement', 'classe_principale', 'telephone')
    search_fields = ('first_name', 'last_name', 'username')
    list_filter = ('domaine_enseignement',)


@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ('matricule', 'nom', 'prenom', 'classe', 'nom_parent', 'date_inscription')
    search_fields = ('nom', 'prenom', 'matricule')
    list_filter = ('classe', 'sexe')


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'matiere', 'trimestre', 'evaluation', 'valeur', 'date_saisie')
    list_filter = ('trimestre', 'evaluation', 'matiere', 'eleve__classe')
    search_fields = ('eleve__nom', 'eleve__prenom', 'eleve__matricule')


@admin.register(CreneauHoraire)
class CreneauHoraireAdmin(admin.ModelAdmin):
    list_display = ('jour', 'heure_debut', 'heure_fin', 'est_pause')
    list_filter = ('jour', 'est_pause')
    ordering = ['jour', 'heure_debut']


@admin.register(EmploiDuTemps)
class EmploiDuTempsAdmin(admin.ModelAdmin):
    list_display = ('classe', 'creneau', 'matiere', 'enseignant')
    list_filter = ('classe', 'creneau__jour')


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'classe', 'creneau', 'date', 'statut', 'enregistre_par')
    list_filter = ('statut', 'classe', 'date')
    search_fields = ('eleve__nom', 'eleve__prenom', 'eleve__matricule')


@admin.register(AppelVerrouille)
class AppelVerrouilleAdmin(admin.ModelAdmin):
    list_display = ('classe', 'creneau', 'date', 'verrouille_par', 'date_verrouillage')
    list_filter = ('classe', 'date')
    actions = ['deverrouiller']

    @admin.action(description="Déverrouiller les appels sélectionnés (permet de les corriger)")
    def deverrouiller(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} appel(s) déverrouillé(s) avec succès.")


@admin.register(BulletinAppreciation)
class BulletinAppreciationAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'trimestre', 'absences_justifiees_heures', 'absences_non_justifiees_heures', 'decision_conseil')
    list_filter = ('trimestre',)
    search_fields = ('eleve__nom', 'eleve__prenom', 'eleve__matricule')

  
from .models import ParentEnfant   


@admin.register(ParentEnfant)
class ParentEnfantAdmin(admin.ModelAdmin):
    list_display = ('parent', 'eleve', 'lien', 'date_liaison')
    list_filter = ('lien',)