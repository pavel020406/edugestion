# ============================================================
# eleve/views.py — COMPLET avec vérification des accès
# ============================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.http import FileResponse, Http404

from administrateur.models import (
    Eleve, Classe, ClasseMatiere, Note, Bulletin,
    EmploiDuTemps, CreneauHoraire, Presence,
)
from .models import Message, AccesEleve


# ── Utilitaires ─────────────────────────────────────────────

def _get_eleve(user):
    try:
        return Eleve.objects.get(compte=user)
    except Eleve.DoesNotExist:
        return None


def _semaine_en_cours():
    from datetime import date, timedelta
    aujourd_hui = date.today()
    lundi = aujourd_hui - timedelta(days=aujourd_hui.weekday())
    jours = ['lundi','mardi','mercredi','jeudi','vendredi','samedi']
    return {j: lundi + timedelta(days=i) for i, j in enumerate(jours)}


def _nb_non_lus(user):
    return Message.objects.filter(destinataire=user, lu=False).count()


# ── Garde accès ─────────────────────────────────────────────

def _verifier_role(request):
    if request.user.role != 'eleve':
        from administrateur.views import redirect_selon_role
        return redirect_selon_role(request.user)
    return None


# ============================================================
# DASHBOARD
# ============================================================

@login_required
def dashboard_eleve(request):
    garde = _verifier_role(request)
    if garde: return garde

    eleve = _get_eleve(request.user)
    if not eleve:
        messages.error(request, "Profil élève introuvable.")
        return redirect('connexion')

    from datetime import date
    aujourd_hui = date.today()
    jours_fr    = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
    code_jour   = jours_fr[aujourd_hui.weekday()]

    trimestre_actif  = request.session.get('trimestre_eleve', 'T1')
    moyenne_generale = None
    prochains_cours  = []

    # Notes visibles uniquement si accès accordé
    if AccesEleve.a_acces(eleve, 'notes', trimestre_actif):
        moyenne_generale = Note.moyenne_generale_ponderee(eleve, trimestre_actif)

    # Emploi visible si accès accordé
    if eleve.classe and AccesEleve.a_acces(eleve, 'emploi'):
        prochains_cours = EmploiDuTemps.objects.filter(
            classe=eleve.classe,
            creneau__jour=code_jour,
            creneau__est_pause=False,
        ).select_related('creneau', 'matiere', 'enseignant').order_by('creneau__heure_debut')

    dernieres_notes = []
    if AccesEleve.a_acces(eleve, 'notes', trimestre_actif):
        dernieres_notes = Note.objects.filter(
            eleve=eleve, valeur__isnull=False
        ).select_related('matiere').order_by('-date_saisie')[:5]

    return render(request, 'dashboard_eleve/eleve_dashboard.html', {
        'eleve'           : eleve,
        'nb_non_lus'      : _nb_non_lus(request.user),
        'dernieres_notes' : dernieres_notes,
        'moyenne_generale': moyenne_generale,
        'trimestre_actif' : trimestre_actif,
        'prochains_cours' : prochains_cours,
        'aujourd_hui'     : aujourd_hui,
        'active_page'     : 'dashboard',
        # Accès disponibles
        'acces_notes'     : AccesEleve.a_acces(eleve, 'notes', trimestre_actif),
        'acces_emploi'    : AccesEleve.a_acces(eleve, 'emploi'),
        'acces_presence'  : AccesEleve.a_acces(eleve, 'presence'),
    })


# ============================================================
# NOTES
# ============================================================

@login_required
def eleve_notes(request):
    garde = _verifier_role(request)
    if garde: return garde

    eleve    = _get_eleve(request.user)
    trimestre = request.GET.get('trimestre', 'T1')
    if trimestre not in ('T1', 'T2', 'T3'):
        trimestre = 'T1'
    request.session['trimestre_eleve'] = trimestre

    # Vérification accès
    a_acces = AccesEleve.a_acces(eleve, 'notes', trimestre)

    lignes           = []
    moyenne_generale = None

    if a_acces and eleve and eleve.classe:
        classe_matieres = ClasseMatiere.objects.filter(
            classe=eleve.classe
        ).select_related('matiere', 'enseignant')

        for cm in classe_matieres:
            notes_qs = Note.objects.filter(
                eleve=eleve, matiere=cm.matiere, trimestre=trimestre
            )
            notes_par_eval = {n.evaluation: n.valeur for n in notes_qs}
            moy = Note.moyenne(eleve, cm.matiere, trimestre)
            lignes.append({
                'matiere'       : cm.matiere,
                'enseignant'    : cm.enseignant,
                'coefficient'   : cm.coefficient,
                'notes_par_eval': notes_par_eval,
                'moyenne'       : moy,
            })

        moyenne_generale = Note.moyenne_generale_ponderee(eleve, trimestre)

    return render(request, 'dashboard_eleve/eleve_notes.html', {
        'eleve'           : eleve,
        'lignes'          : lignes,
        'trimestre'       : trimestre,
        'moyenne_generale': moyenne_generale,
        'a_acces'         : a_acces,
        'active_page'     : 'mes_notes',
        'nb_non_lus'      : _nb_non_lus(request.user),
    })


# ============================================================
# EMPLOI DU TEMPS
# ============================================================

@login_required
def eleve_emploi(request):
    garde = _verifier_role(request)
    if garde: return garde

    eleve   = _get_eleve(request.user)
    a_acces = AccesEleve.a_acces(eleve, 'emploi')

    dates_semaine = _semaine_en_cours()
    jours_ordonnes = ['lundi','mardi','mercredi','jeudi','vendredi','samedi']
    libelles_jours = dict(CreneauHoraire.JOUR_CHOICES)

    entetes_jours = [
        {'libelle': libelles_jours.get(j, j), 'date': dates_semaine.get(j)}
        for j in jours_ordonnes
    ]

    lignes_grille = []

    if a_acces and eleve and eleve.classe:
        creneaux = CreneauHoraire.objects.all()
        emplois  = {
            e.creneau_id: e
            for e in EmploiDuTemps.objects.filter(
                classe=eleve.classe
            ).select_related('matiere', 'enseignant')
        }

        plages = {}
        for c in creneaux:
            plages.setdefault((c.heure_debut, c.heure_fin), {})[c.jour] = c

        for (hd, hf), creneaux_jour in sorted(plages.items()):
            premier  = next(iter(creneaux_jour.values()))
            cellules = []
            for jour in jours_ordonnes:
                cr = creneaux_jour.get(jour)
                if not cr:
                    cellules.append(None)
                    continue
                emploi = emplois.get(cr.id)
                cellules.append({
                    'matiere'   : emploi.matiere    if emploi else None,
                    'enseignant': emploi.enseignant if emploi else None,
                })
            lignes_grille.append({
                'heure_debut': hd,
                'heure_fin'  : hf,
                'est_pause'  : premier.est_pause,
                'cellules'   : cellules,
            })

    return render(request, 'dashboard_eleve/eleve_emploi.html', {
        'eleve'        : eleve,
        'lignes_grille': lignes_grille,
        'entetes_jours': entetes_jours,
        'a_acces'      : a_acces,
        'active_page'  : 'mon_emploi',
        'nb_non_lus'   : _nb_non_lus(request.user),
    })


# ============================================================
# PRÉSENCES
# ============================================================

@login_required
def eleve_presences(request):
    garde = _verifier_role(request)
    if garde: return garde

    eleve   = _get_eleve(request.user)
    a_acces = AccesEleve.a_acces(eleve, 'presence')

    presences    = []
    nb_absences  = 0
    nb_retards   = 0

    if a_acces and eleve:
        presences   = Presence.objects.filter(eleve=eleve).select_related('creneau').order_by('-date')[:50]
        nb_absences = Presence.objects.filter(eleve=eleve, statut='absent').count()
        nb_retards  = Presence.objects.filter(eleve=eleve, statut='retard').count()

    return render(request, 'dashboard_eleve/eleve_presences.html', {
        'eleve'      : eleve,
        'presences'  : presences,
        'nb_absences': nb_absences,
        'nb_retards' : nb_retards,
        'a_acces'    : a_acces,
        'active_page': 'mes_presences',
        'nb_non_lus' : _nb_non_lus(request.user),
    })


# ============================================================
# PROFIL
# ============================================================

@login_required
def eleve_profil(request):
    garde = _verifier_role(request)
    if garde: return garde

    eleve = _get_eleve(request.user)

    if request.method == 'POST':
        request.user.email = request.POST.get('email', request.user.email)
        nouveau_mdp = request.POST.get('password', '').strip()
        if nouveau_mdp:
            request.user.set_password(nouveau_mdp)
            update_session_auth_hash(request, request.user)
        if 'photo_profil' in request.FILES:
            request.user.photo_profil = request.FILES['photo_profil']
        request.user.save()
        messages.success(request, "Votre profil a été mis à jour.")
        return redirect('eleve_profil')

    return render(request, 'dashboard_eleve/eleve_profil.html', {
        'eleve'      : eleve,
        'nb_non_lus' : _nb_non_lus(request.user),
        'active_page': 'profil',
    })


# ============================================================
# MESSAGERIE
# ============================================================

@login_required
def eleve_messages(request):
    garde = _verifier_role(request)
    if garde: return garde

    msgs       = Message.objects.filter(destinataire=request.user).select_related('expediteur').order_by('-date_envoi')
    nb_non_lus = msgs.filter(lu=False).count()

    return render(request, 'dashboard_eleve/eleve_messages.html', {
        'messages_list': msgs,
        'nb_non_lus'   : nb_non_lus,
        'active_page'  : 'messages',
    })


@login_required
def eleve_message_detail(request, message_id):
    garde = _verifier_role(request)
    if garde: return garde

    msg = get_object_or_404(Message, id=message_id, destinataire=request.user)
    if not msg.lu:
        msg.lu = True
        msg.save(update_fields=['lu'])

    return render(request, 'dashboard_eleve/eleve_message_detail.html', {
        'msg'        : msg,
        'nb_non_lus' : _nb_non_lus(request.user),
        'active_page': 'messages',
    })


@login_required
def eleve_message_pdf(request, message_id):
    garde = _verifier_role(request)
    if garde: return garde

    msg = get_object_or_404(Message, id=message_id, destinataire=request.user)
    if not msg.fichier_pdf:
        raise Http404("Aucun fichier joint.")
    return FileResponse(
        msg.fichier_pdf.open('rb'),
        content_type='application/pdf',
        as_attachment=True,
        filename=f"{msg.sujet}.pdf"
    )