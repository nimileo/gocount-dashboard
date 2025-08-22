import os, smtplib
from email.message import EmailMessage

def send_email(to_email: str, subject: str, body: str):
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = str(os.getenv("SMTP_USE_TLS", "true")).lower() == "true"
    from_email = os.getenv("FROM_EMAIL", "no-reply@example.com")

    if not host or not user or not password:
        # Dev fallback: print to console
        print("=== EMAIL DEV MODE ===")
        print("TO:", to_email)
        print("SUBJECT:", subject)
        print("BODY:\n", body)
        return

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, port) as s:
        if use_tls:
            s.starttls()
        s.login(user, password)
        s.send_message(msg)
