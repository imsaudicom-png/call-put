"""
نقطة الدخول الرئيسية للـ Backend.
تشغيل محلي: uvicorn app.main:app --reload --port 8000
"""
import time
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import data_provider as dp
from . import indicators as ind
from .schemas import (
    AnalysisResult, Candle, LinePoint, PivotPoint, HiddenSignal,
    MTFRadarResult, MTFRadarEntry, WatchlistResult, WatchlistEntry,
)

# قائمة المتابعة الافتراضية (بعد حذف التكرار من قائمة المستخدم)
DEFAULT_WATCHLIST = [
    "TSLA", "UNH", "CAT", "NVDA", "AVGO", "META", "MU", "SPY", "QQQ", "ZM",
    "UPST", "XOM", "UBRE", "SMCO", "SNOW", "SBUX", "PLTR", "PDD", "ORCL", "NFLX",
    "FDX", "MDTR", "MSFT", "MRNA", "MDB", "MCD", "MA", "LULU", "LLY", "LMT",
    "IBM", "HD", "GS", "GME", "GE", "FSLR", "DIS", "DIA", "DELL", "DAL",
    "CVS", "CRWD", "CRM", "ARM", "COST", "COIN", "BA", "AXP", "ASML", "APP",
    "ANET", "AMZN", "GOOG", "AMD", "AMAT", "ADBE", "AAPL", "CVNA", "MRK", "CVX", "PEP",
]

# تخزين مؤقت بسيط في الذاكرة لتفادي استهلاك الحصة اليومية من الـ API عند كل تحديث للصفحة
_watchlist_cache: dict = {"data": None, "ts": 0}
WATCHLIST_CACHE_TTL = 60  # ثانية

app = FastAPI(title="بوصلة السوق API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

STRUCTURE_LENGTH = 8
RSI_LEN = 14
ATR_LEN = 14
ATR_MULT = 2.0
LB_LEFT, LB_RIGHT = 5, 5
RANGE_LOWER, RANGE_UPPER = 5, 60

MTF_LIST = ["3m", "5m", "15m"]


def _build_analysis(symbol: str, timeframe: str) -> AnalysisResult:
    df = dp.fetch_ohlcv(symbol, timeframe)
    if len(df) < (STRUCTURE_LENGTH * 2 + 5):
        raise HTTPException(422, "بيانات غير كافية لهذا الرمز/الفريم لإجراء تحليل موثوق.")

    rsi = ind.wilder_rsi(df["close"], RSI_LEN)
    atr = ind.wilder_atr(df["high"], df["low"], df["close"], ATR_LEN)
    ema50 = ind.ema(df["close"], 50)
    ema200 = ind.ema(df["close"], 200)
    vol_ma = ind.sma(df["volume"], 20)
    is_vol_ok = df["volume"] > (vol_ma * 0.8)

    structure = ind.compute_structure(df, STRUCTURE_LENGTH)
    targets = ind.compute_targets(df, structure, rsi, ema50, is_vol_ok)
    hidden_signal = ind.compute_hidden_signal(
        df, rsi, atr, LB_LEFT, LB_RIGHT, RANGE_LOWER, RANGE_UPPER, ATR_MULT
    )

    close_now = float(df["close"].iloc[-1])
    ema50_now = float(ema50.iloc[-1])
    ema200_now = float(ema200.iloc[-1])
    rsi_now = float(rsi.iloc[-1])
    vol_ok_now = bool(is_vol_ok.iloc[-1])

    confidence, reasoning, strength = ind.compute_confidence_and_reasoning(
        structure, rsi_now, vol_ok_now, close_now, ema50_now, ema200_now, hidden_signal
    )

    trend = "BULLISH" if structure["state"] == 1 else "BEARISH" if structure["state"] == -1 else "NEUTRAL"
    midpoint = None
    if structure["upper"] is not None and structure["lower"] is not None:
        midpoint = round((structure["upper"] + structure["lower"]) / 2, 4)

    def _line_points(line: dict | None) -> list[LinePoint]:
        if line is None:
            return []
        return [
            LinePoint(time=int(line["x1"].timestamp()), value=line["y1"]),
            LinePoint(time=int(line["x2"].timestamp()), value=line["y2"]),
        ]

    return AnalysisResult(
        symbol=symbol,
        timeframe=timeframe,
        generatedAt=int(time.time()),
        candles=[
            Candle(time=int(idx.timestamp()), open=r["open"], high=r["high"],
                   low=r["low"], close=r["close"], volume=r["volume"])
            for idx, r in df.iterrows()
        ],
        ema50=[LinePoint(time=int(idx.timestamp()), value=float(v)) for idx, v in ema50.dropna().items()],
        ema200=[LinePoint(time=int(idx.timestamp()), value=float(v)) for idx, v in ema200.dropna().items()],
        trend=trend,
        trendStrength=strength,
        structureState=structure["state"],
        resistanceLine=_line_points(structure["resistance_line"]),
        supportLine=_line_points(structure["support_line"]),
        support=round(structure["lower"], 4) if structure["lower"] else None,
        resistance=round(structure["upper"], 4) if structure["upper"] else None,
        midpoint=midpoint,
        lastPivotHigh=PivotPoint(
            price=structure["last_pivot_high"]["price"],
            time=int(structure["last_pivot_high"]["time"].timestamp()),
        ) if structure["last_pivot_high"] else None,
        lastPivotLow=PivotPoint(
            price=structure["last_pivot_low"]["price"],
            time=int(structure["last_pivot_low"]["time"].timestamp()),
        ) if structure["last_pivot_low"] else None,
        bullishTargets=targets["bullish"],
        bearishTargets=targets["bearish"],
        hiddenSignal=HiddenSignal(**hidden_signal) if hidden_signal else None,
        confidenceScore=confidence,
        reasoning=reasoning,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "time": int(time.time())}


@app.get("/api/analyze", response_model=AnalysisResult)
def analyze(
    symbol: str = Query(..., description="مثال: AAPL, TSLA, NVDA, BTC/USD, EUR/USD"),
    timeframe: str = Query("5m", description="أحد: 1m,3m,5m,15m,30m,45m,1h,75m,2h,4h,1D"),
):
    return _build_analysis(symbol.strip().upper(), timeframe)


@app.get("/api/mtf-radar", response_model=MTFRadarResult)
def mtf_radar(symbol: str = Query(...)):
    """رادار الفريمات المتعددة — نفس محرك الهيكل مطبّقًا على 11 فريمًا زمنيًا."""
    entries = []
    labels = {1: "اختراق 🔥", -1: "كسر 🚨", 0: "داخل ⏳"}
    for tf in MTF_LIST:
        try:
            df = dp.fetch_ohlcv(symbol.strip().upper(), tf)
            structure = ind.compute_structure(df, STRUCTURE_LENGTH)
            state = structure["state"]
        except Exception:
            state = 0
        entries.append(MTFRadarEntry(timeframe=tf, state=state, label=labels[state]))
    return MTFRadarResult(symbol=symbol, generatedAt=int(time.time()), entries=entries)


@app.get("/api/watchlist", response_model=WatchlistResult)
def watchlist(symbols: str = Query(None, description="رموز مفصولة بفواصل؛ إن ترك فارغًا تُستخدم القائمة الافتراضية")):
    now = int(time.time())
    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else DEFAULT_WATCHLIST

    # استخدام التخزين المؤقت فقط عند طلب القائمة الافتراضية (الأكثر شيوعًا)
    use_cache = symbols is None
    if use_cache and _watchlist_cache["data"] is not None and (now - _watchlist_cache["ts"] < WATCHLIST_CACHE_TTL):
        return _watchlist_cache["data"]

    quotes = dp.fetch_batch_quotes(symbol_list)
    entries = []
    for sym in symbol_list:
        q = quotes.get(sym)
        if q is None:
            entries.append(WatchlistEntry(symbol=sym, price=None, percentChange=None, trend="UNKNOWN"))
            continue
        pct = q.get("percent_change")
        if pct is None:
            trend = "UNKNOWN"
        elif pct > 0.05:
            trend = "UP"
        elif pct < -0.05:
            trend = "DOWN"
        else:
            trend = "FLAT"
        entries.append(WatchlistEntry(symbol=sym, price=q.get("price"), percentChange=pct, trend=trend))

    result = WatchlistResult(generatedAt=now, entries=entries)
    if use_cache:
        _watchlist_cache["data"] = result
        _watchlist_cache["ts"] = now
    return result


@app.get("/api/search")
def search(query: str = Query(..., min_length=1)):
    return dp.search_symbols(query.strip())
