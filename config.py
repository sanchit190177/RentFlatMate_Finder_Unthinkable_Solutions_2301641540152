import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'rentmate.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # LLM
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")

    # Mail (Gmail SMTP with app password, or any SMTP provider)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_USERNAME") or "no-reply@rentmate.local"
    # If no mail credentials are set, emails are logged to console instead of sent
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_USERNAME", "") == ""

    HIGH_SCORE_THRESHOLD = 80
