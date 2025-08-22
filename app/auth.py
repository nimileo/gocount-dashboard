import os, hashlib, secrets, random, string
from datetime import datetime, timedelta
from passlib.hash import bcrypt
from sqlalchemy.orm import Session
from . import models
from .emailer import send_email

def hash_password(pw: str) -> str:
    return bcrypt.hash(pw)

def verify_password(pw: str, pw_hash: str) -> bool:
    try:
        return bcrypt.verify(pw, pw_hash)
    except Exception:
    # in case hash schemes change
        return False

def random_otp(n=6) -> str:
    return "".join(random.choices(string.digits, k=n))

def hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

def create_and_send_login_otp(db: Session, user: models.User):
    code = random_otp(6)
    h = hash_otp(code)
    otp = models.OTP(
        user_id=user.id,
        code_hash=h,
        purpose="login",
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.add(otp)
    db.commit()
    subject = "Your gocount.ai login code"
    body = f"Hi,\n\nYour one-time code is: {code}\nIt expires in 10 minutes.\n\nIf you didn't request this, ignore this email."
    send_email(user.email, subject, body)

def verify_login_otp(db: Session, user: models.User, code: str) -> bool:
    h = hash_otp(code.strip())
    now = datetime.utcnow()
    otp = (db.query(models.OTP)
             .filter(models.OTP.user_id==user.id, models.OTP.purpose=="login",
                     models.OTP.consumed_at.is_(None), models.OTP.expires_at>=now)
             .order_by(models.OTP.id.desc())
             .first())
    if not otp:
        return False
    if otp.code_hash != h:
        return False
    otp.consumed_at = now
    db.add(otp); db.commit()
    return True
