# ============================================================
# secretaire/models.py
# ============================================================

from django.db import models
from django.utils import timezone
from administrateur.models import Classe, Eleve


class FraisNiveau(models.Model):
    """
    Frais d'inscription et de scolarité pour UN niveau scolaire
    (ex: 6ème, 5ème...). Gérés par le secrétariat.
    Le PDF associé contient le programme scolaire et les informations
    générales du niveau (pas les montants, saisis ici).
    """

    niveau = models.CharField(
        max_length=20, choices=Classe.NIVEAU_CHOICES, unique=True
    )
    montant_inscription = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        help_text="Frais d'inscription pour ce niveau (FCFA)."
    )
    montant_scolarite = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        help_text="Frais de scolarité annuelle pour ce niveau (FCFA)."
    )
    annee_scolaire = models.CharField(max_length=9, default="2026-2027")
    fichier_pdf = models.FileField(
        upload_to='frais_niveaux/', null=True, blank=True,
        help_text="Programme scolaire et informations du niveau (PDF)."
    )
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['niveau']
        verbose_name = "Frais par niveau"
        verbose_name_plural = "Frais par niveau"

    def __str__(self):
        return self.get_niveau_display()

    @property
    def nb_classes(self):
        return Classe.objects.filter(niveau=self.niveau).count()

    @property
    def total(self):
        return self.montant_inscription + self.montant_scolarite

    @property
    def total_tranches(self):
        return sum((t.montant for t in self.tranches.all()), 0)

    @property
    def configure(self):
        """True si des montants ou un PDF ont déjà été saisis pour ce niveau."""
        return bool(self.montant_inscription or self.montant_scolarite or self.fichier_pdf)


class TranchePaiement(models.Model):
    """
    Une tranche de paiement de la scolarité pour un niveau
    (ex: 1ère tranche — 50 000 FCFA — avant le 30/09).
    Le nombre de tranches est libre, défini par le secrétariat.
    """

    frais = models.ForeignKey(
        FraisNiveau, on_delete=models.CASCADE, related_name='tranches'
    )
    libelle = models.CharField(
        max_length=100, help_text="Ex : 1ère tranche, 2ème tranche..."
    )
    montant = models.DecimalField(max_digits=10, decimal_places=0)
    date_limite = models.DateField(
        help_text="Date limite de paiement pour cette tranche."
    )
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['ordre', 'id']
        verbose_name = "Tranche de paiement"
        verbose_name_plural = "Tranches de paiement"

    def __str__(self):
        return f"{self.libelle} — {self.montant} FCFA"


class Paiement(models.Model):
    """
    Un paiement réellement effectué par un parent pour un élève.
    Peut couvrir l'inscription seule, une ou plusieurs tranches, ou
    l'inscription ET une/des tranche(s) en même temps (paiement groupé).
    """

    eleve = models.ForeignKey(
        Eleve, on_delete=models.CASCADE, related_name='paiements'
    )
    date_paiement = models.DateField(
        default=timezone.now, help_text="Date à laquelle le paiement a été effectué."
    )
    paie_inscription = models.BooleanField(
        default=False, help_text="Ce paiement couvre-t-il les frais d'inscription ?"
    )
    tranches = models.ManyToManyField(
        TranchePaiement, blank=True, related_name='paiements',
        help_text="Tranche(s) de scolarité couvertes par ce paiement."
    )
    montant = models.DecimalField(
        max_digits=10, decimal_places=0,
        help_text="Montant réellement reçu pour ce paiement (FCFA)."
    )
    enregistre_par = models.ForeignKey(
        'utilisateurs.Utilisateur', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='paiements_enregistres'
    )
    date_enregistrement = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_paiement', '-id']
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def __str__(self):
        return f"{self.eleve} — {self.montant} FCFA ({self.date_paiement})"

    @property
    def libelle_contenu(self):
        """Ex : 'Inscription, 1ère tranche, 2ème tranche'."""
        parts = []
        if self.paie_inscription:
            parts.append("Frais d'inscription")
        parts += [t.libelle for t in self.tranches.all()]
        return ", ".join(parts) if parts else "—"


# ============================================================
# Fonctions utilitaires de suivi des paiements
# ============================================================

def statut_paiements_eleve(eleve):
    """
    Construit un état complet des paiements d'un élève :
    inscription payée ou non, statut de chaque tranche (payée /
    en attente / en retard), total dû, total payé, solde restant.
    """
    aujourd_hui = timezone.now().date()

    frais = None
    if eleve.classe:
        frais = FraisNiveau.objects.filter(niveau=eleve.classe.niveau).first()

    paiements = list(eleve.paiements.all())
    inscription_payee = any(p.paie_inscription for p in paiements)

    tranches_payees_ids = set()
    for p in paiements:
        tranches_payees_ids.update(p.tranches.values_list('id', flat=True))

    tranches_statut = []
    total_du = 0
    if frais:
        total_du += float(frais.montant_inscription)
        for t in frais.tranches.all():
            payee = t.id in tranches_payees_ids
            en_retard = (not payee) and (t.date_limite < aujourd_hui)
            tranches_statut.append({
                'tranche': t,
                'payee': payee,
                'en_retard': en_retard,
            })
            total_du += float(t.montant)

    total_paye = sum(float(p.montant) for p in paiements)

    return {
        'frais': frais,
        'inscription_payee': inscription_payee,
        'tranches_statut': tranches_statut,
        'paiements': paiements,
        'total_du': total_du,
        'total_paye': total_paye,
        'solde': total_du - total_paye,
        'en_retard': any(t['en_retard'] for t in tranches_statut),
    }


def eleves_en_retard():
    """
    Renvoie la liste des élèves ayant au moins une tranche dont la date
    limite est dépassée et qui n'a pas encore été payée.
    Chaque entrée : {'eleve': ..., 'tranches_en_retard': [...]}
    """
    resultats = []
    for eleve in Eleve.objects.select_related('classe').all():
        if not eleve.classe:
            continue
        statut = statut_paiements_eleve(eleve)
        tranches_retard = [t for t in statut['tranches_statut'] if t['en_retard']]
        if tranches_retard:
            resultats.append({
                'eleve': eleve,
                'tranches_en_retard': tranches_retard,
                'solde': statut['solde'],
            })
    return resultats