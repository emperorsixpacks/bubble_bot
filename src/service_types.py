from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Error(Exception):
    message: str
    field: str | None

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


type error = Error | None


class Base(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)


class IdentifiedSupply(Base):
    percent_in_cexs: float
    percent_in_contracts: float


class TokenMetrics(Base):
    decentralisation_score: float
    dt_update: datetime
    identified_supply: IdentifiedSupply
    status: str

    @field_serializer("dt_update")
    def serialize_dt(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%d %H:%M:%S")


class TokenCommunityData(Base):
    home_page_url: Optional[str] = Field(default=None)
    white_paper: Optional[str] = Field(default=None)
    token_image_url: str
    twitter_handle: Optional[str] = Field(default=None)
    twitter_followers: Optional[int] = Field(default=None)
    telegram_channel: Optional[str] = Field(default=None)
    repo: Optional[str] = Field(default=None)


class TokenCoinData(Base):
    symbol: str
    name: str
    description: str
    bubble_screenshot_url: Optional[str] = None
    market_cap: int
    volume: int
    price: float
    circulating_supply: int | float
    total_supply: int | float
    community_data: TokenCommunityData

    @field_serializer("price")
    def format_price(self, value: float, _info):
        if abs(value) < 0.0001:  # For very small values
            return f"{value:.8f}"  # Shows 8 decimal places
        if abs(value) < 1:
            return f"{value:.6f}"  # Shows 6 decimal places for small values
        return f"${value:,.2f}"  # Normal formatting with 2 decimals

    @field_serializer("market_cap", "volume")
    def format_large_numbers(self, value: int, _info):
        return f"{value:,}"  # Adds commas to large numbers
