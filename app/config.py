from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import AnyUrl, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(..., alias="BOT_TOKEN")
    channel_id: int = Field(..., alias="CHANNEL_ID")
    discussion_id: int = Field(..., alias="DISCUSSION_ID")
    referral_base_url: AnyUrl = Field(..., alias="REF_BASE_URL")
    database_url: str = Field(..., alias="DATABASE_URL")
    admin_ids_raw: str = Field("", alias="ADMIN_IDS")
    verification_hashtag: str | None = Field(None, alias="VERIFICATION_HASHTAG")

    @property
    def admin_ids(self) -> List[int]:
        ids: List[int] = []
        for chunk in self.admin_ids_raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                ids.append(int(chunk))
            except ValueError:
                continue
        return ids


class RankThresholds(BaseModel):
    name: str
    min_tails: int


RANKS: List[RankThresholds] = [
    RankThresholds(name="Хвостик", min_tails=0),
    RankThresholds(name="Носитель", min_tails=5),
    RankThresholds(name="Собиратель", min_tails=15),
    RankThresholds(name="ERR-фермер", min_tails=35),
    RankThresholds(name="Фантом", min_tails=70),
]


@lru_cache
def get_settings() -> Settings:
    return Settings()
