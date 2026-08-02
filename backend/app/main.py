"""
نقطة الدخول الرئيسية للـ Backend.
تشغيل محلي: uvicorn app.main:app --reload --port 8000
"""
import time
import threading
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

# قائمة المتابعة الافتراضية — 15 سهم فقط، محسوبة عشان تتوافق مع حد Twelve Data
# المجاني (8 credits/دقيقة). كل رمز إضافي = credit إضافي عند تحديث القائمة.
DEFAULT_WATCHLIST = [
    "SPY", "CVX", "AAPL", "MSFT", "NVDA", "UNH", "META", "AMZN",
    "GOOG", "AVGO", "AMD", "NFLX", "PLTR", "COIN", "DELL",
]

# تخزين مؤقت بسيط في الذاكرة — نرجع آخر بيانات محفوظة فورًا للمستخدم، ونحدّثها
# بالخلفية بخيط منفصل إذا صارت قديمة، بدل ما نخلي المستخدم ينتظر جلبها من جديد
# (جلب 15 رمز يحتاج أكثر من دقيقة بسبب حد الـ API، فما نقدر ننتظرها بشكل متزامن).
_watchlist_cache: dict = {"data": None, "ts": 0, "refreshing": False}
WATCHLIST_CACHE_TTL = 90  # ثانية

app = FastAPI(title="بوصلة السوق API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

TENKAN_LEN = 9
KIJUN_LEN = 26
SENKOU_B_LEN = 52
DISPLACEMENT = 26
SR_LEN = 50
SR_STRENGTH = 3
RANGE_LEN = 20
VOL_LEN = 20
OBV_LEN = 10
VOL_RATIO_THRESHOLD = 1.2

MTF_LIST = ["3m", "5m", "15m"]


def _build_analysis(symbol: str, timeframe: str) -> AnalysisResult:
    df = dp.fetch_ohlcv(symbol, timeframe)
    min_needed = SENKOU_B_LEN + DISPLACEMENT + 5
    if len(df) < min_needed:
        raise HTTPException(422, "بيانات غير كافية لهذا الرمز/الفريم لإجراء تحليل موثوق.")

    sig = ind.compute_ichimoku_signal(
        df,
        tenkan_len=TENKAN_LEN, kijun_len=KIJUN_LEN, senkou_b_len=SENKOU_B_LEN, displacement=DISPLACEMENT,
        sr_len=SR_LEN, sr_strength=SR_STRENGTH, range_len=RANGE_LEN,
        vol_len=VOL_LEN, obv_len=OBV_LEN, vol_ratio_threshold=VOL_RATIO_THRESHOLD,
    )

    def _hline_points(value: float | None) -> list[LinePoint]:
        if value is None or len(df) < 2:
            return []
        return [
            LinePoint(time=int(df.index[0].timestamp()), value=value),
            LinePoint(time=int(df.index[-1].timestamp()), value=value),
        ]

    targets_list = [t for t in [sig["target1"], sig["target2"], sig["target3"]] if t is not None]
    bullish_targets = [round(t, 4) for t in targets_list] if sig["trend"] == "BULLISH" and targets_list else None
    bearish_targets = [round(t, 4) for t in targets_list] if sig["trend"] == "BEARISH" and targets_list else None

    return AnalysisResult(
        symbol=symbol,
        timeframe=timeframe,
        generatedAt=int(time.time()),
        candles=[
            Candle(time=int(idx.timestamp()), open=r["open"], high=r["high"],
                   low=r["low"], close=r["close"], volume=r["volume"])
            for idx, r in df.iterrows()
        ],
        # هذين الحقلين كانا EMA50/200، صاروا يمثلوا Tenkan/Kijun (خطوط الإيشيموكو الأساسية)
        ema50=[LinePoint(time=int(idx.timestamp()), value=float(v)) for idx, v in sig["tenkan"].dropna().items()],
        ema200=[LinePoint(time=int(idx.timestamp()), value=float(v)) for idx, v in sig["kijun"].dropna().items()],
        trend=sig["trend"],
        trendStrength=sig["trendStrength"],
        structureState=sig["structureState"],
        resistanceLine=_hline_points(sig["resistance"]),
        supportLine=_hline_points(sig["support"]),
        support=sig["support"],
        resistance=sig["resistance"],
        midpoint=sig["midpoint"],
        lastPivotHigh=PivotPoint(
            price=sig["lastPivotHigh"]["price"], time=int(sig["lastPivotHigh"]["time"].timestamp()),
        ) if sig["lastPivotHigh"] else None,
        lastPivotLow=PivotPoint(
            price=sig["lastPivotLow"]["price"], time=int(sig["lastPivotLow"]["time"].timestamp()),
        ) if sig["lastPivotLow"] else None,
        bullishTargets=bullish_targets,
        bearishTargets=bearish_targets,
        hiddenSignal=None,
        signal=sig["signal"],
        stopLoss=sig["stopLoss"],
        confidenceScore=sig["confidenceScore"],
        reasoning=sig["reasoning"],
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
    """رادار الفريمات المتعددة — نفس محرك الإيشيموكو الجديد مطبّقًا على 3 فريمات زمنية."""
    entries = []
    labels = {1: "CALL 🟢", -1: "PUT 🔴", 0: "انتظار ⏳"}
    for tf in MTF_LIST:
        try:
            df = dp.fetch_ohlcv(symbol.strip().upper(), tf)
            sig = ind.compute_ichimoku_signal(
                df, tenkan_len=TENKAN_LEN, kijun_len=KIJUN_LEN, senkou_b_len=SENKOU_B_LEN,
                displacement=DISPLACEMENT, sr_len=SR_LEN, sr_strength=SR_STRENGTH,
                range_len=RANGE_LEN, vol_len=VOL_LEN, obv_len=OBV_LEN,
                vol_ratio_threshold=VOL_RATIO_THRESHOLD,
            )
            state = sig["structureState"]
        except Exception:
            state = 0
        entries.append(MTFRadarEntry(timeframe=tf, state=state, label=labels[state]))
    return MTFRadarResult(symbol=symbol, generatedAt=int(time.time()), entries=entries)


def _compute_watchlist(symbol_list: list[str]) -> "WatchlistResult":
    now = int(time.time())
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
    return WatchlistResult(generatedAt=now, entries=entries)


def _refresh_watchlist_cache_background():
    try:
        result = _compute_watchlist(DEFAULT_WATCHLIST)
        _watchlist_cache["data"] = result
        _watchlist_cache["ts"] = int(time.time())
    finally:
        _watchlist_cache["refreshing"] = False


@app.get("/api/watchlist", response_model=WatchlistResult)
def watchlist(symbols: str = Query(None, description="رموز مفصولة بفواصل؛ إن ترك فارغًا تُستخدم القائمة الافتراضية")):
    now = int(time.time())
    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else DEFAULT_WATCHLIST
    use_cache = symbols is None

    if not use_cache:
        # طلب مخصص برموز محددة من المستخدم — نحسبه مباشرة (بدون كاش مشترك)
        return _compute_watchlist(symbol_list)

    stale = _watchlist_cache["data"] is None or (now - _watchlist_cache["ts"] >= WATCHLIST_CACHE_TTL)

    # لو ما فيه أي بيانات سابقة أبدًا (أول تشغيل للسيرفر) — لازم ننتظر أول مرة فقط
    if _watchlist_cache["data"] is None:
        result = _compute_watchlist(symbol_list)
        _watchlist_cache["data"] = result
        _watchlist_cache["ts"] = now
        return result

    # فيه بيانات سابقة (حتى لو قديمة) — نرجعها فورًا، ونحدّثها بالخلفية إذا صارت قديمة
    if stale and not _watchlist_cache["refreshing"]:
        _watchlist_cache["refreshing"] = True
        threading.Thread(target=_refresh_watchlist_cache_background, daemon=True).start()

    return _watchlist_cache["data"]


@app.get("/api/search")
def search(query: str = Query(..., min_length=1)):
    return dp.search_symbols(query.strip())
