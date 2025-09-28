from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📟 Профиль", callback_data="menu:profile")],
            [InlineKeyboardButton(text="🧭 Миссии", callback_data="menu:missions")],
            [InlineKeyboardButton(text="🏴‍☠️ Ранг", callback_data="menu:rank")],
            [InlineKeyboardButton(text="🌀 Рефералка", callback_data="menu:ref")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="menu:help")],
        ]
    )


def mission_keyboard(mission_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔥 Участвовать", callback_data=f"mission:join:{mission_id}")]]
    )


def mission_participation_keyboard(mission_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить пруф", callback_data=f"mission:proof:{mission_id}")],
        ]
    )


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Новая миссия", callback_data="admin:mission_new")],
            [InlineKeyboardButton(text="📤 Экспорт", callback_data="admin:export")],
        ]
    )
