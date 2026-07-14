
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone




from administrateur.models import (
    Eleve, Matiere, Classe, ClasseMatiere, Note, Presence, Enseignant,
    EmploiDuTemps, AppelVerrouille, CreneauHoraire,
)


from administrateur.views import redirect_selon_role


def classes_accessibles(enseignant):
   
    ids_principal = Classe.objects.filter(enseignant_principal=enseignant).values_list('id', flat=True)
    ids_matiere = ClasseMatiere.objects.filter(enseignant=enseignant).values_list('classe_id', flat=True)
    ids = set(ids_principal) | set(ids_matiere)
    return Classe.objects.filter(id__in=ids)


def matieres_accessibles(enseignant, classe):
   
    if classe.enseignant_principal_id == enseignant.id:
        return classe.matieres.all()
    matiere_ids = ClasseMatiere.objects.filter(
        classe=classe, enseignant=enseignant
    ).values_list('matiere_id', flat=True)
    return Matiere.objects.filter(id__in=matiere_ids)


@login_required
def dashboard_enseignant(request):
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)

    enseignant = Enseignant.objects.get(id=request.user.id)
    classes = classes_accessibles(enseignant)
    total_eleves = Eleve.objects.filter(classe__in=classes).count()

    return render(request, 'dashboard_enseignant/enseignant_dashboard.html', {
        'enseignant': enseignant,
        'total_classes': classes.count(),
        'total_eleves': total_eleves,
        'active_page': 'dashboard',
    })

from administrateur.models import SemaineScolaire

semaine_en_cours = SemaineScolaire.semaine_en_cours()

@login_required
def enseignant_mes_classes(request):
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)

    enseignant = Enseignant.objects.get(id=request.user.id)
    classes = classes_accessibles(enseignant)

    

    lignes = []

    for classe in classes:
        creneau = (
            EmploiDuTemps.objects.filter(
                
                classe=classe,
                enseignant=enseignant
            )
            .select_related("creneau")
            .first()
        )

        lignes.append({
            'classe': classe,
            'est_principal': classe.enseignant_principal_id == enseignant.id,
            'matieres': matieres_accessibles(enseignant, classe),
            'creneau': creneau.creneau if creneau else None,
        })

    return render(request, 'dashboard_enseignant/enseignant_classes.html', {
        'lignes': lignes,
        'active_page': 'mes_classes',
    })

@login_required
def enseignant_notes_classes(request):
    """Étape 1 (espace enseignant) : choix de la classe pour saisir des notes."""
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)

    enseignant = Enseignant.objects.get(id=request.user.id)
    classes = classes_accessibles(enseignant)

    return render(request, 'dashboard_enseignant/enseignant_notes_classes.html', {
        'classes': classes,
        'active_page': 'mes_notes',
    })


@login_required
def enseignant_notes_matieres(request, classe_id):
    """Étape 2 : matières accessibles à l'enseignant pour cette classe."""
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)

    enseignant = Enseignant.objects.get(id=request.user.id)
    classe = get_object_or_404(Classe, id=classe_id)

    if classe not in classes_accessibles(enseignant):
        messages.error(request, "Vous n'avez pas accès à cette classe.")
        return redirect('enseignant_notes_classes')

    matieres = matieres_accessibles(enseignant, classe)

    return render(request, 'dashboard_enseignant/enseignant_notes_matieres.html', {
        'classe': classe,
        'matieres': matieres,
        'active_page': 'mes_notes',
    })


from administrateur.models import NoteVerrou
from administrateur.views import _trimestre_accessible, _toutes_notes_completes, ORDRE_TRIMESTRES


@login_required
def enseignant_notes_saisie(request, classe_id, matiere_id):
    """Étape 3 : saisie des notes — soumise aux mêmes verrous que l'admin."""
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)

    enseignant = Enseignant.objects.get(id=request.user.id)
    classe = get_object_or_404(Classe, id=classe_id)
    matiere = get_object_or_404(Matiere, id=matiere_id)

    if classe not in classes_accessibles(enseignant) or matiere not in matieres_accessibles(enseignant, classe):
        messages.error(request, "Vous n'avez pas accès à cette matière pour cette classe.")
        return redirect('enseignant_notes_classes')

    eleves = classe.eleves.all().order_by('nom', 'prenom')

    trimestre = request.GET.get('trimestre', 'T1')
    if trimestre not in ORDRE_TRIMESTRES:
        trimestre = 'T1'

    # ── Accès séquentiel : identique à la règle admin ──
    if not _trimestre_accessible(classe, matiere, trimestre):
        bon_trimestre = 'T1'
        for t in ORDRE_TRIMESTRES:
            if _trimestre_accessible(classe, matiere, t):
                bon_trimestre = t
            else:
                break
        messages.warning(
            request,
            f"Le {trimestre} est inaccessible. L'administrateur doit d'abord "
            f"verrouiller les trimestres précédents."
        )
        return redirect(f"{request.path}?trimestre={bon_trimestre}")

    # ── Statut du verrou actuel ──
    verrou_actuel = NoteVerrou.objects.filter(
        classe=classe, matiere=matiere, trimestre=trimestre
    ).first()
    est_verrouille = verrou_actuel.verrouille if verrou_actuel else False

    if request.method == 'POST':
        trimestre = request.POST.get('trimestre', trimestre)

        # Recharge le verrou pour CE trimestre (au cas où il aurait changé)
        verrou_actuel = NoteVerrou.objects.filter(
            classe=classe, matiere=matiere, trimestre=trimestre
        ).first()
        est_verrouille = verrou_actuel.verrouille if verrou_actuel else False

        # ── Bloqué si l'admin a verrouillé ce trimestre ──
        if est_verrouille:
            messages.error(
                request,
                "Ces notes sont verrouillées par l'administrateur. "
                "Contactez-le pour toute modification."
            )
            return redirect(f"{request.path}?trimestre={trimestre}")

        # ── Re-vérifie l'accès séquentiel sur POST aussi ──
        if not _trimestre_accessible(classe, matiere, trimestre):
            messages.error(request, f"Accès refusé au {trimestre}.")
            return redirect(f"{request.path}?trimestre=T1")

        for eleve in eleves:
            for code_eval, _ in Note.EVALUATION_CHOICES:
                champ = f"note_{eleve.id}_{code_eval}"
                valeur_brute = request.POST.get(champ, '').strip()
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

    lignes = []
    for eleve in eleves:
        notes_existantes = {
            n.evaluation: n.valeur
            for n in Note.objects.filter(eleve=eleve, matiere=matiere, trimestre=trimestre)
        }
        cellules = []
        for code_eval, libelle in Note.EVALUATION_CHOICES:
            cellules.append((code_eval, libelle, notes_existantes.get(code_eval)))

        lignes.append({
            'eleve': eleve,
            'cellules': cellules,
            'moyenne': Note.moyenne(eleve, matiere, trimestre),
        })

    entetes_evaluations = list(Note.EVALUATION_CHOICES)
    complet, _ = _toutes_notes_completes(classe, matiere, trimestre)

    return render(request, 'dashboard_enseignant/enseignant_notes_saisie.html', {
        'classe': classe,
        'matiere': matiere,
        'lignes': lignes,
        'trimestre': trimestre,
        'entetes_evaluations': entetes_evaluations,
        'est_verrouille': est_verrouille,
        'peut_verrouiller': complet,
        'active_page': 'mes_notes',
    })

@login_required
def enseignant_presences_classes(request):
    """Étape 1 (présences) : choix de la classe pour faire l'appel."""
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)

    enseignant = Enseignant.objects.get(id=request.user.id)
    classes = classes_accessibles(enseignant)

    return render(request, 'dashboard_enseignant/enseignant_presences_classes.html', {
        'classes': classes,
        'active_page': 'mes_presences',
    })


@login_required
def enseignant_presences_creneaux(request, classe_id):
    """
    Étape 2 : choix du créneau du jour pour cette classe (basé sur
    l'emploi du temps), pour une date donnée (aujourd'hui par défaut).
    """
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)

    enseignant = Enseignant.objects.get(id=request.user.id)
    classe = get_object_or_404(Classe, id=classe_id)

    if classe not in classes_accessibles(enseignant):
        messages.error(request, "Vous n'avez pas accès à cette classe.")
        return redirect('enseignant_presences_classes')

    date_choisie = request.GET.get('date') or timezone.now().date().isoformat()
    date_obj = timezone.datetime.strptime(date_choisie, '%Y-%m-%d').date()

    # Le jour de la semaine en français, pour filtrer les créneaux du bon jour.
    jours_fr = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
    jour_code = jours_fr[date_obj.weekday()]

    emplois_du_jour = EmploiDuTemps.objects.filter(
        classe=classe, creneau__jour=jour_code, creneau__est_pause=False
    ).select_related('creneau', 'matiere').order_by('creneau__heure_debut')

    lignes = []
    for emploi in emplois_du_jour:
        est_verrouille = AppelVerrouille.objects.filter(
            classe=classe, creneau=emploi.creneau, date=date_obj
        ).exists()
        lignes.append({
            'emploi': emploi,
            'verrouille': est_verrouille,
        })

    return render(request, 'dashboard_enseignant/enseignant_presences_creneaux.html', {
        'classe': classe,
        'lignes': lignes,
        'date_choisie': date_choisie,
        'active_page': 'mes_presences',
    })


@login_required
def enseignant_presences_appel(request, classe_id, creneau_id):
    """Étape 3 : faire l'appel pour un créneau précis. Verrouillé après envoi."""
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)

    enseignant = Enseignant.objects.get(id=request.user.id)
    classe = get_object_or_404(Classe, id=classe_id)
    creneau = get_object_or_404(CreneauHoraire, id=creneau_id)

    if classe not in classes_accessibles(enseignant):
        messages.error(request, "Vous n'avez pas accès à cette classe.")
        return redirect('enseignant_presences_classes')

    date_appel = request.GET.get('date') or timezone.now().date().isoformat()
    eleves = classe.eleves.all().order_by('nom', 'prenom')

    deja_verrouille = AppelVerrouille.objects.filter(
        classe=classe, creneau=creneau, date=date_appel
    ).exists()

    if request.method == 'POST':
        if deja_verrouille:
            messages.error(request, "Cet appel a déjà été enregistré et ne peut plus être modifié.")
            return redirect('enseignant_presences_creneaux', classe_id=classe.id)

        date_appel = request.POST.get('date', date_appel)

        for eleve in eleves:
            statut    = request.POST.get(f'statut_{eleve.id}', 'present')
            justifiee = request.POST.get(f'justifiee_{eleve.id}') == '1'
        
            Presence.objects.update_or_create(
                eleve=eleve, classe=classe, creneau=creneau, date=date_appel,
                defaults={
                    'statut'        : statut,
                    'justifiee'     : justifiee,
                    'enregistre_par': enseignant,
                },
            )

        # Verrouille définitivement cet appel : impossible à modifier ensuite
        # par un enseignant (seul un admin peut le débloquer).
        AppelVerrouille.objects.create(
            classe=classe, creneau=creneau, date=date_appel, verrouille_par=enseignant
        )

        messages.success(request, "L'appel a été enregistré et verrouillé avec succès.")
        return redirect('enseignant_presences_creneaux', classe_id=classe.id)

    presences_existantes = {
        p.eleve_id: p.statut
        for p in Presence.objects.filter(classe=classe, creneau=creneau, date=date_appel)
    }

    lignes = [
        {'eleve': eleve, 'statut_actuel': presences_existantes.get(eleve.id, 'present')}
        for eleve in eleves
    ]

    return render(request, 'dashboard_enseignant/enseignant_presences_appel.html', {
        'classe': classe,
        'creneau': creneau,
        'lignes': lignes,
        'date_appel': date_appel,
        'deja_verrouille': deja_verrouille,
        'active_page': 'mes_presences',
    })



login_required
def enseignant_presences_historique(request, classe_id):
    """
    Historique des appels faits par l'enseignant pour une classe donnée.
    Affiche tous les appels verrouillés avec résumé présents/absents/retards.
    """
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)
 
    enseignant = Enseignant.objects.get(id=request.user.id)
    classe = get_object_or_404(Classe, id=classe_id)
 
    if classe not in classes_accessibles(enseignant):
        messages.error(request, "Vous n'avez pas accès à cette classe.")
        return redirect('enseignant_presences_classes')
 
    appels = AppelVerrouille.objects.filter(
        classe=classe
    ).select_related('creneau', 'verrouille_par').order_by('-date', 'creneau__heure_debut')
 
    historique = []
    for appel in appels:
        presences = Presence.objects.filter(
            classe=classe, creneau=appel.creneau, date=appel.date
        )
        historique.append({
            'appel'    : appel,
            'presents' : presences.filter(statut='present').count(),
            'absents'  : presences.filter(statut='absent').count(),
            'retards'  : presences.filter(statut='retard').count(),
            'total'    : presences.count(),
        })
 
    return render(request, 'dashboard_enseignant/enseignant_presences_historique.html', {
        'classe'      : classe,
        'historique'  : historique,
        'active_page' : 'mes_presences',
    })

@login_required
def enseignant_profil(request):
    """Page de profil de l'enseignant connecté : modification infos + photo."""
    if request.user.role != 'enseignant':
        return redirect_selon_role(request.user)

    enseignant = Enseignant.objects.get(id=request.user.id)

    if request.method == 'POST':
        enseignant.first_name = request.POST.get('first_name', enseignant.first_name)
        enseignant.last_name = request.POST.get('last_name', enseignant.last_name)
        enseignant.email = request.POST.get('email', enseignant.email)
        enseignant.telephone = request.POST.get('telephone', enseignant.telephone)
        enseignant.domaine_enseignement = request.POST.get('domaine_enseignement', enseignant.domaine_enseignement)

        nouveau_mdp = request.POST.get('password', '').strip()
        if nouveau_mdp:
            enseignant.set_password(nouveau_mdp)

        if 'photo_profil' in request.FILES:
            enseignant.photo_profil = request.FILES['photo_profil']

        enseignant.save()

       
        if nouveau_mdp:
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, enseignant)

        messages.success(request, "Votre profil a été mis à jour avec succès.")
        return redirect('enseignant_profil')

    return render(request, 'dashboard_enseignant/enseignant_profil.html', {
        'enseignant': enseignant,
        'active_page': 'profil',
    })