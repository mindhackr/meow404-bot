from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    ActionType,
    Mission,
    MissionParticipant,
    MissionStatus,
    MissionVerifyMode,
    ParticipantStatus,
    User,
)
from .actions import log_action
from .users import award_tails


async def list_active_missions(session: AsyncSession) -> list[Mission]:
    result = await session.execute(
        select(Mission).where(Mission.status == MissionStatus.ACTIVE).order_by(Mission.deadline.asc())
    )
    return list(dict.fromkeys(result.scalars().all()))


async def get_mission(session: AsyncSession, mission_id: int) -> Mission | None:
    result = await session.execute(select(Mission).where(Mission.id == mission_id))
    return result.scalar_one_or_none()


async def join_mission(session: AsyncSession, mission: Mission, user: "User") -> MissionParticipant:
    result = await session.execute(
        select(MissionParticipant).where(
            MissionParticipant.mission_id == mission.id, MissionParticipant.user_id == user.id
        )
    )
    participant = result.scalar_one_or_none()
    if participant:
        return participant

    participant = MissionParticipant(mission_id=mission.id, user_id=user.id)
    session.add(participant)
    await log_action(
        session,
        user_id=user.id,
        action_type=ActionType.MISSION_JOINED,
        meta={"mission_id": mission.id},
    )
    return participant


async def submit_proof(
    session: AsyncSession,
    participant: MissionParticipant,
    proof_link: str,
) -> MissionParticipant:
    participant.proof_link = proof_link
    participant.status = ParticipantStatus.PENDING
    participant.created_at = datetime.utcnow()
    await log_action(
        session,
        user_id=participant.user_id,
        action_type=ActionType.MISSION_COMPLETED,
        meta={"mission_id": participant.mission_id, "proof_link": proof_link},
    )
    return participant


async def approve_participant(session: AsyncSession, participant: MissionParticipant) -> None:
    if participant.status == ParticipantStatus.APPROVED:
        return
    participant.status = ParticipantStatus.APPROVED
    participant.reward_paid_at = datetime.utcnow()
    await award_tails(session, participant.user, participant.mission.reward_tails, "mission_completed")


async def reject_participant(session: AsyncSession, participant: MissionParticipant) -> None:
    participant.status = ParticipantStatus.REJECTED
    participant.reward_paid_at = None


async def create_mission(
    session: AsyncSession,
    *,
    title: str,
    slug: str,
    description: str,
    reward_tails: int,
    deadline: datetime | None,
    verify_mode: MissionVerifyMode,
    extra: dict | None,
    activate: bool,
) -> Mission:
    mission = Mission(
        title=title,
        slug=slug,
        description=description,
        reward_tails=reward_tails,
        deadline=deadline,
        verify_mode=verify_mode,
        status=MissionStatus.ACTIVE if activate else MissionStatus.DRAFT,
        extra=extra,
    )
    session.add(mission)
    await session.flush()
    return mission


async def export_missions(session: AsyncSession) -> list[dict[str, object]]:
    result = await session.execute(select(Mission))
    missions: Iterable[Mission] = result.scalars().all()
    payload: list[dict[str, object]] = []
    for mission in missions:
        payload.append(
            {
                "id": mission.id,
                "title": mission.title,
                "slug": mission.slug,
                "status": mission.status.value,
                "reward_tails": mission.reward_tails,
                "deadline": mission.deadline.isoformat() if mission.deadline else None,
                "verify_mode": mission.verify_mode.value,
            }
        )
    return payload
