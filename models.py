from app import db
from sqlalchemy import Numeric



# =========================
# Utilisateur
# =========================
class Utilisateur(db.Model):
    __tablename__ = 'utilisateur'

    id_utilisateur         = db.Column(db.Integer, primary_key=True)
    prenom_utilisateur     = db.Column(db.String(255), nullable=False)
    nom_utilisateur        = db.Column(db.String(255), nullable=False)
    email_utilisateur      = db.Column(db.String(255), unique=True, nullable=False)
    role_utilisateur       = db.Column(db.String(50), nullable=False)
    mot_de_passe_utilisateur = db.Column(db.String(255), nullable=False)

    # 1 utilisateur -> N clients
    clients = db.relationship('Client', backref='utilisateur', lazy=True)


# =========================
# Client
# =========================
class Client(db.Model):
    __tablename__ = 'client'

    id_client        = db.Column(db.Integer, primary_key=True)
    societe          = db.Column(db.String(255))
    numero_TVA       = db.Column(db.String(50))
    nom_client       = db.Column(db.String(255), nullable=False)
    prenom_client    = db.Column(db.String(255), nullable=False)
    adresse_client   = db.Column(db.Text, nullable=False)
    code_postal      = db.Column(db.String(20))
    ville            = db.Column(db.String(50))
    pays             = db.Column(db.String(50))
    email_client     = db.Column(db.String(255), nullable=False)
    telephone_client = db.Column(db.String(20))
    mot_de_passe_client = db.Column(db.String(255))

    id_utilisateur   = db.Column(db.Integer, db.ForeignKey('utilisateur.id_utilisateur'))


# =========================
# Projet
# =========================
class Projet(db.Model):
    __tablename__ = 'projet'

    id_projet        = db.Column(db.Integer, primary_key=True)
    nom_projet       = db.Column(db.String(255), nullable=False)
    description_projet = db.Column(db.Text)
    statut_projet    = db.Column(db.String(50), nullable=False)
    date_echeance    = db.Column(db.Date)  # optionnel
    slug             = db.Column(db.String(255), unique=True, nullable=False, index=True)

    id_client        = db.Column(db.Integer, db.ForeignKey('client.id_client'), nullable=False)

    # N projets -> 1 client
    client           = db.relationship('Client', backref='projets', lazy=True)


# =========================
# Ouvrage (catalogue articles)
# =========================
class Ouvrage(db.Model):
    __tablename__ = 'ouvrage'

    id_ouvrage          = db.Column(db.Integer, primary_key=True)
    description_ouvrage = db.Column(db.String(255), nullable=False)
    prix_unitaire       = db.Column(db.Float, nullable=False)
    unite_ouvrage       = db.Column(db.String(50), nullable=False)


# =========================
# Devis
# =========================
class Devis(db.Model):
    __tablename__ = 'devis'

    id_devis            = db.Column(db.Integer, primary_key=True)
    date_creation_devis = db.Column(db.Date, nullable=False)
    taux_TVA            = db.Column(db.Float, nullable=False, default=21.0)
    statut_devis        = db.Column(db.String(50), nullable=False)
    validite            = db.Column(db.Date, nullable=False)
    condition_reglement = db.Column(db.Text)

    id_projet       = db.Column(db.Integer, db.ForeignKey('projet.id_projet'))
    id_client       = db.Column(db.Integer, db.ForeignKey('client.id_client'))
    id_utilisateur  = db.Column(db.Integer, db.ForeignKey('utilisateur.id_utilisateur'), nullable=False)

    # N devis -> 1 client / 1 projet
    client = db.relationship('Client',  backref=db.backref('devis',  lazy=True))
    projet = db.relationship('Projet',  backref=db.backref('devis',  lazy=True))

    # 1 devis -> 1 facture (back_populates des 2 côtés, pas de backref dupliqué)
    facture = db.relationship(
        'Facture',
        back_populates='devis',
        uselist=False,
        cascade='all, delete-orphan'
    )

    # 1 devis -> N lignes
    lignes = db.relationship(
        'Ligne_Devis',
        back_populates='devis',
        cascade='all, delete-orphan',
        lazy=True,
        order_by='Ligne_Devis.id_ligne'
    )

    # ----- Totaux calculés -----
    @property
    def total_ht(self):
        total = 0.0
        for l in self.lignes or []:
            pu  = float(l.article.prix_unitaire or 0)
            qte = float(l.quantite_ouvrage or 0)
            total += pu * qte
        return round(total, 2)

    @property
    def total_tva(self):
        return round(self.total_ht * (float(self.taux_TVA) / 100.0), 2)

    @property
    def total_ttc(self):
        return round(self.total_ht + self.total_tva, 2)


# =========================
# Lignes de devis
# =========================
class Ligne_Devis(db.Model):
    __tablename__ = 'ligne_devis'

    id_ligne          = db.Column(db.Integer, primary_key=True)
    id_devis          = db.Column(db.Integer, db.ForeignKey('devis.id_devis'), nullable=False)
    id_article        = db.Column(db.Integer, db.ForeignKey('ouvrage.id_ouvrage'), nullable=False)
    quantite_ouvrage = db.Column(Numeric(10, 2), nullable=False, default=1)

    # N lignes -> 1 devis
    devis   = db.relationship('Devis',   back_populates='lignes')
    # N lignes -> 1 article
    article = db.relationship('Ouvrage', backref='lignes', lazy=True)


# =========================
# Facture
# =========================
class Facture(db.Model):
    __tablename__ = 'facture'

    id_facture           = db.Column(db.Integer, primary_key=True)
    date_creation_facture = db.Column(db.Date, nullable=False)
    statut_facture       = db.Column(db.String(50), nullable=False)
    acompte              = db.Column(db.Float)
    solde                = db.Column(db.Float)
    communication        = db.Column(db.Text)
    conditions           = db.Column(db.Text)
    date_echeance        = db.Column(db.Date, nullable=False)

    id_devis       = db.Column(db.Integer, db.ForeignKey('devis.id_devis'), unique=True, nullable=False)
    id_client      = db.Column(db.Integer, db.ForeignKey('client.id_client'))
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateur.id_utilisateur'))

    # 1 facture -> 1 devis (paire de back_populates *mirroir* de Devis.facture)
    devis  = db.relationship('Devis', back_populates='facture')
    client = db.relationship('Client')


# =========================
# Notification
# =========================
class Notification(db.Model):
    __tablename__ = 'notification'

    id_notification     = db.Column(db.Integer, primary_key=True)
    type_notifications  = db.Column(db.String(50), nullable=False)
    message             = db.Column(db.Text, nullable=False)
    statut_notifications = db.Column(db.String(50), nullable=False)
    date_envoi          = db.Column(db.Date, nullable=False)
    mode_de_notification = db.Column(db.String(50), nullable=False)

    id_facture     = db.Column(db.Integer, db.ForeignKey('facture.id_facture'))
    id_devis       = db.Column(db.Integer, db.ForeignKey('devis.id_devis'))
    id_paiement    = db.Column(db.Integer, db.ForeignKey('paiement.id_paiement'))
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateur.id_utilisateur'))


# =========================
# Paiement
# =========================
class Paiement(db.Model):
    __tablename__ = 'paiement'

    id_paiement     = db.Column(db.Integer, primary_key=True)
    montant         = db.Column(db.Float, nullable=False)
    date_paiement   = db.Column(db.Date, nullable=False)
    mode_paiement   = db.Column(db.String(50), nullable=False)
    statut_paiement = db.Column(db.String(50), nullable=False)

    id_facture     = db.Column(db.Integer, db.ForeignKey('facture.id_facture'))
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateur.id_utilisateur'))
