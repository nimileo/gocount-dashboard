# app/main.py
import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .database import SessionLocal, init_db
from . import models
from .auth import hash_password, verify_password, create_and_send_login_otp, verify_login_otp

# -------------------- Setup --------------------
load_dotenv()
app = FastAPI(title="Gocount Dashboard")

# session cookie for login
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret"),
    session_cookie=os.getenv("SESSION_COOKIE_NAME", "gocount_session"),
)

# static and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# -------------------- DB dependency --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------- Helpers --------------------
def get_current_user(request: Request, db: Session) -> Optional[models.User]:
    uid = request.session.get("uid")
    if not uid:
        return None
    # .get() is fine here; this is a small app
    return db.query(models.User).get(uid)

@app.on_event("startup")
def on_startup():
    init_db()

# -------------------- Auth pages --------------------
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "title": "Login"})

@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "title": "Login", "message": "Invalid email or password"},
        )
    # send OTP and show verify screen
    create_and_send_login_otp(db, user)
    return templates.TemplateResponse("verify.html", {"request": request, "email": user.email})

@app.post("/verify-otp", response_class=HTMLResponse)
def verify_otp(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
    if not user:
        return templates.TemplateResponse(
            "verify.html", {"request": request, "email": email, "message": "User not found"}
        )
    ok = verify_login_otp(db, user, code)
    if not ok:
        return templates.TemplateResponse(
            "verify.html", {"request": request, "email": email, "message": "Wrong or expired code"}
        )
    # log in
    request.session["uid"] = user.id
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard", status_code=302)

# -------------------- Dashboard --------------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    org = user.org
    docs = (
        db.query(models.Document)
        .filter(models.Document.org_id == org.id)
        .order_by(models.Document.created_at.desc())
        .limit(20)
        .all()
    )

    total_docs = db.query(models.Document).filter(models.Document.org_id == org.id).count()
    income_count = (
        db.query(models.Document)
        .filter(models.Document.org_id == org.id, models.Document.type == "income")
        .count()
    )
    expense_count = (
        db.query(models.Document)
        .filter(models.Document.org_id == org.id, models.Document.type == "expense")
        .count()
    )

    # very simple "this month" amount (best-effort based on stored 'date' like '08-Jan-2025')
    now = datetime.utcnow()
    this_month_amount = 0.0
    for d in docs:
        try:
            if d.date:
                dt = datetime.strptime(d.date, "%d-%b-%Y")
                if dt.year == now.year and dt.month == now.month:
                    this_month_amount += float(d.amount or 0)
        except Exception:
            pass

    currency = docs[0].currency if docs else "INR"

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "docs": docs,
            "stats": {
                "total_docs": total_docs,
                "income_count": income_count,
                "expense_count": expense_count,
                "this_month_amount": this_month_amount,
                "currency": currency,
            },
        },
    )

# -------------------- Ingest API --------------------
class IngestDoc(BaseModel):
    org_slug: str = Field(..., description="organization slug, e.g., 'count'")
    date: str = ""
    name: str = ""
    file: str = ""
    type: str = "unknown"
    amount: float = 0.0
    currency: str = "INR"
    status: str = "processed"

@app.post("/api/ingest")
def ingest(docs: List[IngestDoc], request: Request, db: Session = Depends(get_db)):
    api_key = request.headers.get("X-API-KEY")
    expected = os.getenv("INGEST_API_KEY")
    if not expected or api_key != expected:
        raise HTTPException(status_code=401, detail="Bad API key")

    inserted = 0
    for d in docs:
        org = db.query(models.Organization).filter(models.Organization.slug == d.org_slug).first()
        if not org:
            raise HTTPException(status_code=400, detail=f"Unknown org slug {d.org_slug}")
        rec = models.Document(
            org_id=org.id,
            date=d.date,
            name=d.name,
            file=d.file,
            type=d.type,
            amount=float(d.amount or 0),
            currency=d.currency,
            status=d.status,
        )
        db.add(rec)
        inserted += 1
    db.commit()
    return {"ok": True, "inserted": inserted}
