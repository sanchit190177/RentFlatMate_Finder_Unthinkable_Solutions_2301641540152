from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from models import db, Listing, TenantProfile, Interest

listings_bp = Blueprint("listings", __name__)


@listings_bp.route("/listings/new", methods=["GET", "POST"])
@login_required
def new_listing():
    if current_user.role != "owner":
        abort(403)

    if request.method == "POST":
        listing = Listing(
            owner_id=current_user.id,
            location=request.form.get("location", "").strip(),
            rent=int(request.form.get("rent", 0)),
            available_from=datetime.strptime(request.form.get("available_from"), "%Y-%m-%d").date(),
            room_type=request.form.get("room_type"),
            furnishing_status=request.form.get("furnishing_status"),
            photo_url=request.form.get("photo_url", "").strip() or None,
            description=request.form.get("description", "").strip(),
        )
        db.session.add(listing)
        db.session.commit()
        flash("Listing posted.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("listing_form.html")


@listings_bp.route("/listings/<int:listing_id>/fill", methods=["POST"])
@login_required
def mark_filled(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.owner_id != current_user.id:
        abort(403)
    listing.is_filled = True
    db.session.commit()
    flash("Listing marked as filled and hidden from search.", "success")
    return redirect(url_for("main.dashboard"))


@listings_bp.route("/browse")
@login_required
def browse():
    if current_user.role != "tenant":
        abort(403)

    profile = TenantProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash("Please complete your tenant profile first so we can rank listings for you.", "error")
        return redirect(url_for("listings.profile"))

    location = request.args.get("location", "").strip()
    max_budget = request.args.get("max_budget", type=int)

    query = Listing.query.filter_by(is_filled=False)
    if location:
        query = query.filter(Listing.location.ilike(f"%{location}%"))
    if max_budget:
        query = query.filter(Listing.rent <= max_budget)

    listings = query.order_by(Listing.created_at.desc()).all()

    # Rank by compatibility with the tenant's saved profile (rule-based for fast browse view;
    # the precise LLM score is computed and stored when interest is actually expressed)
    from llm_service import rule_based_score
    scored = []
    for listing in listings:
        score, _ = rule_based_score(listing, profile)
        scored.append((score, listing))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    already_interested_ids = {
        i.listing_id for i in Interest.query.filter_by(tenant_id=current_user.id).all()
    }

    return render_template(
        "browse.html", scored=scored, location=location, max_budget=max_budget,
        already_interested_ids=already_interested_ids,
    )


@listings_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if current_user.role != "tenant":
        abort(403)

    profile = TenantProfile.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        if not profile:
            profile = TenantProfile(user_id=current_user.id)
            db.session.add(profile)

        profile.preferred_location = request.form.get("preferred_location", "").strip()
        profile.budget_min = int(request.form.get("budget_min", 0))
        profile.budget_max = int(request.form.get("budget_max", 0))
        profile.move_in_date = datetime.strptime(request.form.get("move_in_date"), "%Y-%m-%d").date()
        profile.bio = request.form.get("bio", "").strip()
        db.session.commit()
        flash("Profile saved.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("profile_form.html", profile=profile)
