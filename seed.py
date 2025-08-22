import argparse, os, re, unicodedata
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app import models
from app.auth import hash_password

def slugify(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s or "org"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", required=True, help="Organization name")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="User password")
    args = parser.parse_args()

    init_db()
    db: Session = SessionLocal()

    slug = slugify(args.org)
    org = db.query(models.Organization).filter(models.Organization.slug==slug).first()
    if not org:
        org = models.Organization(name=args.org.strip(), slug=slug)
        db.add(org); db.commit(); db.refresh(org)
        print(f"Created org '{org.name}' with slug '{org.slug}'")

    user = db.query(models.User).filter(models.User.email==args.email.lower()).first()
    if not user:
        user = models.User(org_id=org.id, email=args.email.lower(), password_hash=hash_password(args.password), is_active=True)
        db.add(user); db.commit()
        print(f"Created user {user.email} in org '{org.name}'")
    else:
        print("User already exists")

if __name__ == "__main__":
    main()
