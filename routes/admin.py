from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from models import User, Listing, Interest

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@login_required
def dashboard():
    if current_user.role != "admin":
        abort(403)

    users = User.query.order_by(User.created_at.desc()).all()
    listings = Listing.query.order_by(Listing.created_at.desc()).all()
    interests = Interest.query.order_by(Interest.created_at.desc()).limit(50).all()

    return render_template("admin.html", users=users, listings=listings, interests=interests)
