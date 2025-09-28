from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class MissionCreationStates(StatesGroup):
    title = State()
    slug = State()
    description = State()
    reward = State()
    deadline = State()
    verify_mode = State()
    extra = State()
    confirm = State()


class ProofSubmissionState(StatesGroup):
    proof_link = State()
