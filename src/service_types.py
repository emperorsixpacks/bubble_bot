from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


@dataclass
class TokenMetrics:
    decentralisation_score: float
    dt_update: datetime
    identified_supply: dict[str:float]
    status: str


class TokenCommunityData(BaseModel):
    home_page_url: str | None = Field(default=None)
    white_paper: str | None = Field(default=None)
    twitter_handle: str | None = Field(default=None)
    twitter_followers: int | None = Field(default=None)
    telegram_channel: str | None = Field(default=None)
    repo: str | None = Field(default=None)


class TokenCoinData(BaseModel):
    symbol: str
    name: str
    description: str
    bubble_screenshot_url: str | None = None
    token_image_url: str
    market_cap: int
    volume: int
    price: float
    community_data: TokenCommunityData
