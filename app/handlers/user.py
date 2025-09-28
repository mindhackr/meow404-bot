from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..config import get_settings
from ..db import session_manager
from ..models import MissionStatus, ParticipantStatus
from ..services import missions as missions_service
from ..services.users import (
    award_tails,
    ensure_referral_link,
    ensure_user,
    get_referral_owner_by_code,
    get_user_by_tg_id,
    register_referral,
)
from ..utils.keyboards import main_menu_keyboard, mission_keyboard, mission_participation_keyboard
from ..utils.texts import (
    format_mission_card,
    format_participation_status,
    format_profile,
    format_rank_progress,
)
from .states import ProofSubmissionState

router = Router()
settings = get_settings()


async def _check_membership(bot: Bot, user_id: int) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for title, chat_id in (("канал", settings.channel_id), ("обсуждения", settings.discussion_id)):
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in {"left", "kicked"}:
                missing.append(title)
        except Exception:
            missing.append(title)
    return len(missing) == 0, missing


async def _send_main_menu(message: Message, text: str) -> None:
    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot) -> None:
    args = (command.args or "").strip()
    user_id = message.from_user.id

    async with session_manager() as session:
        user = await ensure_user(
            session,
            tg_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        ref_owner = None
        if args:
            ref_owner = await get_referral_owner_by_code(session, args)
            if not ref_owner and args.isdigit():
                ref_owner = await get_user_by_tg_id(session, int(args))
        if ref_owner:
            linked = await register_referral(session, user, ref_owner)
            if linked:
                await award_tails(session, ref_owner, 3, "referral")

        is_member, missing = await _check_membership(bot, user_id)
        if not is_member:
            missing_text = " и ".join(missing)
            await message.answer(
                "Чтобы продолжить, подпишись на канал и обсуждения:"
                f"\n• @meowx404 ({missing_text})"
            )
            return

        link = await ensure_referral_link(session, user)

    await _send_main_menu(
        message,
        "🐾 MEOW×404: система трескается. Нажми кнопку, чтобы открыть панель.",
    )
    await message.answer(
        "Твоя персональная реф-ссылка:"
        f"\n`{settings.referral_base_url}?start={link.code}`",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    async with session_manager() as session:
        user = await ensure_user(
            session,
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        referrals = len(user.referrals)
        missions_completed = sum(1 for participant in user.missions if participant.status == ParticipantStatus.APPROVED)
        text = format_profile(user, referrals, missions_completed)
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("rank"))
async def cmd_rank(message: Message) -> None:
    async with session_manager() as session:
        user = await ensure_user(
            session,
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        text = format_rank_progress(user)
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("ref"))
async def cmd_ref(message: Message) -> None:
    async with session_manager() as session:
        user = await ensure_user(
            session,
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        link = await ensure_referral_link(session, user)
        text = (
            "🐱 Твоя ссылка для призыва хвостатых:\n"
            f"{settings.referral_base_url}?start={link.code}\n"
            f"Принято: {len(user.referrals)}"
        )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("missions"))
async def cmd_missions(message: Message) -> None:
    async with session_manager() as session:
        missions = await missions_service.list_active_missions(session)
    if not missions:
        await message.answer("Пока нет активных миссий. Следи за обновлениями! 💤")
        return
    for mission in missions:
        await message.answer(
            format_mission_card(mission),
            reply_markup=mission_keyboard(mission.id),
            parse_mode=ParseMode.MARKDOWN,
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "ℹ️ Доступные команды:\n"
        "/profile — профиль\n"
        "/rank — ранг\n"
        "/missions — миссии\n"
        "/ref — рефералка",
    )


@router.callback_query(F.data.startswith("menu:"))
async def cb_main_menu(callback: CallbackQuery) -> None:
    command = callback.data.split(":", 1)[1]
    message = callback.message
    if not message:
        await callback.answer()
        return

    if command == "profile":
        async with session_manager() as session:
            user = await ensure_user(
                session,
                tg_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
            )
            referrals = len(user.referrals)
            missions_completed = sum(
                1 for participant in user.missions if participant.status == ParticipantStatus.APPROVED
            )
            text = format_profile(user, referrals, missions_completed)
        await message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)
    elif command == "missions":
        async with session_manager() as session:
            missions = await missions_service.list_active_missions(session)
        if not missions:
            await message.edit_text("Пока нет активных миссий. 💤", reply_markup=main_menu_keyboard())
            await callback.answer()
            return
        text = "\n\n".join(format_mission_card(m) for m in missions)
        await message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)
    elif command == "rank":
        async with session_manager() as session:
            user = await ensure_user(
                session,
                tg_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
            )
            text = format_rank_progress(user)
        await message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)
    elif command == "ref":
        async with session_manager() as session:
            user = await ensure_user(
                session,
                tg_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
            )
            link = await ensure_referral_link(session, user)
            text = (
                "🐱 Поделись ссылкой:\n"
                f"{settings.referral_base_url}?start={link.code}\n"
                f"Принято: {len(user.referrals)}"
            )
        await message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)
    else:
        await message.edit_text(
            "ℹ️ Доступные команды:\n/profile — профиль\n/rank — ранг\n/missions — миссии\n/ref — рефералка",
            reply_markup=main_menu_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("mission:join:"))
async def cb_join_mission(callback: CallbackQuery) -> None:
    mission_id = int(callback.data.split(":")[2])
    async with session_manager() as session:
        user = await ensure_user(
            session,
            tg_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )
        mission = await missions_service.get_mission(session, mission_id)
        if not mission or mission.status != MissionStatus.ACTIVE:
            await callback.answer("Миссия недоступна", show_alert=True)
            return
        participant = await missions_service.join_mission(session, mission, user)
    await callback.message.answer(
        "Ты в миссии! Следуй инструкциям и пришли доказательство, когда будешь готов."
        f"\nСтатус: {format_participation_status(participant)}",
        reply_markup=mission_participation_keyboard(mission_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mission:proof:"))
async def cb_request_proof(callback: CallbackQuery, state: FSMContext) -> None:
    mission_id = int(callback.data.split(":")[2])
    await state.set_state(ProofSubmissionState.proof_link)
    await state.update_data(mission_id=mission_id)
    await callback.message.answer("Пришли ссылку на репост или хэштег-пост для проверки.")
    await callback.answer()


@router.message(ProofSubmissionState.proof_link)
async def handle_proof_submission(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    mission_id = data.get("mission_id")
    proof_link = (message.text or "").strip()
    if not proof_link:
        await message.answer("Нужно прислать ссылку или описание пруфа.")
        return

    async with session_manager() as session:
        user = await ensure_user(
            session,
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        mission = await missions_service.get_mission(session, mission_id)
        if not mission:
            await message.answer("Миссия не найдена.")
            await state.clear()
            return
        participant = await missions_service.join_mission(session, mission, user)
        participant = await missions_service.submit_proof(session, participant, proof_link)
    await state.clear()
    await message.answer(
        "⚡ Принято! ERR проверяет твой след. Хвосты будут начислены после верификации"
        f"\nТекущий статус: {format_participation_status(participant)}"
    )
