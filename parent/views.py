# ============================================================
# parent/views.py
# ============================================================

from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from administrateur.models import Eleve, Classe, ParentEnfant
from secretaire.models import FraisNiveau, statut_paiements_eleve


def parent_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'parent':
            messages.error(request, "Accès réservé aux parents.")
            return redirect('connexion')
        return view_func(request, *args, **kwargs)
    return wrapper


def _enfants_du_parent(request):
    return Eleve.objects.filter(
        parents_lies__parent=request.user
    ).select_related('classe').distinct().order_by('nom', 'prenom')


def _enfant_selectionne(request, enfants):
    """
    Détermine l'enfant actuellement sélectionné (session), avec retombée
    sur le premier enfant de la liste si rien n'est encore choisi ou si
    la sélection précédente n'est plus valide.
    """
    enfant_id = request.session.get('parent_enfant_id')
    enfant = enfants.filter(id=enfant_id).first() if enfant_id else None
    if enfant is None:
        enfant = enfants.first()
        if enfant:
            request.session['parent_enfant_id'] = enfant.id
    return enfant


@parent_required
def parent_choisir_enfant(request, eleve_id):
    enfants = _enfants_du_parent(request)
    enfant = get_object_or_404(enfants, id=eleve_id)
    request.session['parent_enfant_id'] = enfant.id
    return redirect('dashboard_parent')


@parent_required
def dashboard_parent(request):
    enfants = _enfants_du_parent(request)

    if not enfants.exists():
        return render(request, 'parent_dashboard/aucun_enfant.html', {
            'active_page': 'dashboard',
        })

    enfant = _enfant_selectionne(request, enfants)
    statut = statut_paiements_eleve(enfant) if enfant else None

    return render(request, 'parent_dashboard/dashboard.html', {
        'enfants': enfants,
        'enfant': enfant,
        'statut': statut,
        'active_page': 'dashboard',
    })


@parent_required
def parent_frais_niveaux(request):
    """
    Vue d'ensemble de TOUS les niveaux de l'établissement (lecture seule) :
    montants, tranches et PDF, tels que configurés par le secrétariat.
    """
    niveaux = []
    for code, libelle in Classe.NIVEAU_CHOICES:
        frais = FraisNiveau.objects.filter(niveau=code).first()
        niveaux.append({
            'code': code,
            'libelle': libelle,
            'frais': frais,
            'configure': bool(frais and frais.configure),
            'tranches': frais.tranches.all() if frais else [],
        })

    enfants = _enfants_du_parent(request)
    enfant = _enfant_selectionne(request, enfants)

    return render(request, 'parent_dashboard/frais_niveaux.html', {
        'niveaux': niveaux,
        'enfant': enfant,
        'enfants': enfants,
        'active_page': 'frais',
    })


# ============================================================
# NOTES & BULLETINS (parent) — protégés par AccesEleve
# ============================================================

from eleve.models import AccesEleve
from administrateur.models import Note, ClasseMatiere, Matiere, Bulletin, BulletinAppreciation

from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa


@parent_required
def parent_notes(request):
    """
    Affiche les notes de l'enfant sélectionné pour un trimestre donné.
    Accès bloqué si AccesEleve n'a pas accordé l'accès 'notes' pour ce trimestre.
    """
    enfants = _enfants_du_parent(request)
    enfant = _enfant_selectionne(request, enfants)

    if not enfant:
        return redirect('dashboard_parent')

    trimestre = request.GET.get('trimestre', 'T1')
    if trimestre not in ('T1', 'T2', 'T3'):
        trimestre = 'T1'

    # Vérification de l'accès
    acces = AccesEleve.a_acces(enfant, 'notes', trimestre)

    if not acces:
        return render(request, 'parent_dashboard/acces_bloque.html', {
            'enfant': enfant,
            'enfants': enfants,
            'message': f"Les notes du {trimestre} ne sont pas encore publiées.",
            'active_page': 'notes',
        })

    # Construit les lignes de notes par matière
    lignes = []
    if enfant.classe:
        for cm in ClasseMatiere.objects.filter(classe=enfant.classe).select_related('matiere', 'enseignant'):
            notes_dict = {
                n.evaluation: n.valeur
                for n in Note.objects.filter(eleve=enfant, matiere=cm.matiere, trimestre=trimestre)
            }
            moy = Note.moyenne(enfant, cm.matiere, trimestre)
            lignes.append({
                'matiere': cm.matiere,
                'enseignant': cm.enseignant,
                'coefficient': cm.coefficient,
                'notes': notes_dict,
                'moyenne': moy,
            })

    moyenne_generale = Note.moyenne_generale_ponderee(enfant, trimestre)

    TRIMESTRES = [('T1', 'Trimestre 1'), ('T2', 'Trimestre 2'), ('T3', 'Trimestre 3')]
    acces_par_trimestre = {
        t: AccesEleve.a_acces(enfant, 'notes', t) for t, _ in TRIMESTRES
    }

    return render(request, 'parent_dashboard/notes.html', {
        'enfant': enfant,
        'enfants': enfants,
        'trimestre': trimestre,
        'trimestres': TRIMESTRES,
        'acces_par_trimestre': acces_par_trimestre,
        'lignes': lignes,
        'moyenne_generale': moyenne_generale,
        'evaluations': Note.EVALUATION_CHOICES,
        'active_page': 'notes',
    })


@parent_required
def parent_bulletins(request):
    """
    Page de choix du trimestre pour télécharger le bulletin PDF.
    Accès bloqué par AccesEleve pour chaque trimestre.
    """
    enfants = _enfants_du_parent(request)
    enfant = _enfant_selectionne(request, enfants)

    if not enfant:
        return redirect('dashboard_parent')

    TRIMESTRES = [('T1', 'Trimestre 1'), ('T2', 'Trimestre 2'), ('T3', 'Trimestre 3')]
    acces_par_trimestre = {
        t: AccesEleve.a_acces(enfant, 'notes', t) for t, _ in TRIMESTRES
    }

    return render(request, 'parent_dashboard/bulletins.html', {
        'enfant': enfant,
        'enfants': enfants,
        'trimestres': TRIMESTRES,
        'acces_par_trimestre': acces_par_trimestre,
        'active_page': 'notes',
    })


@parent_required
def parent_bulletin_pdf(request, trimestre):
    """Génère le bulletin PDF pour l'enfant sélectionné (réutilise le template admin)."""
    if trimestre not in ('T1', 'T2', 'T3'):
        return redirect('parent_bulletins')

    enfants = _enfants_du_parent(request)
    enfant = _enfant_selectionne(request, enfants)

    if not enfant or not enfant.classe:
        return redirect('parent_bulletins')

    if not AccesEleve.a_acces(enfant, 'notes', trimestre):
        return redirect('parent_bulletins')

    # Réutilise exactement la même logique que admin/bulletin_pdf
    classe = enfant.classe
    bulletin_obj = Bulletin(classe, trimestre)
    groupes_bruts = bulletin_obj.matieres_par_groupe()
    libelles_groupes = dict(Matiere.GROUPE_CHOICES)

    sections = []
    for code_groupe, classe_matieres in groupes_bruts.items():
        if not classe_matieres:
            continue
        lignes_matieres = []
        for cm in classe_matieres:
            notes_qs = Note.objects.filter(eleve=enfant, matiere=cm.matiere, trimestre=trimestre)
            notes_par_eval = {n.evaluation: n.valeur for n in notes_qs}
            moy_eleve = Note.moyenne(enfant, cm.matiere, trimestre)
            stats = bulletin_obj.stats_matiere(cm.matiere)
            lignes_matieres.append({
                'matiere': cm.matiere,
                'enseignant': cm.enseignant,
                'coefficient': cm.coefficient,
                'notes_par_eval': notes_par_eval,
                'moyenne': moy_eleve,
                'moyenne_ponderee': round(float(moy_eleve) * float(cm.coefficient), 2) if moy_eleve is not None else None,
                'stats_classe': stats,
                'rang': None,
            })
        sections.append({
            'code': code_groupe,
            'libelle': libelles_groupes.get(code_groupe, code_groupe),
            'matieres': lignes_matieres,
            'moyenne_groupe': bulletin_obj.moyenne_groupe(enfant, code_groupe),
        })

    appreciation, _ = BulletinAppreciation.objects.get_or_create(eleve=enfant, trimestre=trimestre)

    contexte = {
        'classe': classe,
        'eleve': enfant,
        'trimestre': trimestre,
        'sections': sections,
        'moyenne_generale': Note.moyenne_generale_ponderee(enfant, trimestre),
        'rang': bulletin_obj.rang_eleve(enfant),
        'effectif': classe.effectif,
        'moyenne_premier': bulletin_obj.moyenne_premier(),
        'moyenne_dernier': bulletin_obj.moyenne_dernier(),
        'moyenne_classe': bulletin_obj.moyenne_classe(),
        'appreciation': appreciation,
    }

    html = render_to_string('admin_dashboard/bulletin/bulletin_pdf.html', contexte, request=request)
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF.", status=500)
    buffer.seek(0)
    nom_fichier = f"bulletin_{enfant.nom}_{enfant.prenom}_{trimestre}.pdf"
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    return response


# ============================================================
# EMPLOI DU TEMPS (parent) — protégé par AccesEleve
# ============================================================

from administrateur.models import EmploiDuTemps, CreneauHoraire


@parent_required
def parent_emploi_du_temps(request):
    enfants = _enfants_du_parent(request)
    enfant = _enfant_selectionne(request, enfants)

    if not enfant:
        return redirect('dashboard_parent')

    # Vérification accès
    if not AccesEleve.a_acces(enfant, 'emploi'):
        return render(request, 'parent_dashboard/acces_bloque.html', {
            'enfant': enfant,
            'enfants': enfants,
            'message': "L'emploi du temps n'a pas encore été publié pour votre enfant.",
            'active_page': 'emploi',
        })

    if not enfant.classe:
        return render(request, 'parent_dashboard/emploi_du_temps.html', {
            'enfant': enfant,
            'enfants': enfants,
            'lignes_grille': [],
            'entetes_jours': [],
            'active_page': 'emploi',
        })

    # Construction de la grille (même logique que la vue admin)
    jours_ordonnes = [code for code, _ in CreneauHoraire.JOUR_CHOICES]
    libelles_jours = dict(CreneauHoraire.JOUR_CHOICES)

    emplois = {
        e.creneau_id: e
        for e in EmploiDuTemps.objects.filter(
            classe=enfant.classe
        ).select_related('matiere', 'enseignant', 'creneau')
    }

    creneaux = CreneauHoraire.objects.all()

    # Regroupe les créneaux par plage horaire
    plages = {}
    for c in creneaux:
        cle = (c.heure_debut, c.heure_fin)
        plages.setdefault(cle, {})[c.jour] = c

    lignes_grille = []
    for (heure_debut, heure_fin), creneaux_du_jour in sorted(plages.items()):
        premier = next(iter(creneaux_du_jour.values()))
        cellules = []
        for jour in jours_ordonnes:
            c = creneaux_du_jour.get(jour)
            if not c:
                cellules.append(None)
                continue
            emploi = emplois.get(c.id)
            cellules.append({
                'est_pause': c.est_pause,
                'matiere': emploi.matiere if emploi else None,
                'enseignant': emploi.enseignant if emploi else None,
            })
        lignes_grille.append({
            'heure_debut': heure_debut,
            'heure_fin': heure_fin,
            'est_pause': premier.est_pause,
            'cellules': cellules,
        })

    entetes_jours = [libelles_jours[j] for j in jours_ordonnes]

    return render(request, 'parent_dashboard/emploi_du_temps.html', {
        'enfant': enfant,
        'enfants': enfants,
        'lignes_grille': lignes_grille,
        'entetes_jours': entetes_jours,
        'active_page': 'emploi',
    })


# ============================================================
# MESSAGERIE (parent) — envoi vers admin + réception
# ============================================================

from eleve.models import Message as MessageEleve
from utilisateurs.models import Utilisateur


@parent_required
def parent_messages(request):
    """
    Messagerie du parent : messages reçus (de l'admin/secrétariat)
    + messages envoyés par le parent.
    """
    enfants = _enfants_du_parent(request)
    enfant = _enfant_selectionne(request, enfants)

    # Messages reçus par le parent (depuis admin/secrétariat)
    recus = MessageEleve.objects.filter(
        destinataire=request.user
    ).select_related('expediteur', 'eleve').order_by('-date_envoi')

    # Messages envoyés par le parent
    envoyes = MessageEleve.objects.filter(
        expediteur=request.user
    ).select_related('destinataire', 'eleve').order_by('-date_envoi')

    # Marque les messages reçus comme lus
    recus.filter(lu=False).update(lu=True)

    return render(request, 'parent_dashboard/messages.html', {
        'enfant': enfant,
        'enfants': enfants,
        'recus': recus,
        'envoyes': envoyes,
        'active_page': 'messages',
    })


@parent_required
def parent_envoyer_message(request):
    """
    Formulaire d'envoi d'un message vers l'administration ou le secrétariat.
    Les échanges transitent obligatoirement par l'administration (cahier des charges).
    """
    enfants = _enfants_du_parent(request)
    enfant = _enfant_selectionne(request, enfants)

    # Destinataires autorisés : admin + secrétaires uniquement
    destinataires = Utilisateur.objects.filter(
        role__in=['admin', 'secretaire']
    ).order_by('role', 'last_name')

    if request.method == 'POST':
        destinataire_id = request.POST.get('destinataire_id', '').strip()
        sujet = request.POST.get('sujet', '').strip()
        contenu = request.POST.get('contenu', '').strip()

        if not destinataire_id or not sujet:
            messages.error(request, "Veuillez choisir un destinataire et indiquer un sujet.")
            return render(request, 'parent_dashboard/envoyer_message.html', {
                'enfant': enfant,
                'enfants': enfants,
                'destinataires': destinataires,
                'active_page': 'messages',
            })

        try:
            destinataire = Utilisateur.objects.get(id=destinataire_id, role__in=['admin', 'secretaire'])
        except Utilisateur.DoesNotExist:
            messages.error(request, "Destinataire invalide.")
            return render(request, 'parent_dashboard/envoyer_message.html', {
                'enfant': enfant,
                'enfants': enfants,
                'destinataires': destinataires,
                'active_page': 'messages',
            })

        MessageEleve.objects.create(
            expediteur=request.user,
            destinataire=destinataire,
            eleve=enfant,
            type_message='general',
            sujet=sujet,
            contenu=contenu,
        )

        messages.success(request, "Votre message a été envoyé avec succès.")
        return redirect('parent_messages')

    return render(request, 'parent_dashboard/envoyer_message.html', {
        'enfant': enfant,
        'enfants': enfants,
        'destinataires': destinataires,
        'active_page': 'messages',
    })