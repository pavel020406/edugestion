# ============================================================
# secretaire/views.py
# ============================================================

from functools import wraps
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa

from administrateur.models import Eleve, Classe
from parent.services import creer_ou_lier_parent
from utilisateurs.models import Utilisateur
from eleve.models import Message

from .models import FraisNiveau, TranchePaiement, Paiement, statut_paiements_eleve, eleves_en_retard


# ============================================================
# Décorateur d'accès : réservé au rôle "secretaire"
# ============================================================

def secretaire_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'secretaire':
            messages.error(request, "Accès réservé au secrétariat.")
            return redirect('connexion')
        return view_func(request, *args, **kwargs)
    return wrapper


def secretaire_ou_admin_required(view_func):
    """
    Pour les fonctionnalités partagées entre admin et secrétariat
    (frais, paiements) — le cahier des charges précise que l'admin
    et le secrétariat partagent les droits de gestion des paiements.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role not in ('secretaire', 'admin'):
            messages.error(request, "Accès réservé à l'administration et au secrétariat.")
            return redirect('connexion')
        return view_func(request, *args, **kwargs)
    return wrapper


def _frais_par_niveau_pour_js():
    """
    Construit {niveau_code: {'inscription':..,'scolarite':..,'configure':bool}}
    pour affichage en direct du montant dû dans le formulaire d'inscription.
    """
    donnees = {}
    for f in FraisNiveau.objects.all():
        donnees[f.niveau] = {
            'inscription': float(f.montant_inscription),
            'scolarite': float(f.montant_scolarite),
            'configure': f.configure,
        }
    return donnees


# ============================================================
# DASHBOARD
# ============================================================

@secretaire_required
def dashboard_secretaire(request):
    niveaux_configures = sum(1 for f in FraisNiveau.objects.all() if f.configure)
    retards = eleves_en_retard()

    contexte = {
        'active_page': 'dashboard',
        'total_eleves': Eleve.objects.count(),
        'total_classes': Classe.objects.count(),
        'total_frais_configures': niveaux_configures,
        'nb_eleves_en_retard': len(retards),
        'dernieres_inscriptions': Eleve.objects.order_by('-date_inscription')[:5],
    }
    return render(request, 'secretaire_dashboard/dashboard.html', contexte)


# ============================================================
# FRAIS PAR NIVEAU — montants + tranches + PDF programme/infos
# ============================================================

@secretaire_ou_admin_required
def frais_niveaux(request):
    """Liste des niveaux scolaires avec un résumé de leurs frais."""
    lignes = []
    for code, libelle in Classe.NIVEAU_CHOICES:
        frais = FraisNiveau.objects.filter(niveau=code).first()
        lignes.append({
            'code': code,
            'libelle': libelle,
            'nb_classes': Classe.objects.filter(niveau=code).count(),
            'frais': frais,
            'configure': bool(frais and frais.configure),
            'nb_tranches': frais.tranches.count() if frais else 0,
        })

    return render(request, 'secretaire_dashboard/frais/niveaux.html', {
        'lignes': lignes,
        'active_page': 'frais',
    })


@secretaire_ou_admin_required
def frais_niveau_detail(request, niveau):
    """Saisie des montants, du PDF, et gestion des tranches pour un niveau."""
    libelle = dict(Classe.NIVEAU_CHOICES).get(niveau)
    if libelle is None:
        messages.error(request, "Niveau scolaire invalide.")
        return redirect('frais_niveaux')

    frais, _ = FraisNiveau.objects.get_or_create(niveau=niveau)

    if request.method == 'POST':
        montant_inscription = request.POST.get('montant_inscription', '0').strip() or '0'
        montant_scolarite = request.POST.get('montant_scolarite', '0').strip() or '0'
        annee_scolaire = request.POST.get('annee_scolaire', '').strip()
        fichier = request.FILES.get('fichier_pdf')

        if fichier and not fichier.name.lower().endswith('.pdf'):
            messages.error(request, "Le fichier doit être au format PDF.")
            return redirect('frais_niveau_detail', niveau=niveau)

        frais.montant_inscription = montant_inscription
        frais.montant_scolarite = montant_scolarite
        if annee_scolaire:
            frais.annee_scolaire = annee_scolaire
        if fichier:
            frais.fichier_pdf = fichier
        frais.save()

        messages.success(request, f"Les frais du niveau « {libelle} » ont été enregistrés.")
        return redirect('frais_niveau_detail', niveau=niveau)

    return render(request, 'secretaire_dashboard/frais/detail.html', {
        'niveau': niveau,
        'libelle': libelle,
        'frais': frais,
        'tranches': frais.tranches.all(),
        'active_page': 'frais',
    })


@secretaire_ou_admin_required
def frais_niveau_supprimer_pdf(request, niveau):
    frais = get_object_or_404(FraisNiveau, niveau=niveau)
    if request.method == 'POST':
        frais.fichier_pdf.delete(save=False)
        frais.fichier_pdf = None
        frais.save()
        messages.success(request, "Le document a été supprimé.")
    return redirect('frais_niveau_detail', niveau=niveau)


# ── Tranches de paiement ─────────────────────────────────────

@secretaire_ou_admin_required
def frais_tranche_ajouter(request, niveau):
    libelle_niveau = dict(Classe.NIVEAU_CHOICES).get(niveau)
    if libelle_niveau is None:
        messages.error(request, "Niveau scolaire invalide.")
        return redirect('frais_niveaux')

    frais, _ = FraisNiveau.objects.get_or_create(niveau=niveau)

    if request.method == 'POST':
        libelle = request.POST.get('libelle', '').strip()
        montant = request.POST.get('montant', '').strip()
        date_limite_str = request.POST.get('date_limite', '').strip()

        if not libelle or not montant or not date_limite_str:
            messages.error(request, "Le libellé, le montant et la date limite sont obligatoires.")
            return render(request, 'secretaire_dashboard/frais/tranche_form.html', {
                'niveau': niveau, 'libelle_niveau': libelle_niveau,
                'tranche': None, 'active_page': 'frais',
            })

        try:
            date_limite = datetime.strptime(date_limite_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Date invalide.")
            return render(request, 'secretaire_dashboard/frais/tranche_form.html', {
                'niveau': niveau, 'libelle_niveau': libelle_niveau,
                'tranche': None, 'active_page': 'frais',
            })

        aujourd_hui = timezone.now().date()
        if date_limite < aujourd_hui:
            messages.error(request, "La date limite ne peut pas être antérieure à la date d'aujourd'hui (date d'enregistrement).")
            return render(request, 'secretaire_dashboard/frais/tranche_form.html', {
                'niveau': niveau, 'libelle_niveau': libelle_niveau,
                'tranche': None, 'active_page': 'frais',
            })

        derniere_tranche = frais.tranches.order_by('-ordre').first()
        if derniere_tranche and date_limite <= derniere_tranche.date_limite:
            messages.error(
                request,
                f"La date limite doit être postérieure à celle de « {derniere_tranche.libelle} » "
                f"({derniere_tranche.date_limite.strftime('%d/%m/%Y')}) : les tranches doivent se suivre dans le temps."
            )
            return render(request, 'secretaire_dashboard/frais/tranche_form.html', {
                'niveau': niveau, 'libelle_niveau': libelle_niveau,
                'tranche': None, 'active_page': 'frais',
            })

        TranchePaiement.objects.create(
            frais=frais,
            libelle=libelle,
            montant=montant,
            date_limite=date_limite,
            ordre=frais.tranches.count() + 1,
        )
        messages.success(request, "Tranche ajoutée avec succès.")
        return redirect('frais_niveau_detail', niveau=niveau)

    derniere_tranche_existante = frais.tranches.order_by('-ordre').first()
    aujourd_hui = timezone.now().date()
    if derniere_tranche_existante:
        date_min = max(aujourd_hui, derniere_tranche_existante.date_limite + timedelta(days=1))
    else:
        date_min = aujourd_hui

    return render(request, 'secretaire_dashboard/frais/tranche_form.html', {
        'niveau': niveau,
        'libelle_niveau': libelle_niveau,
        'tranche': None,
        'date_min': date_min,
        'active_page': 'frais',
    })


@secretaire_ou_admin_required
def frais_tranche_modifier(request, tranche_id):
    tranche = get_object_or_404(TranchePaiement, id=tranche_id)
    niveau = tranche.frais.niveau
    libelle_niveau = tranche.frais.get_niveau_display()

    if request.method == 'POST':
        libelle = request.POST.get('libelle', '').strip()
        montant = request.POST.get('montant', '').strip()
        date_limite_str = request.POST.get('date_limite', '').strip()

        contexte_erreur = {
            'niveau': niveau, 'libelle_niveau': libelle_niveau,
            'tranche': tranche, 'active_page': 'frais',
        }

        if not libelle or not montant or not date_limite_str:
            messages.error(request, "Le libellé, le montant et la date limite sont obligatoires.")
            return render(request, 'secretaire_dashboard/frais/tranche_form.html', contexte_erreur)

        try:
            date_limite = datetime.strptime(date_limite_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Date invalide.")
            return render(request, 'secretaire_dashboard/frais/tranche_form.html', contexte_erreur)

        aujourd_hui = timezone.now().date()
        if date_limite < aujourd_hui:
            messages.error(request, "La date limite ne peut pas être antérieure à la date d'aujourd'hui (date d'enregistrement).")
            return render(request, 'secretaire_dashboard/frais/tranche_form.html', contexte_erreur)

        # Vérifie que l'ordre chronologique des tranches reste respecté
        # par rapport à ses voisines (précédente et suivante).
        toutes_les_tranches = list(tranche.frais.tranches.all())
        index = next((i for i, t in enumerate(toutes_les_tranches) if t.id == tranche.id), None)
        precedente = toutes_les_tranches[index - 1] if index and index > 0 else None
        suivante = toutes_les_tranches[index + 1] if index is not None and index + 1 < len(toutes_les_tranches) else None

        if precedente and date_limite <= precedente.date_limite:
            messages.error(
                request,
                f"La date doit être postérieure à celle de « {precedente.libelle} » ({precedente.date_limite.strftime('%d/%m/%Y')})."
            )
            return render(request, 'secretaire_dashboard/frais/tranche_form.html', contexte_erreur)

        if suivante and date_limite >= suivante.date_limite:
            messages.error(
                request,
                f"La date doit être antérieure à celle de « {suivante.libelle} » ({suivante.date_limite.strftime('%d/%m/%Y')})."
            )
            return render(request, 'secretaire_dashboard/frais/tranche_form.html', contexte_erreur)

        tranche.libelle = libelle
        tranche.montant = montant
        tranche.date_limite = date_limite
        tranche.save()
        messages.success(request, "Tranche modifiée avec succès.")
        return redirect('frais_niveau_detail', niveau=niveau)

    toutes_les_tranches_get = list(tranche.frais.tranches.all())
    index_get = next((i for i, t in enumerate(toutes_les_tranches_get) if t.id == tranche.id), None)
    precedente_get = toutes_les_tranches_get[index_get - 1] if index_get and index_get > 0 else None
    suivante_get = toutes_les_tranches_get[index_get + 1] if index_get is not None and index_get + 1 < len(toutes_les_tranches_get) else None

    aujourd_hui_get = timezone.now().date()
    date_min = max(aujourd_hui_get, precedente_get.date_limite + timedelta(days=1)) if precedente_get else aujourd_hui_get
    date_max = (suivante_get.date_limite - timedelta(days=1)) if suivante_get else None

    return render(request, 'secretaire_dashboard/frais/tranche_form.html', {
        'niveau': niveau,
        'libelle_niveau': libelle_niveau,
        'tranche': tranche,
        'date_min': date_min,
        'date_max': date_max,
        'active_page': 'frais',
    })


@secretaire_ou_admin_required
def frais_tranche_supprimer(request, tranche_id):
    tranche = get_object_or_404(TranchePaiement, id=tranche_id)
    niveau = tranche.frais.niveau
    if request.method == 'POST':
        tranche.delete()
        messages.success(request, "Tranche supprimée.")
    return redirect('frais_niveau_detail', niveau=niveau)


# ============================================================
# ÉLÈVES — CRUD complet + inscription du parent
# ============================================================

@secretaire_required
def secretaire_list_eleve(request):
    search = request.GET.get('search', '')
    classe_id = request.GET.get('classe', '')

    eleves = Eleve.objects.select_related('classe').all()
    classe_filtree = None

    if search:
        eleves = eleves.filter(nom__icontains=search) | eleves.filter(prenom__icontains=search)
    if classe_id:
        eleves = eleves.filter(classe_id=classe_id)
        classe_filtree = Classe.objects.filter(id=classe_id).first()

    return render(request, 'secretaire_dashboard/eleves/list_eleve.html', {
        'eleves': eleves,
        'classes': Classe.objects.all(),
        'classe_filtree': classe_filtree,
        'total': eleves.count(),
        'active_page': 'eleves',
    })


@secretaire_required
def secretaire_add_eleve(request, eleve_id=None):
    eleve = None
    if eleve_id:
        eleve = get_object_or_404(Eleve, id=eleve_id)

    if request.method == 'POST':
        nom              = request.POST.get('nom', '').strip()
        prenom           = request.POST.get('prenom', '').strip()
        date_naissance   = request.POST.get('date_naissance')
        sexe             = request.POST.get('sexe')
        classe_id        = request.POST.get('classe')
        nom_parent       = request.POST.get('nom_parent', '').strip()
        telephone_parent = request.POST.get('telephone_parent', '').strip()
        email_parent     = request.POST.get('email_parent', '').strip()
        username         = request.POST.get('username', '').strip()
        password         = request.POST.get('password', '').strip()

        if not nom or not prenom or not date_naissance or not sexe or not nom_parent or not telephone_parent:
            messages.error(request, "Veuillez remplir tous les champs obligatoires (élève et parent).")
            return render(request, 'secretaire_dashboard/eleves/add_eleve.html', {
                'eleve': eleve, 'classes': Classe.objects.all(), 'active_page': 'eleves',
                'frais_par_niveau': _frais_par_niveau_pour_js(),
            })

        if eleve:
            eleve.nom              = nom
            eleve.prenom           = prenom
            eleve.date_naissance   = date_naissance
            eleve.sexe             = sexe
            eleve.classe_id        = classe_id or None
            eleve.nom_parent       = nom_parent
            eleve.telephone_parent = telephone_parent
            eleve.email_parent     = email_parent or None
            eleve.save()

            if eleve.compte:
                if username:
                    eleve.compte.username   = username
                    eleve.compte.first_name = prenom
                    eleve.compte.last_name  = nom
                if password:
                    eleve.compte.set_password(password)
                eleve.compte.save()

            messages.success(request, f"L'élève {nom} {prenom} a été modifié avec succès.")
            return redirect('secretaire_list_eleve')

        else:
            if not username:
                username = f"{prenom}.{nom}".lower().replace(' ', '')

            if Utilisateur.objects.filter(username=username).exists():
                messages.error(
                    request,
                    f"Le nom d'utilisateur « {username} » est déjà utilisé. Choisissez-en un autre."
                )
                return render(request, 'secretaire_dashboard/eleves/add_eleve.html', {
                    'eleve': None, 'classes': Classe.objects.all(), 'active_page': 'eleves',
                    'frais_par_niveau': _frais_par_niveau_pour_js(),
                })

            eleve = Eleve.objects.create(
                nom=nom, prenom=prenom, date_naissance=date_naissance, sexe=sexe,
                classe_id=classe_id or None,
                nom_parent=nom_parent, telephone_parent=telephone_parent,
                email_parent=email_parent or None,
            )

            mdp_final = password if password else eleve.matricule
            compte = Utilisateur(
                username=username, first_name=prenom, last_name=nom,
                email=email_parent or '', role='eleve',
            )
            compte.set_password(mdp_final)
            compte.save()

            eleve.compte = compte
            eleve.save()

            # ── Création ou liaison du compte parent (même formulaire) ──
            username_parent = request.POST.get('username_parent', '').strip()
            password_parent = request.POST.get('password_parent', '').strip()
            compte_parent, parent_cree, mdp_parent_affiche = creer_ou_lier_parent(
                eleve=eleve,
                nom_parent=nom_parent,
                telephone_parent=telephone_parent,
                email_parent=email_parent,
                username=username_parent,
                password=password_parent,
            )

            # ── Si un montant a été versé pour l'inscription, on l'enregistre
            #    immédiatement comme un vrai paiement (pas une simple estimation).
            montant_verse = request.POST.get('montant_inscription_paye', '').strip()
            paiement = None
            if montant_verse:
                try:
                    montant_verse_valeur = float(montant_verse)
                except ValueError:
                    montant_verse_valeur = 0
                if montant_verse_valeur > 0:
                    paiement = Paiement.objects.create(
                        eleve=eleve,
                        date_paiement=timezone.now().date(),
                        paie_inscription=True,
                        montant=montant_verse_valeur,
                        enregistre_par=request.user,
                    )

            message_succes = f"Élève inscrit avec succès. Identifiant : {username} — Mot de passe : {mdp_final}"
            if parent_cree:
                message_succes += f" — Compte parent créé : {compte_parent.username} / {mdp_parent_affiche}"
            else:
                message_succes += f" — Lié au compte parent existant : {compte_parent.username}"
            messages.success(request, message_succes)

            if paiement:
                return redirect('secretaire_recu_paiement', paiement_id=paiement.id)
            return redirect('secretaire_recu_inscription', eleve_id=eleve.id)

    return render(request, 'secretaire_dashboard/eleves/add_eleve.html', {
        'eleve': eleve, 'classes': Classe.objects.all(), 'active_page': 'eleves',
        'frais_par_niveau': _frais_par_niveau_pour_js(),
    })


@secretaire_required
def secretaire_detail_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    statut = statut_paiements_eleve(eleve)
    return render(request, 'secretaire_dashboard/eleves/detail_eleve.html', {
        'eleve': eleve, 'statut': statut, 'active_page': 'eleves',
    })


# ============================================================
# PAIEMENTS — enregistrement réel + reçus + suivi des retards
# ============================================================

@secretaire_ou_admin_required
def secretaire_paiement_ajouter(request, eleve_id):
    """Enregistre un paiement réel (inscription et/ou tranche(s))."""
    eleve = get_object_or_404(Eleve, id=eleve_id)
    statut = statut_paiements_eleve(eleve)

    if not statut['frais']:
        messages.error(
            request,
            f"Aucun tarif configuré pour le niveau « {eleve.classe.get_niveau_display() if eleve.classe else '—'} »."
        )
        return redirect('secretaire_detail_eleve', eleve_id=eleve.id)

    tranches_disponibles = [t for t in statut['tranches_statut'] if not t['payee']]

    if request.method == 'POST':
        date_paiement = request.POST.get('date_paiement', '').strip()
        montant = request.POST.get('montant', '').strip()
        paie_inscription = request.POST.get('paie_inscription') == '1' and not statut['inscription_payee']
        tranche_ids = request.POST.getlist('tranches')

        if not date_paiement or not montant:
            messages.error(request, "La date et le montant sont obligatoires.")
            return render(request, 'secretaire_dashboard/eleves/paiement_form.html', {
                'eleve': eleve, 'statut': statut,
                'tranches_disponibles': tranches_disponibles,
                'active_page': 'eleves',
            })

        if not paie_inscription and not tranche_ids:
            messages.error(request, "Sélectionnez au moins l'inscription ou une tranche.")
            return render(request, 'secretaire_dashboard/eleves/paiement_form.html', {
                'eleve': eleve, 'statut': statut,
                'tranches_disponibles': tranches_disponibles,
                'active_page': 'eleves',
            })

        paiement = Paiement.objects.create(
            eleve=eleve,
            date_paiement=date_paiement,
            paie_inscription=paie_inscription,
            montant=montant,
            enregistre_par=request.user,
        )
        if tranche_ids:
            paiement.tranches.set(TranchePaiement.objects.filter(id__in=tranche_ids))

        messages.success(request, "Paiement enregistré avec succès.")
        return redirect('secretaire_recu_paiement', paiement_id=paiement.id)

    return render(request, 'secretaire_dashboard/eleves/paiement_form.html', {
        'eleve': eleve, 'statut': statut,
        'tranches_disponibles': tranches_disponibles,
        'active_page': 'eleves',
    })


def _contexte_recu_paiement(paiement):
    eleve = paiement.eleve
    statut = statut_paiements_eleve(eleve)
    return {
        'eleve': eleve,
        'paiement': paiement,
        'statut': statut,
        'historique': statut['paiements'],
    }


@secretaire_ou_admin_required
def secretaire_recu_paiement(request, paiement_id):
    paiement = get_object_or_404(Paiement, id=paiement_id)
    contexte = _contexte_recu_paiement(paiement)
    contexte['active_page'] = 'eleves'
    return render(request, 'secretaire_dashboard/eleves/recu_paiement.html', contexte)


@secretaire_ou_admin_required
def secretaire_recu_paiement_pdf(request, paiement_id):
    paiement = get_object_or_404(Paiement, id=paiement_id)
    contexte = _contexte_recu_paiement(paiement)

    html = render_to_string('secretaire_dashboard/eleves/recu_paiement_pdf.html', contexte)
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF.", status=500)
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recu_paiement_{paiement.eleve.matricule}_{paiement.id}.pdf"'
    return response


@secretaire_ou_admin_required
def secretaire_paiements_retard(request):
    """Liste des élèves ayant au moins une tranche en retard de paiement."""
    retards = eleves_en_retard()
    return render(request, 'secretaire_dashboard/eleves/paiements_retard.html', {
        'retards': retards,
        'active_page': 'retard',
    })


def _contexte_recu(eleve):
    """Construit le contexte commun à la page de reçu (HTML) et au PDF."""
    frais = None
    tranches = []
    if eleve.classe:
        frais = FraisNiveau.objects.filter(niveau=eleve.classe.niveau).first()
        if frais:
            tranches = list(frais.tranches.all())
    return {
        'eleve': eleve,
        'frais': frais,
        'tranches': tranches,
    }


@secretaire_required
def secretaire_recu_inscription(request, eleve_id):
    """Page de confirmation après inscription : montant dû + accès au PDF."""
    eleve = get_object_or_404(Eleve, id=eleve_id)
    contexte = _contexte_recu(eleve)
    contexte['active_page'] = 'eleves'
    return render(request, 'secretaire_dashboard/eleves/recu_inscription.html', contexte)


@secretaire_required
def secretaire_recu_inscription_pdf(request, eleve_id):
    """Génère le reçu d'inscription en PDF (montant dû selon le niveau)."""
    eleve = get_object_or_404(Eleve, id=eleve_id)
    contexte = _contexte_recu(eleve)

    html = render_to_string('secretaire_dashboard/eleves/recu_pdf.html', contexte)
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF.", status=500)
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recu_inscription_{eleve.matricule}.pdf"'
    return response


@secretaire_required
def secretaire_delete_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    if request.method == 'POST':
        nom_complet = f"{eleve.nom} {eleve.prenom}"
        eleve.delete()
        messages.success(request, f"{nom_complet} a été supprimé avec succès.")
    return redirect('secretaire_list_eleve')


# ============================================================
# MESSAGES — vers l'élève (interne) et le parent (e-mail)
# ============================================================

@secretaire_required
def secretaire_messages(request):
    msgs = Message.objects.filter(
        expediteur__role='secretaire'
    ).select_related('eleve', 'destinataire')

    notifications_recues = Message.objects.filter(
        destinataire=request.user
    ).select_related('eleve', 'expediteur').order_by('-date_envoi')

    # Marque les notifications comme lues dès qu'on consulte la page.
    notifications_recues.filter(lu=False).update(lu=True)
    msgs_recus_parents = Message.objects.filter(
    destinataire=request.user,
    expediteur__role='parent',
).select_related('expediteur', 'eleve').order_by('-date_envoi')

    return render(request, 'secretaire_dashboard/messages/list_messages.html', {
        'messages_envoyes': msgs,
        'notifications_recues': notifications_recues,
        'active_page': 'messages',
        'messages_recus_parents': msgs_recus_parents,
    })


@secretaire_required
def secretaire_envoyer_message(request, eleve_id=None):
    eleve_preselect = None
    if eleve_id:
        eleve_preselect = get_object_or_404(Eleve, id=eleve_id)

    if request.method == 'POST':
        dest_eleve_id  = request.POST.get('eleve_id')
        sujet          = request.POST.get('sujet', '').strip()
        contenu        = request.POST.get('contenu', '').strip()
        envoyer_eleve  = request.POST.get('envoyer_eleve') == '1'
        envoyer_parent = request.POST.get('envoyer_parent') == '1'

        if not dest_eleve_id or not sujet:
            messages.error(request, "Veuillez choisir un élève et indiquer un sujet.")
            return render(request, 'secretaire_dashboard/messages/envoyer_message.html', {
                'eleves': Eleve.objects.select_related('classe').all().order_by('nom'),
                'eleve_preselect': eleve_preselect, 'active_page': 'messages',
            })

        if not envoyer_eleve and not envoyer_parent:
            messages.error(request, "Choisissez au moins un destinataire (élève et/ou parent).")
            return render(request, 'secretaire_dashboard/messages/envoyer_message.html', {
                'eleves': Eleve.objects.select_related('classe').all().order_by('nom'),
                'eleve_preselect': eleve_preselect, 'active_page': 'messages',
            })

        eleve = get_object_or_404(Eleve, id=dest_eleve_id)

        if envoyer_eleve:
            if eleve.compte:
                Message.objects.create(
                    expediteur=request.user, destinataire=eleve.compte, eleve=eleve,
                    type_message='general', sujet=sujet, contenu=contenu,
                )
            else:
                messages.warning(request, "Cet élève n'a pas de compte : message interne non envoyé.")

        if envoyer_parent:
            if eleve.email_parent:
                send_mail(
                    subject=sujet, message=contenu,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                    recipient_list=[eleve.email_parent], fail_silently=True,
                )
            else:
                messages.warning(request, "Aucun e-mail renseigné pour le parent : message non envoyé.")

        messages.success(request, f"Message traité pour {eleve.nom} {eleve.prenom}.")
        return redirect('secretaire_messages')

    return render(request, 'secretaire_dashboard/messages/envoyer_message.html', {
        'eleves': Eleve.objects.select_related('classe').all().order_by('nom'),
        'eleve_preselect': eleve_preselect, 'active_page': 'messages',
    })


# ============================================================
# PROFIL DU SECRÉTAIRE
# ============================================================

@secretaire_required
def secretaire_profil(request):
    utilisateur = request.user

    if request.method == 'POST':
        utilisateur.first_name = request.POST.get('first_name', utilisateur.first_name)
        utilisateur.last_name = request.POST.get('last_name', utilisateur.last_name)
        utilisateur.email = request.POST.get('email', utilisateur.email)

        nouveau_mdp = request.POST.get('password', '').strip()
        confirmer_mdp = request.POST.get('password_confirm', '').strip()

        if nouveau_mdp:
            if nouveau_mdp != confirmer_mdp:
                messages.error(request, "Les deux mots de passe ne correspondent pas.")
                return render(request, 'secretaire_dashboard/profil/profil.html', {
                    'active_page': 'profil',
                })
            utilisateur.set_password(nouveau_mdp)

        if 'photo_profil' in request.FILES:
            utilisateur.photo_profil = request.FILES['photo_profil']

        utilisateur.save()

        if nouveau_mdp:
            update_session_auth_hash(request, utilisateur)

        messages.success(request, "Votre profil a été mis à jour avec succès.")
        return redirect('secretaire_profil')

    return render(request, 'secretaire_dashboard/profil/profil.html', {
        'active_page': 'profil',
    })