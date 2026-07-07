

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from utilisateurs.models import Utilisateur
from datetime import timedelta




class Enseignant(Utilisateur):
   

    telephone = models.CharField(max_length=20, blank=True)
    domaine_enseignement = models.CharField(
        max_length=150, blank=True,
        help_text="Ex : Sciences, Langues, Lettres..."
    )
    classe_principale = models.ForeignKey(
        'Classe', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='enseignants_principaux_de',
        help_text="Classe dont cet enseignant est le professeur principal."
    )

    class Meta:
        verbose_name = "Enseignant"
        verbose_name_plural = "Enseignants"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class CreneauHoraire(models.Model):
    """
    Un créneau horaire fixe de la grille hebdomadaire (ex: 7h30-8h25),
    identique pour toutes les classes de l'établissement.
    """

    JOUR_CHOICES = [
        ('lundi', 'Lundi'),
        ('mardi', 'Mardi'),
        ('mercredi', 'Mercredi'),
        ('jeudi', 'Jeudi'),
        ('vendredi', 'Vendredi'),
        ('samedi', 'Samedi'),
    ]

    jour = models.CharField(max_length=10, choices=JOUR_CHOICES)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    est_pause = models.BooleanField(
        default=False,
        help_text="Cochez pour une pause (récréation, déjeuner) : aucun cours n'y est assigné."
    )

    class Meta:
        ordering = ['jour', 'heure_debut']
        unique_together = ['jour', 'heure_debut']
        verbose_name = "Créneau horaire"
        verbose_name_plural = "Créneaux horaires"

    def __str__(self):
        return f"{self.get_jour_display()} {self.heure_debut.strftime('%Hh%M')}-{self.heure_fin.strftime('%Hh%M')}"


class Salle(models.Model):
    """Une salle physique de l'établissement."""

    nom = models.CharField(max_length=50, unique=True)
    capacite = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ['nom']
        verbose_name = "Salle"
        verbose_name_plural = "Salles"

    def __str__(self):
        return self.nom


class Matiere(models.Model):
    """Une matière enseignée (ex: Mathématiques)."""

    GROUPE_CHOICES = [
        ('scientifique', 'Matières Scientifiques'),
        ('litteraire', 'Matières Littéraires'),
        ('autre', 'Autres Matières'),
    ]

    nom_matiere = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    groupe = models.CharField(
        max_length=20, choices=GROUPE_CHOICES, default='autre',
        help_text="Catégorie utilisée pour regrouper les matières sur le bulletin."
    )

    class Meta:
        ordering = ['nom_matiere']
        verbose_name = "Matière"
        verbose_name_plural = "Matières"

    def __str__(self):
        return self.nom_matiere


class Classe(models.Model):
    """Une classe (ex: 6ème A), liée à une salle et plusieurs matières."""

    NIVEAU_CHOICES = [
        ('6eme', '6ème'),
        ('5eme', '5ème'),
        ('4eme', '4ème'),
        ('3eme', '3ème'),
        ('seconde', 'Seconde'),
        ('premiere', '1ère'),
        ('terminale', 'Terminale'),
    ]

    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES)
    salle = models.ForeignKey(
        Salle, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='classes'
    )
    matieres = models.ManyToManyField(
        Matiere, blank=True, related_name='classes',
        through='ClasseMatiere'
    )
    enseignant_principal = models.ForeignKey(
        'Enseignant', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='classes_dirigees'
    )

    class Meta:
        ordering = ['niveau']
        verbose_name = "Classe"
        verbose_name_plural = "Classes"

    def __str__(self):
        return f"{self.get_niveau_display()}" + (f" — {self.salle}" if self.salle else "")

    @property
    def nom(self):
        """Alias utilisé dans les templates ({{ classe.nom }})."""
        return str(self)

    @property
    def effectif(self):
        return self.eleves.count()


class ClasseMatiere(models.Model):
    """
    Table intermédiaire entre Classe et Matiere : porte le coefficient
    et le volume horaire hebdomadaire propres à cette matière, pour cette classe.
    (Le même Mathématiques peut avoir un coef différent en 6ème et en Terminale.)
    """

    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    enseignant = models.ForeignKey(
        Enseignant, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='matieres_enseignees',
        help_text="Enseignant qui dispense cette matière dans cette classe."
    )

    coefficient = models.DecimalField(
        max_digits=4, decimal_places=1, default=1,
        validators=[MinValueValidator(0.5)],
        help_text="Coefficient utilisé pour le calcul de la moyenne pondérée."
    )
    heures_semaine = models.DecimalField(
        max_digits=4, decimal_places=1, default=1,
        validators=[MinValueValidator(0)],
        help_text="Nombre d'heures de cours par semaine pour cette matière dans cette classe."
    )

    class Meta:
        unique_together = ['classe', 'matiere']
        verbose_name = "Matière de la classe"
        verbose_name_plural = "Matières des classes"

    def __str__(self):
        return f"{self.matiere} (coef. {self.coefficient}) — {self.classe}"


class EmploiDuTemps(models.Model):
    

    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='emploi_du_temps')
    creneau = models.ForeignKey(CreneauHoraire, on_delete=models.CASCADE, related_name='emplois')
    matiere = models.ForeignKey(Matiere, on_delete=models.SET_NULL, null=True, blank=True, related_name='emplois')
    enseignant = models.ForeignKey(
        Enseignant, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='emplois_du_temps'
    )
    semaine = models.ForeignKey(
       'SemaineScolaire',
       on_delete=models.CASCADE,
       related_name='emplois_du_temps',
        
   )

    class Meta:
        unique_together = ['semaine', 'classe', 'creneau']
        ordering = ['creneau__jour', 'creneau__heure_debut']
        verbose_name = "Case d'emploi du temps"
        verbose_name_plural = "Emploi du temps"

    def __str__(self):
        return f"{self.classe} — {self.creneau} — {self.matiere or 'Libre'}"


# ============================================================
# MODIFICATION administrateur/models.py
# Ajoute le champ 'compte' dans la classe Eleve
# ============================================================
#
# Trouve la classe Eleve dans ton models.py et ajoute
# le champ 'compte' comme indiqué ci-dessous.
# ============================================================


class Eleve(models.Model):
    """Un élève inscrit, avec son parent/tuteur."""

    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]

    matricule = models.CharField(max_length=20, unique=True, blank=True)
    nom       = models.CharField(max_length=100)
    prenom    = models.CharField(max_length=100)
    date_naissance = models.DateField()
    sexe      = models.CharField(max_length=1, choices=SEXE_CHOICES)
    classe    = models.ForeignKey(
        'Classe', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='eleves'
    )

    # ── Informations du parent / tuteur ──
    nom_parent       = models.CharField(max_length=150)
    telephone_parent = models.CharField(max_length=20)
    email_parent     = models.EmailField(blank=True, null=True)

    # ── Compte de connexion ──
    # ↓↓↓ NOUVEAU CHAMP À AJOUTER ↓↓↓
    compte = models.OneToOneField(
        'utilisateurs.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eleve_profil',
        help_text="Compte de connexion de l'élève (role='eleve')."
    )

    date_inscription = models.DateField(default=timezone.now)

    class Meta:
        ordering = ['-date_inscription', 'nom']
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"

    def __str__(self):
        return f"{self.nom} {self.prenom}"

    def save(self, *args, **kwargs):
        if not self.matricule:
            annee = timezone.now().year
            dernier = Eleve.objects.filter(
                matricule__startswith=f"ELV-{annee}-"
            ).order_by('-matricule').first()

            if dernier:
                dernier_numero = int(dernier.matricule.split('-')[-1])
                nouveau_numero = dernier_numero + 1
            else:
                nouveau_numero = 1

            self.matricule = f"ELV-{annee}-{nouveau_numero:04d}"

        super().save(*args, **kwargs)




class Note(models.Model):
  

    TRIMESTRE_CHOICES = [
        ('T1', 'Trimestre 1'),
        ('T2', 'Trimestre 2'),
        ('T3', 'Trimestre 3'),
    ]

    EVALUATION_CHOICES = [
        ('sequence1', 'Séquence 1'),
        ('sequence2', 'Séquence 2'),
        ('examen', 'Examen'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='notes')
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='notes')
    trimestre = models.CharField(max_length=2, choices=TRIMESTRE_CHOICES)
    evaluation = models.CharField(max_length=20, choices=EVALUATION_CHOICES)

    valeur = models.DecimalField(
        max_digits=4, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        help_text="Note sur 20. Laisser vide si l'élève n'a pas encore de note."
    )

    date_saisie = models.DateTimeField(auto_now=True)

    class Meta:
        # Une seule note par élève, par matière, par trimestre, par évaluation.
        unique_together = ['eleve', 'matiere', 'trimestre', 'evaluation']
        ordering = ['trimestre', 'evaluation']
        verbose_name = "Note"
        verbose_name_plural = "Notes"

    def __str__(self):
        valeur_str = self.valeur if self.valeur is not None else "—"
        return f"{self.eleve} — {self.matiere} — {self.get_evaluation_display()} ({self.get_trimestre_display()}) : {valeur_str}/20"

    @staticmethod
    def moyenne(eleve, matiere, trimestre):
        """
        Calcule la moyenne d'un élève pour une matière et un trimestre donnés,
        en ignorant les notes vides (None). Renvoie None si aucune note saisie.
        """
        notes = Note.objects.filter(
            eleve=eleve, matiere=matiere, trimestre=trimestre, valeur__isnull=False
        ).values_list('valeur', flat=True)

        if not notes:
            return None

        return round(sum(notes) / len(notes), 2)

    @staticmethod
    def moyenne_generale_ponderee(eleve, trimestre):
        """
        Calcule la moyenne générale d'un élève pour un trimestre, en pondérant
        chaque matière par son coefficient (ClasseMatiere.coefficient).
        Les matières sans aucune note saisie sont ignorées (pas comptées comme 0).
        """
        if not eleve.classe:
            return None

        total_points = 0
        total_coef = 0

        classe_matieres = ClasseMatiere.objects.filter(classe=eleve.classe)

        for cm in classe_matieres:
            moy_matiere = Note.moyenne(eleve, cm.matiere, trimestre)
            if moy_matiere is not None:
                total_points += float(moy_matiere) * float(cm.coefficient)
                total_coef += float(cm.coefficient)

        if total_coef == 0:
            return None

        return round(total_points / total_coef, 2)


class Bulletin:
    """
    Classe utilitaire (pas un modèle de base de données) qui regroupe tous
    les calculs nécessaires pour générer un bulletin : moyenne par matière,
    rang de l'élève, statistiques de classe (min/moy/max), moyennes par
    groupe de matières, rang dans la classe.

    Usage :
        b = Bulletin(classe, trimestre)
        b.classement()              -> liste des élèves triés par moyenne générale
        b.rang_eleve(eleve)          -> position de l'élève dans le classement
        b.stats_matiere(matiere)     -> {'min': ..., 'moy': ..., 'max': ...}
        b.moyenne_groupe(eleve, 'scientifique')
    """

    def __init__(self, classe, trimestre):
        self.classe = classe
        self.trimestre = trimestre
        self._eleves = list(classe.eleves.all())
        self._classe_matieres = list(ClasseMatiere.objects.filter(classe=classe).select_related('matiere'))

    def classement(self):
        """
        Renvoie la liste des élèves de la classe triés par moyenne générale
        décroissante, sous forme de tuples (eleve, moyenne). Les élèves sans
        aucune moyenne calculable sont placés en fin de liste.
        """
        resultats = []
        for eleve in self._eleves:
            moy = Note.moyenne_generale_ponderee(eleve, self.trimestre)
            resultats.append((eleve, moy))

        # Trie par moyenne décroissante ; les None vont à la fin.
        resultats.sort(key=lambda t: (t[1] is None, -(t[1] or 0)))
        return resultats

    def rang_eleve(self, eleve):
        """Renvoie le rang (1 = premier) de cet élève dans la classe, ou None."""
        classement = self.classement()
        for position, (e, moy) in enumerate(classement, start=1):
            if e.id == eleve.id:
                return position if moy is not None else None
        return None

    def moyenne_premier(self):
        classement = self.classement()
        return classement[0][1] if classement else None

    def moyenne_dernier(self):
        classement = [c for c in self.classement() if c[1] is not None]
        return classement[-1][1] if classement else None

    def moyenne_classe(self):
        """Moyenne générale de la classe (moyenne des moyennes des élèves)."""
        moyennes = [moy for _, moy in self.classement() if moy is not None]
        if not moyennes:
            return None
        return round(sum(moyennes) / len(moyennes), 2)

    def stats_matiere(self, matiere):
        """
        Renvoie {'min': ..., 'moy': ..., 'max': ...} des moyennes de TOUS les
        élèves de la classe pour cette matière et ce trimestre. None si aucune
        note saisie pour personne.
        """
        moyennes = []
        for eleve in self._eleves:
            moy = Note.moyenne(eleve, matiere, self.trimestre)
            if moy is not None:
                moyennes.append(moy)

        if not moyennes:
            return {'min': None, 'moy': None, 'max': None}

        return {
            'min': min(moyennes),
            'moy': round(sum(moyennes) / len(moyennes), 2),
            'max': max(moyennes),
        }

    def moyenne_groupe(self, eleve, groupe):
        """
        Moyenne pondérée des matières appartenant à un groupe donné
        ('scientifique', 'litteraire', 'autre') pour cet élève.
        """
        total_points = 0
        total_coef = 0

        for cm in self._classe_matieres:
            if cm.matiere.groupe != groupe:
                continue
            moy = Note.moyenne(eleve, cm.matiere, self.trimestre)
            if moy is not None:
                total_points += float(moy) * float(cm.coefficient)
                total_coef += float(cm.coefficient)

        if total_coef == 0:
            return None

        return round(total_points / total_coef, 2)

    def matieres_par_groupe(self):
        """
        Renvoie un dict {groupe_code: [liste de ClasseMatiere]} pour organiser
        l'affichage du bulletin section par section.
        """
        groupes = {'scientifique': [], 'litteraire': [], 'autre': []}
        for cm in self._classe_matieres:
            groupes.setdefault(cm.matiere.groupe, []).append(cm)
        return groupes


class Presence(models.Model):
    """Présence d'un élève à un cours."""
 
    STATUT_CHOICES = [
        ('present', 'Présent'),
        ('absent',  'Absent'),
        ('retard',  'Retard'),
    ]
 
    eleve    = models.ForeignKey(Eleve,          on_delete=models.CASCADE, related_name='presences')
    classe   = models.ForeignKey(Classe,         on_delete=models.CASCADE, related_name='presences')
    creneau  = models.ForeignKey(CreneauHoraire, on_delete=models.CASCADE, related_name='presences')
    date     = models.DateField()
    statut   = models.CharField(max_length=10, choices=STATUT_CHOICES, default='present')
 
    # ── NOUVEAU CHAMP ──────────────────────────────────────
    # Permet de distinguer absence justifiée / non justifiée
    # Modifiable par l'admin ou le secrétaire après coup
    justifiee = models.BooleanField(
        default=False,
        help_text="Cochez si l'absence est justifiée (certificat médical, autorisation...)"
    )
 
    enregistre_par = models.ForeignKey(
        'utilisateurs.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='presences_enregistrees',
    )
 
    # Lien optionnel vers la semaine scolaire
    semaine = models.ForeignKey(
        'SemaineScolaire',
        on_delete=models.CASCADE,
        related_name='presences',
        null=True, blank=True,
    )
 
    class Meta:
        unique_together = ['eleve', 'classe', 'date', 'creneau']
        ordering        = ['-date']
        verbose_name    = "Présence"
        verbose_name_plural = "Présences"
 
    def __str__(self):
        return f"{self.eleve} — {self.date} — {self.get_statut_display()}"
 

class AppelVerrouille(models.Model):
    """
    Marque qu'un appel (pour une classe, un créneau, une date donnés) a été
    définitivement enregistré. Une fois cette ligne créée, l'enseignant ne
    peut plus modifier les présences correspondantes — seul un admin peut
    supprimer cette ligne pour débloquer une correction.
    """

    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='appels_verrouilles')
    creneau = models.ForeignKey(CreneauHoraire, on_delete=models.CASCADE, related_name='appels_verrouilles')
    date = models.DateField()
    verrouille_par = models.ForeignKey(
        Enseignant, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='appels_verrouilles_par_moi'
    )
    date_verrouillage = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['classe', 'creneau', 'date']
        verbose_name = "Appel verrouillé"
        verbose_name_plural = "Appels verrouillés"

    def __str__(self):
        return f"{self.classe} — {self.creneau} — {self.date} (verrouillé)"


class BulletinAppreciation(models.Model):
    """
    Informations complémentaires d'un bulletin pour un élève à un trimestre
    donné : heures d'absence (justifiées / non justifiées) et appréciation
    du conseil de classe. Une ligne par élève par trimestre.
    """

    TRIMESTRE_CHOICES = Note.TRIMESTRE_CHOICES

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='bulletins')
    trimestre = models.CharField(max_length=2, choices=TRIMESTRE_CHOICES)

    absences_justifiees_heures = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    absences_non_justifiees_heures = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    appreciation_conseil = models.TextField(
        blank=True,
        help_text="Appréciation générale du conseil de classe pour ce trimestre."
    )
    decision_conseil = models.CharField(
        max_length=100, blank=True,
        help_text="Ex : Admis(e), Travail insuffisant, Conseil d'avertissement..."
    )

    class Meta:
        unique_together = ['eleve', 'trimestre']
        verbose_name = "Appréciation de bulletin"
        verbose_name_plural = "Appréciations de bulletin"

    def __str__(self):
        return f"{self.eleve} — {self.get_trimestre_display()}"
    
class NoteVerrou(models.Model):
   
 
    TRIMESTRE_CHOICES = [
        ('T1', 'Trimestre 1'),
        ('T2', 'Trimestre 2'),
        ('T3', 'Trimestre 3'),
    ]
 
    classe    = models.ForeignKey('Classe',  on_delete=models.CASCADE, related_name='note_verrous')
    matiere   = models.ForeignKey('Matiere', on_delete=models.CASCADE, related_name='note_verrous')
    trimestre = models.CharField(max_length=2, choices=TRIMESTRE_CHOICES)
 
    verrouille    = models.BooleanField(default=False)
    verrouille_le = models.DateTimeField(null=True, blank=True)
    verrouille_par = models.ForeignKey(
        'utilisateurs.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='notes_verrouillees',
    )
 
    class Meta:
        unique_together = ['classe', 'matiere', 'trimestre']
        verbose_name = "Verrou de notes"
        verbose_name_plural = "Verrous de notes"
 
    def __str__(self):
        statut = "🔒" if self.verrouille else "🔓"
        return f"{statut} {self.classe} — {self.matiere} — {self.trimestre}"
 
    @staticmethod
    def est_verrouille(classe, matiere, trimestre):
        v = NoteVerrou.objects.filter(classe=classe, matiere=matiere, trimestre=trimestre).first()
        return v.verrouille if v else False
 
    @staticmethod
    def toutes_notes_saisies(classe, matiere, trimestre):
        """
        Vérifie que tous les élèves de la classe ont au moins
        une note saisie pour cette matière et ce trimestre.
        """
        from django.utils import timezone
        eleves = classe.eleves.all()
        if not eleves.exists():
            return False
 
        for eleve in eleves:
            notes = Note.objects.filter(
                eleve=eleve,
                matiere=matiere,
                trimestre=trimestre,
                valeur__isnull=False,
            )
            if not notes.exists():
                return False
        return True
 
 
class BulletinVerrou(models.Model):
    """
    Verrouille le bulletin d'un élève pour un trimestre.
    Impossible de verrouiller sans que toutes les notes soient saisies.
    Une fois verrouillé, seul l'admin peut modifier.
    """
 
    TRIMESTRE_CHOICES = [
        ('T1', 'Trimestre 1'),
        ('T2', 'Trimestre 2'),
        ('T3', 'Trimestre 3'),
    ]
 
    eleve     = models.ForeignKey('Eleve', on_delete=models.CASCADE, related_name='bulletin_verrous')
    trimestre = models.CharField(max_length=2, choices=TRIMESTRE_CHOICES)
 
    verrouille     = models.BooleanField(default=False)
    verrouille_le  = models.DateTimeField(null=True, blank=True)
    verrouille_par = models.ForeignKey(
        'utilisateurs.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bulletins_verrouilles',
    )
 
    class Meta:
        unique_together = ['eleve', 'trimestre']
        verbose_name = "Verrou de bulletin"
        verbose_name_plural = "Verrous de bulletins"
 
    def __str__(self):
        statut = "🔒" if self.verrouille else "🔓"
        return f"{statut} {self.eleve} — {self.trimestre}"
 
    @staticmethod
    def est_verrouille(eleve, trimestre):
        v = BulletinVerrou.objects.filter(eleve=eleve, trimestre=trimestre).first()
        return v.verrouille if v else False
 
    @staticmethod
    def toutes_notes_saisies(eleve, trimestre):
        """
        Vérifie que toutes les matières de la classe de l'élève
        ont au moins une note saisie pour ce trimestre.
        """
        if not eleve.classe:
            return False
        classe_matieres = ClasseMatiere.objects.filter(classe=eleve.classe)
        if not classe_matieres.exists():
            return False
        for cm in classe_matieres:
            if not Note.objects.filter(
                eleve=eleve,
                matiere=cm.matiere,
                trimestre=trimestre,
                valeur__isnull=False,
            ).exists():
                return False
        return True
 

class SemaineScolaire(models.Model):
   
 
    date_debut = models.DateField(unique=True, help_text="Lundi de la semaine")
    date_fin   = models.DateField(help_text="Samedi de la semaine")
 
    cloturee     = models.BooleanField(default=False)
    cloturee_le  = models.DateTimeField(null=True, blank=True)
    cloturee_par = models.ForeignKey(
        'utilisateurs.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='semaines_cloturees',
    )
 
    class Meta:
        ordering = ['-date_debut']
        verbose_name = "Semaine scolaire"
        verbose_name_plural = "Semaines scolaires"
 
    def __str__(self):
        statut = "🔒" if self.cloturee else "🔓"
        return f"{statut} Semaine du {self.date_debut.strftime('%d/%m')} au {self.date_fin.strftime('%d/%m/%Y')}"
 
    @staticmethod
    def semaine_en_cours():
        """
        Récupère ou crée la semaine en cours (basée sur la date du jour).
        """
        aujourd_hui = timezone.now().date()
        lundi = aujourd_hui - timedelta(days=aujourd_hui.weekday())
        samedi = lundi + timedelta(days=5)
 
        semaine, created = SemaineScolaire.objects.get_or_create(
            date_debut=lundi,
            defaults={'date_fin': samedi}
        )
 
        # Si la semaine vient d'être créée, copie l'emploi du temps
        # de la dernière semaine clôturée (modèle de référence)
        if created:
            derniere_semaine = SemaineScolaire.objects.filter(
                cloturee=True
            ).exclude(id=semaine.id).order_by('-date_debut').first()
 
            if derniere_semaine:
                semaine.copier_emploi_depuis(derniere_semaine)
 
        return semaine
 
    def copier_emploi_depuis(self, autre_semaine):
      
        emplois_source = EmploiDuTemps.objects.filter(semaine=autre_semaine)
        nouveaux = []
        for e in emplois_source:
            nouveaux.append(EmploiDuTemps(
                semaine=self,
                classe=e.classe,
                creneau=e.creneau,
                matiere=e.matiere,
                enseignant=e.enseignant,
            ))
        EmploiDuTemps.objects.bulk_create(nouveaux)
 
    def cloturer(self, utilisateur):
       
        from eleve.models import AccesEleve
 
        self.cloturee     = True
        self.cloturee_le  = timezone.now()
        self.cloturee_par = utilisateur
        self.save()
 
        # Partage les présences à TOUS les élèves de TOUTES les classes
        from .models import Eleve
        eleves = Eleve.objects.all()
        for eleve in eleves:
            AccesEleve.accorder(
                eleve        = eleve,
                type_contenu = 'presence',
                trimestre    = None,
                active_par   = utilisateur,
            )
 
        # Crée automatiquement la semaine suivante en copiant celle-ci
        nouvelle_date_debut = self.date_fin + timedelta(days=2)  # lundi suivant
        nouvelle_date_fin   = nouvelle_date_debut + timedelta(days=5)
 
        nouvelle_semaine, created = SemaineScolaire.objects.get_or_create(
            date_debut=nouvelle_date_debut,
            defaults={'date_fin': nouvelle_date_fin}
        )
        if created:
            nouvelle_semaine.copier_emploi_depuis(self)
 
        return nouvelle_semaine
    
  
class ParentEnfant(models.Model):
   

    parent = models.ForeignKey(
        'utilisateurs.Utilisateur', on_delete=models.CASCADE,
        related_name='enfants_lies',
        limit_choices_to={'role': 'parent'},
    )
    eleve = models.ForeignKey(
        Eleve, on_delete=models.CASCADE,
        related_name='parents_lies',
    )
    lien = models.CharField(
        max_length=50, default='Parent/Tuteur',
        help_text="Ex : Père, Mère, Tuteur..."
    )
    date_liaison = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['parent', 'eleve']
        verbose_name = "Lien parent / enfant"
        verbose_name_plural = "Liens parents / enfants"

    def __str__(self):
        return f"{self.parent} — {self.eleve} ({self.lien})"
    
class TrimestrePeriode(models.Model):
    """
    Définit les dates de début et de fin de chaque trimestre.
    Configuré par l'admin dans les paramètres.
    Utilisé pour calculer automatiquement les heures d'absence
    par trimestre à partir des présences enregistrées.
    """
 
    TRIMESTRE_CHOICES = [
        ('T1', 'Trimestre 1'),
        ('T2', 'Trimestre 2'),
        ('T3', 'Trimestre 3'),
    ]
 
    trimestre  = models.CharField(max_length=2, choices=TRIMESTRE_CHOICES, unique=True)
    date_debut = models.DateField(help_text="Date de début du trimestre")
    date_fin   = models.DateField(help_text="Date de fin du trimestre")
    annee      = models.CharField(
        max_length=9, default='2025-2026',
        help_text="Année scolaire (ex: 2025-2026)"
    )
 
    class Meta:
        ordering = ['trimestre']
        verbose_name = "Période de trimestre"
        verbose_name_plural = "Périodes de trimestres"
 
    def __str__(self):
        return f"{self.get_trimestre_display()} {self.annee} ({self.date_debut} → {self.date_fin})"
 
    @staticmethod
    def get_periode(trimestre):
        """Retourne la période configurée pour un trimestre, ou None."""
        return TrimestrePeriode.objects.filter(trimestre=trimestre).first()
def calculer_absences_eleve(eleve, trimestre):
    """
    Calcule les heures d'absence justifiées et non justifiées
    d'un élève pour un trimestre donné.
    """
    from decimal import Decimal
    from datetime import datetime, date as date_type
 
    periode = TrimestrePeriode.get_periode(trimestre)
 
    if not periode:
        return {
            'justifiees'    : Decimal('0'),
            'non_justifiees': Decimal('0'),
            'total'         : Decimal('0'),
            'periode'       : None,
        }
 
    def duree_heures(creneau):
        debut = datetime.combine(date_type.today(), creneau.heure_debut)
        fin   = datetime.combine(date_type.today(), creneau.heure_fin)
        delta = fin - debut
        return Decimal(str(round(delta.seconds / 3600, 2)))
 
    # Absences dans la plage du trimestre
    absences_qs = Presence.objects.filter(
        eleve=eleve,
        date__gte=periode.date_debut,
        date__lte=periode.date_fin,
        statut='absent',
    ).select_related('creneau')
 
    # Retards dans la plage du trimestre (comptés 0.5h chacun)
    retards_qs = Presence.objects.filter(
        eleve=eleve,
        date__gte=periode.date_debut,
        date__lte=periode.date_fin,
        statut='retard',
    )
 
    justifiees     = Decimal('0')
    non_justifiees = Decimal('0')
 
    for p in absences_qs:
        h = duree_heures(p.creneau)
        if p.justifiee:
            justifiees     += h
        else:
            non_justifiees += h
 
    # Retards : 0.5h, tous non justifiés par défaut
    for p in retards_qs:
        if p.justifiee:
            justifiees     += Decimal('0.5')
        else:
            non_justifiees += Decimal('0.5')
 
    return {
        'justifiees'    : justifiees,
        'non_justifiees': non_justifiees,
        'total'         : justifiees + non_justifiees,
        'periode'       : periode,
    }
 