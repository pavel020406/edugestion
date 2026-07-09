# ============================================================
# AJOUT dans eleve/models.py
# ============================================================

from django.db import models
from django.utils import timezone


class Message(models.Model):
    """Message envoyé par l'admin à un élève."""

    TYPE_CHOICES = [
        ('general',  'Message général'),
        ('notes',    'Notes'),
        ('bulletin', 'Bulletin'),
        ('emploi',   'Emploi du temps'),
        ('presence', 'Présences'),
    ]

    expediteur   = models.ForeignKey(
        'utilisateurs.Utilisateur', on_delete=models.SET_NULL, null=True,
        related_name='messages_envoyes',
    )
    destinataire = models.ForeignKey(
        'utilisateurs.Utilisateur', on_delete=models.CASCADE,
        related_name='messages_recus',
    )
    eleve = models.ForeignKey(
        'administrateur.Eleve', on_delete=models.CASCADE,
        null=True, blank=True, related_name='messages',
    )
    reponse_a = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reponses',
        help_text="Message d'origine auquel celui-ci répond (vide si c'est un message initial)."
    )

    type_message = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    sujet        = models.CharField(max_length=200)
    contenu      = models.TextField(blank=True)
    fichier_pdf  = models.FileField(upload_to='messages/pdf/', null=True, blank=True)
    lu           = models.BooleanField(default=False)
    date_envoi   = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date_envoi']
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"[{self.get_type_message_display()}] {self.sujet} → {self.destinataire}"


class AccesEleve(models.Model):
    """
    Contrôle l'accès d'un élève à ses données.
    Une ligne = un type de contenu débloqué pour un élève.

    type_contenu : 'notes' | 'bulletin' | 'emploi' | 'presence'
    trimestre    : 'T1' | 'T2' | 'T3' | None (pour emploi)
    actif        : True = l'élève peut voir ce contenu
    """

    TYPE_CHOICES = [
        ('notes',    'Notes'),
        ('bulletin', 'Bulletin'),
        ('emploi',   'Emploi du temps'),
        ('presence', 'Présences'),
    ]

    TRIMESTRE_CHOICES = [
        ('T1', 'Trimestre 1'),
        ('T2', 'Trimestre 2'),
        ('T3', 'Trimestre 3'),
    ]

    eleve = models.ForeignKey(
        'administrateur.Eleve', on_delete=models.CASCADE,
        related_name='acces',
    )
    type_contenu = models.CharField(max_length=20, choices=TYPE_CHOICES)
    trimestre    = models.CharField(
        max_length=2, choices=TRIMESTRE_CHOICES,
        null=True, blank=True,
        help_text="Trimestre concerné (notes/bulletin). Vide pour emploi/présence."
    )
    actif           = models.BooleanField(default=True)
    date_activation = models.DateTimeField(auto_now_add=True)
    active_par      = models.ForeignKey(
        'utilisateurs.Utilisateur', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='acces_accordes',
    )

    class Meta:
        # Un seul verrou par élève + type + trimestre
        unique_together = ['eleve', 'type_contenu', 'trimestre']
        verbose_name = "Accès élève"
        verbose_name_plural = "Accès élèves"

    def __str__(self):
        trim = f" ({self.trimestre})" if self.trimestre else ""
        statut = "✓" if self.actif else "✗"
        return f"{statut} {self.eleve} — {self.get_type_contenu_display()}{trim}"

    @staticmethod
    def a_acces(eleve, type_contenu, trimestre=None):
        """
        Vérifie si un élève a accès à un type de contenu.
        Retourne True / False.
        """
        return AccesEleve.objects.filter(
            eleve=eleve,
            type_contenu=type_contenu,
            trimestre=trimestre,
            actif=True,
        ).exists()

    @staticmethod
    def accorder(eleve, type_contenu, trimestre=None, active_par=None):
        """
        Accorde ou réactive l'accès à un contenu pour un élève.
        Crée la ligne si elle n'existe pas, l'active si elle existe.
        """
        acces, created = AccesEleve.objects.get_or_create(
            eleve=eleve,
            type_contenu=type_contenu,
            trimestre=trimestre,
            defaults={'actif': True, 'active_par': active_par},
        )
        if not created and not acces.actif:
            acces.actif = True
            acces.active_par = active_par
            acces.save()
        return acces

    @staticmethod
    def revoquer(eleve, type_contenu, trimestre=None):
        """Révoque l'accès (désactive sans supprimer)."""
        AccesEleve.objects.filter(
            eleve=eleve,
            type_contenu=type_contenu,
            trimestre=trimestre,
        ).update(actif=False)