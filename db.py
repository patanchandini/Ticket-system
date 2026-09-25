from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()
engine = create_engine("sqlite:///tickets.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class TicketRow(Base):
    __tablename__ = "tickets"
    ticket_id = Column(String, primary_key=True)
    state = Column(String, index=True)
    priority = Column(String, index=True)
    priority_score = Column(Float)
    fingerprint = Column(String, index=True)
    order_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    category = Column(String, index=True)
    payload = Column(JSON)
    sla_state = Column(String, index=True)
    sla_breach_at = Column(DateTime, index=True)
    sla_warn_at = Column(DateTime, index=True)
    paused = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EventRow(Base):
    __tablename__ = "events"
    event_id = Column(String, primary_key=True)
    ticket_id = Column(String, index=True)
    event_type = Column(String, index=True)
    policy_version = Column(String)
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(engine)