from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'owner' | 'tenant' | 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    listings = db.relationship("Listing", backref="owner", lazy=True)
    tenant_profile = db.relationship("TenantProfile", backref="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    rent = db.Column(db.Integer, nullable=False)
    available_from = db.Column(db.Date, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)  # e.g. Single, Shared, 1BHK
    furnishing_status = db.Column(db.String(50), nullable=False)  # Furnished/Semi/Unfurnished
    photo_url = db.Column(db.String(300))
    description = db.Column(db.Text)
    is_filled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    interests = db.relationship("Interest", backref="listing", lazy=True)


class TenantProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    preferred_location = db.Column(db.String(150))
    budget_min = db.Column(db.Integer)
    budget_max = db.Column(db.Integer)
    move_in_date = db.Column(db.Date)
    bio = db.Column(db.Text)


class Interest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listing.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending/accepted/declined
    compatibility_score = db.Column(db.Integer)
    compatibility_explanation = db.Column(db.Text)
    score_source = db.Column(db.String(20), default="llm")  # 'llm' or 'fallback'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tenant = db.relationship("User", foreign_keys=[tenant_id])
    messages = db.relationship("Message", backref="interest", lazy=True)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interest_id = db.Column(db.Integer, db.ForeignKey("interest.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id])
