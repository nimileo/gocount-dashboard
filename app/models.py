from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    users = relationship("User", back_populates="org")
    documents = relationship("Document", back_populates="org")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    email = Column(String(320), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    org = relationship("Organization", back_populates="users")
    otps = relationship("OTP", back_populates="user")

class OTP(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code_hash = Column(String(128), nullable=False)
    purpose = Column(String(32), default="login")
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="otps")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    date = Column(String(32))  # store normalized string like '01-Jan-2025'
    name = Column(String(300))
    file = Column(String(300))
    type = Column(String(24))  # 'income' or 'expense'
    amount = Column(Float, default=0.0)
    currency = Column(String(8), default="INR")
    status = Column(String(64), default="processed")
    created_at = Column(DateTime, default=datetime.utcnow)
    org = relationship("Organization", back_populates="documents")
