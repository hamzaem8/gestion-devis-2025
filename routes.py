from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
from functools import wraps
import re, unicodedata, os, smtplib, ssl
from datetime import datetime, date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

try:
    # PDF (facultatif). Si absent, on enverra l'email sans pièce jointe.
    from weasyprint import HTML
except Exception:
    HTML = None

from app import db
from app.models import (
    Utilisateur, Client, Projet, Devis, Ouvrage, Ligne_Devis, Facture
)

# --- Statuts autorisés pour une facture
ALLOWED_FACTURE_STATUTS = ("Brouillon", "Envoyée", "Payée")

# -------------------------------------------------------------------
# Utils
# -------------------------------------------------------------------
def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower()
    return text or 'projet'

def unique_slug_for_project(name: str) -> str:
    base = slugify(name)
    slug = base
    i = 2
    while Projet.query.filter_by(slug=slug).first() is not None:
        slug = f"{base}-{i}"
        i += 1
    return slug

main = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def wrapped_function(*args, **kwargs):
        if 'utilisateur_id' not in session:
            return redirect(url_for('main.connexion'))
        return f(*args, **kwargs)
    return wrapped_function

# -------------------------------------------------------------------
# Accueil / Auth
# -------------------------------------------------------------------
@main.route('/')
@login_required
def accueil():
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@login_required
def dashboard():
    try:
        return render_template('dashboard.html', prenom=session.get('prenom_utilisateur'))
    except Exception as e:
        print(f"/dashboard ERROR: {e}")
        return "Une erreur est survenue. Consulte les logs.", 500

@main.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        try:
            prenom = request.form['prenom']
            nom = request.form['nom']
            email = request.form['email']
            mot_de_passe = request.form['mot_de_passe']
            role = 'Utilisateur'

            if Utilisateur.query.filter_by(email_utilisateur=email).first():
                flash('Un compte avec cet email existe déjà.', 'danger')
                return redirect(url_for('main.inscription'))

            nouvel_utilisateur = Utilisateur(
                prenom_utilisateur=prenom,
                nom_utilisateur=nom,
                email_utilisateur=email,
                mot_de_passe_utilisateur=generate_password_hash(mot_de_passe),
                role_utilisateur=role
            )
            db.session.add(nouvel_utilisateur)
            db.session.commit()
            flash('Inscription réussie ! Veuillez vous connecter.', 'success')
            return redirect(url_for('main.confirmation_inscription'))
        except Exception as e:
            print(f"Inscription ERROR: {e}")
            flash('Une erreur est survenue. Veuillez réessayer.', 'danger')
            return redirect(url_for('main.inscription'))
    return render_template('inscription.html')

@main.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form['email'].strip()
        mot_de_passe = request.form['mot_de_passe']

        # DEBUG — OK car on est dans la requête
        print('LOGIN TRY:', email)
        utilisateur = Utilisateur.query.filter_by(email_utilisateur=email).first()
        print('FOUND USER:', bool(utilisateur))

        if utilisateur:
            from werkzeug.security import check_password_hash
            ok = check_password_hash(utilisateur.mot_de_passe_utilisateur, mot_de_passe)
            print('CHECK:', ok)

            if ok:
                session['utilisateur_id'] = utilisateur.id_utilisateur
                session['prenom_utilisateur'] = utilisateur.prenom_utilisateur
                return redirect(url_for('main.dashboard'))
            else:
                flash('Email ou mot de passe incorrect.', 'danger')
        else:
            flash('Compte introuvable.', 'danger')

    return render_template('connexion.html')


@main.route('/deconnexion')
def deconnexion():
    # on enlève l'utilisateur de la session
    session.pop('utilisateur_id', None)
    session.pop('prenom_utilisateur', None)
    session.pop('nom_utilisateur', None)

    # IMPORTANT : on vide les anciennes flash messages
    session.pop('_flashes', None)

    # puis on met seulement le message de déconnexion
    flash('Vous vous êtes déconnecté.', 'success')
    return redirect(url_for('main.connexion'))

# -------------------------------------------------------------------
# Clients
# -------------------------------------------------------------------
@main.route('/mes_clients')
@login_required
def mes_clients():
    try:
        q = request.args.get('q', '').strip()
        base = Client.query.filter_by(id_utilisateur=session['utilisateur_id'])
        if q:
            like = f"%{q}%"
            base = base.filter(or_(
                Client.nom_client.ilike(like),
                Client.prenom_client.ilike(like),
                Client.societe.ilike(like),
                Client.email_client.ilike(like),
                Client.ville.ilike(like),
            ))
        clients = base.order_by(Client.nom_client.asc(), Client.prenom_client.asc()).all()
        return render_template('mes_clients.html', clients=clients, q=q)
    except Exception as e:
        print(f"mes_clients ERROR: {e}")
        flash("Une erreur est survenue lors du chargement des clients.", "danger")
        return redirect(url_for('main.dashboard'))

@main.route('/ajouter_client', methods=['GET', 'POST'])
@login_required
def ajouter_client():
    if request.method == 'POST':
        try:
            nouveau_client = Client(
                societe=request.form.get('societe'),
                numero_TVA=request.form.get('numero_TVA'),
                prenom_client=request.form.get('prenom_client'),
                nom_client=request.form.get('nom_client'),
                adresse_client=request.form.get('adresse_client'),
                code_postal=request.form.get('code_postal'),
                ville=request.form.get('ville'),
                pays=request.form.get('pays'),
                email_client=request.form.get('email_client'),
                telephone_client=request.form.get('telephone_client'),
                id_utilisateur=session['utilisateur_id']
            )
            db.session.add(nouveau_client)
            db.session.commit()
            flash('Le client a été ajouté avec succès.', 'success')
            return redirect(url_for('main.mes_clients'))
        except Exception as e:
            print(f"ajouter_client ERROR: {e}")
            flash('Une erreur est survenue lors de l’ajout du client.', 'danger')
    return render_template('ajouter_client.html')

@main.route('/modifier_client/<int:client_id>', methods=['GET', 'POST'])
@login_required
def modifier_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        if request.method == 'POST':
            client.societe = request.form.get('societe')
            client.numero_TVA = request.form.get('numero_TVA')
            client.prenom_client = request.form.get('prenom_client')
            client.nom_client = request.form.get('nom_client')
            client.adresse_client = request.form.get('adresse_client')
            client.code_postal = request.form.get('code_postal')
            client.ville = request.form.get('ville')
            client.pays = request.form.get('pays')
            client.email_client = request.form.get('email_client')
            client.telephone_client = request.form.get('telephone_client')
            db.session.commit()
            flash('Client modifié avec succès.', 'success')
            return redirect(url_for('main.mes_clients'))
        return render_template('modifier_client.html', client=client)
    except Exception as e:
        print(f"modifier_client ERROR: {e}")
        flash('Une erreur est survenue lors de la modification du client.', 'danger')
        return redirect(url_for('main.mes_clients'))

@main.route('/supprimer_client/<int:client_id>', methods=['POST'])
@login_required
def supprimer_client(client_id):
    client = Client.query.get_or_404(client_id)
    try:
        db.session.delete(client)
        db.session.commit()
        flash("Client supprimé avec succès !", "success")
    except Exception as e:
        print(f"supprimer_client ERROR: {e}")
        flash("Une erreur est survenue. Veuillez réessayer.", "danger")
    return redirect(url_for('main.mes_clients'))

# -------------------------------------------------------------------
# Projets
# -------------------------------------------------------------------
@main.route('/ajouter_projet', methods=['GET', 'POST'])
@login_required
def ajouter_projet():
    if request.method == 'POST':
        try:
            client_id = request.form.get('client_id')
            client = Client.query.filter_by(id_client=client_id, id_utilisateur=session['utilisateur_id']).first()
            if not client:
                flash("Client invalide ou non autorisé.", "danger")
                return redirect(url_for('main.ajouter_projet'))

            nouveau_projet = Projet(
                nom_projet=request.form.get('nom_projet'),
                description_projet=request.form.get('description_projet'),
                statut_projet=request.form.get('statut_projet'),
                date_echeance=request.form.get('date_echeance'),
                id_client=client_id
            )
            db.session.add(nouveau_projet)
            db.session.commit()
            flash("Projet ajouté avec succès !", "success")
            return redirect(url_for('main.mes_projets'))
        except Exception as e:
            print(f"ajouter_projet ERROR: {e}")
            flash("Une erreur est survenue. Veuillez réessayer.", "danger")
    clients = Client.query.filter_by(id_utilisateur=session['utilisateur_id']).all()
    projets = Projet.query.join(Client).filter(Client.id_utilisateur == session['utilisateur_id']).all()
    return render_template('ajouter_projet.html', clients=clients)

@main.route('/mes_projets')
@login_required
def mes_projets():
    try:
        projets = (Projet.query
                   .join(Client)
                   .filter(Client.id_utilisateur == session['utilisateur_id'])
                   .all())
        return render_template('mes_projets.html', projets=projets)
    except Exception as e:
        print(f"mes_projets ERROR: {e}")
        flash("Une erreur est survenue lors du chargement des projets.", "danger")
        return redirect(url_for('main.dashboard'))

@main.route('/modifier_projet/<int:projet_id>', methods=['GET', 'POST'])
@login_required
def modifier_projet(projet_id):
    try:
        projet = Projet.query.get_or_404(projet_id)
        if request.method == 'POST':
            projet.nom_projet = request.form.get('nom_projet')
            projet.description_projet = request.form.get('description_projet')
            projet.statut_projet = request.form.get('statut_projet')
            projet.date_echeance = request.form.get('date_echeance')
            projet.id_client = request.form.get('client_id')
            db.session.commit()
            flash('Projet modifié avec succès.', 'success')
            return redirect(url_for('main.mes_projets'))
        return render_template('modifier_projet.html', projet=projet)
    except Exception as e:
        print(f"modifier_projet ERROR: {e}")
        flash('Une erreur est survenue lors de la modification du projet.', 'danger')
        return redirect(url_for('main.mes_projets'))

@main.route('/supprimer_projet/<int:projet_id>', methods=['POST'])
@login_required
def supprimer_projet(projet_id):
    try:
        projet = Projet.query.get_or_404(projet_id)
        db.session.delete(projet)
        db.session.commit()
        flash('Projet supprimé avec succès.', 'success')
    except Exception as e:
        print(f"supprimer_projet ERROR: {e}")
        flash('Une erreur est survenue lors de la suppression du projet.', 'danger')
    return redirect(url_for('main.mes_projets'))

# -------------------------------------------------------------------
# Devis
# -------------------------------------------------------------------
@main.route('/ajouter_devis', methods=['GET', 'POST'])
@login_required
def ajouter_devis():
    if request.method == 'POST':
        try:
            client_id = request.form.get('client_id')
            projet_id = request.form.get('projet_id')
            date_creation = request.form.get('date_creation')
            validite = request.form.get('validite')

            if not client_id or not projet_id or not date_creation:
                flash("Veuillez remplir tous les champs requis.", "danger")
                return redirect(url_for('main.ajouter_devis'))

            date_creation_dt = datetime.strptime(date_creation, '%Y-%m-%d').date()
            validite_dt = datetime.strptime(validite, '%Y-%m-%d').date() if validite else (date_creation_dt + timedelta(days=30))

            nouveau_devis = Devis(
                date_creation_devis=date_creation_dt,
                taux_TVA=21,
                statut_devis="En cours",
                validite=validite_dt,
                condition_reglement=None,
                id_projet=projet_id,
                id_client=client_id,
                id_utilisateur=session['utilisateur_id']
            )
            db.session.add(nouveau_devis)
            db.session.commit()
            flash("Le devis a été créé avec succès !", "success")
            return redirect(url_for('main.editer_lignes_devis', devis_id=nouveau_devis.id_devis))
        except Exception as e:
            db.session.rollback()
            print(f"ajouter_devis ERROR: {e}")
            flash("Une erreur est survenue lors de la création du devis.", "danger")
            return redirect(url_for('main.ajouter_devis'))

    clients = Client.query.filter_by(id_utilisateur=session['utilisateur_id']).all()
    projets = Projet.query.join(Client).filter(Client.id_utilisateur == session['utilisateur_id']).all()
    return render_template('creer_devis.html', clients=clients, projets=projets)

@main.route('/devis/<int:devis_id>/lignes', methods=['GET', 'POST'])
@login_required
def editer_lignes_devis(devis_id):
    devis = Devis.query.get_or_404(devis_id)
    if devis.id_utilisateur != session['utilisateur_id']:
        flash("Accès refusé.", "danger")
        return redirect(url_for('main.mes_devis'))

    ouvrages = Ouvrage.query.all()

    if request.method == 'POST':
        try:
            article_id = int(request.form.get('article_id'))
            quantite = float(request.form.get('quantite', 1))

            if quantite <= 0:
                raise ValueError("Quantité invalide")
            ligne = Ligne_Devis(id_devis=devis.id_devis, id_article=article_id, quantite_ouvrage=quantite)
            db.session.add(ligne)
            db.session.commit()
            flash("Ligne ajoutée.", "success")
        except Exception as e:
            db.session.rollback()
            print(f"editer_lignes_devis ERROR: {e}")
            flash("Impossible d'ajouter la ligne.", "danger")
        return redirect(url_for('main.editer_lignes_devis', devis_id=devis.id_devis))

    return render_template('editer_lignes_devis.html', devis=devis, ouvrages=ouvrages)

@main.route('/modifier_devis/<int:devis_id>', methods=['GET', 'POST'])
@login_required
def modifier_devis(devis_id):
    devis = Devis.query.get_or_404(devis_id)
    if devis.id_utilisateur != session['utilisateur_id']:
        flash("Vous n'êtes pas autorisé à modifier ce devis.", "danger")
        return redirect(url_for('main.mes_devis'))

    if request.method == 'POST':
        try:
            date_creation = request.form.get('date_creation') or None
            statut       = request.form.get('statut') or None
            validite     = request.form.get('validite') or None
            taux_tva_str = request.form.get('taux_tva')  # name="taux_tva" dans le template

            if date_creation:
                devis.date_creation_devis = datetime.strptime(date_creation, '%Y-%m-%d').date()
            if statut:
                devis.statut_devis = statut
            if validite:
                devis.validite = datetime.strptime(validite, '%Y-%m-%d').date()
            if taux_tva_str not in (None, ''):
                devis.taux_TVA = float(taux_tva_str.replace(',', '.'))

            db.session.commit()
            flash("Le devis a été modifié avec succès.", "success")
            return redirect(url_for('main.mes_devis'))
        except Exception as e:
            db.session.rollback()
            print(f"modifier_devis ERROR: {e}")
            flash("Une erreur est survenue lors de la modification du devis.", "danger")

    return render_template('modifier_devis.html', devis=devis)

@main.route('/supprimer_devis/<int:devis_id>', methods=['POST'])
@login_required
def supprimer_devis(devis_id):
    devis = Devis.query.get_or_404(devis_id)
    if devis.id_utilisateur != session['utilisateur_id']:
        flash("Vous n'êtes pas autorisé à supprimer ce devis.", "danger")
        return redirect(url_for('main.mes_devis'))
    try:
        db.session.delete(devis)
        db.session.commit()
        flash("Devis supprimé avec succès.", "success")
    except Exception as e:
        print(f"supprimer_devis ERROR: {e}")
        flash("Une erreur est survenue lors de la suppression du devis.", "danger")
    return redirect(url_for('main.mes_devis'))

@main.route('/mes_devis')
@login_required
def mes_devis():
    devis = (Devis.query
             .join(Client, Devis.id_client == Client.id_client)
             .filter(Client.id_utilisateur == session['utilisateur_id'],
                     Devis.statut_devis != 'Facturé')
             .order_by(Devis.id_devis.asc())
             .all())
    return render_template('mes_devis.html', devis=devis)

@main.route('/devis/<int:devis_id>/lignes/<int:ligne_id>/supprimer', methods=['POST'])
@login_required
def supprimer_ligne_devis(devis_id, ligne_id):
    ligne = (Ligne_Devis.query
             .join(Devis, Ligne_Devis.id_devis == Devis.id_devis)
             .filter(Ligne_Devis.id_ligne == ligne_id,
                     Ligne_Devis.id_devis == devis_id,
                     Devis.id_utilisateur == session['utilisateur_id'])
             .first_or_404())
    try:
        db.session.delete(ligne)
        db.session.commit()
        flash("Ligne supprimée.", "success")

        if Ligne_Devis.query.filter_by(id_devis=devis_id).count() == 0:
            devis = Devis.query.get_or_404(devis_id)
            db.session.delete(devis)
            db.session.commit()
            flash("La dernière ligne a été supprimée : le devis vide a été supprimé.", "success")
            return redirect(url_for('main.mes_devis'))
    except Exception as e:
        db.session.rollback()
        print(f"supprimer_ligne_devis ERROR: {e}")
        flash("Suppression impossible.", "danger")
    return redirect(url_for('main.editer_lignes_devis', devis_id=devis_id))

# -------------------------------------------------------------------
# Factures : génération PDF + envoi e-mail
# -------------------------------------------------------------------
def _smtp_conf():
    """Lit la config SMTP depuis les variables d'env."""
    server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    port = int(os.getenv('SMTP_PORT', '587'))
    user = os.getenv('SMTP_USER')
    pwd  = os.getenv('SMTP_PASS')
    sender = os.getenv('SMTP_SENDER', user)
    if not user or not pwd:
        raise RuntimeError("SMTP_USER/SMTP_PASS non configurés dans l'environnement.")
    return server, port, user, pwd, sender

def _invoice_context(facture: Facture):
    """Construit le contexte/les totaux pour la facture."""
    devis = Devis.query.get_or_404(facture.id_devis)
    client = Client.query.get_or_404(devis.id_client)
    lignes = devis.lignes or []
    total_ht = round(sum((float(l.article.prix_unitaire or 0) * float(l.quantite_ouvrage or 0)) for l in lignes), 2)
    tva_rate = float(devis.taux_TVA or 21.0)
    total_tva = round(total_ht * (tva_rate / 100.0), 2)
    total_ttc = round(total_ht + total_tva, 2)
    return devis, client, lignes, total_ht, tva_rate, total_tva, total_ttc

def _render_invoice_html(facture: Facture) -> str:
    """Rend l'HTML de la facture (on réutilise le template de détail)."""
    devis, client, lignes, total_ht, tva_rate, total_tva, total_ttc = _invoice_context(facture)
    return render_template(
        'facture_detail.html',
        facture=facture, devis=devis, client=client, lignes=lignes,
        total_ht=total_ht, total_tva=total_tva, total_ttc=total_ttc, tva_rate=tva_rate
    )

def _generate_pdf_from_html(html: str) -> bytes | None:
    """Retourne les bytes PDF (WeasyPrint), ou None si indisponible."""
    if HTML is None:
        print("[PDF] WeasyPrint non installé : envoi sans pièce jointe.")
        return None
    base_url = request.host_url  # ex: http://127.0.0.1:5000/
    pdf = HTML(string=html, base_url=base_url).write_pdf()
    return pdf

def _send_email_with_pdf(to_email: str, subject: str, html: str, pdf_bytes: bytes | None, pdf_filename: str):
    server, port, user, pwd, sender = _smtp_conf()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    txt = "Veuillez trouver ci-joint votre facture.\n"
    msg.attach(MIMEText(txt, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    if pdf_bytes:
        part = MIMEApplication(pdf_bytes, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(server, port, timeout=20) as smtp:
        smtp.starttls(context=context)
        smtp.login(user, pwd)
        smtp.sendmail(sender, [to_email], msg.as_string())

def send_invoice_email(facture: Facture):
    """Construit l'HTML, génère le PDF et envoie l’e-mail au client."""
    devis, client, *_ = _invoice_context(facture)
    if not client or not client.email_client:
        raise RuntimeError("Pas d'email client.")

    html = _render_invoice_html(facture)
    pdf_bytes = None
    try:
        pdf_bytes = _generate_pdf_from_html(html)
    except Exception as e:
        print(f"[PDF] Erreur génération PDF: {e} -> envoi sans pièce jointe")

    subject = f"Facture {facture.communication}"
    filename = f"{facture.communication}.pdf"
    _send_email_with_pdf(client.email_client, subject, html, pdf_bytes, filename)

# ---- Valider un devis -> créer (si besoin) + envoyer la facture
@main.route('/devis/<int:devis_id>/valider', methods=['POST'])
@login_required
def valider_devis(devis_id):
    devis = Devis.query.filter_by(id_devis=devis_id, id_utilisateur=session['utilisateur_id']).first_or_404()
    if not devis.lignes:
        flash("Ajoutez au moins une ligne avant validation.", "danger")
        return redirect(url_for('main.editer_lignes_devis', devis_id=devis_id))

    facture = Facture.query.filter_by(id_devis=devis_id).first()
    if facture is None:
        facture = Facture(
            date_creation_facture=date.today(),
            statut_facture='Payée',   # ou 'Envoyée'
            acompte=0,
            solde=devis.total_ttc,
            communication=f"FACT-{devis_id:05d}",
            conditions='Paiement sous 30 jours',
            date_echeance=date.today() + timedelta(days=30),
            id_devis=devis.id_devis,
            id_client=devis.id_client,
            id_utilisateur=devis.id_utilisateur
        )
        db.session.add(facture)

    devis.statut_devis = 'Facturé'
    db.session.commit()

    try:
        send_invoice_email(facture)
        flash("Facture générée et envoyée au client.", "success")
    except Exception as e:
        print(f"[MAIL] {e}")
        flash("Facture générée. (Envoi email non configuré)", "warning")

    return redirect(url_for('main.mes_devis'))

# ---- Affichage facture + liste
@main.route('/facture/<int:facture_id>')
@login_required
def facture_detail(facture_id):
    facture = (Facture.query
               .join(Devis, Facture.id_devis == Devis.id_devis)
               .filter(Facture.id_facture == facture_id,
                       Devis.id_utilisateur == session['utilisateur_id'])
               .first_or_404())

    devis, client, lignes, total_ht, tva_rate, total_tva, total_ttc = _invoice_context(facture)
    return render_template('facture_detail.html',
                           facture=facture, devis=devis, client=client, lignes=lignes,
                           total_ht=total_ht, total_tva=total_tva, total_ttc=total_ttc, tva_rate=tva_rate)

@main.route('/factures')
@main.route('/facture')   # alias
@login_required
def liste_facture():
    statut = (request.args.get('statut') or "").strip()

    q = (Facture.query
         .join(Devis, Facture.id_devis == Devis.id_devis)
         .filter(Devis.id_utilisateur == session['utilisateur_id'])
         .order_by(Facture.id_facture.desc()))

    if statut and statut in ALLOWED_FACTURE_STATUTS:
        q = q.filter(Facture.statut_facture == statut)

    factures = q.all()
    return render_template(
        'facture.html',
        factures=factures,
        statut=statut,
        STATUTS=ALLOWED_FACTURE_STATUTS
    )

@main.route('/facture/<int:facture_id>/statut', methods=['POST'])
@login_required
def maj_statut_facture(facture_id):
    facture = (Facture.query
               .join(Devis, Facture.id_devis == Devis.id_devis)
               .filter(Facture.id_facture == facture_id,
                       Devis.id_utilisateur == session['utilisateur_id'])
               .first_or_404())

    nouveau = (request.form.get('statut') or "").strip()
    if nouveau not in ALLOWED_FACTURE_STATUTS:
        flash("Statut invalide.", "danger")
    else:
        facture.statut_facture = nouveau
        db.session.commit()
        flash("Statut mis à jour.", "success")

    keep = request.args.get('retour_statut')
    if keep:
        return redirect(url_for('main.liste_facture', statut=keep))
    return redirect(url_for('main.liste_facture'))

# ---- Alias pratique pour le bouton "Voir les Factures" du dashboard
@main.route('/voir_factures')
@login_required
def voir_factures():
    return redirect(url_for('main.liste_facture'))

# -------------------------------------------------------------------
# Envoi d'un devis par email (depuis Mes Devis)
# -------------------------------------------------------------------

def _quote_context(devis: Devis):
    """Construit le contexte/les totaux pour un DEVIS."""
    client = Client.query.get_or_404(devis.id_client)
    lignes = devis.lignes or []
    total_ht = round(sum((float(l.article.prix_unitaire or 0) * float(l.quantite_ouvrage or 0)) for l in lignes), 2)
    tva_rate = float(devis.taux_TVA or 21.0)
    total_tva = round(total_ht * (tva_rate / 100.0), 2)
    total_ttc = round(total_ht + total_tva, 2)
    return client, lignes, total_ht, tva_rate, total_tva, total_ttc

def _render_devis_email_html(devis: Devis, client: Client,
                             total_ht: float, tva_rate: float, total_tva: float, total_ttc: float,
                             lien_page: str) -> str:
    """Corps HTML minimal pour l'email de devis (pas de template séparé nécessaire)."""
    return f"""<!doctype html>
<html lang="fr"><body style="font-family:Arial,sans-serif">
  <p>Bonjour {client.prenom_client or client.nom_client},</p>
  <p>Veuillez trouver votre <strong>devis n° {devis.id_devis}</strong>
     relatif au projet <strong>{devis.projet.nom_projet}</strong>.</p>
  <p>
    Total HT : <strong>{total_ht:.2f} €</strong><br>
    TVA ({tva_rate:.1f} %) : <strong>{total_tva:.2f} €</strong><br>
    Total TTC : <strong>{total_ttc:.2f} €</strong>
  </p>
  <p>➡️ Consulter le devis en ligne : <a href="{lien_page}">{lien_page}</a></p>
  <p>Bien à vous,<br>Gestion Devis</p>
</body></html>"""

@main.route('/devis/<int:devis_id>/envoyer', methods=['POST'])
@login_required
def envoyer_devis(devis_id):
    """Envoie le DEVIS par e-mail au client (sans pièce jointe)."""
    devis = Devis.query.get_or_404(devis_id)
    # sécurité : propriétaire uniquement
    if devis.id_utilisateur != session['utilisateur_id']:
        flash("Accès refusé.", "danger")
        return redirect(url_for('main.mes_devis'))

    client, lignes, total_ht, tva_rate, total_tva, total_ttc = _quote_context(devis)

    if not client.email_client:
        flash("Ce client n’a pas d’adresse email.", "danger")
        return redirect(url_for('main.mes_devis'))

    lien_page = url_for('main.editer_lignes_devis', devis_id=devis.id_devis, _external=True)
    html = _render_devis_email_html(devis, client, total_ht, tva_rate, total_tva, total_ttc, lien_page)
    subject = f"Votre devis #{devis.id_devis} — {devis.projet.nom_projet}"

    try:
        # On réutilise le même expéditeur SMTP que pour les factures, sans PDF
        _send_email_with_pdf(client.email_client, subject, html, None, "")
        flash(f"Devis #{devis.id_devis} envoyé à {client.email_client}.", "success")
    except Exception as e:
        print(f"[MAIL DEVIS] {e}")
        flash("Échec de l’envoi du devis. Vérifie la configuration SMTP.", "danger")

    return redirect(url_for('main.mes_devis'))
