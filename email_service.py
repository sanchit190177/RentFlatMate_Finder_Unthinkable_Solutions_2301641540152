import logging
from flask_mail import Mail, Message as MailMessage

logger = logging.getLogger(__name__)
mail = Mail()


def send_email(subject, recipient, body):
    msg = MailMessage(subject=subject, recipients=[recipient], body=body)
    try:
        mail.send(msg)
    except Exception as exc:  # noqa: BLE001
        # Never let an email failure break the request/response flow
        logger.warning(
            "Email send failed (logged instead): %s | to=%s | subject=%s | body=%s",
            exc, recipient, subject, body,
        )


def notify_owner_high_score_interest(owner_email, tenant_name, listing_location, score):
    send_email(
        subject=f"High-match interest on your {listing_location} listing",
        recipient=owner_email,
        body=(f"{tenant_name} expressed interest in your listing at {listing_location} "
              f"with a compatibility score of {score}/100. Log in to RentMate to review."),
    )


def notify_tenant_interest_decision(tenant_email, listing_location, accepted):
    if accepted:
        body = f"Good news! The owner accepted your interest in {listing_location}. You can now chat."
    else:
        body = f"The owner declined your interest in {listing_location}. Keep browsing for other matches."
    send_email(
        subject=f"Your interest in {listing_location} was {'accepted' if accepted else 'declined'}",
        recipient=tenant_email,
        body=body,
    )
