"""
db.py — the database layer for Shreya Auto Enterprises.

ONE SQLAlchemy setup that works the SAME on two databases; only the connection
string (SHREYA_DATABASE_URL, see config.py) changes between them:

  • SQLite  (default) — a single local file at  data/shreya.db .
                        No server, no password. Great for local + small sites.
  • MySQL   (production) — set:
        SHREYA_DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME
                        A real DB server (better for a busy, hosted site).

Tables:
  • inquiries — every contact-form message from the website.
  • reviews   — customer reviews (stay PENDING until the owner approves them).
  • sales     — a record of each car sold and who bought it (buyer capture).

Prices are NEVER shown to the public (see app.public_cars); the price stored on
a sale here is internal, for the owner's records only.
"""
import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, String, Integer, Text, Boolean, DateTime, select, delete
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column,
                            sessionmaker, scoped_session)

import config

DATABASE_URL = config.DATABASE_URL
_IS_SQLITE = DATABASE_URL.startswith("sqlite")

# SQLite: make sure the folder exists, and allow use across Flask's request threads.
if _IS_SQLITE:
    _path = DATABASE_URL.replace("sqlite:///", "", 1)
    if _path:
        os.makedirs(os.path.dirname(_path), exist_ok=True)

_connect_args = {"check_same_thread": False} if _IS_SQLITE else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True, connect_args=_connect_args)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False,
                                           expire_on_commit=False, future=True))


class Base(DeclarativeBase):
    pass


def _now():
    return datetime.now(timezone.utc)


class Inquiry(Base):
    __tablename__ = "inquiries"
    id:      Mapped[int] = mapped_column(Integer, primary_key=True)
    name:    Mapped[str] = mapped_column(String(120))
    phone:   Mapped[str] = mapped_column(String(40))
    car:     Mapped[str] = mapped_column(String(120), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "phone": self.phone, "car": self.car,
                "message": self.message,
                "time": (self.created_at or _now()).strftime("%Y-%m-%d %H:%M")}


class Review(Base):
    __tablename__ = "reviews"
    id:       Mapped[int] = mapped_column(Integer, primary_key=True)
    name:     Mapped[str] = mapped_column(String(80))
    rating:   Mapped[int] = mapped_column(Integer, default=5)
    text:     Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(60), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "rating": self.rating, "text": self.text,
                "location": self.location, "approved": self.approved,
                "time": (self.created_at or _now()).strftime("%Y-%m-%d")}


class Sale(Base):
    __tablename__ = "sales"
    id:          Mapped[int] = mapped_column(Integer, primary_key=True)
    car_id:      Mapped[int] = mapped_column(Integer, default=0)
    car_desc:    Mapped[str] = mapped_column(String(200), default="")
    buyer_name:  Mapped[str] = mapped_column(String(120), default="")
    buyer_phone: Mapped[str] = mapped_column(String(40), default="")
    price:       Mapped[str] = mapped_column(String(60), default="")   # internal only
    notes:       Mapped[str] = mapped_column(Text, default="")
    sold_on:     Mapped[datetime] = mapped_column(DateTime, default=_now)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self):
        return {"id": self.id, "car_id": self.car_id, "car_desc": self.car_desc,
                "buyer_name": self.buyer_name, "buyer_phone": self.buyer_phone,
                "price": self.price, "notes": self.notes,
                "sold_on": (self.sold_on or _now()).strftime("%Y-%m-%d")}


def init_db():
    """Create any missing tables. Safe to call on every startup."""
    Base.metadata.create_all(engine)


def _parse_dt(value, fmt):
    """Best-effort parse of an old JSON time string; fall back to 'now' if it can't."""
    try:
        return datetime.strptime(str(value), fmt)
    except (ValueError, TypeError):
        return _now()


def bulk_import_inquiries(items):
    """One-time migration: load old inquiries.json rows into the DB, keeping their time."""
    s = SessionLocal()
    try:
        for it in items:
            s.add(Inquiry(
                name=(it.get("name") or "")[:120], phone=(it.get("phone") or "")[:40],
                car=(it.get("car") or "")[:120], message=(it.get("message") or "")[:3000],
                created_at=_parse_dt(it.get("time", ""), "%Y-%m-%d %H:%M")))
        s.commit()
    finally:
        s.close()


def bulk_import_reviews(items):
    """One-time migration: load old reviews.json rows into the DB, keeping approval + date."""
    s = SessionLocal()
    try:
        for it in items:
            try:
                rating = int(it.get("rating", 5) or 5)
            except (ValueError, TypeError):
                rating = 5
            s.add(Review(
                name=(it.get("name") or "")[:80], rating=max(1, min(5, rating)),
                text=(it.get("text") or "")[:1000], location=(it.get("location") or "")[:60],
                approved=bool(it.get("approved", False)),
                created_at=_parse_dt(it.get("time", ""), "%Y-%m-%d")))
        s.commit()
    finally:
        s.close()


# ── Inquiries ────────────────────────────────────────────────────────────────
def add_inquiry(name, phone, car="", message=""):
    s = SessionLocal()
    try:
        row = Inquiry(name=name, phone=phone, car=car, message=message)
        s.add(row); s.commit()
        return row.as_dict()
    finally:
        s.close()


def all_inquiries():
    """Newest first."""
    s = SessionLocal()
    try:
        rows = s.execute(select(Inquiry).order_by(Inquiry.id.desc())).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


def delete_inquiry(inquiry_id):
    s = SessionLocal()
    try:
        s.execute(delete(Inquiry).where(Inquiry.id == inquiry_id)); s.commit()
    finally:
        s.close()


# ── Reviews ──────────────────────────────────────────────────────────────────
def add_review(name, rating, text, location=""):
    s = SessionLocal()
    try:
        row = Review(name=name, rating=rating, text=text, location=location, approved=False)
        s.add(row); s.commit()
        return row.as_dict()
    finally:
        s.close()


def all_reviews():
    """For the admin: pending first, then approved; newest within each group."""
    s = SessionLocal()
    try:
        rows = s.execute(
            select(Review).order_by(Review.approved.asc(), Review.id.desc())
        ).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


def approved_reviews():
    """For the public site: only approved, newest first."""
    s = SessionLocal()
    try:
        rows = s.execute(
            select(Review).where(Review.approved.is_(True)).order_by(Review.id.desc())
        ).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


def approve_review(review_id):
    s = SessionLocal()
    try:
        row = s.get(Review, review_id)
        if row:
            row.approved = True; s.commit()
    finally:
        s.close()


def delete_review(review_id):
    s = SessionLocal()
    try:
        s.execute(delete(Review).where(Review.id == review_id)); s.commit()
    finally:
        s.close()


# ── Sales / buyers ───────────────────────────────────────────────────────────
def add_sale(car_id=0, car_desc="", buyer_name="", buyer_phone="", price="", notes=""):
    s = SessionLocal()
    try:
        row = Sale(car_id=car_id, car_desc=car_desc, buyer_name=buyer_name,
                   buyer_phone=buyer_phone, price=price, notes=notes)
        s.add(row); s.commit()
        return row.as_dict()
    finally:
        s.close()


def all_sales():
    """Newest first."""
    s = SessionLocal()
    try:
        rows = s.execute(select(Sale).order_by(Sale.id.desc())).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


def delete_sale(sale_id):
    s = SessionLocal()
    try:
        s.execute(delete(Sale).where(Sale.id == sale_id)); s.commit()
    finally:
        s.close()


def count_rows():
    """Small helper used by the one-time JSON→DB migration to check emptiness."""
    s = SessionLocal()
    try:
        return {
            "inquiries": s.execute(select(Inquiry)).scalars().first() is not None,
            "reviews":   s.execute(select(Review)).scalars().first() is not None,
        }
    finally:
        s.close()
