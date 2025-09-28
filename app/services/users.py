from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import RANKS
from ..models import ActionType, ReferralLink, User
from .actions import log_action


def _generate_ref_code() -> str:
    return secrets.token_urlsafe(6)


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    normalized = username.strip().lstrip("@")
    if not normalized:
        return None
    result = await session.execute(select(User).where(User.username == normalized))
    return result.scalar_one_or_none()


async def ensure_user(session: AsyncSession, *, tg_id: int, username: str | None, first_name: str | None) -> User:
    user = await get_user_by_tg_id(session, tg_id)
    if user:
        updated = False
        if username != user.username:
            user.username = username
            updated = True
        if first_name != user.first_name:
            user.first_name = first_name
            updated = True
        if updated:
            user.last_action_at = datetime.utcnow()
        return user

    user = User(tg_id=tg_id, username=username, first_name=first_name)
    session.add(user)
    await session.flush()
    await log_action(session, user_id=user.id, action_type=ActionType.USER_JOINED)
    return user


async def ensure_referral_link(session: AsyncSession, user: User) -> ReferralLink:
    if user.referral_links:
        return user.referral_links[0]

    code = _generate_ref_code()
    while (await session.execute(select(ReferralLink).where(ReferralLink.code == code))).scalar_one_or_none():
        code = _generate_ref_code()
    link = ReferralLink(owner_id=user.id, code=code)
    session.add(link)
    await session.flush()
    return link


async def get_referral_owner_by_code(session: AsyncSession, code: str) -> User | None:
    result = await session.execute(
        select(User).join(ReferralLink, ReferralLink.owner_id == User.id).where(ReferralLink.code == code)
    )
    return result.scalar_one_or_none()


async def export_users(session: AsyncSession) -> list[dict[str, object]]:
    result = await session.execute(select(User))
    users = result.scalars().unique().all()
    data: list[dict[str, object]] = []
    for user in users:
        data.append(
            {
                "id": user.id,
                "tg_id": user.tg_id,
                "username": user.username,
                "rank": user.rank,
                "tails": user.tails,
                "referrer_id": user.referrer_id,
                "joined_at": user.joined_at.isoformat() if user.joined_at else None,
            }
        )
    return data


async def export_referrals(session: AsyncSession) -> list[dict[str, object]]:
    result = await session.execute(select(User))
    users = result.scalars().unique().all()
    payload: list[dict[str, object]] = []
    for user in users:
        payload.append(
            {
                "referrer_id": user.id,
                "referrer_username": user.username,
                "referrals": len(user.referrals),
            }
        )
    return payload


def get_rank_for_tails(tails: int) -> str:
    current = RANKS[0].name
    for rank in RANKS:
        if tails >= rank.min_tails:
            current = rank.name
        else:
            break
    return current


async def recalculate_rank(session: AsyncSession, user: User) -> None:
    new_rank = get_rank_for_tails(user.tails)
    if new_rank != user.rank:
        user.rank = new_rank
        await log_action(
            session,
            user_id=user.id,
            action_type=ActionType.RANK_UPDATED,
            meta={"rank": new_rank},
        )


async def award_tails(session: AsyncSession, user: User, amount: int, reason: str) -> None:
    if amount <= 0:
        return
    user.tails += amount
    user.last_action_at = datetime.utcnow()
    await log_action(
        session,
        user_id=user.id,
        action_type=ActionType.TAILS_GRANTED,
        value=amount,
        meta={"reason": reason},
    )
    await recalculate_rank(session, user)


async def register_referral(session: AsyncSession, user: User, referrer: User) -> bool:
    if user.id == referrer.id:
        return False
    if user.referrer_id:
        return False

    user.referrer_id = referrer.id
    await log_action(
        session,
        user_id=referrer.id,
        action_type=ActionType.REFERRAL_ACCEPTED,
        meta={"referred_user_id": user.id},
    )
    return True
