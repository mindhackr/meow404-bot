from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class ActionType(str, enum.Enum):
    REFERRAL_ACCEPTED = "referral_accepted"
    MISSION_JOINED = "mission_joined"
    MISSION_COMPLETED = "mission_completed"
    RANK_UPDATED = "rank_updated"
    TAILS_GRANTED = "tails_granted"
    STARS_RECEIVED = "stars_received"
    USER_JOINED = "user_joined"


class MissionVerifyMode(str, enum.Enum):
    AUTO_HASHTAG = "auto_hashtag"
    AUTO_REPOST = "auto_repost"
    MANUAL = "manual"


class MissionStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class ParticipantStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    referrer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    rank: Mapped[str] = mapped_column(String(64), default="Хвостик")
    tails: Mapped[int] = mapped_column(Integer, default=0)
    stars_total: Mapped[int] = mapped_column(Integer, default=0)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    flags: Mapped[dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    referrer: Mapped["User" | None] = relationship("User", remote_side=[id], backref="referrals")
    referral_links: Mapped[list["ReferralLink"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    missions: Mapped[list["MissionParticipant"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ReferralLink(Base):
    __tablename__ = "refs"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    joins: Mapped[int] = mapped_column(Integer, default=0)

    owner: Mapped[User] = relationship(back_populates="referral_links")


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[MissionStatus] = mapped_column(Enum(MissionStatus), default=MissionStatus.DRAFT, index=True)
    reward_tails: Mapped[int] = mapped_column(Integer, default=0)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verify_mode: Mapped[MissionVerifyMode] = mapped_column(Enum(MissionVerifyMode), default=MissionVerifyMode.MANUAL)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    participants: Mapped[list["MissionParticipant"]] = relationship(back_populates="mission", cascade="all, delete-orphan")


class MissionParticipant(Base):
    __tablename__ = "mission_participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    proof_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ParticipantStatus] = mapped_column(Enum(ParticipantStatus), default=ParticipantStatus.PENDING, index=True)
    reward_paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="missions")
    mission: Mapped[Mission] = relationship(back_populates="participants")


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[ActionType] = mapped_column(Enum(ActionType))
    meta_json: Mapped[dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Ban(Base):
    __tablename__ = "bans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    until_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

