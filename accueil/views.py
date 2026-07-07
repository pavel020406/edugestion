# ============================================================
# accueil/views.py
# Toutes les vues d'EduGestion, assemblées et cohérentes
# ============================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Eleve, Matiere, Classe, Salle, Note, ClasseMatiere, Enseignant


# ============================================================
# PAGES PUBLIQUES
# ============================================================

def accueil(request):
    return render(request, 'index.html')


# ============================================================
# AUTHENTIFICATION
# ============================================================

def redirect_selon_role(user):
    """
    Centralise la logique de redirection après connexion.
    Ajoutez ici un nouveau cas dès qu'un rôle obtient son propre espace.
    """
    if user.role == 'admin':
        return redirect('dashboard')
    elif user.role == 'enseignant':
        return redirect('dashboard_enseignant')
    else:
        # Rôles pas encore pris en charge (secretaire, parent, eleve) :
        # on les renvoie pour l'instant vers la page publique.
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

@login_required
def dashboard(request):
    if request.user.role != 'admin':
        return redirect_selon_role(request.user)

    contexte = {
        'active_page': 'dashboard',
        'total_eleves': Eleve.objects.count(),
        'total_classes': Classe.objects.count(),
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
        nom = request.POST.get('nom')
        prenom = request.POST.get('prenom')
        date_naissance = request.POST.get('date_naissance')
        sexe = request.POST.get('sexe')
        classe_id = request.POST.get('classe')
        nom_parent = request.POST.get('nom_parent')
        telephone_parent = request.POST.get('telephone_parent')
        email_parent = request.POST.get('email_parent', '')

        if eleve:
            eleve.nom = nom
            eleve.prenom = prenom
            eleve.date_naissance = date_naissance
            eleve.sexe = sexe
            eleve.classe_id = classe_id if classe_id else None
            eleve.nom_parent = nom_parent
            eleve.telephone_parent = telephone_parent
            eleve.email_parent = email_parent or None
            eleve.save()
            messages.success(request, "L'élève a été modifié avec succès.")
        else:
            Eleve.objects.create(
                nom=nom,
                prenom=prenom,
                date_naissance=date_naissance,
                sexe=sexe,
                classe_id=classe_id if classe_id else None,
                nom_parent=nom_parent,
                telephone_parent=telephone_parent,
                email_parent=email_parent or None,
            )
            messages.success(request, "L'élève a été inscrit avec succès.")

        return redirect('list_eleve')

    return render(request, 'admin_dashboard/eleves/add_eleve.html', {
        'eleve': eleve,
        'classes': Classe.objects.all(),
        'active_page': 'eleves',
    })


@login_required
def detail_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    return render(request, 'admin_dashboard/eleves/detail_eleve.html', {
        'eleve': eleve,
        'active_page': 'eleves',
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

@login_required
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


@login_required
def add_matiere(request, matiere_id=None):
    matiere = None
    if matiere_id:
        matiere = get_object_or_404(Matiere, id=matiere_id)

    if request.method == 'POST':
        nom_matiere = request.POST.get('nom_matiere')
        description = request.POST.get('description', '')

        if matiere:
            matiere.nom_matiere = nom_matiere
            matiere.description = description or None
            matiere.save()
            messages.success(request, "La matière a été modifiée avec succès.")
        else:
            Matiere.objects.create(
                nom_matiere=nom_matiere,
                description=description or None,
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
    classe = get_object_or_404(Classe, id=classe_id)
    classe_matieres = ClasseMatiere.objects.filter(classe=classe).select_related('matiere', 'enseignant')
    return render(request, 'admin_dashboard/classes/detail_classe.html', {
        'classe': classe,
        'classe_matieres': classe_matieres,
        'eleves': classe.eleves.all(),
        'active_page': 'classes',
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


@login_required
def notes_saisie(request, classe_id, matiere_id):
    """Étape 4 : saisie des notes des élèves de la classe pour cette matière."""
    classe = get_object_or_404(Classe, id=classe_id)
    matiere = get_object_or_404(Matiere, id=matiere_id)
    eleves = classe.eleves.all().order_by('nom', 'prenom')

    trimestre = request.GET.get('trimestre', 'T1')
    if trimestre not in ('T1', 'T2', 'T3'):
        trimestre = 'T1'

    if request.method == 'POST':
        trimestre = request.POST.get('trimestre', 'T1')

        for eleve in eleves:
            for code_eval, _ in Note.EVALUATION_CHOICES:
                champ = f"note_{eleve.id}_{code_eval}"
                valeur_brute = request.POST.get(champ, '').strip()

                # Note vide acceptée : on la stocke comme None (pas comme 0).
                valeur = valeur_brute if valeur_brute else None

                Note.objects.update_or_create(
                    eleve=eleve,
                    matiere=matiere,
                    trimestre=trimestre,
                    evaluation=code_eval,
                    defaults={'valeur': valeur},
                )

        messages.success(request, "Les notes ont été enregistrées avec succès.")
        return redirect(f"{request.path}?trimestre={trimestre}")

    # Construit, pour chaque élève, la liste de ses cellules (une par évaluation)
    # et la valeur actuelle déjà existante, pour préremplir le formulaire.
    lignes = []
    for eleve in eleves:
        notes_existantes = {
            n.evaluation: n.valeur
            for n in Note.objects.filter(eleve=eleve, matiere=matiere, trimestre=trimestre)
        }

        cellules = []
        for code_eval, libelle in Note.EVALUATION_CHOICES:
            valeur = notes_existantes.get(code_eval)
            cellules.append((code_eval, libelle, valeur))

        lignes.append({
            'eleve': eleve,
            'cellules': cellules,
            'moyenne': Note.moyenne(eleve, matiere, trimestre),
        })

    # Libellés des en-têtes de colonnes (identiques pour toutes les lignes).
    entetes_evaluations = list(Note.EVALUATION_CHOICES)

    return render(request, 'admin_dashboard/notes/notes_saisie.html', {
        'classe': classe,
        'matiere': matiere,
        'lignes': lignes,
        'trimestre': trimestre,
        'entetes_evaluations': entetes_evaluations,
        'active_page': 'notes',
    })


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