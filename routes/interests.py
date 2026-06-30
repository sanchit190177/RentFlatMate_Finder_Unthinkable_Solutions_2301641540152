from flask import Blueprint, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user

from models import db, Listing, TenantProfile, Interest
from llm_service import get_compatibility_score
from email_service import notify_owner_high_score_interest, notify_tenant_interest_decision

interests_bp = Blueprint("interests", __name__)


@interests_bp.route("/listings/<int:listing_id>/interest", methods=["POST"])
@login_required
def express_interest(listing_id):
    if current_user.role != "tenant":
        abort(403)

    listing = Listing.query.get_or_404(listing_id)
    profile = TenantProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash("Complete your profile before expressing interest.", "error")
        return redirect(url_for("listings.profile"))

    existing = Interest.query.filter_by(tenant_id=current_user.id, listing_id=listing_id).first()
    if existing:
        flash("You've already expressed interest in this listing.", "error")
        return redirect(url_for("listings.browse"))

    score, explanation, source = get_compatibility_score(listing, profile)

    interest = Interest(
        tenant_id=current_user.id,
        listing_id=listing_id,
        compatibility_score=score,
        compatibility_explanation=explanation,
        score_source=source,
    )
    db.session.add(interest)
    db.session.commit()

    if score >= current_app.config["HIGH_SCORE_THRESHOLD"]:
        notify_owner_high_score_interest(listing.owner.email, current_user.name, listing.location, score)

    flash(f"Interest sent. Compatibility score: {score}/100.", "success")
    return redirect(url_for("listings.browse"))


@interests_bp.route("/interests/<int:interest_id>/accept", methods=["POST"])
@login_required
def accept_interest(interest_id):
    interest = Interest.query.get_or_404(interest_id)
    if interest.listing.owner_id != current_user.id:
        abort(403)

    interest.status = "accepted"
    db.session.commit()
    notify_tenant_interest_decision(interest.tenant.email, interest.listing.location, accepted=True)
    flash("Interest accepted. Chat is now open.", "success")
    return redirect(url_for("main.dashboard"))


@interests_bp.route("/interests/<int:interest_id>/decline", methods=["POST"])
@login_required
def decline_interest(interest_id):
    interest = Interest.query.get_or_404(interest_id)
    if interest.listing.owner_id != current_user.id:
        abort(403)

    interest.status = "declined"
    db.session.commit()
    notify_tenant_interest_decision(interest.tenant.email, interest.listing.location, accepted=False)
    flash("Interest declined.", "success")
    return redirect(url_for("main.dashboard"))
