"""
نماذج البيانات (Schemas) التي يُرجعها الـ API — نفس البنية الموصوفة في التوثيق الفني (قسم 1.7).
"""
from typing import Optional, Literal
from pydantic import BaseModel


class Candle(BaseModel):
    time: int          # unix timestamp بالثواني (يطابق تنسيق TradingView Lightweight Charts)
    open: float
    high: float
    low: float
    close: float
    volume: float


class LinePoint(BaseModel):
    time: int
    value: float


class PivotPoint(BaseModel):
    price: float
    time: int


class HiddenSignal(BaseModel):
    type: Literal["HIDDEN_BULL", "HIDDEN_BEAR"]
    price: float
    time: int
    target: float
    stop: float
    midPrice: float


class AnalysisResult(BaseModel):
    symbol: str
    timeframe: str
    generatedAt: int

    candles: list[Candle]
    ema50: list[LinePoint]
    ema200: list[LinePoint]

    trend: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    trendStrength: Literal["STRONG", "MODERATE", "WEAK"]
    structureState: int  # 1 / 0 / -1

    resistanceLine: list[LinePoint]   # نقطتان لرسم خط المقاومة الممتد
    supportLine: list[LinePoint]      # نقطتان لرسم خط الدعم الممتد

    support: Optional[float]
    resistance: Optional[float]
    midpoint: Optional[float]

    lastPivotHigh: Optional[PivotPoint]
    lastPivotLow: Optional[PivotPoint]

    bullishTargets: Optional[list[float]]   # [target1, target2]
    bearishTargets: Optional[list[float]]

    hiddenSignal: Optional[HiddenSignal]

    signal: Literal["CALL", "PUT", "WAIT"] = "WAIT"
    stopLoss: Optional[float] = None

    spanA: list[LinePoint] = []
    spanB: list[LinePoint] = []
    vwapLine: list[LinePoint] = []
    target1: Optional[float] = None
    target2: Optional[float] = None
    target3: Optional[float] = None

    ema9: list[LinePoint] = []
    ema26: list[LinePoint] = []
    ema100: list[LinePoint] = []
    ema380: list[LinePoint] = []
    midLine: list[LinePoint] = []

    confidenceScore: int  # 0-100
    reasoning: list[str]


class MTFRadarEntry(BaseModel):
    timeframe: str
    state: int          # 1 / 0 / -1
    label: str           # "اختراق 🔥" / "كسر 🚨" / "داخل ⏳"


class MTFRadarResult(BaseModel):
    symbol: str
    generatedAt: int
    entries: list[MTFRadarEntry]


class WatchlistEntry(BaseModel):
    symbol: str
    price: Optional[float]
    percentChange: Optional[float]   # نسبة التغير اليومي من مزوّد البيانات
    trend: Literal["UP", "DOWN", "FLAT", "UNKNOWN"]


class WatchlistResult(BaseModel):
    generatedAt: int
    entries: list[WatchlistEntry]
