

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from io import BytesIO
from django.http import HttpResponse
from parent.services import creer_ou_lier_parent

from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.utils import timezone
from administrateur.models import NoteVerrou, BulletinVerrou, ClasseMatiere
from eleve.models import AccesEleve
from datetime import timedelta
from .models import SemaineScolaire, EmploiDuTemps, CreneauHoraire, Classe, Enseignant, Presence, AppelVerrouille


 


from .models import (
    Eleve, Matiere, Classe, Salle, Note, ClasseMatiere, Enseignant, Bulletin,
    BulletinAppreciation, CreneauHoraire, EmploiDuTemps, Presence, AppelVerrouille,
    NoteVerrou  
)

# ============================================================
# PAGES PUBLIQUES
# ============================================================
from .models import Etablissement
 
 
def get_etablissement():
    """Renvoie l'établissement configuré (le premier, en mode mono-établissement)."""
    return Etablissement.objects.first()
 
def accueil(request):
    if request.user.is_authenticated:
        return redirect_selon_role(request.user)
    return render(request, 'index.html')
def setup_etablissement(request):
    # ── Verrou : une seule école possible pour toute l'installation ──
    if Etablissement.objects.exists():
        messages.info(request, "Un établissement est déjà configuré pour cette plateforme.")
        return redirect('accueil')
 
    if request.method == 'POST':
        nom                 = request.POST.get('nom', '').strip()
        sigle               = request.POST.get('sigle', '').strip()
        type_etablissement  = request.POST.get('type_etablissement', 'lycee')
        ministere           = request.POST.get('ministere', 'minesec')
        region              = request.POST.get('region', '').strip()
        departement         = request.POST.get('departement', '').strip()
        delegation_regionale = request.POST.get('delegation_regionale', '').strip()
        delegation_departementale = request.POST.get('delegation_departementale', '').strip()
        ville               = request.POST.get('ville', '').strip()
        boite_postale       = request.POST.get('boite_postale', '').strip()
        telephone           = request.POST.get('telephone', '').strip()
        email               = request.POST.get('email', '').strip()
        logo                = request.FILES.get('logo')
 
        if not nom:
            messages.error(request, "Le nom de l'établissement est obligatoire.")
            return render(request, 'setup/setup_etablissement.html')
 
        etablissement = Etablissement.objects.create(
            nom=nom,
            sigle=sigle or None,
            type_etablissement=type_etablissement,
            ministere=ministere,
            region=region or None,
            departement=departement or None,
            delegation_regionale=delegation_regionale or None,
            delegation_departementale=delegation_departementale or None,
            ville=ville or None,
            boite_postale=boite_postale or None,
            telephone=telephone or None,
            email=email or None,
        )
        if logo:
            etablissement.logo = logo
            etablissement.save()
 
        messages.success(request, f"✓ Établissement « {nom} » créé. Créez maintenant le compte administrateur.")
        return redirect('setup_admin')
 
    return render(request, 'setup/setup_etablissement.html')
 
# ============================================================
# ÉTAPE 2 : Créer le compte administrateur
# ============================================================
 
def setup_admin(request):
    etablissement = get_etablissement()
    if not etablissement:
        messages.warning(request, "Veuillez d'abord créer un établissement.")
        return redirect('setup_etablissement')
 
    # Si un admin existe déjà, cette étape n'a plus de raison d'être.
    if Utilisateur.objects.filter(role='admin').exists():
        return redirect('setup_secretaire')
 
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        username   = request.POST.get('username', '').strip()
        email      = request.POST.get('email', '').strip()
        password   = request.POST.get('password', '').strip()
        password2  = request.POST.get('password2', '').strip()
 
        if not first_name or not last_name or not username or not password:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return render(request, 'setup/setup_admin.html', {'etablissement': etablissement})
 
        if password != password2:
            messages.error(request, "Les deux mots de passe ne correspondent pas.")
            return render(request, 'setup/setup_admin.html', {'etablissement': etablissement})
 
        if Utilisateur.objects.filter(username=username).exists():
            messages.error(request, f"Le nom d'utilisateur « {username} » est déjà utilisé.")
            return render(request, 'setup/setup_admin.html', {'etablissement': etablissement})
 
        admin = Utilisateur(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role='admin',
            etablissement=etablissement,   
        )
        admin.set_password(password)
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
 
        messages.success(request, f"✓ Compte administrateur « {username} » créé avec succès.")
        return redirect('setup_secretaire')
 
    return render(request, 'setup/setup_admin.html', {'etablissement': etablissement})
 
 
# ============================================================
# ÉTAPE 3 : Créer le compte secrétaire (OPTIONNELLE — peut être passée)
# ============================================================
 
def setup_secretaire(request):
    etablissement = get_etablissement()
    if not etablissement:
        return redirect('setup_etablissement')
 
    if not Utilisateur.objects.filter(role='admin').exists():
        return redirect('setup_admin')
 
    if request.method == 'POST':
        action = request.POST.get('action', 'creer')
 
        if action == 'passer':
            messages.info(request, "Étape passée. Vous pourrez créer un compte secrétaire plus tard depuis le dashboard.")
            return redirect('connexion')
 
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        username   = request.POST.get('username', '').strip()
        email      = request.POST.get('email', '').strip()
        password   = request.POST.get('password', '').strip()
 
        if not first_name or not last_name or not username or not password:
            messages.error(request, "Veuillez remplir tous les champs obligatoires, ou cliquez sur « Passer cette étape ».")
            return render(request, 'setup/setup_secretaire.html', {'etablissement': etablissement})
 
        if Utilisateur.objects.filter(username=username).exists():
            messages.error(request, f"Le nom d'utilisateur « {username} » est déjà utilisé.")
            return render(request, 'setup/setup_secretaire.html', {'etablissement': etablissement})
 
        secretaire = Utilisateur(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role='secretaire',
            etablissement=etablissement,
        )
        secretaire.set_password(password)
        secretaire.save()
 
        messages.success(request, f"✓ Compte secrétaire « {username} » créé. Vous pouvez maintenant vous connecter.")
        return redirect('connexion')
 
    return render(request, 'setup/setup_secretaire.html', {'etablissement': etablissement})

login_required
def admin_modifier_etablissement(request):
    """Modifie les informations de l'établissement depuis le dashboard admin."""
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    etablissement = get_etablissement()
    if not etablissement:
        messages.error(request, "Aucun établissement configuré.")
        return redirect('admin_periodes_trimestres')
 
    if request.method == 'POST':
        etablissement.nom                 = request.POST.get('nom', '').strip() or etablissement.nom
        etablissement.sigle               = request.POST.get('sigle', '').strip() or None
        etablissement.type_etablissement  = request.POST.get('type_etablissement', etablissement.type_etablissement)
        etablissement.ministere           = request.POST.get('ministere', etablissement.ministere)
        etablissement.region              = request.POST.get('region', '').strip() or None
        etablissement.departement         = request.POST.get('departement', '').strip() or None
        etablissement.delegation_regionale        = request.POST.get('delegation_regionale', '').strip() or None
        etablissement.delegation_departementale   = request.POST.get('delegation_departementale', '').strip() or None
        etablissement.ville               = request.POST.get('ville', '').strip() or None
        etablissement.boite_postale       = request.POST.get('boite_postale', '').strip() or None
        etablissement.telephone           = request.POST.get('telephone', '').strip() or None
        etablissement.email               = request.POST.get('email', '').strip() or None
 
        if not etablissement.nom:
            messages.error(request, "Le nom de l'établissement est obligatoire.")
            return redirect('admin_periodes_trimestres')
 
        logo = request.FILES.get('logo')
        if logo:
            etablissement.logo = logo
 
        etablissement.save()
        messages.success(request, "✓ Informations de l'établissement mises à jour avec succès.")
        return redirect('admin_periodes_trimestres')
 
    return redirect('admin_periodes_trimestres')
# ============================================================
# AUTHENTIFICATION
# ============================================================

def redirect_selon_role(user):
    if user.role == 'admin':
        return redirect('dashboard')
    elif user.role == 'enseignant':
        return redirect('dashboard_enseignant')
    elif user.role == 'eleve':
        return redirect('dashboard_eleve')
    elif user.role == 'secretaire':         
        return redirect('dashboard_secretaire')
    elif user.role == 'parent':         
        return redirect('dashboard_parent')
    else:
        return redirect('accueil')


def connexion(request):
    if request.user.is_authenticated:
        return redirect_selon_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect_selon_role(user)
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            return render(request, 'authen/login.html')

    return render(request, 'authen/login.html')


def deconnexion(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté.")
    return redirect('connexion')


# ============================================================
# DASHBOARDS
# ============================================================

from secretaire.models import eleves_en_retard
 
 
@login_required
def dashboard(request):
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    # ── Taux de présence du jour ──
    presences_du_jour = Presence.objects.filter(date=date.today())
    total_presences_jour = presences_du_jour.count()
    if total_presences_jour > 0:
        nb_presents = presences_du_jour.filter(statut='present').count()
        taux_presence = round((nb_presents / total_presences_jour) * 100)
    else:
        taux_presence = None  # aucun appel fait aujourd'hui pour l'instant
 
    # ── Paiements en retard ──
    nb_paiements_retard = len(eleves_en_retard())
 
    contexte = {
        'active_page'        : 'dashboard',
        'total_eleves'       : Eleve.objects.count(),
        'total_classes'      : Classe.objects.count(),
        'total_enseignants'  : Enseignant.objects.count(),
        'taux_presence'      : taux_presence,
        'nb_paiements_retard': nb_paiements_retard,
    }
    return render(request, 'admin_dashboard/admin_dashboard.html', contexte)

# ============================================================
# ÉLÈVES
# ============================================================

@login_required
def list_eleve(request):
    search = request.GET.get('search', '')
    classe_id = request.GET.get('classe', '')

    eleves = Eleve.objects.select_related('classe').all()
    classe_filtree = None

    if search:
        eleves = eleves.filter(nom__icontains=search) | eleves.filter(prenom__icontains=search)
    if classe_id:
        eleves = eleves.filter(classe_id=classe_id)
        classe_filtree = Classe.objects.filter(id=classe_id).first()
    for e in eleves:
     print(
        "id =", e.id,
        "pk =", e.pk,
        "matricule =", e.matricule
    )
    return render(request, 'admin_dashboard/eleves/list_eleve.html', {
        'eleves': eleves,
        'classes': Classe.objects.all(),
        'classe_filtree': classe_filtree,
        'total': eleves.count(),
        'active_page': 'eleves',
    })


@login_required
def add_eleve(request, eleve_id=None):
    eleve = None
    if eleve_id:
        eleve = get_object_or_404(Eleve, id=eleve_id)
 
    if request.method == 'POST':
        # ── Infos personnelles ──
        nom              = request.POST.get('nom', '').strip()
        prenom           = request.POST.get('prenom', '').strip()
        date_naissance   = request.POST.get('date_naissance')
        sexe             = request.POST.get('sexe')
        classe_id        = request.POST.get('classe')
        nom_parent       = request.POST.get('nom_parent', '').strip()
        telephone_parent = request.POST.get('telephone_parent', '').strip()
        email_parent     = request.POST.get('email_parent', '').strip()
 
        # ── Compte de connexion ──
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
 
        # ── Validation ──
        if not nom or not prenom or not date_naissance or not sexe:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return render(request, 'admin_dashboard/eleves/add_eleve.html', {
                'eleve': eleve,
                'classes': Classe.objects.all(),
                'active_page': 'eleves',
            })
 
        if eleve:
            # ────── MODIFICATION ──────
            eleve.nom              = nom
            eleve.prenom           = prenom
            eleve.date_naissance   = date_naissance
            eleve.sexe             = sexe
            eleve.classe_id        = classe_id or None
            eleve.nom_parent       = nom_parent
            eleve.telephone_parent = telephone_parent
            eleve.email_parent     = email_parent or None
            eleve.save()
 
            # Met à jour le compte si l'élève en a déjà un
            if eleve.compte:
                if username:
                    eleve.compte.username   = username
                    eleve.compte.first_name = prenom
                    eleve.compte.last_name  = nom
                if password:
                    eleve.compte.set_password(password)
                eleve.compte.save()
 
            messages.success(request, f"L'élève {nom} {prenom} a été modifié avec succès.")
 
        else:
            # ────── CRÉATION ──────
 
            # Username par défaut : prenom.nom (minuscules, sans espaces)
            if not username:
                username = f"{prenom}.{nom}".lower().replace(' ', '')
 
            # Vérifie unicité du username
            if Utilisateur.objects.filter(username=username).exists():
                messages.error(
                    request,
                    f"Le nom d'utilisateur « {username} » est déjà utilisé. "
                    f"Choisissez-en un autre."
                )
                return render(request, 'admin_dashboard/eleves/add_eleve.html', {
                    'eleve': None,
                    'classes': Classe.objects.all(),
                    'active_page': 'eleves',
                })
 
            # Mot de passe par défaut : matricule généré automatiquement
            # (on crée d'abord l'élève pour avoir le matricule, puis le compte)
            eleve = Eleve.objects.create(
                nom              = nom,
                prenom           = prenom,
                date_naissance   = date_naissance,
                sexe             = sexe,
                classe_id        = classe_id or None,
                nom_parent       = nom_parent,
                telephone_parent = telephone_parent,
                email_parent     = email_parent or None,
            )
 
            # Mot de passe par défaut = matricule si non saisi
            mdp_final = password if password else eleve.matricule
 
            # Crée le compte Utilisateur
            compte = Utilisateur(
                username   = username,
                first_name = prenom,
                last_name  = nom,
                email      = email_parent or '',
                role       = 'eleve',
            )
            compte.set_password(mdp_final)
            compte.save()
 
            # Lie le compte à l'élève
            eleve.compte = compte
            eleve.save()
            creer_ou_lier_parent(
                eleve=eleve,
                nom_parent=nom_parent,
                telephone_parent=telephone_parent,
                email_parent=email_parent or '',
            )
 
            messages.success(
                request,
                f"Élève inscrit avec succès. "
                f"Identifiant : {username} — "
                f"Mot de passe : {mdp_final}"
            )
 
        return redirect('list_eleve')
 
    return render(request, 'admin_dashboard/eleves/add_eleve.html', {
        'eleve'      : eleve,
        'classes'    : Classe.objects.all(),
        'active_page': 'eleves',
    })

@login_required
def detail_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
 
    # ── Notes récentes (10 dernières) ──
    notes_recentes = Note.objects.filter(
        eleve=eleve, valeur__isnull=False
    ).select_related('matiere').order_by('-date_saisie')[:10]
 
    # ── Moyennes par trimestre ──
    moyennes_trimestres = {}
    for t_code, _ in Note.TRIMESTRE_CHOICES:
        moyennes_trimestres[t_code] = Note.moyenne_generale_ponderee(eleve, t_code)
 
    # ── Présences ──
    dernieres_presences = Presence.objects.filter(
        eleve=eleve
    ).select_related('creneau').order_by('-date')[:8]
 
    nb_presents  = Presence.objects.filter(eleve=eleve, statut='present').count()
    nb_absences  = Presence.objects.filter(eleve=eleve, statut='absent').count()
    nb_retards   = Presence.objects.filter(eleve=eleve, statut='retard').count()
 
    # ── Accès publiés ──
    acces_list = AccesEleve.objects.filter(eleve=eleve).order_by('type_contenu', 'trimestre')
 
    return render(request, 'admin_dashboard/eleves/detail_eleve.html', {
        'eleve'               : eleve,
        'notes_recentes'      : notes_recentes,
        'moyennes_trimestres' : moyennes_trimestres,
        'trimestres'          : Note.TRIMESTRE_CHOICES,
        'dernieres_presences' : dernieres_presences,
        'nb_presents'         : nb_presents,
        'nb_absences'         : nb_absences,
        'nb_retards'          : nb_retards,
        'acces_list'          : acces_list,
        'active_page'         : 'eleves',
    })
 

@login_required
def delete_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    if request.method == 'POST':
        nom_complet = f"{eleve.nom} {eleve.prenom}"
        eleve.delete()
        messages.success(request, f"{nom_complet} a été supprimé avec succès.")
    return redirect('list_eleve')


# ============================================================
# MATIÈRES
# ============================================================

login_required
def list_matiere(request):
    search = request.GET.get('search', '')
 
    matieres = Matiere.objects.all()
    if search:
        matieres = matieres.filter(nom_matiere__icontains=search)
 
    matieres_avec_description = matieres.exclude(description__isnull=True).exclude(description__exact='').count()
 
    return render(request, 'admin_dashboard/matieres/list_matiere.html', {
        'matieres': matieres,
        'total': matieres.count(),
        'matieres_avec_description': matieres_avec_description,
        'active_page': 'matieres',
    })
 
 
def add_matiere(request, matiere_id=None):
    matiere = None
    if matiere_id:
        matiere = get_object_or_404(Matiere, id=matiere_id)

    if request.method == 'POST':
        nom_matiere = request.POST.get('nom_matiere')
        description = request.POST.get('description', '')
        groupe = request.POST.get('groupe', 'autre')          
        if matiere:
            matiere.nom_matiere = nom_matiere
            matiere.description = description or None
            matiere.groupe = groupe                           
            matiere.save()
            messages.success(request, "La matière a été modifiée avec succès.")
        else:
            Matiere.objects.create(
                nom_matiere=nom_matiere,
                description=description or None,
                groupe=groupe,                                  # ← nouvelle ligne
            )
            messages.success(request, "La matière a été ajoutée avec succès.")

        return redirect('list_matiere')

    return render(request, 'admin_dashboard/matieres/add_matiere.html', {
        'matiere': matiere,
        'active_page': 'matieres',
    })
 
@login_required
def detail_matiere(request, matiere_id):
    matiere = get_object_or_404(Matiere, id=matiere_id)
    classes_concernees = matiere.classes.all()
    return render(request, 'admin_dashboard/matieres/detail_matiere.html', {
        'matiere': matiere,
        'classes_concernees': classes_concernees,
        'active_page': 'matieres',
    })
 
 
@login_required
def delete_matiere(request, matiere_id):
    matiere = get_object_or_404(Matiere, id=matiere_id)
    if request.method == 'POST':
        nom = matiere.nom_matiere
        matiere.delete()
        messages.success(request, f"La matière « {nom} » a été supprimée avec succès.")
    return redirect('list_matiere')


# ============================================================
# CLASSES
# ============================================================

@login_required
def list_classe(request):
    classes = Classe.objects.select_related('salle').prefetch_related('matieres').all()

    return render(request, 'admin_dashboard/classes/list_classe.html', {
        'classes': classes,
        'total': classes.count(),
        'active_page': 'classes',
    })


@login_required
def add_classe(request, classe_id=None):
    classe = None
    eleves_count = 0

    if classe_id:
        classe = get_object_or_404(Classe, id=classe_id)
        eleves_count = classe.eleves.count()

    if request.method == 'POST':
        niveau = request.POST.get('niveau')
        nom_salle = request.POST.get('salle', '').strip()
        enseignant_principal_id = request.POST.get('enseignant_principal', '').strip()
        confirmer_changement = request.POST.get('confirmer_changement_principal')

        # Le champ "salle" est un texte libre : on récupère la salle si elle
        # existe déjà (même nom), sinon on la crée à la volée.
        salle_obj = None
        if nom_salle:
            salle_obj, _ = Salle.objects.get_or_create(nom=nom_salle)

        # ---- Règle métier : une classe a un et un seul enseignant principal.
        # Si un principal différent est déjà en place, on bloque et on demande
        # confirmation avant de le remplacer (pas de remplacement silencieux).
        if classe and enseignant_principal_id:
            principal_actuel_id = classe.enseignant_principal_id
            nouveau_id = int(enseignant_principal_id)

            if principal_actuel_id and principal_actuel_id != nouveau_id and not confirmer_changement:
                ancien = classe.enseignant_principal
                messages.error(
                    request,
                    f"{ancien.first_name} {ancien.last_name} est déjà l'enseignant principal de "
                    f"cette classe. Cochez la case de confirmation pour le remplacer."
                )
                return render(request, 'admin_dashboard/classes/add_classe.html', {
                    'classe': classe,
                    'lignes_matieres': _construire_lignes_matieres(classe),
                    'enseignants': Enseignant.objects.all(),
                    'eleves_count': eleves_count,
                    'active_page': 'classes',
                })

        if classe:
            classe.niveau = niveau
            classe.salle = salle_obj
            classe.enseignant_principal_id = enseignant_principal_id if enseignant_principal_id else None
            classe.save()
        else:
            classe = Classe.objects.create(
                niveau=niveau,
                salle=salle_obj,
                enseignant_principal_id=enseignant_principal_id if enseignant_principal_id else None,
            )

        # Pour chaque matière disponible, on regarde si sa case a été cochée.
        # Si oui : on crée ou met à jour sa ligne ClasseMatiere (coef + heures + enseignant).
        # Si non : on supprime la ligne existante (la matière est retirée de la classe).
        for matiere in Matiere.objects.all():
            case_cochee = request.POST.get(f'matiere_{matiere.id}')

            if case_cochee:
                coefficient = request.POST.get(f'coef_{matiere.id}', '1').strip() or '1'
                heures_semaine = request.POST.get(f'heures_{matiere.id}', '1').strip() or '1'
                enseignant_id = request.POST.get(f'enseignant_{matiere.id}', '').strip()

                ClasseMatiere.objects.update_or_create(
                    classe=classe,
                    matiere=matiere,
                    defaults={
                        'coefficient': coefficient,
                        'heures_semaine': heures_semaine,
                        'enseignant_id': enseignant_id if enseignant_id else None,
                    },
                )
            else:
                ClasseMatiere.objects.filter(classe=classe, matiere=matiere).delete()

        messages.success(request, "La classe a été enregistrée avec succès.")
        return redirect('list_classe')

    return render(request, 'admin_dashboard/classes/add_classe.html', {
        'classe': classe,
        'lignes_matieres': _construire_lignes_matieres(classe),
        'enseignants': Enseignant.objects.all(),
        'eleves_count': eleves_count,
        'active_page': 'classes',
    })


def _construire_lignes_matieres(classe):
    """
    Pour préremplir le formulaire de classe : associe à chaque matière
    disponible sa ligne ClasseMatiere existante (ou vide si pas assignée).
    """
    classe_matieres_existantes = {}
    if classe:
        classe_matieres_existantes = {
            cm.matiere_id: cm for cm in ClasseMatiere.objects.filter(classe=classe)
        }

    lignes_matieres = []
    for matiere in Matiere.objects.all():
        cm_existante = classe_matieres_existantes.get(matiere.id)
        lignes_matieres.append({
            'matiere': matiere,
            'cochee': cm_existante is not None,
            'coefficient': cm_existante.coefficient if cm_existante else '',
            'heures_semaine': cm_existante.heures_semaine if cm_existante else '',
            'enseignant_id': cm_existante.enseignant_id if cm_existante else None,
        })
    return lignes_matieres


@login_required
def detail_classe(request, classe_id):
    classe         = get_object_or_404(Classe, id=classe_id)
    classe_matieres = ClasseMatiere.objects.filter(classe=classe).select_related('matiere', 'enseignant')
    eleves         = classe.eleves.all()
 
    # ── Statut d'accès notes par trimestre ──────────────────
    # Vérifie si les notes sont partagées (on prend le 1er élève comme référence)
    premier_eleve      = eleves.first()
    acces_notes_statut = {}
 
    for t_code, _ in Note.TRIMESTRE_CHOICES:
        if premier_eleve:
            acces_notes_statut[t_code] = AccesEleve.a_acces(
                premier_eleve, 'notes', t_code
            )
        else:
            acces_notes_statut[t_code] = False
 
    # ── Verrous notes par matière ────────────────────────────
    # Pour chaque matière + trimestre, vérifie si c'est verrouillé
    verrous_notes = {}
    for cm in classe_matieres:
        for t_code, _ in Note.TRIMESTRE_CHOICES:
            v = NoteVerrou.objects.filter(
                classe=classe,
                matiere=cm.matiere,
                trimestre=t_code,
            ).first()
            verrous_notes[f"{cm.matiere_id}_{t_code}"] = v.verrouille if v else False
 
    # ── Vérifie si toutes les matières sont verrouillées par trimestre ──
    # (condition pour pouvoir partager les notes)
    peut_partager = {}
    for t_code, _ in Note.TRIMESTRE_CHOICES:
        toutes_verrou = all(
            verrous_notes.get(f"{cm.matiere_id}_{t_code}", False)
            for cm in classe_matieres
        )
        peut_partager[t_code] = toutes_verrou and classe_matieres.exists()
 
    return render(request, 'admin_dashboard/classes/detail_classe.html', {
        'classe'             : classe,
        'classe_matieres'    : classe_matieres,
        'eleves'             : eleves,
        'trimestres'         : Note.TRIMESTRE_CHOICES,
        'acces_notes_statut' : acces_notes_statut,
        'peut_partager'      : peut_partager,
        'active_page'        : 'classes',
    })


@login_required
def delete_classe(request, classe_id):
    classe = get_object_or_404(Classe, id=classe_id)
    if request.method == 'POST':
        nom = str(classe)
        classe.delete()
        messages.success(request, f"La classe « {nom} » a été supprimée avec succès.")
    return redirect('list_classe')


# ============================================================
# SALLES
# ============================================================

@login_required
def list_salle(request):
    search = request.GET.get('search', '')

    salles = Salle.objects.all()
    if search:
        salles = salles.filter(nom__icontains=search)

    return render(request, 'admin_dashboard/salles/list_salle.html', {
        'salles': salles,
        'total': salles.count(),
        'active_page': 'salles',
    })


@login_required
def add_salle(request, salle_id=None):
    salle = None
    if salle_id:
        salle = get_object_or_404(Salle, id=salle_id)

    if request.method == 'POST':
        nom = request.POST.get('nom')
        capacite = request.POST.get('capacite') or 30

        if salle:
            salle.nom = nom
            salle.capacite = capacite
            salle.save()
            messages.success(request, "La salle a été modifiée avec succès.")
        else:
            Salle.objects.create(nom=nom, capacite=capacite)
            messages.success(request, "La salle a été ajoutée avec succès.")

        return redirect('list_salle')

    return render(request, 'admin_dashboard/salles/add_salle.html', {
        'salle': salle,
        'active_page': 'salles',
    })


@login_required
def detail_salle(request, salle_id):
    salle = get_object_or_404(Salle, id=salle_id)
    classes_dans_salle = salle.classes.all()
    return render(request, 'admin_dashboard/salles/detail_salle.html', {
        'salle': salle,
        'classes_dans_salle': classes_dans_salle,
        'active_page': 'salles',
    })


@login_required
def delete_salle(request, salle_id):
    salle = get_object_or_404(Salle, id=salle_id)
    if request.method == 'POST':
        nom = salle.nom
        salle.delete()
        messages.success(request, f"La salle « {nom} » a été supprimée avec succès.")
    return redirect('list_salle')


# ============================================================
# NOTES — parcours Niveau → Classes → Matières → Saisie
# ============================================================

@login_required
def notes_niveaux(request):
    """Étape 1 : choix du niveau (6ème, 5ème, ... Terminale)."""
    niveaux = []
    for code, libelle in Classe.NIVEAU_CHOICES:
        nb_classes = Classe.objects.filter(niveau=code).count()
        niveaux.append({'code': code, 'libelle': libelle, 'nb_classes': nb_classes})

    return render(request, 'admin_dashboard/notes/notes_niveaux.html', {
        'niveaux': niveaux,
        'active_page': 'notes',
    })


@login_required
def notes_classes(request, niveau):
    """Étape 2 : liste des classes pour le niveau choisi."""
    classes = Classe.objects.filter(niveau=niveau).select_related('salle')
    niveau_libelle = dict(Classe.NIVEAU_CHOICES).get(niveau, niveau)

    return render(request, 'admin_dashboard/notes/notes_classes.html', {
        'classes': classes,
        'niveau': niveau,
        'niveau_libelle': niveau_libelle,
        'active_page': 'notes',
    })


@login_required
def notes_matieres(request, classe_id):
    """Étape 3 : liste des matières de la classe choisie."""
    classe = get_object_or_404(Classe, id=classe_id)
    matieres = classe.matieres.all()

    return render(request, 'admin_dashboard/notes/notes_matieres.html', {
        'classe': classe,
        'matieres': matieres,
        'active_page': 'notes',
    })



# ============================================================
# administrateur/views.py
# Vue notes_saisie — version finale avec passage séquentiel
# ============================================================

from django.utils import timezone
from django.utils import timezone
from .models import NoteVerrou, Note, Classe, Matiere, ClasseMatiere
from eleve.models import AccesEleve


ORDRE_TRIMESTRES = ['T1', 'T2', 'T3']
 

def _trimestre_accessible(classe, matiere, trimestre):
    """
    Règle séquentielle stricte — s'applique à TOUT LE MONDE (admin inclus) :
    - T1 : toujours accessible
    - T2 : accessible SEULEMENT si T1 est verrouillé
    - T3 : accessible SEULEMENT si T1 ET T2 sont verrouillés
    """
    idx = ORDRE_TRIMESTRES.index(trimestre)
 
    if idx == 0:
        return True  # T1 toujours accessible
 
    # Vérifie que TOUS les trimestres précédents sont verrouillés
    for t_precedent in ORDRE_TRIMESTRES[:idx]:
        v = NoteVerrou.objects.filter(
            classe=classe, matiere=matiere, trimestre=t_precedent
        ).first()
        if not v or not v.verrouille:
            return False
 
    return True
 
 
def _statut_trimestres(classe, matiere, trimestre_actif, est_admin):
    """
    Construit la liste des statuts de chaque trimestre.
    accessible = basé sur la règle séquentielle (tout le monde)
    peut_deverrouiller = admin uniquement
    """
    verrous = {
        v.trimestre: v
        for v in NoteVerrou.objects.filter(classe=classe, matiere=matiere)
    }
 
    statuts = []
    for t in ORDRE_TRIMESTRES:
        v          = verrous.get(t)
        verrouille = v.verrouille if v else False
        accessible = _trimestre_accessible(classe, matiere, t)  # ← plus de est_admin
 
        statuts.append({
            'code'             : t,
            'libelle'          : dict(Note.TRIMESTRE_CHOICES)[t],
            'verrouille'       : verrouille,
            'accessible'       : accessible,
            'actif'            : t == trimestre_actif,
            'verrou_obj'       : v,
            'peut_deverrouiller': est_admin and verrouille,  # admin peut déverrouiller
        })
 
    return statuts, verrous
 
 
@login_required
def notes_saisie(request, classe_id, matiere_id):
    classe    = get_object_or_404(Classe,  id=classe_id)
    matiere   = get_object_or_404(Matiere, id=matiere_id)
    eleves    = classe.eleves.all().order_by('nom', 'prenom')
    est_admin = request.user.role == 'admin'
 
    trimestre = request.GET.get('trimestre', 'T1')
    if trimestre not in ORDRE_TRIMESTRES:
        trimestre = 'T1'
 
    # ── Redirection si trimestre non accessible (TOUT LE MONDE) ──
    if not _trimestre_accessible(classe, matiere, trimestre):
        # Trouve le trimestre le plus avancé accessible
        bon_trimestre = 'T1'
        for t in ORDRE_TRIMESTRES:
            if _trimestre_accessible(classe, matiere, t):
                bon_trimestre = t
            else:
                break
        messages.warning(
            request,
            f"Le {trimestre} est inaccessible. "
            f"Verrouillez d'abord les trimestres précédents."
        )
        return redirect(f"{request.path}?trimestre={bon_trimestre}")
 
    statut_trimestres, verrous = _statut_trimestres(
        classe, matiere, trimestre, est_admin
    )
    verrou_actuel  = verrous.get(trimestre)
    est_verrouille = verrou_actuel.verrouille if verrou_actuel else False
 
    # ── POST ─────────────────────────────────────────────────
    if request.method == 'POST':
        action    = request.POST.get('action', 'enregistrer')
        trimestre = request.POST.get('trimestre', trimestre)
 
        # Recharge
        verrous        = {v.trimestre: v for v in NoteVerrou.objects.filter(classe=classe, matiere=matiere)}
        verrou_actuel  = verrous.get(trimestre)
        est_verrouille = verrou_actuel.verrouille if verrou_actuel else False
 
        # ── Déverrouiller (admin uniquement) ──
        if action == 'deverrouiller':
            if not est_admin:
                messages.error(request, "Seul l'administrateur peut déverrouiller.")
                return redirect(f"{request.path}?trimestre={trimestre}")
            NoteVerrou.objects.filter(
                classe=classe, matiere=matiere, trimestre=trimestre
            ).update(verrouille=False)
            messages.success(request, f"✓ Notes du {trimestre} déverrouillées.")
            return redirect(f"{request.path}?trimestre={trimestre}")
 
        # ── Vérifie accès séquentiel sur POST aussi ──
        if not _trimestre_accessible(classe, matiere, trimestre):
            messages.error(request, f"Accès refusé au {trimestre}.")
            return redirect(f"{request.path}?trimestre=T1")

        # ── Verrouiller (admin uniquement) ──
        if action == 'verrouiller':
            if not est_admin:
                messages.error(
                    request,
                    "Seul l'administrateur peut verrouiller un trimestre. "
                    "Contactez-le une fois toutes les notes saisies."
                )
                return redirect(f"{request.path}?trimestre={trimestre}")

            complet, incomplets = _toutes_notes_completes(classe, matiere, trimestre)
            if not complet:
                detail = []
                for item in incomplets[:5]:
                    e = item['eleve']
                    detail.append(f"{e.nom} {e.prenom} ({', '.join(item['manquantes'])})")
                if len(incomplets) > 5:
                    detail.append(f"et {len(incomplets)-5} autre(s)...")
                messages.error(
                    request,
                    f"Impossible : {len(incomplets)} élève(s) incomplet(s) — {' | '.join(detail)}"
                )
                return redirect(f"{request.path}?trimestre={trimestre}")

            verrou, _ = NoteVerrou.objects.get_or_create(
                classe=classe, matiere=matiere, trimestre=trimestre
            )
            verrou.verrouille     = True
            verrou.verrouille_le  = timezone.now()
            verrou.verrouille_par = request.user
            verrou.save()

            idx = ORDRE_TRIMESTRES.index(trimestre)
            suite = (
                f" Vous pouvez maintenant accéder au {ORDRE_TRIMESTRES[idx+1]}."
                if idx < 2 else " Tous les trimestres sont verrouillés."
            )
            messages.success(request, f"✓ Notes du {trimestre} verrouillées.{suite}")
            return redirect(f"{request.path}?trimestre={trimestre}")

      
        if est_verrouille:                 
            messages.error(
                request,
                "Ces notes sont verrouillées. Déverrouillez-les d'abord pour pouvoir les modifier."
            )
            return redirect(f"{request.path}?trimestre={trimestre}")

        nb_saisis = 0
        for eleve in eleves:
            for code_eval, _ in Note.EVALUATION_CHOICES:
                champ  = f"note_{eleve.id}_{code_eval}"
                valeur = request.POST.get(champ, '').strip() or None
                Note.objects.update_or_create(
                    eleve=eleve, matiere=matiere,
                    trimestre=trimestre, evaluation=code_eval,
                    defaults={'valeur': valeur},
                )
                if valeur:
                    nb_saisis += 1

        complet, _ = _toutes_notes_completes(classe, matiere, trimestre)
        suite = (
            "✓ Toutes les notes sont saisies. Vous pouvez verrouiller."
            if complet else
            "Des notes sont encore manquantes."
        )
        messages.success(request, f"✓ {nb_saisis} note(s) enregistrée(s). {suite}")
        return redirect(f"{request.path}?trimestre={trimestre}")

    
    # ── GET ──────────────────────────────────────────────────
    lignes = []
    nb_saisies = nb_manquantes = 0
 
    for eleve in eleves:
        notes_existantes = {
            n.evaluation: n.valeur
            for n in Note.objects.filter(
                eleve=eleve, matiere=matiere, trimestre=trimestre
            )
        }
        cellules      = []
        eleve_complet = True
 
        for code_eval, libelle in Note.EVALUATION_CHOICES:
            valeur = notes_existantes.get(code_eval)
            cellules.append((code_eval, libelle, valeur))
            if valeur is not None:
                nb_saisies += 1
            else:
                nb_manquantes += 1
                eleve_complet = False
 
        lignes.append({
            'eleve'        : eleve,
            'cellules'     : cellules,
            'moyenne'      : Note.moyenne(eleve, matiere, trimestre),
            'eleve_complet': eleve_complet,
        })
 
    total       = nb_saisies + nb_manquantes
    progression = round((nb_saisies / total * 100) if total > 0 else 0)
    complet, _  = _toutes_notes_completes(classe, matiere, trimestre)
 
    return render(request, 'admin_dashboard/notes/notes_saisie.html', {
        'classe'             : classe,
        'matiere'            : matiere,
        'lignes'             : lignes,
        'trimestre'          : trimestre,
        'entetes_evaluations': list(Note.EVALUATION_CHOICES),
        'est_verrouille'     : est_verrouille,
        'est_admin'          : est_admin,
        'peut_verrouiller'   : complet,
        'statut_trimestres'  : statut_trimestres,
        'verrou_info'        : verrou_actuel,
        'nb_saisies'         : nb_saisies,
        'nb_manquantes'      : nb_manquantes,
        'progression'        : progression,
        'active_page'        : 'notes',
    })
 
 
def _toutes_notes_completes(classe, matiere, trimestre):
   
    eleves = classe.eleves.all()
    if not eleves.exists():
        return False, []
 
    incomplets = []
    for eleve in eleves:
        manquantes = []
        for code_eval, libelle in Note.EVALUATION_CHOICES:
            existe = Note.objects.filter(
                eleve=eleve,
                matiere=matiere,
                trimestre=trimestre,
                evaluation=code_eval,
                valeur__isnull=False,
            ).exists()
            if not existe:
                manquantes.append(libelle)
 
        if manquantes:
            incomplets.append({
                'eleve'    : eleve,
                'manquantes': manquantes,
            })
 
    return len(incomplets) == 0, incomplets
 
 

 
# ============================================================
# VUE PARTAGE EN MASSE : publie les notes à toute une classe
# ============================================================
 
@login_required
def notes_partager_classe(request, classe_id):
    """
    Publie les notes (AccesEleve) à TOUS les élèves d'une classe
    pour un trimestre donné, en un seul clic.
    N'est disponible que si les notes du trimestre sont verrouillées
    pour TOUTES les matières de la classe.
    """
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    classe    = get_object_or_404(Classe, id=classe_id)
    trimestre = request.POST.get('trimestre', 'T1')
    action    = request.POST.get('action', 'accorder')   # 'accorder' | 'revoquer'
 
    if trimestre not in ORDRE_TRIMESTRES:
        messages.error(request, "Trimestre invalide.")
        return redirect('detail_classe', classe_id=classe_id)
 
    # Vérifie que toutes les matières de la classe sont verrouillées pour ce trimestre
    classe_matieres = ClasseMatiere.objects.filter(classe=classe).select_related('matiere')
    matieres_non_verrouillees = []
 
    for cm in classe_matieres:
        v = NoteVerrou.objects.filter(
            classe=classe, matiere=cm.matiere, trimestre=trimestre
        ).first()
        if not v or not v.verrouille:
            matieres_non_verrouillees.append(cm.matiere.nom_matiere)
 
    if matieres_non_verrouillees and action == 'accorder':
        messages.error(
            request,
            f"Impossible de partager : les matières suivantes ne sont pas encore verrouillées "
            f"pour le {trimestre} — {', '.join(matieres_non_verrouillees)}."
        )
        return redirect('detail_classe', classe_id=classe_id)
 
    # Accorde ou révoque l'accès à tous les élèves
    eleves = classe.eleves.all()
    count  = 0
 
    for eleve in eleves:
        if action == 'accorder':
            AccesEleve.accorder(
                eleve        = eleve,
                type_contenu = 'notes',
                trimestre    = trimestre,
                active_par   = request.user,
            )
        else:
            AccesEleve.revoquer(
                eleve        = eleve,
                type_contenu = 'notes',
                trimestre    = trimestre,
            )
        count += 1
 
    verbe = "partagées" if action == 'accorder' else "masquées"
    messages.success(
        request,
        f"✓ Notes du {trimestre} {verbe} pour {count} élève(s) de la classe {classe}."
    )
    return redirect('detail_classe', classe_id=classe_id)
# ============================================================
# ENSEIGNANTS
# ============================================================

@login_required
def list_enseignant(request):
    search = request.GET.get('search', '')

    enseignants = Enseignant.objects.select_related('classe_principale').all()
    if search:
        enseignants = enseignants.filter(first_name__icontains=search) | \
                      enseignants.filter(last_name__icontains=search)

    return render(request, 'admin_dashboard/enseignants/list_enseignant.html', {
        'enseignants': enseignants,
        'total': enseignants.count(),
        'active_page': 'enseignants',
    })


@login_required
def add_enseignant(request, enseignant_id=None):
    enseignant = None
    if enseignant_id:
        enseignant = get_object_or_404(Enseignant, id=enseignant_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        sexe = request.POST.get('sexe')
        telephone = request.POST.get('telephone', '')
        email = request.POST.get('email', '')
        domaine_enseignement = request.POST.get('domaine_enseignement', '')
        classe_principale_id = request.POST.get('classe_principale')
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if enseignant:
           
            enseignant.first_name = first_name
            enseignant.last_name = last_name
            enseignant.sexe = sexe
            enseignant.telephone = telephone
            enseignant.email = email
            enseignant.domaine_enseignement = domaine_enseignement
            enseignant.classe_principale_id = classe_principale_id or None

            if username:
                enseignant.username = username
            if password:
                enseignant.set_password(password)

            enseignant.save()
            messages.success(request, "L'enseignant a été modifié avec succès.")
        else:
            # Création : le nom d'utilisateur doit être unique.
            if not username:
                username = f"{first_name}.{last_name}".lower().replace(' ', '')

            if Enseignant.objects.filter(username=username).exists():
                messages.error(request, f"Le nom d'utilisateur « {username} » est déjà utilisé.")
                return render(request, 'admin_dashboard/enseignants/add_enseignant.html', {
                    'enseignant': None,
                    'classes': Classe.objects.all(),
                    'active_page': 'enseignants',
                })

           
            if not password:
                password = f"{first_name.lower()}{2026}"

            enseignant = Enseignant(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                sexe=sexe,
                role='enseignant',
                telephone=telephone,
                domaine_enseignement=domaine_enseignement,
                classe_principale_id=classe_principale_id or None,
            )
            enseignant.set_password(password)
            enseignant.save()

            messages.success(
                request,
                f"Enseignant créé avec succès. Identifiant : {username} — Mot de passe initial : {password}"
            )

        return redirect('list_enseignant')

    return render(request, 'admin_dashboard/enseignants/add_enseignant.html', {
        'enseignant': enseignant,
        'classes': Classe.objects.all(),
        'active_page': 'enseignants',
    })


@login_required
def detail_enseignant(request, enseignant_id):
    enseignant = get_object_or_404(Enseignant, id=enseignant_id)
    matieres_enseignees = ClasseMatiere.objects.filter(enseignant=enseignant).select_related('classe', 'matiere')

    return render(request, 'admin_dashboard/enseignants/detail_enseignant.html', {
        'enseignant': enseignant,
        'matieres_enseignees': matieres_enseignees,
        'active_page': 'enseignants',
    })


@login_required
def delete_enseignant(request, enseignant_id):
    enseignant = get_object_or_404(Enseignant, id=enseignant_id)
    if request.method == 'POST':
        nom_complet = f"{enseignant.first_name} {enseignant.last_name}"
        enseignant.delete()
        messages.success(request, f"{nom_complet} a été supprimé avec succès.")
    return redirect('list_enseignant')

@login_required
def admin_profil(request):
    """Page de profil de l'administrateur connecté : modification infos + photo."""
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    utilisateur = request.user
 
    if request.method == 'POST':
        utilisateur.first_name = request.POST.get('first_name', utilisateur.first_name)
        utilisateur.last_name = request.POST.get('last_name', utilisateur.last_name)
        utilisateur.email = request.POST.get('email', utilisateur.email)
 
        nouveau_mdp = request.POST.get('password', '').strip()
        if nouveau_mdp:
            utilisateur.set_password(nouveau_mdp)
 
        if 'photo_profil' in request.FILES:
            utilisateur.photo_profil = request.FILES['photo_profil']
 
        utilisateur.save()
 
        if nouveau_mdp:
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, utilisateur)
 
        messages.success(request, "Votre profil a été mis à jour avec succès.")
        return redirect('admin_profil')
 
    return render(request, 'admin_dashboard/admin_profil.html', {
        'active_page': 'profil',
    })
 

 # ============================================================
# BULLETINS
# ============================================================
 
@login_required
def bulletin_classes(request):
    """Étape 1 : choix de la classe pour générer un bulletin."""
    classes = Classe.objects.select_related('salle').all()
    return render(request, 'admin_dashboard/bulletin/bulletin_classes.html', {
        'classes': classes,
        'active_page': 'bulletins',
    })
 
 
@login_required
def bulletin_eleves(request, classe_id):
    """Étape 2 : choix de l'élève dans la classe."""
    classe = get_object_or_404(Classe, id=classe_id)
    eleves = classe.eleves.all().order_by('nom', 'prenom')
    return render(request, 'admin_dashboard/bulletin/bulletin_eleves.html', {
        'classe': classe,
        'eleves': eleves,
        'active_page': 'bulletins',
    })
 
 
def _bulletin_trimestre_accessible(eleve, trimestre):
   
    idx = ORDRE_TRIMESTRES.index(trimestre)
 
    if idx == 0:
        return True
 
    for t_precedent in ORDRE_TRIMESTRES[:idx]:
        v = BulletinVerrou.objects.filter(
            eleve=eleve, trimestre=t_precedent
        ).first()
        if not v or not v.verrouille:
            return False
 
    return True
 
 
def _statut_trimestres_bulletin(eleve, trimestre_actif, est_admin):
    """Construit la liste des statuts trimestre pour le bulletin."""
    verrous = {
        v.trimestre: v
        for v in BulletinVerrou.objects.filter(eleve=eleve)
    }
 
    statuts = []
    for t in ORDRE_TRIMESTRES:
        v          = verrous.get(t)
        verrouille = v.verrouille if v else False
        accessible = _bulletin_trimestre_accessible(eleve, t)
 
        statuts.append({
            'code'              : t,
            'libelle'           : dict(Note.TRIMESTRE_CHOICES)[t],
            'verrouille'        : verrouille,
            'accessible'        : accessible,
            'actif'             : t == trimestre_actif,
            'verrou_obj'        : v,
            'peut_deverrouiller': est_admin and verrouille,
        })
 
    return statuts, verrous
 
 
from .models import TrimestrePeriode, calculer_absences_eleve
 
 
@login_required
def bulletin_generer(request, classe_id, eleve_id):
    """Génération du bulletin avec absences calculées automatiquement depuis la BD."""
    classe    = get_object_or_404(Classe, id=classe_id)
    eleve     = get_object_or_404(Eleve, id=eleve_id, classe=classe)
    est_admin = request.user.role == 'admin'
 
    trimestre = request.GET.get('trimestre', 'T1')
    if trimestre not in ORDRE_TRIMESTRES:
        trimestre = 'T1'
 
    # ── Vérification accès séquentiel ──
    if not _bulletin_trimestre_accessible(eleve, trimestre):
        bon_trimestre = 'T1'
        for t in ORDRE_TRIMESTRES:
            if _bulletin_trimestre_accessible(eleve, t):
                bon_trimestre = t
            else:
                break
        messages.warning(request, f"Verrouillez d'abord les bulletins précédents.")
        return redirect(f"{request.path}?trimestre={bon_trimestre}")
 
    statut_trimestres, verrous = _statut_trimestres_bulletin(eleve, trimestre, est_admin)
    verrou_actuel  = verrous.get(trimestre)
    est_verrouille = verrou_actuel.verrouille if verrou_actuel else False
 
    # ── Calcul automatique des absences depuis la BD ────────
    absences = calculer_absences_eleve(eleve, trimestre)
 
    # ── Récupère ou crée l'appréciation ─────────────────────
    appreciation, _ = BulletinAppreciation.objects.get_or_create(
        eleve=eleve, trimestre=trimestre
    )
 
    # Met à jour automatiquement les absences si la période est configurée
    if absences['periode'] is not None:
        appreciation.absences_justifiees_heures     = absences['justifiees']
        appreciation.absences_non_justifiees_heures = absences['non_justifiees']
        appreciation.save(update_fields=[
            'absences_justifiees_heures',
            'absences_non_justifiees_heures',
        ])
 
    # ── Sections du bulletin ─────────────────────────────────
    bulletin_obj     = Bulletin(classe, trimestre)
    groupes_bruts    = bulletin_obj.matieres_par_groupe()
    libelles_groupes = dict(Matiere.GROUPE_CHOICES)
 
    sections = []
    for code_groupe, classe_matieres in groupes_bruts.items():
        if not classe_matieres:
            continue
        lignes_matieres = []
        for cm in classe_matieres:
            moy_eleve = Note.moyenne(eleve, cm.matiere, trimestre)
            stats     = bulletin_obj.stats_matiere(cm.matiere)
            lignes_matieres.append({
                'matiere'         : cm.matiere,
                'enseignant'      : cm.enseignant,
                'coefficient'     : cm.coefficient,
                'moyenne'         : moy_eleve,
                'moyenne_ponderee': round(float(moy_eleve) * float(cm.coefficient), 2)
                                    if moy_eleve is not None else None,
                'stats_classe'    : stats,
            })
        sections.append({
            'code'          : code_groupe,
            'libelle'       : libelles_groupes.get(code_groupe, code_groupe),
            'matieres'      : lignes_matieres,
            'moyenne_groupe': bulletin_obj.moyenne_groupe(eleve, code_groupe),
        })
 
    peut_verrouiller  = BulletinVerrou.toutes_notes_saisies(eleve, trimestre)
    notes_incompletes = not peut_verrouiller
 
    # ── POST ─────────────────────────────────────────────────
    if request.method == 'POST':
        action = request.POST.get('action', 'enregistrer')
 
        verrou_actuel  = BulletinVerrou.objects.filter(eleve=eleve, trimestre=trimestre).first()
        est_verrouille = verrou_actuel.verrouille if verrou_actuel else False
 
        # Déverrouiller (admin)
        if action == 'deverrouiller':
            if not est_admin:
                messages.error(request, "Seul l'administrateur peut déverrouiller.")
                return redirect(f"{request.path}?trimestre={trimestre}")
            BulletinVerrou.objects.filter(eleve=eleve, trimestre=trimestre).update(verrouille=False)
            messages.success(request, f"✓ Bulletin {trimestre} déverrouillé.")
            return redirect(f"{request.path}?trimestre={trimestre}")
 
        # Verrouiller
        if action == 'verrouiller':
            if notes_incompletes:
                messages.error(request, "Toutes les notes ne sont pas encore saisies.")
                return redirect(f"{request.path}?trimestre={trimestre}")
            verrou, _ = BulletinVerrou.objects.get_or_create(eleve=eleve, trimestre=trimestre)
            verrou.verrouille     = True
            verrou.verrouille_le  = timezone.now()
            verrou.verrouille_par = request.user
            verrou.save()
            idx   = ORDRE_TRIMESTRES.index(trimestre)
            suite = f" Vous pouvez accéder au bulletin {ORDRE_TRIMESTRES[idx+1]}." if idx < 2 else " Tous les bulletins sont verrouillés."
            messages.success(request, f"✓ Bulletin {trimestre} verrouillé.{suite}")
            return redirect(f"{request.path}?trimestre={trimestre}")
 
        # Enregistrer appréciation
        if est_verrouille and not est_admin:
            messages.error(request, "Bulletin verrouillé. Contactez l'administrateur.")
            return redirect(f"{request.path}?trimestre={trimestre}")
 
        appreciation.appreciation_conseil = request.POST.get('appreciation_conseil', '')
        appreciation.decision_conseil     = request.POST.get('decision_conseil', '')
        appreciation.save(update_fields=['appreciation_conseil', 'decision_conseil'])
        messages.success(request, "✓ Bulletin mis à jour.")
        return redirect(f"{request.path}?trimestre={trimestre}")
 
    return render(request, 'admin_dashboard/bulletin/bulletin_detail.html', {
        'classe'            : classe,
        'eleve'             : eleve,
        'trimestre'         : trimestre,
        'sections'          : sections,
        'moyenne_generale'  : Note.moyenne_generale_ponderee(eleve, trimestre),
        'rang'              : bulletin_obj.rang_eleve(eleve),
        'effectif'          : classe.effectif,
        'moyenne_premier'   : bulletin_obj.moyenne_premier(),
        'moyenne_dernier'   : bulletin_obj.moyenne_dernier(),
        'moyenne_classe'    : bulletin_obj.moyenne_classe(),
        'appreciation'      : appreciation,
        'absences'          : absences,          # ← dict avec justifiees, non_justifiees, total, periode
        'periode_configuree': absences['periode'] is not None,
        'est_verrouille'    : est_verrouille,
        'est_admin'         : est_admin,
        'peut_verrouiller'  : peut_verrouiller,
        'notes_incompletes' : notes_incompletes,
        'statut_trimestres' : statut_trimestres,
        'verrou_info'       : verrou_actuel,
        'active_page'       : 'bulletins',
    })
 
def _get_appreciation_avec_absences(eleve, trimestre):
   
    from .models import calculer_absences_eleve, BulletinAppreciation
 
    appreciation, _ = BulletinAppreciation.objects.get_or_create(
        eleve=eleve, trimestre=trimestre
    )
 
    # Calcule les absences automatiquement
    absences = calculer_absences_eleve(eleve, trimestre)
 
   
    if absences['periode'] is not None:
        appreciation.absences_non_justifiees_heures = absences['non_justifiees']
        appreciation.absences_justifiees_heures     = absences['justifiees']
        appreciation.save(update_fields=[
            'absences_non_justifiees_heures',
            'absences_justifiees_heures',
        ])
 
    return appreciation, absences
 
    # Vérifie si toutes les notes sont saisies
    peut_verrouiller  = BulletinVerrou.toutes_notes_saisies(eleve, trimestre)
    notes_incompletes = not peut_verrouiller
 
    # ── POST ─────────────────────────────────────────────────
    if request.method == 'POST':
        action = request.POST.get('action', 'enregistrer')
 
        # Recharge verrou
        verrou_actuel  = BulletinVerrou.objects.filter(
            eleve=eleve, trimestre=trimestre
        ).first()
        est_verrouille = verrou_actuel.verrouille if verrou_actuel else False
 
        # ── Déverrouiller (admin uniquement) ──
        if action == 'deverrouiller':
            if not est_admin:
                messages.error(request, "Seul l'administrateur peut déverrouiller.")
                return redirect(f"{request.path}?trimestre={trimestre}")
            BulletinVerrou.objects.filter(
                eleve=eleve, trimestre=trimestre
            ).update(verrouille=False)
            messages.success(
                request,
                f"✓ Bulletin {trimestre} déverrouillé."
            )
            return redirect(f"{request.path}?trimestre={trimestre}")
 
        # ── Vérifie accès séquentiel sur POST ──
        if not _bulletin_trimestre_accessible(eleve, trimestre):
            messages.error(request, f"Accès refusé au bulletin {trimestre}.")
            return redirect(f"{request.path}?trimestre=T1")
 
        # ── Verrouiller ──
        if action == 'verrouiller':
            if notes_incompletes:
                messages.error(
                    request,
                    f"Impossible de verrouiller : toutes les notes du {trimestre} "
                    f"ne sont pas encore saisies. Complétez les notes avant de verrouiller le bulletin."
                )
                return redirect(f"{request.path}?trimestre={trimestre}")
 
            verrou, _ = BulletinVerrou.objects.get_or_create(
                eleve=eleve, trimestre=trimestre
            )
            verrou.verrouille     = True
            verrou.verrouille_le  = timezone.now()
            verrou.verrouille_par = request.user
            verrou.save()
 
            idx   = ORDRE_TRIMESTRES.index(trimestre)
            suite = (
                f" Vous pouvez maintenant accéder au bulletin {ORDRE_TRIMESTRES[idx+1]}."
                if idx < 2 else " Tous les bulletins sont verrouillés."
            )
            messages.success(
                request,
                f"✓ Bulletin {trimestre} verrouillé.{suite}"
            )
            return redirect(f"{request.path}?trimestre={trimestre}")
 
        # ── Enregistrer l'appréciation ──
        if est_verrouille and not est_admin:
            messages.error(request, "Ce bulletin est verrouillé. Contactez l'administrateur.")
            return redirect(f"{request.path}?trimestre={trimestre}")
 
        appreciation.absences_justifiees_heures     = request.POST.get('absences_justifiees', 0) or 0
        appreciation.absences_non_justifiees_heures = request.POST.get('absences_non_justifiees', 0) or 0
        appreciation.appreciation_conseil           = request.POST.get('appreciation_conseil', '')
        appreciation.decision_conseil               = request.POST.get('decision_conseil', '')
        appreciation.save()
        messages.success(request, "✓ Bulletin mis à jour.")
        return redirect(f"{request.path}?trimestre={trimestre}")
 
    # ── GET ──────────────────────────────────────────────────
    return render(request, 'admin_dashboard/bulletin/bulletin_detail.html', {
        'classe'            : classe,
        'eleve'             : eleve,
        'trimestre'         : trimestre,
        'sections'          : sections,
        'moyenne_generale'  : Note.moyenne_generale_ponderee(eleve, trimestre),
        'rang'              : bulletin_obj.rang_eleve(eleve),
        'effectif'          : classe.effectif,
        'moyenne_premier'   : bulletin_obj.moyenne_premier(),
        'moyenne_dernier'   : bulletin_obj.moyenne_dernier(),
        'moyenne_classe'    : bulletin_obj.moyenne_classe(),
        'appreciation'      : appreciation,
        'est_verrouille'    : est_verrouille,
        'est_admin'         : est_admin,
        'peut_verrouiller'  : peut_verrouiller,
        'notes_incompletes' : notes_incompletes,
        'statut_trimestres' : statut_trimestres,
        'verrou_info'       : verrou_actuel,
        'active_page'       : 'bulletins',
    })
 
def _chevauchement(debut1, fin1, debut2, fin2):
    """Deux périodes se chevauchent si l'une commence avant que l'autre finisse."""
    return debut1 <= fin2 and debut2 <= fin1
 
 
@login_required
def admin_periodes_trimestres(request):
    """Page de configuration des dates de trimestre."""
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    periodes = TrimestrePeriode.objects.all().order_by('trimestre')
 
    if request.method == 'POST':
        annee = request.POST.get('annee', '2025-2026').strip()
 
        # ── 1. Parse toutes les dates saisies ──
        saisies = {}   # {'T1': (date_debut, date_fin), ...}
        erreurs = []
 
        for t_code in ['T1', 'T2', 'T3']:
            brut_debut = request.POST.get(f'debut_{t_code}', '').strip()
            brut_fin   = request.POST.get(f'fin_{t_code}', '').strip()
 
            if not brut_debut or not brut_fin:
                continue  # trimestre non renseigné, on l'ignore (pas obligatoire)
 
            try:
                d_debut = datetime.strptime(brut_debut, '%Y-%m-%d').date()
                d_fin   = datetime.strptime(brut_fin, '%Y-%m-%d').date()
            except ValueError:
                erreurs.append(f"Format de date invalide pour le {t_code}.")
                continue
 
            # ── 2. Début doit précéder la fin ──
            if d_debut >= d_fin:
                erreurs.append(
                    f"{t_code} : la date de début ({d_debut.strftime('%d/%m/%Y')}) doit "
                    f"précéder la date de fin ({d_fin.strftime('%d/%m/%Y')})."
                )
                continue
 
            saisies[t_code] = (d_debut, d_fin)
 
        # ── 3. Vérifie les chevauchements entre trimestres ──
        codes = list(saisies.keys())
        for i in range(len(codes)):
            for j in range(i + 1, len(codes)):
                c1, c2 = codes[i], codes[j]
                d1, f1 = saisies[c1]
                d2, f2 = saisies[c2]
                if _chevauchement(d1, f1, d2, f2):
                    erreurs.append(
                        f"{c1} ({d1.strftime('%d/%m/%Y')} → {f1.strftime('%d/%m/%Y')}) "
                        f"chevauche {c2} ({d2.strftime('%d/%m/%Y')} → {f2.strftime('%d/%m/%Y')})."
                    )
 
        # ── 4. Vérifie l'ordre chronologique T1 < T2 < T3 ──
        ordre = ['T1', 'T2', 'T3']
        codes_presents = [c for c in ordre if c in saisies]
        for i in range(len(codes_presents) - 1):
            c_avant, c_apres = codes_presents[i], codes_presents[i + 1]
            if saisies[c_avant][1] > saisies[c_apres][0]:
                erreurs.append(
                    f"{c_avant} doit se terminer avant que {c_apres} ne commence "
                    f"(l'ordre chronologique T1 → T2 → T3 doit être respecté)."
                )
 
        # ── 5. Si erreurs : on affiche tout sans rien enregistrer ──
        if erreurs:
            for e in erreurs:
                messages.error(request, e)
 
            # Reconstruit periodes_dict à partir de ce que l'utilisateur a saisi,
            # pour ne pas lui faire perdre sa saisie même en cas d'erreur.
            periodes_dict_saisie = {}
            for t_code in ['T1', 'T2', 'T3']:
                if t_code in saisies:
                    d_debut, d_fin = saisies[t_code]
                    periodes_dict_saisie[t_code] = type('Periode', (), {
                        'date_debut': d_debut,
                        'date_fin': d_fin,
                        'annee': annee,
                    })()
                else:
                    existante = TrimestrePeriode.objects.filter(trimestre=t_code).first()
                    if existante:
                        periodes_dict_saisie[t_code] = existante
 
            return render(request, 'admin_dashboard/parametres/periodes_trimestres.html', {
                'periodes_dict': periodes_dict_saisie,
                'trimestres'   : [('T1', 'Trimestre 1'), ('T2', 'Trimestre 2'), ('T3', 'Trimestre 3')],
                'active_page'  : 'parametres',
            })
 
        # ── 6. Tout est valide : on enregistre ──
        for t_code, (d_debut, d_fin) in saisies.items():
            TrimestrePeriode.objects.update_or_create(
                trimestre=t_code,
                defaults={
                    'date_debut': d_debut,
                    'date_fin'  : d_fin,
                    'annee'     : annee,
                }
            )
 
        messages.success(request, "✓ Périodes des trimestres enregistrées avec succès.")
        return redirect('admin_periodes_trimestres')
 
    # ── GET ──
    periodes_dict = {p.trimestre: p for p in periodes}
 
    return render(request, 'admin_dashboard/parametres/periodes_trimestres.html', {
        'periodes_dict': periodes_dict,
        'trimestres'   : [('T1', 'Trimestre 1'), ('T2', 'Trimestre 2'), ('T3', 'Trimestre 3')],
        'active_page'  : 'parametres',
    })
    
 



@login_required
def bulletin_pdf(request, classe_id, eleve_id):
    """Génère le bulletin en PDF avec absences calculées automatiquement."""
    classe    = get_object_or_404(Classe, id=classe_id)
    eleve     = get_object_or_404(Eleve, id=eleve_id, classe=classe)
 
    trimestre = request.GET.get('trimestre', 'T1')
    if trimestre not in ('T1', 'T2', 'T3'):
        trimestre = 'T1'
 
    # ── Calcul automatique des absences ──────────────────────
    absences = calculer_absences_eleve(eleve, trimestre)
 
    # ── Récupère l'appréciation et met à jour les absences ───
    appreciation, _ = BulletinAppreciation.objects.get_or_create(
        eleve=eleve, trimestre=trimestre
    )
    if absences['periode'] is not None:
        appreciation.absences_justifiees_heures     = absences['justifiees']
        appreciation.absences_non_justifiees_heures = absences['non_justifiees']
        appreciation.save(update_fields=[
            'absences_justifiees_heures',
            'absences_non_justifiees_heures',
        ])
 
    # ── Sections du bulletin ─────────────────────────────────
    bulletin_obj     = Bulletin(classe, trimestre)
    groupes_bruts    = bulletin_obj.matieres_par_groupe()
    libelles_groupes = dict(Matiere.GROUPE_CHOICES)
 
    sections = []
    for code_groupe, classe_matieres in groupes_bruts.items():
        if not classe_matieres:
            continue
        lignes_matieres = []
        for cm in classe_matieres:
            notes_qs = Note.objects.filter(
                eleve=eleve, matiere=cm.matiere, trimestre=trimestre
            )
            notes_par_eval = {n.evaluation: n.valeur for n in notes_qs}
            moy_eleve      = Note.moyenne(eleve, cm.matiere, trimestre)
            stats          = bulletin_obj.stats_matiere(cm.matiere)
            lignes_matieres.append({
                'matiere'         : cm.matiere,
                'enseignant'      : cm.enseignant,
                'coefficient'     : cm.coefficient,
                'notes_par_eval'  : notes_par_eval,
                'moyenne'         : moy_eleve,
                'moyenne_ponderee': round(float(moy_eleve) * float(cm.coefficient), 2)
                                    if moy_eleve is not None else None,
                'stats_classe'    : stats,
            })
        sections.append({
            'code'          : code_groupe,
            'libelle'       : libelles_groupes.get(code_groupe, code_groupe),
            'matieres'      : lignes_matieres,
            'moyenne_groupe': bulletin_obj.moyenne_groupe(eleve, code_groupe),
        })
 
    contexte = {
        'classe'          : classe,
        'eleve'           : eleve,
        'trimestre'       : trimestre,
        'sections'        : sections,
        'moyenne_generale': Note.moyenne_generale_ponderee(eleve, trimestre),
        'rang'            : bulletin_obj.rang_eleve(eleve),
        'effectif'        : classe.effectif,
        'moyenne_premier' : bulletin_obj.moyenne_premier(),
        'moyenne_dernier' : bulletin_obj.moyenne_dernier(),
        'moyenne_classe'  : bulletin_obj.moyenne_classe(),
        'appreciation'    : appreciation,  # absences déjà mises à jour
        'absences'        : absences,
    }
 
    # ── Rendu HTML → PDF ─────────────────────────────────────
    html        = render_to_string(
        'admin_dashboard/bulletin/bulletin_pdf.html',
        contexte, request=request
    )
    buffer      = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
 
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF.", status=500)
 
    buffer.seek(0)
    nom_fichier = f"bulletin_{eleve.nom}_{eleve.prenom}_{trimestre}.pdf"
    response    = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    return response
 

@login_required
def list_creneau(request):
    creneaux = CreneauHoraire.objects.all()
    return render(request, 'admin_dashboard/emploi/list_creneau.html', {
        'creneaux': creneaux,
        'total': creneaux.count(),
        'active_page': 'creneaux',
    })
 
 
from datetime import datetime
 
 
# ── Utilitaire ──────────────────────────────────────────────
 
def _creneaux_se_chevauchent(debut1, fin1, debut2, fin2):
  
    return debut1 < fin2 and debut2 < fin1
 
 

 
@login_required
def add_creneau(request, creneau_id=None):
    """
    Création de créneau(x) horaire(s).
    En création : permet de cocher plusieurs jours → crée une ligne par jour.
    En modification : un seul créneau (jour fixe).
    """
    creneau = None
    if creneau_id:
        creneau = get_object_or_404(CreneauHoraire, id=creneau_id)
 
    if request.method == 'POST':
        heure_debut = request.POST.get('heure_debut')
        heure_fin   = request.POST.get('heure_fin')
        est_pause   = bool(request.POST.get('est_pause'))
 
        # ── Validation ──
        if not heure_debut or not heure_fin:
            messages.error(request, "Veuillez renseigner les heures de début et de fin.")
            return render(request, 'admin_dashboard/emploi/add_creneau.html', {
                'creneau': creneau, 'active_page': 'creneaux',
            })
 
        from datetime import datetime
        try:
            debut_t = datetime.strptime(heure_debut, '%H:%M').time()
            fin_t   = datetime.strptime(heure_fin, '%H:%M').time()
        except ValueError:
            messages.error(request, "Format d'heure invalide.")
            return render(request, 'admin_dashboard/emploi/add_creneau.html', {
                'creneau': creneau, 'active_page': 'creneaux',
            })
 
        if debut_t >= fin_t:
            messages.error(request, "L'heure de début doit précéder l'heure de fin.")
            return render(request, 'admin_dashboard/emploi/add_creneau.html', {
                'creneau': creneau, 'active_page': 'creneaux',
            })
 
        # ── MODIFICATION : un seul jour ──
        if creneau:
            jour = request.POST.get('jour')
 
            # Vérifie chevauchement (hors lui-même)
            existants = CreneauHoraire.objects.filter(jour=jour).exclude(id=creneau.id)
            for c in existants:
                if debut_t < c.heure_fin and c.heure_debut < fin_t:
                    messages.error(
                        request,
                        f"Chevauchement avec {c.heure_debut.strftime('%Hh%M')}–{c.heure_fin.strftime('%Hh%M')} le {jour}."
                    )
                    return render(request, 'admin_dashboard/emploi/add_creneau.html', {
                        'creneau': creneau, 'active_page': 'creneaux',
                    })
 
            creneau.jour        = jour
            creneau.heure_debut = heure_debut
            creneau.heure_fin   = heure_fin
            creneau.est_pause   = est_pause
            creneau.save()
            messages.success(request, "Le créneau a été modifié avec succès.")
            return redirect('list_creneau')
 
        # ── CRÉATION : plusieurs jours possibles ──
        jours_selectionnes = request.POST.getlist('jours')  # liste de codes jours
 
        if not jours_selectionnes:
            messages.error(request, "Veuillez sélectionner au moins un jour.")
            return render(request, 'admin_dashboard/emploi/add_creneau.html', {
                'creneau': None, 'active_page': 'creneaux',
            })
 
        crees      = []
        conflits   = []
 
        for jour in jours_selectionnes:
            # Vérifie chevauchement pour ce jour
            existants  = CreneauHoraire.objects.filter(jour=jour)
            a_conflit  = False
            for c in existants:
                if debut_t < c.heure_fin and c.heure_debut < fin_t:
                    a_conflit = True
                    conflits.append(
                        f"{dict(CreneauHoraire.JOUR_CHOICES)[jour]} "
                        f"({c.heure_debut.strftime('%Hh%M')}–{c.heure_fin.strftime('%Hh%M')})"
                    )
                    break
 
            if not a_conflit:
                nouveau = CreneauHoraire.objects.create(
                    jour=jour, heure_debut=heure_debut,
                    heure_fin=heure_fin, est_pause=est_pause
                )
                crees.append(jour)
 
        # ── Messages de résultat ──
        if crees:
            libelles_crees = [dict(CreneauHoraire.JOUR_CHOICES)[j] for j in crees]
            messages.success(
                request,
                f"✓ Créneau créé pour : {', '.join(libelles_crees)}."
            )
        if conflits:
            messages.warning(
                request,
                f"⚠ Non créé (chevauchement) : {', '.join(conflits)}."
            )
 
        return redirect('list_creneau')
 
    return render(request, 'admin_dashboard/emploi/add_creneau.html', {
        'creneau'      : creneau,
        'jours_choices': CreneauHoraire.JOUR_CHOICES,
        'active_page'  : 'creneaux',
    })
 
 
# ============================================================
# EMPLOI DU TEMPS — par semaine, historique, clôture
# ============================================================
 
@login_required
def emploi_du_temps_classes(request):
    """Étape 1 : choix de la classe, avec sélecteur de semaine."""
    classes = Classe.objects.select_related('salle').all()
    semaine = _get_semaine_demandee(request)
 
    return render(request, 'admin_dashboard/emploi/emploi_classes.html', {
        'classes'     : classes,
        'semaine'     : semaine,
        'active_page' : 'emploi',
    })

 
 
def _get_semaine_demandee(request):
    """
    Récupère la semaine demandée via ?semaine_id=X,
    sinon retourne la semaine en cours.
    """
    semaine_id = request.GET.get('semaine_id')
    if semaine_id:
        semaine = SemaineScolaire.objects.filter(id=semaine_id).first()
        if semaine:
            return semaine
    return SemaineScolaire.semaine_en_cours()
 
 
 

 
 
@login_required
def cloturer_semaine(request, semaine_id):
    """
    Clôture une semaine :
    - Verrouille l'emploi du temps
    - Partage les présences à tous les élèves
    - Crée automatiquement la semaine suivante
    """
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    semaine = get_object_or_404(SemaineScolaire, id=semaine_id)
 
    if semaine.cloturee:
        messages.warning(request, "Cette semaine est déjà clôturée.")
        return redirect('emploi_du_temps_classes')
 
    if request.method == 'POST':
        nouvelle_semaine = semaine.cloturer(request.user)
        messages.success(
            request,
            f"✓ Semaine du {semaine.date_debut.strftime('%d/%m')} clôturée. "
            f"Présences partagées à tous les élèves. "
            f"Nouvelle semaine du {nouvelle_semaine.date_debut.strftime('%d/%m')} créée."
        )
        return redirect('emploi_du_temps_classes')
 
    return render(request, 'admin_dashboard/emploi/confirmer_cloture.html', {
        'semaine'    : semaine,
        'active_page': 'emploi',
    })
 
 
 
@login_required
def historique_semaines(request):
    """Liste de toutes les semaines avec leur statut."""
    semaines = SemaineScolaire.objects.all().order_by('-date_debut')
    return render(request, 'admin_dashboard/emploi/historique_semaines.html', {
        'semaines'    : semaines,
        'active_page' : 'emploi',
    })

@login_required
def emploi_du_temps_grille(request, classe_id):
    """Grille jour × créneau pour une classe, pour une semaine donnée."""
    classe   = get_object_or_404(Classe, id=classe_id)
    creneaux = CreneauHoraire.objects.all()
    matieres_classe = classe.matieres.all()
    enseignants     = Enseignant.objects.all()
 
    semaine = _get_semaine_demandee(request)
 
    # Dates réelles de cette semaine (lundi à samedi)
    jours_ordonnes = [code for code, _ in CreneauHoraire.JOUR_CHOICES]
    dates_semaine  = {}
    for i, jour in enumerate(jours_ordonnes):
        dates_semaine[jour] = semaine.date_debut + timedelta(days=i)
 
    if request.method == 'POST':
        if semaine.cloturee:
            messages.error(request, "Cette semaine est clôturée, modification impossible.")
            return redirect(f"{request.path}?semaine_id={semaine.id}")
 
        erreurs      = []
        affectations = {}
 
        for creneau in creneaux:
            if creneau.est_pause:
                continue
            matiere_id    = request.POST.get(f'matiere_{creneau.id}', '').strip()
            enseignant_id = request.POST.get(f'enseignant_{creneau.id}', '').strip()
            if matiere_id:
                affectations[creneau.id] = {
                    'matiere_id'   : matiere_id,
                    'enseignant_id': enseignant_id or None,
                }
 
        # Conflit enseignant (au sein de la même semaine)
        for creneau_id, affect in affectations.items():
            ens_id = affect['enseignant_id']
            if not ens_id:
                continue
            conflit = EmploiDuTemps.objects.filter(
                semaine=semaine, creneau_id=creneau_id, enseignant_id=ens_id
            ).exclude(classe=classe).select_related('classe', 'creneau', 'enseignant').first()
            if conflit:
                c   = CreneauHoraire.objects.get(id=creneau_id)
                ens = conflit.enseignant
                erreurs.append(
                    f"{ens.first_name} {ens.last_name} déjà affecté à « {conflit.classe} » "
                    f"le {c.get_jour_display()} {c.heure_debut.strftime('%Hh%M')}–{c.heure_fin.strftime('%Hh%M')}."
                )
 
        if erreurs:
            for e in erreurs:
                messages.error(request, e)
            return redirect(f"{request.path}?semaine_id={semaine.id}")
 
        for creneau in creneaux:
            if creneau.est_pause:
                continue
            if creneau.id in affectations:
                affect = affectations[creneau.id]
                EmploiDuTemps.objects.update_or_create(
                    semaine=semaine, classe=classe, creneau=creneau,
                    defaults={
                        'matiere_id'   : affect['matiere_id'],
                        'enseignant_id': affect['enseignant_id'],
                    },
                )
            else:
                EmploiDuTemps.objects.filter(
                    semaine=semaine, classe=classe, creneau=creneau
                ).delete()
 
        messages.success(request, "Emploi du temps enregistré pour cette semaine.")
        return redirect(f"{request.path}?semaine_id={semaine.id}")
 
    # ── GET : construit la grille ──
    emplois_existants = {
        e.creneau_id: e
        for e in EmploiDuTemps.objects.filter(semaine=semaine, classe=classe)
        .select_related('matiere', 'enseignant')
    }
 
    libelles_jours = dict(CreneauHoraire.JOUR_CHOICES)
    entetes_jours  = [
        {'code': j, 'libelle': libelles_jours[j], 'date': dates_semaine[j]}
        for j in jours_ordonnes
    ]
 
    plages = {}
    for c in creneaux:
        plages.setdefault((c.heure_debut, c.heure_fin), {})[c.jour] = c
 
    lignes_grille = []
    for (hd, hf), creneaux_jour in sorted(plages.items()):
        premier = next(iter(creneaux_jour.values()))
        cellules = []
        for jour in jours_ordonnes:
            cr = creneaux_jour.get(jour)
            if not cr:
                cellules.append(None)
                continue
            emploi = emplois_existants.get(cr.id)
            cellules.append({
                'creneau_id'   : cr.id,
                'matiere_id'   : emploi.matiere_id    if emploi else None,
                'enseignant_id': emploi.enseignant_id if emploi else None,
            })
        lignes_grille.append({
            'heure_debut': hd, 'heure_fin': hf,
            'est_pause'  : premier.est_pause,
            'cellules'   : cellules,
        })
 
    # Historique des semaines (pour le sélecteur)
    semaines_historique = SemaineScolaire.objects.all().order_by('-date_debut')[:12]
 
    return render(request, 'admin_dashboard/emploi/emploi_grille.html', {
        'classe'              : classe,
        'lignes_grille'       : lignes_grille,
        'entetes_jours'       : entetes_jours,
        'matieres_classe'     : matieres_classe,
        'enseignants'         : enseignants,
        'semaine'             : semaine,
        'semaines_historique' : semaines_historique,
        'active_page'         : 'emploi',
    })
 

 
 
@login_required
def delete_creneau(request, creneau_id):
    creneau = get_object_or_404(CreneauHoraire, id=creneau_id)
    if request.method == 'POST':
        nom = str(creneau)
        creneau.delete()
        messages.success(request, f"Le créneau « {nom} » a été supprimé avec succès.")
    return redirect('list_creneau')
 

 
# ============================================================
# EMPLOI DU TEMPS (grille matière par classe)
# ============================================================
 


 
def _render_grille(request, classe, creneaux, matieres_classe, enseignants,
                   dates_semaine=None, override_post=None):
    """Construit et retourne la réponse de la grille emploi du temps."""
 
    if dates_semaine is None:
        dates_semaine = _semaine_en_cours()
 
    if override_post:
        emplois_existants = {}
        for creneau in creneaux:
            matiere_id    = override_post.get(f'matiere_{creneau.id}', '').strip()
            enseignant_id = override_post.get(f'enseignant_{creneau.id}', '').strip()
            if matiere_id:
                class _F:
                    pass
                e = _F()
                e.matiere_id    = int(matiere_id)
                e.enseignant_id = int(enseignant_id) if enseignant_id else None
                emplois_existants[creneau.id] = e
    else:
        emplois_existants = {
            e.creneau_id: e
            for e in EmploiDuTemps.objects.filter(classe=classe).select_related('matiere', 'enseignant')
        }
 
    # Appels déjà verrouillés cette semaine pour cette classe
    # { (creneau_id, date): True }
    appels_verrouilles = set()
    for jour_code, jour_date in dates_semaine.items():
        for av in AppelVerrouille.objects.filter(classe=classe, date=jour_date):
            appels_verrouilles.add((av.creneau_id, jour_date))
 
    jours_ordonnes = [code for code, _ in CreneauHoraire.JOUR_CHOICES]
    libelles_jours = dict(CreneauHoraire.JOUR_CHOICES)
 
    # En-têtes : libellé jour + date réelle
    entetes_jours = []
    for jour_code in jours_ordonnes:
        jour_date = dates_semaine.get(jour_code)
        entetes_jours.append({
            'code'   : jour_code,
            'libelle': libelles_jours[jour_code],
            'date'   : jour_date,  # objet date Python, formaté dans le template
        })
 
    plages = {}
    for creneau in creneaux:
        cle = (creneau.heure_debut, creneau.heure_fin)
        plages.setdefault(cle, {})[creneau.jour] = creneau
 
    lignes_grille = []
    for (heure_debut, heure_fin), creneaux_du_jour in sorted(plages.items()):
        premier_creneau = next(iter(creneaux_du_jour.values()))
 
        cellules_jours = []
        for jour_code in jours_ordonnes:
            creneau_jour = creneaux_du_jour.get(jour_code)
            if not creneau_jour:
                cellules_jours.append(None)
                continue
 
            emploi  = emplois_existants.get(creneau_jour.id)
            jour_date = dates_semaine.get(jour_code)
            verrouille = (creneau_jour.id, jour_date) in appels_verrouilles
 
            cellules_jours.append({
                'creneau_id'   : creneau_jour.id,
                'matiere_id'   : emploi.matiere_id    if emploi else None,
                'matiere_nom'  : emploi.matiere.nom_matiere if emploi and hasattr(emploi, 'matiere') and emploi.matiere else None,
                'enseignant_id': emploi.enseignant_id if emploi else None,
                'a_cours'      : emploi is not None and emploi.matiere_id is not None,
                'date'         : jour_date,
                'verrouille'   : verrouille,
            })
 
        lignes_grille.append({
            'heure_debut': heure_debut,
            'heure_fin'  : heure_fin,
            'est_pause'  : premier_creneau.est_pause,
            'cellules'   : cellules_jours,
        })
 
    return render(request, 'admin_dashboard/emploi/emploi_grille.html', {
        'classe'              : classe,
        'lignes_grille'       : lignes_grille,
        'entetes_jours'       : entetes_jours,
        'jours_ordonnes'      : jours_ordonnes,
        'libelles_jours_liste': [libelles_jours[j] for j in jours_ordonnes],
        'matieres_classe'     : matieres_classe,
        'enseignants'         : enseignants,
        'active_page'         : 'emploi',
    })
 
 


from datetime import date, timedelta, datetime


# ── Utilitaire : semaine en cours ───────────────────────────

def _semaine_en_cours():
    """
    Renvoie un dict {code_jour: date} pour la semaine ISO en cours.
    Ex: {'lundi': date(2026,6,23), 'mardi': date(2026,6,24), ...}
    """
    aujourd_hui = date.today()
    # lundi de la semaine courante
    lundi = aujourd_hui - timedelta(days=aujourd_hui.weekday())

    jours_map = {
        'lundi'   : lundi,
        'mardi'   : lundi + timedelta(days=1),
        'mercredi': lundi + timedelta(days=2),
        'jeudi'   : lundi + timedelta(days=3),
        'vendredi': lundi + timedelta(days=4),
        'samedi'  : lundi + timedelta(days=5),
    }
    return jours_map






# ============================================================
# APPELS — pages dédiées
# ============================================================

@login_required
def appel_classes(request):
    """Étape 1 : choisir la classe pour faire l'appel."""
    classes = Classe.objects.select_related('salle').all()
    return render(request, 'admin_dashboard/appels/appel_classes.html', {
        'classes'     : classes,
        'active_page' : 'appels',
    })


@login_required
def appel_creneaux(request, classe_id):
    """
    Étape 2 : liste des cours du JOUR EN COURS pour la classe choisie.
    Affiche les créneaux de l'emploi du temps avec leur statut appel.
    """
    classe        = get_object_or_404(Classe, id=classe_id)
    aujourd_hui   = date.today()
    nom_jour      = aujourd_hui.strftime('%A').lower()  # 'lundi', 'mardi'...

    # Correspondance Python weekday → code jour
    jours_python = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
    code_jour    = jours_python[aujourd_hui.weekday()]

    # Cours programmés aujourd'hui pour cette classe
    emplois_aujourd_hui = EmploiDuTemps.objects.filter(
        classe=classe,
        creneau__jour=code_jour,
        creneau__est_pause=False,
        matiere__isnull=False,
    ).select_related('creneau', 'matiere', 'enseignant').order_by('creneau__heure_debut')

    # Statut verrouillage pour chaque créneau
    creneaux_verrouilles = set(
        AppelVerrouille.objects.filter(
            classe=classe, date=aujourd_hui
        ).values_list('creneau_id', flat=True)
    )

    cours = []
    for emploi in emplois_aujourd_hui:
        cours.append({
            'emploi'    : emploi,
            'verrouille': emploi.creneau_id in creneaux_verrouilles,
        })

    return render(request, 'admin_dashboard/appels/appel_creneaux.html', {
        'classe'      : classe,
        'cours'       : cours,
        "aujourd_hui" : aujourd_hui,
        'active_page' : 'appels',
    })

from administrateur.models import SemaineScolaire


@login_required
def appel_depuis_grille(request, classe_id, creneau_id):
    """
    Raccourci depuis la grille emploi du temps :
    redirige directement vers la saisie d'appel du jour.
    """
    return redirect('appel_saisie', classe_id=classe_id, creneau_id=creneau_id)


@login_required
def appel_historique(request, classe_id):
    """
    Historique des appels pour une classe : liste des dates/créneaux verrouillés
    avec résumé présents/absents/retards.
    """
    classe   = get_object_or_404(Classe, id=classe_id)
    historique = []

    appels = AppelVerrouille.objects.filter(
        classe=classe
    ).select_related('creneau', 'verrouille_par').order_by('-date', 'creneau__heure_debut')

    for appel in appels:
        presences = Presence.objects.filter(
            classe=classe, creneau=appel.creneau, date=appel.date
        )
        historique.append({
            'appel'   : appel,
            'presents': presences.filter(statut='present').count(),
            'absents' : presences.filter(statut='absent').count(),
            'retards' : presences.filter(statut='retard').count(),
            'total'   : presences.count(),
        })

    return render(request, 'admin_dashboard/appels/appel_historique.html', {
        'classe'     : classe,
        'historique' : historique,
        'active_page': 'appels',
    })
 
 


# ============================================================
# CRÉNEAUX HORAIRES (grille fixe, partagée par toutes les classes)
# ============================================================

@login_required
def list_creneau(request):
    creneaux = CreneauHoraire.objects.all()
    return render(request, 'admin_dashboard/emploi/list_creneau.html', {
        'creneaux': creneaux,
        'total': creneaux.count(),
        'active_page': 'creneaux',
    })


@login_required
def appel_saisie(request, classe_id, creneau_id):
    """
    Étape 3 : saisie de l'appel pour un créneau et la date du jour.
    - GET  : affiche la liste des élèves avec leur statut actuel
    - POST : enregistre les présences et verrouille l'appel
    """
    classe   = get_object_or_404(Classe, id=classe_id)
    creneau  = get_object_or_404(CreneauHoraire, id=creneau_id)
    aujourd_hui = date.today()
    try:
        semaine_en_cours = SemaineScolaire.semaine_en_cours()
    except Exception:
        semaine_en_cours = None

    # Vérifie que ce créneau correspond bien à un cours aujourd'hui
    jours_python = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
    code_jour    = jours_python[aujourd_hui.weekday()]

    emploi = EmploiDuTemps.objects.filter(
        classe=classe, creneau=creneau
    ).select_related('matiere', 'enseignant').first()

    # Appel déjà verrouillé ?
    deja_verrouille = AppelVerrouille.objects.filter(
        classe=classe, creneau=creneau, date=aujourd_hui
    ).exists()

    eleves = classe.eleves.all().order_by('nom', 'prenom')

    if request.method == 'POST':
        if deja_verrouille:
            messages.error(request, "Cet appel est déjà verrouillé. Contactez un administrateur pour le modifier.")
            return redirect('appel_saisie', classe_id=classe_id, creneau_id=creneau_id)

        # Récupère l'enseignant connecté si c'est un enseignant
        enregistre_par = None
        if hasattr(request.user, 'role') and request.user.role == 'enseignant':
            try:
                enregistre_par = Enseignant.objects.get(id=request.user.id)
            except Enseignant.DoesNotExist:
                pass

        # ── Tout ce bloc était mal indenté : maintenant bien À L'INTÉRIEUR du if POST ──
        for eleve in eleves:
            statut    = request.POST.get(f'statut_{eleve.id}', 'present')
            justifiee = request.POST.get(f'justifiee_{eleve.id}') == '1'

            if statut not in ('present', 'absent', 'retard'):
                statut = 'present'

            # ── La justification n'a de sens que pour une absence ──
            if statut != 'absent':
                justifiee = False

            Presence.objects.update_or_create(
                eleve=eleve, classe=classe, creneau=creneau, date=aujourd_hui,
                defaults={
                    'statut'        : statut,
                    'justifiee'     : justifiee,
                    'enregistre_par': enregistre_par,
                    'semaine'       : semaine_en_cours,
                },
            )

        # Verrouille l'appel (une seule fois, pas à chaque élève)
        AppelVerrouille.objects.get_or_create(
            classe=classe,
            creneau=creneau,
            date=aujourd_hui,
            defaults={'verrouille_par': enregistre_par},
        )

        messages.success(request, f"Appel enregistré et verrouillé pour le {aujourd_hui.strftime('%d/%m/%Y')}.")
        return redirect('appel_creneaux', classe_id=classe_id)

    # ── GET : préremplit les statuts existants ──
    presences_existantes = {
        p.eleve_id: {
            'statut': p.statut,
            'justifiee': p.justifiee,
        }
        for p in Presence.objects.filter(
            classe=classe,
            creneau=creneau,
            date=aujourd_hui
        )
    }

    lignes = []
    for eleve in eleves:
        data = presences_existantes.get(eleve.id, {'statut': 'present', 'justifiee': False})
        lignes.append({
            'eleve'    : eleve,
            'statut'   : data['statut'],
            'justifiee': data['justifiee'],
        })

    return render(request, 'admin_dashboard/appels/appel_saisie.html', {
        'classe'         : classe,
        'creneau'        : creneau,
        'emploi'         : emploi,
        'lignes'         : lignes,
        'aujourd_hui'    : aujourd_hui,
        'deja_verrouille': deja_verrouille,
        'active_page'    : 'appels',
    })

from eleve.models import Message, AccesEleve
from utilisateurs.models import Utilisateur
 



# ============================================================
# administrateur/views.py — AJOUT
# ============================================================

from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime
from secretaire.models import Paiement, TranchePaiement, FraisNiveau, statut_paiements_eleve


@login_required
def secretaire_historique_paiements(request):
    """
    Historique global de TOUS les paiements enregistrés (toutes classes,
    tous élèves), avec recherche, filtres par classe/période, et total
    encaissé sur la sélection affichée. Accessible à l'admin et au secrétariat.
    """
    if request.user.role not in ('admin', 'secretaire'):
        return redirect_selon_role(request.user)

    paiements = Paiement.objects.select_related(
        'eleve', 'eleve__classe', 'enregistre_par'
    ).prefetch_related('tranches').all()

    # ── Filtres ──
    search      = request.GET.get('search', '').strip()
    classe_id   = request.GET.get('classe', '').strip()
    date_debut  = request.GET.get('date_debut', '').strip()
    date_fin    = request.GET.get('date_fin', '').strip()

    if search:
        paiements = paiements.filter(
            Q(eleve__nom__icontains=search) |
            Q(eleve__prenom__icontains=search) |
            Q(eleve__matricule__icontains=search)
        )

    if classe_id:
        paiements = paiements.filter(eleve__classe_id=classe_id)

    if date_debut:
        try:
            d = datetime.strptime(date_debut, '%Y-%m-%d').date()
            paiements = paiements.filter(date_paiement__gte=d)
        except ValueError:
            pass

    if date_fin:
        try:
            d = datetime.strptime(date_fin, '%Y-%m-%d').date()
            paiements = paiements.filter(date_paiement__lte=d)
        except ValueError:
            pass

    # ── Total encaissé sur la sélection filtrée (avant pagination) ──
    total_periode = sum(float(p.montant) for p in paiements)
    nb_paiements  = paiements.count()

    # ── Pagination ──
    paginator   = Paginator(paiements, 30)
    page_number = request.GET.get('page')
    page_obj    = paginator.get_page(page_number)

    return render(request, 'secretaire_dashboard/eleves/historique_paiements.html', {
        'page_obj'      : page_obj,
        'total_periode' : total_periode,
        'nb_paiements'  : nb_paiements,
        'classes'       : Classe.objects.all().order_by('niveau'),
        'search'        : search,
        'classe_id'     : classe_id,
        'date_debut'    : date_debut,
        'date_fin'      : date_fin,
        'active_page'   : 'historique_paiements',
    })
# ── Correspondance type_message → type_contenu AccesEleve ──
TYPE_MESSAGE_TO_ACCES = {
    'notes'   : 'notes',
    'bulletin': 'notes',   # bulletin donne aussi accès aux notes
    'emploi'  : 'emploi',
    'presence': 'presence',
}
 
# ============================================================
# administrateur/views.py — AJOUT
# ============================================================

@login_required
def admin_historiques(request):
    """Page centrale regroupant les différents historiques disponibles."""
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)

    return render(request, 'admin_dashboard/historiques/admin_historiques.html', {
        'active_page': 'historiques',
    })


@login_required
def admin_messages(request):
    """Liste de tous les messages envoyés par l'admin."""
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    search      = request.GET.get('search', '')
    type_filtre = request.GET.get('type', '')
 
    msgs = Message.objects.select_related('destinataire', 'eleve', 'expediteur').all().order_by('-date_envoi')
 
    if search:
        msgs = msgs.filter(sujet__icontains=search) | \
               msgs.filter(eleve__nom__icontains=search) | \
               msgs.filter(eleve__prenom__icontains=search)
    if type_filtre:
        msgs = msgs.filter(type_message=type_filtre)
 
    # Pour chaque message, vérifie si l'accès est actif
    msgs_avec_acces = []
    for msg in msgs:
        acces_actif = False
        if msg.eleve and msg.type_message in TYPE_MESSAGE_TO_ACCES:
            type_acces = TYPE_MESSAGE_TO_ACCES[msg.type_message]
            trimestre  = None
            acces_actif = AccesEleve.a_acces(msg.eleve, type_acces, trimestre)
        msgs_avec_acces.append({'msg': msg, 'acces_actif': acces_actif})
 
    msgs_recus_parents = Message.objects.filter(
        destinataire=request.user,
        expediteur__role='parent',
    ).select_related('expediteur', 'eleve').order_by('-date_envoi')
 
    return render(request, 'admin_dashboard/messages/admin_messages.html', {
        'msgs_avec_acces'        : msgs_avec_acces,   # ← CORRIGÉ : c'est bien ça qu'on utilise au template
        'total'                  : msgs.count(),
        'type_filtre'            : type_filtre,
        'search'                 : search,
        'type_choices'           : Message.TYPE_CHOICES,
        'active_page'            : 'messages',
        'messages_recus_parents' : msgs_recus_parents,
    })
 
 
@login_required
def admin_envoyer_message(request, eleve_id=None):
    """Envoi d'un message + publication automatique de l'accès."""
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    eleve_preselect = None
    if eleve_id:
        eleve_preselect = get_object_or_404(Eleve, id=eleve_id)
 
    if request.method == 'POST':
        dest_eleve_id = request.POST.get('eleve_id')
        sujet         = request.POST.get('sujet', '').strip()
        contenu       = request.POST.get('contenu', '').strip()
        type_message  = request.POST.get('type_message', 'general')
        trimestre     = request.POST.get('trimestre', '').strip() or None
        fichier_pdf   = request.FILES.get('fichier_pdf')
        publier_acces = request.POST.get('publier_acces') == '1'
 
        if not dest_eleve_id or not sujet:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return render(request, 'admin_dashboard/messages/admin_envoyer_message.html', {
                'eleves'          : Eleve.objects.select_related('classe').all().order_by('nom'),
                'eleve_preselect' : eleve_preselect,
                'type_choices'    : Message.TYPE_CHOICES,
                'active_page'     : 'messages',
            })
 
        dest_eleve = get_object_or_404(Eleve, id=dest_eleve_id)
 
        try:
            dest_user = Utilisateur.objects.get(role='eleve', eleve_profil=dest_eleve)
        except Utilisateur.DoesNotExist:
            messages.error(request, "Cet élève n'a pas de compte utilisateur.")
            return redirect('admin_messages')
 
        # Crée le message
        msg = Message(
            expediteur   = request.user,
            destinataire = dest_user,
            eleve        = dest_eleve,
            type_message = type_message,
            sujet        = sujet,
            contenu      = contenu,
        )
        if fichier_pdf:
            msg.fichier_pdf = fichier_pdf
        msg.save()
 
        # ── Publication automatique de l'accès ──
        # Si le type de message correspond à un contenu verrouillé,
        # on accorde automatiquement l'accès à l'élève.
        if type_message in TYPE_MESSAGE_TO_ACCES and publier_acces:
            type_acces = TYPE_MESSAGE_TO_ACCES[type_message]
            AccesEleve.accorder(
                eleve        = dest_eleve,
                type_contenu = type_acces,
                trimestre    = trimestre if type_acces == 'notes' else None,
                active_par   = request.user,
            )
            messages.success(
                request,
                f"Message envoyé et accès « {type_acces} » accordé à "
                f"{dest_eleve.nom} {dest_eleve.prenom}."
            )
        else:
            messages.success(
                request,
                f"Message envoyé à {dest_eleve.nom} {dest_eleve.prenom}."
            )
 
        return redirect('admin_messages')
 
    return render(request, 'admin_dashboard/messages/admin_envoyer_message.html', {
        'eleves'          : Eleve.objects.select_related('classe').all().order_by('nom'),
        'eleve_preselect' : eleve_preselect,
        'type_choices'    : Message.TYPE_CHOICES,
        'active_page'     : 'messages',
    })
 
 

@login_required
def admin_repondre_message(request, message_id):
    """
    Permet à l'admin de répondre à un message reçu (d'un parent ou d'un élève).
    La réponse est envoyée à l'EXPÉDITEUR du message original (pas forcément
    l'élève lui-même — ça peut être son parent).
    """
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    message_original = get_object_or_404(Message, id=message_id)
 
    if request.method == 'POST':
        contenu     = request.POST.get('contenu', '').strip()
        sujet       = request.POST.get('sujet', '').strip()
        fichier_pdf = request.FILES.get('fichier_pdf')
 
        if not contenu:
            messages.error(request, "Le message ne peut pas être vide.")
            return render(request, 'admin_dashboard/messages/admin_repondre_message.html', {
                'message_original': message_original,
                'active_page'     : 'messages',
            })
 
        reponse = Message(
            expediteur   = request.user,
            destinataire = message_original.expediteur,
            eleve        = message_original.eleve,
            type_message = message_original.type_message,
            sujet        = sujet or f"Re: {message_original.sujet}",
            contenu      = contenu,
            reponse_a    = message_original,   # nécessite le champ ci-dessous
        )
        if fichier_pdf:
            reponse.fichier_pdf = fichier_pdf
        reponse.save()
 
        messages.success(
            request,
            f"✓ Réponse envoyée à {message_original.expediteur.get_full_name()}."
        )
        return redirect('admin_messages')
 
    # ── GET : pré-remplit le sujet avec "Re: ..." ──
    return render(request, 'admin_dashboard/messages/admin_repondre_message.html', {
        'message_original': message_original,
        'sujet_prerempli' : f"Re: {message_original.sujet}",
        'active_page'     : 'messages',
    })


@login_required
def admin_publier_acces(request, eleve_id):
    """
    Bouton manuel : accorde ou révoque l'accès à un contenu pour un élève.
    POST params: type_contenu, trimestre (optionnel), action ('accorder'|'revoquer')
    """
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    eleve        = get_object_or_404(Eleve, id=eleve_id)
    type_contenu = request.POST.get('type_contenu')
    trimestre    = request.POST.get('trimestre') or None
    action       = request.POST.get('action', 'accorder')
 
    if type_contenu not in ['notes', 'bulletin', 'emploi', 'presence']:
        messages.error(request, "Type de contenu invalide.")
        return redirect('admin_gestion_acces', eleve_id=eleve_id)
 
    if action == 'accorder':
        AccesEleve.accorder(eleve, type_contenu, trimestre, active_par=request.user)
        messages.success(
            request,
            f"Accès « {type_contenu} » accordé à {eleve.nom} {eleve.prenom}."
        )
    else:
        AccesEleve.revoquer(eleve, type_contenu, trimestre)
        messages.success(
            request,
            f"Accès « {type_contenu} » révoqué pour {eleve.nom} {eleve.prenom}."
        )
 
    return redirect('admin_gestion_acces', eleve_id=eleve_id)
 
 
@login_required
def admin_gestion_acces(request, eleve_id):
    """
    Page de gestion des accès d'un élève :
    liste tous les types de contenu avec leur statut actif/inactif.
    """
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    eleve = get_object_or_404(Eleve, id=eleve_id)
 
    # Récupère tous les accès existants pour cet élève
    acces_existants = {
        (a.type_contenu, a.trimestre): a
        for a in AccesEleve.objects.filter(eleve=eleve)
    }
 
    # Construit la grille : type × trimestre
    types     = [('notes', 'Notes'), ('bulletin', 'Bulletin'), ('emploi', 'Emploi du temps'), ('presence', 'Présences')]
    trimestres = [('T1', 'Trimestre 1'), ('T2', 'Trimestre 2'), ('T3', 'Trimestre 3'), (None, '—')]
 
    grille = []
    for type_code, type_libelle in types:
        if type_code in ('emploi', 'presence'):
            # Pas de trimestre pour emploi/présence
            acces = acces_existants.get((type_code, None))
            grille.append({
                'type_code'   : type_code,
                'type_libelle': type_libelle,
                'trimestre'   : None,
                'trim_libelle': '—',
                'actif'       : acces.actif if acces else False,
                'date'        : acces.date_activation if acces else None,
            })
        else:
            for trim_code, trim_libelle in [('T1','T1'), ('T2','T2'), ('T3','T3')]:
                acces = acces_existants.get((type_code, trim_code))
                grille.append({
                    'type_code'   : type_code,
                    'type_libelle': type_libelle,
                    'trimestre'   : trim_code,
                    'trim_libelle': trim_libelle,
                    'actif'       : acces.actif if acces else False,
                    'date'        : acces.date_activation if acces else None,
                })
 
    return render(request, 'admin_dashboard/messages/admin_gestion_acces.html', {
        'eleve'      : eleve,
        'grille'     : grille,
        'active_page': 'messages',
    })
 
 
@login_required
def admin_supprimer_message(request, message_id):
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
    msg = get_object_or_404(Message, id=message_id)
    if request.method == 'POST':
        msg.delete()
        messages.success(request, "Message supprimé.")
    return redirect('admin_messages')

login_required
def admin_acces_classe(request, classe_id):
    """
    Accorde ou révoque l'accès à un type de contenu
    pour TOUS les élèves d'une classe en un clic.
    """
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)
 
    classe       = get_object_or_404(Classe, id=classe_id)
    type_contenu = request.POST.get('type_contenu')
    trimestre    = request.POST.get('trimestre') or None
    action       = request.POST.get('action', 'accorder')
 
    if type_contenu not in ['notes', 'bulletin', 'emploi', 'presence']:
        messages.error(request, "Type de contenu invalide.")
        return redirect('detail_classe', classe_id=classe_id)
 
    eleves = classe.eleves.all()
    count  = 0
 
    for eleve in eleves:
        if action == 'accorder':
            AccesEleve.accorder(
                eleve        = eleve,
                type_contenu = type_contenu,
                trimestre    = trimestre if type_contenu in ('notes', 'bulletin') else None,
                active_par   = request.user,
            )
        else:
            AccesEleve.revoquer(
                eleve        = eleve,
                type_contenu = type_contenu,
                trimestre    = trimestre if type_contenu in ('notes', 'bulletin') else None,
            )
        count += 1
 
    verbe = "accordé" if action == 'accorder' else "révoqué"
    messages.success(
        request,
        f"Accès « {type_contenu} » {verbe} pour {count} élève(s) de la classe {classe}."
    )
    return redirect('detail_classe', classe_id=classe_id)




