from __future__ import annotations

from datetime import datetime

from ..config import RANKS
from ..models import Mission, MissionParticipant, ParticipantStatus, User


def format_profile(user: User, referrals_count: int, missions_completed: int) -> str:
    return (
        "🐾 *Твой профиль*\n"
        f"Ранг: *{user.rank}*\n"
        f"Хвосты: *{user.tails}*\n"
        f"Рефералов: *{referrals_count}*\n"
        f"Миссии завершены: *{missions_completed}*"
    )


def format_rank_progress(user: User) -> str:
    current_index = next((i for i, rank in enumerate(RANKS) if rank.name == user.rank), 0)
    lines = [f"💀 Твой текущий титул: *{user.rank}*"]
    if current_index + 1 < len(RANKS):
        next_rank = RANKS[current_index + 1]
        remaining = max(0, next_rank.min_tails - user.tails)
        lines.append(f"До ранга *{next_rank.name}* осталось {remaining} хвостов.")
    else:
        lines.append("Ты достиг вершины и стал легендой MEOW×404.")
    return "\n".join(lines)


def format_mission_card(mission: Mission) -> str:
    deadline_text = (
        mission.deadline.strftime("%d.%m.%Y %H:%M") if isinstance(mission.deadline, datetime) else "Без дедлайна"
    )
    return (
        f"⚡ *{mission.title}*\n"
        f"Награда: {mission.reward_tails} хвостов\n"
        f"Дедлайн: {deadline_text}\n\n"
        f"{mission.description}"
    )


def format_participation_status(participant: MissionParticipant) -> str:
    mapping = {
        ParticipantStatus.PENDING: "⏳ На проверке",
        ParticipantStatus.APPROVED: "✅ Принято",
        ParticipantStatus.REJECTED: "❌ Отклонено",
    }
    return mapping.get(participant.status, participant.status.value)
