from typing import Optional, List
from datetime import date, datetime
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship

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
    created_at: datetime = Field(default_factory=datetime.utcnow)

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
    timestamp: datetime = Field(default_factory=datetime.utcnow)

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
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, index=True)

class ProductList(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("product_id", "list_key", name="uq_productlist_product_list"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    list_key: str = Field(index=True)
    rank: int
