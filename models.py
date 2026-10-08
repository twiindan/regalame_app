from typing import Optional, List
from datetime import date, datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, Index


def utcnow_naive() -> datetime:
    """Current naive UTC, matching this module's naive DateTime columns.

    Replaces the deprecated ``datetime.utcnow`` without switching to aware
    datetimes: an aware value round-trips back naive from a naive column and
    then compares unequal to what was written.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Tabla intermedia con datos extra (quién regala a quién)
class GroupMember(SQLModel, table=True):
    group_id: int = Field(foreign_key="group.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    giftee_id: Optional[int] = Field(default=None, foreign_key="user.id")

class GroupExclusion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id")
    giver_id: int = Field(foreign_key="user.id")
    forbidden_giftee_id: int = Field(foreign_key="user.id")

    group: "Group" = Relationship(back_populates="exclusions")

class Friendship(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    friend_id: int = Field(foreign_key="user.id", primary_key=True)
    created_at: datetime = Field(default_factory=utcnow_naive)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    hashed_password: str

    # Relaciones
    groups: List["Group"] = Relationship(
        back_populates="members",
        link_model=GroupMember,
        sa_relationship_kwargs={
            "primaryjoin": "User.id==GroupMember.user_id",
            "secondaryjoin": "Group.id==GroupMember.group_id",
        },
    )
    wishes: List["Wish"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"primaryjoin": "User.id==Wish.user_id"},
    )
    friends: List["User"] = Relationship(
        link_model=Friendship,
        sa_relationship_kwargs={
            "primaryjoin": "User.id==Friendship.user_id",
            "secondaryjoin": "User.id==Friendship.friend_id",
        },
    )

class Group(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    code: str = Field(unique=True, index=True)
    admin_id: int = Field(foreign_key="user.id")
    
    # Logística
    budget: Optional[str] = None
    event_date: Optional[date] = None

    members: List[User] = Relationship(
        back_populates="groups",
        link_model=GroupMember,
        sa_relationship_kwargs={
            "primaryjoin": "Group.id==GroupMember.group_id",
            "secondaryjoin": "User.id==GroupMember.user_id",
        },
    )
    exclusions: List[GroupExclusion] = Relationship(back_populates="group")

class Wish(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    title: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    
    # Sistema de reservas
    reserved_by_id: Optional[int] = Field(default=None, foreign_key="user.id")

    user: User = Relationship(
        back_populates="wishes",
        sa_relationship_kwargs={"foreign_keys": "[Wish.user_id]"}
    )

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id")
    sender_id: int = Field(foreign_key="user.id")
    receiver_id: int = Field(foreign_key="user.id")
    content: str
    timestamp: datetime = Field(default_factory=utcnow_naive)

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asin: str = Field(unique=True, index=True)
    title: str
    title_normalized: str = Field(index=True)
    image_url: Optional[str] = None
    url: str
    category: str = Field(index=True)
    category_slug: str = Field(index=True)
    price_numeric: Optional[float] = Field(default=None, index=True)
    price_raw: Optional[str] = None
    scraped_at: datetime
    updated_at: datetime = Field(default_factory=utcnow_naive)
    is_active: bool = Field(default=True, index=True)

class ProductList(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("product_id", "list_key", name="uq_productlist_product_list"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    list_key: str = Field(index=True)
    rank: int

class EditorialDecision(SQLModel, table=True):
    """One editorial decision per product (AI output + manual override).

    The AI-produced columns and the manual-override columns are separate
    nullable groups; the effective decision is ``coalesce(manual, ai)`` at the
    read sites. A manual override always wins over a fresh AI decision.
    """
    __tablename__ = "editorial_decision"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", unique=True, index=True)

    # AI-produced decision (nullable: a manual override may exist on its own).
    state: Optional[str] = None
    context: Optional[str] = None
    reason: Optional[str] = None
    model_id: Optional[str] = None
    policy_version: Optional[str] = None
    input_fingerprint: Optional[str] = None
    classified_at: Optional[datetime] = Field(default_factory=utcnow_naive)

    # Manual override (nullable: absent until an operator sets it).
    manual_state: Optional[str] = None
    manual_context: Optional[str] = None
    manual_reason: Optional[str] = None
    manual_updated_at: Optional[datetime] = None

class EditorialGateState(SQLModel, table=True):
    """Single-row record of the last evaluation-gate verdict."""
    __tablename__ = "editorial_gate_state"

    id: Optional[int] = Field(default=None, primary_key=True)
    gate_passed: bool
    coverage_ratio: float
    unknown_ratio: float
    overall_agreement: Optional[float] = None
    excluded_leak_ratio: Optional[float] = None
    policy_version: str
    model_id: str
    evaluated_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)

class ConversionEvent(SQLModel, table=True):
    """Append-only, privacy-scoped conversion event.

    Deliberately stores only the allowlisted event ``name`` and the naive UTC
    ``occurred_at``. No user id, email, group, wish, IP, or user-agent is ever
    persisted here: the privacy scope is enforced by the schema itself.
    """
    __tablename__ = "conversion_event"
    __table_args__ = (
        Index("ix_conversion_event_name_occurred_at", "name", "occurred_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    occurred_at: datetime = Field(default_factory=utcnow_naive, index=True)
