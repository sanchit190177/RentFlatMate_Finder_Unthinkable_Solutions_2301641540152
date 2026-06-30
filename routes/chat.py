from datetime import datetime
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from flask_socketio import join_room, emit

from app import socketio
from models import db, Interest, Message

chat_bp = Blueprint("chat", __name__)


def _authorized(interest, user):
    return user.id in (interest.tenant_id, interest.listing.owner_id)


@chat_bp.route("/chat/<int:interest_id>")
@login_required
def chat_room(interest_id):
    interest = Interest.query.get_or_404(interest_id)
    if not _authorized(interest, current_user) or interest.status != "accepted":
        abort(403)

    history = Message.query.filter_by(interest_id=interest_id).order_by(Message.sent_at.asc()).all()
    return render_template("chat.html", interest=interest, history=history)


@socketio.on("join")
def handle_join(data):
    interest_id = data.get("interest_id")
    interest = Interest.query.get(interest_id)
    if interest and _authorized(interest, current_user) and interest.status == "accepted":
        join_room(f"interest-{interest_id}")


@socketio.on("send_message")
def handle_send_message(data):
    interest_id = data.get("interest_id")
    content = (data.get("content") or "").strip()
    interest = Interest.query.get(interest_id)

    if not interest or not content or not _authorized(interest, current_user) or interest.status != "accepted":
        return

    message = Message(interest_id=interest_id, sender_id=current_user.id, content=content)
    db.session.add(message)
    db.session.commit()

    emit(
        "new_message",
        {
            "sender_id": current_user.id,
            "sender_name": current_user.name,
            "content": content,
            "sent_at": datetime.utcnow().strftime("%H:%M"),
        },
        room=f"interest-{interest_id}",
    )
