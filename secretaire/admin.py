from django.contrib import admin
from .models import FraisNiveau, TranchePaiement, Paiement


class TranchePaiementInline(admin.TabularInline):
    model = TranchePaiement
    extra = 1


@admin.register(FraisNiveau)
class FraisNiveauAdmin(admin.ModelAdmin):
    list_display = ('niveau', 'montant_inscription', 'montant_scolarite', 'total', 'annee_scolaire')
    list_filter = ('annee_scolaire',)
    inlines = [TranchePaiementInline]


@admin.register(TranchePaiement)
class TranchePaiementAdmin(admin.ModelAdmin):
    list_display = ('frais', 'libelle', 'montant', 'date_limite', 'ordre')
    list_filter = ('date_limite',)


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'date_paiement', 'libelle_contenu', 'montant', 'enregistre_par')
    list_filter = ('date_paiement',)