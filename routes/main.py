from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from models import Listing, Interest, TenantProfile

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    recent = Listing.query.filter_by(is_filled=False).order_by(Listing.created_at.desc()).limit(6).all()
    return render_template("index.html", recent=recent)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "owner":
        listings = Listing.query.filter_by(owner_id=current_user.id).order_by(Listing.created_at.desc()).all()
        pending_interests = (
            Interest.query.join(Listing)
            .filter(Listing.owner_id == current_user.id, Interest.status == "pending")
            .all()
        )
        return render_template("dashboard_owner.html", listings=listings, pending_interests=pending_interests)

    if current_user.role == "tenant":
        profile = TenantProfile.query.filter_by(user_id=current_user.id).first()
        my_interests = Interest.query.filter_by(tenant_id=current_user.id).order_by(Interest.created_at.desc()).all()
        return render_template("dashboard_tenant.html", profile=profile, my_interests=my_interests)

    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))

    return redirect(url_for("main.index"))
