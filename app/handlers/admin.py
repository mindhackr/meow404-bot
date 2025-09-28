from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from ..config import get_settings
from ..db import session_manager
from ..models import MissionVerifyMode
from ..services import missions as missions_service
from ..services.users import award_tails, export_referrals, export_users, get_user_by_username
from ..utils.keyboards import admin_panel_keyboard
from ..utils.texts import format_mission_card
from .states import MissionCreationStates

router = Router()
settings = get_settings()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


async def _ensure_admin(message: Message) -> bool:
    if not _is_admin(message.from_user.id):
        await message.answer("Эта панель доступна только администраторам.")
        return False
    return True


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    await message.answer("Админ-панель MEOW×404", reply_markup=admin_panel_keyboard())


@router.callback_query(F.data == "admin:mission_new")
async def cb_admin_mission_new(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(MissionCreationStates.title)
    await callback.message.answer("Введи название миссии:")
    await callback.answer()


@router.message(Command("mission_new"))
async def cmd_mission_new(message: Message, state: FSMContext) -> None:
    if not await _ensure_admin(message):
        return
    await state.set_state(MissionCreationStates.title)
    await message.answer("Введи название миссии:")


@router.message(MissionCreationStates.title)
async def mission_title(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(MissionCreationStates.slug)
    await message.answer("Придумай короткий slug (латиница, без пробелов):")


@router.message(MissionCreationStates.slug)
async def mission_slug(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(slug=(message.text or "").strip())
    await state.set_state(MissionCreationStates.description)
    await message.answer("Дай описание миссии:")


@router.message(MissionCreationStates.description)
async def mission_description(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(description=(message.text or "").strip())
    await state.set_state(MissionCreationStates.reward)
    await message.answer("Сколько хвостов награда?")


@router.message(MissionCreationStates.reward)
async def mission_reward(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    try:
        reward = int((message.text or "").strip())
    except ValueError:
        await message.answer("Нужно число. Попробуй ещё раз")
        return
    await state.update_data(reward=reward)
    await state.set_state(MissionCreationStates.deadline)
    await message.answer("Дедлайн (формат YYYY-MM-DD HH:MM) или 'нет':")


@router.message(MissionCreationStates.deadline)
async def mission_deadline(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    text = (message.text or "").strip().lower()
    deadline = None
    if text not in {"нет", "no", "none", "-"}:
        try:
            deadline = datetime.strptime((message.text or "").strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            await message.answer("Не удалось распарсить дату. Используй формат YYYY-MM-DD HH:MM или 'нет'.")
            return
    await state.update_data(deadline=deadline.isoformat() if deadline else None)
    await state.set_state(MissionCreationStates.verify_mode)
    await message.answer(
        "Тип проверки (auto_hashtag / auto_repost / manual):"
    )


@router.message(MissionCreationStates.verify_mode)
async def mission_verify_mode(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    text = (message.text or "").strip().lower()
    try:
        mode = MissionVerifyMode(text)
    except ValueError:
        await message.answer("Неизвестный режим. Введи: auto_hashtag, auto_repost или manual")
        return
    await state.update_data(verify_mode=mode.value)
    await state.set_state(MissionCreationStates.extra)
    await message.answer("Доп. параметры в JSON или 'нет':")


@router.message(MissionCreationStates.extra)
async def mission_extra(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    text = (message.text or "").strip()
    if text.lower() in {"нет", "no", "none", "-"}:
        extra = None
    else:
        try:
            extra = json.loads(text)
        except json.JSONDecodeError:
            await message.answer("Некорректный JSON. Попробуй снова или введи 'нет'.")
            return
    await state.update_data(extra=extra)
    await state.set_state(MissionCreationStates.confirm)
    data = await state.get_data()
    preview = (
        f"Название: {data['title']}\n"
        f"Slug: {data['slug']}\n"
        f"Награда: {data['reward']} хвостов\n"
        f"Дедлайн: {data['deadline'] or 'нет'}\n"
        f"Проверка: {data['verify_mode']}\n"
        f"Extra: {extra}"
    )
    await message.answer(preview + "\n\nНапиши 'публикуй' чтобы активировать или 'черновик' для черновика.")


@router.message(MissionCreationStates.confirm)
async def mission_confirm(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    text = (message.text or "").strip().lower()
    if text not in {"публикуй", "черновик"}:
        await message.answer("Ответь 'публикуй' или 'черновик'.")
        return
    data = await state.get_data()
    await state.clear()
    activate = text == "публикуй"
    deadline = datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None
    async with session_manager() as session:
        mission = await missions_service.create_mission(
            session,
            title=data["title"],
            slug=data["slug"],
            description=data["description"],
            reward_tails=data["reward"],
            deadline=deadline,
            verify_mode=MissionVerifyMode(data["verify_mode"]),
            extra=data.get("extra"),
            activate=activate,
        )
    await message.answer(
        "Миссия создана!\n\n" + format_mission_card(mission),
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(Command("give"))
async def cmd_give(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /give @user <amount>")
        return
    username, amount_str = parts[1], parts[2]
    try:
        amount = int(amount_str)
    except ValueError:
        await message.answer("Количество должно быть числом")
        return
    async with session_manager() as session:
        user = await get_user_by_username(session, username)
        if not user:
            await message.answer("Пользователь не найден")
            return
        await award_tails(session, user, amount, "manual_grant")
        display = f"@{user.username}" if user.username else str(user.tg_id)
    await message.answer(f"Выдано {amount} хвостов для {display}")


@router.message(Command("setrank"))
async def cmd_setrank(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /setrank @user <rank>")
        return
    username, rank_name = parts[1], parts[2]
    async with session_manager() as session:
        user = await get_user_by_username(session, username)
        if not user:
            await message.answer("Пользователь не найден")
            return
        user.rank = rank_name
        display = f"@{user.username}" if user.username else str(user.tg_id)
    await message.answer(f"Ранг пользователя {display} обновлён на {rank_name}")


@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Укажи тип экспорта: users | missions | referrals")
        return
    export_type = parts[1].strip().lower()
    async with session_manager() as session:
        if export_type == "users":
            data = await export_users(session)
        elif export_type == "missions":
            data = await missions_service.export_missions(session)
        elif export_type == "referrals":
            data = await export_referrals(session)
        else:
            await message.answer("Неизвестный тип экспорта")
            return
    buffer = io.StringIO()
    if data:
        writer = csv.DictWriter(buffer, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
    else:
        buffer.write("empty")
    payload = buffer.getvalue().encode("utf-8")
    filename = f"export_{export_type}.csv"
    await message.answer_document(
        BufferedInputFile(payload, filename=filename),
        caption="Экспорт готов",
    )
