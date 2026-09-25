from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TicketState(str, Enum):
    AWAITING_INFO = "AWAITING_INFO"
    READY = "READY"
    OPEN = "OPEN"
    PENDING_TEAM_AVAILABILITY = "PENDING_TEAM_AVAILABILITY"
    QUEUED_OFF_HOURS = "QUEUED_OFF_HOURS"
    MANUAL_TRIAGE = "MANUAL_TRIAGE"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"

class Priority(str, Enum):
    P1 = "P1"; P2 = "P2"; P3 = "P3"; P4 = "P4"

class SLAState(str, Enum):
    OK = "OK"
    WARNED = "WARNED"
    BREACHED = "BREACHED"
    PAUSED = "PAUSED"

class Customer(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    tier: Optional[str] = "standard"

class Order(BaseModel):
    id: Optional[str] = None
    status: Optional[str] = None
    value: Optional[float] = None

class Product(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None

class Issue(BaseModel):
    category: Optional[str] = None
    severity: Optional[str] = None       # S1..S4
    description: Optional[str] = None

class Contact(BaseModel):
    preferred_channel: str = "email"
    email: Optional[str] = None
    phone: Optional[str] = None

class Evidence(BaseModel):
    type: str
    ref: str

class Extraction(BaseModel):
    customer: Customer = Customer()
    order: Order = Order()
    product: Product = Product()
    issue: Issue = Issue()
    contact: Contact = Contact()
    evidence: List[Evidence] = []
    sentiment: float = 0.0
    missing_fields: List[str] = []
    confidence: Dict[str, float] = {}

class SLAInfo(BaseModel):
    policy_version: str = "v1"
    allowed_minutes: int = 0
    elapsed_minutes: int = 0
    warn_at: int = 0
    breach_at: int = 0
    state: SLAState = SLAState.OK
    paused: bool = False
    started_at: Optional[datetime] = None
    last_paused_at: Optional[datetime] = None

class RoutingInfo(BaseModel):
    team: Optional[str] = None
    agent: Optional[str] = None
    reason: Optional[str] = None

class Links(BaseModel):
    parent_id: Optional[str] = None
    duplicates: List[str] = []
    related: List[str] = []
    problem_id: Optional[str] = None

class Ticket(BaseModel):
    ticket_id: Optional[str] = None
    state: TicketState = TicketState.READY
    priority: Priority = Priority.P4
    priority_score: float = 0.0
    customer: Customer = Customer()
    order: Order = Order()
    product: Product = Product()
    issue: Issue = Issue()
    contact: Contact = Contact()
    evidence: List[Evidence] = []
    sentiment: float = 0.0
    waiting_minutes_business: int = 0
    sla: SLAInfo = SLAInfo()
    routing: RoutingInfo = RoutingInfo()
    links: Links = Links()
    fingerprint: Optional[str] = None
    handoff_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)