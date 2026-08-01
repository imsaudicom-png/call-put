"""
طبقة جلب بيانات الشموع (OHLCV) من Twelve Data — مزوّد واحد يدعم الأسهم والفوركس والعملات الرقمية
بنفس نقطة الاتصال، وهذا يبسّط الـ backend كثيرًا مقارنة باستخدام مزوّد منفصل لكل فئة أصول.

سجّل مفتاحًا مجانيًا من: https://twelvedata.com/
ثم ضعه في متغير البيئة TWELVE_DATA_API_KEY
"""
import time
import threading
import httpx
import pandas as pd
from fastapi import HTTPException

from .config import settings

BASE_URL = "https://api.twelvedata.com"

# ── تخزين مؤقت في الذاكرة لكل (رمز, فريم) ────────────────────────────────
# يمنع إعادة طلب نفس البيانات من Twelve Data خلال مدة صلاحية الفريم نفسه
# (مثلاً فريم 5m لا تتغير شمعته الأخيرة إلا كل 90 ثانية تقريبًا، فلا داعي لطلب جديد قبلها)
_ohlcv_cache: dict[tuple[str, str], tuple[float, "pd.DataFrame"]] = {}
_cache_lock = threading.Lock()


def _cache_ttl(timeframe: str) -> int:
    return settings.CACHE_TTL_SECONDS.get(timeframe, 60)


# ── محدّد معدّل الطلبات (Rate Limiter) على مستوى السيرفر بالكامل ─────────
# خطة Twelve Data المجانية تسمح بـ 8 credits/دقيقة فقط. المهم: طلب واحد فيه عدة
# رموز (batch) يستهلك credit مستقل لكل رمز — طلب فيه 7 رموز = 7 credits دفعة وحدة،
# مو 1! فلازم نحسب "وزن" كل طلب (عدد الرموز فيه) مو بس عدد الطلبات.
_MAX_CREDITS_PER_MINUTE = 7  # نترك هامش 1 credit احتياطي عن الحد الرسمي (8)
_call_log: list[tuple[float, int]] = []  # (وقت الطلب, عدد الـ credits المستهلكة)
_rate_lock = threading.Lock()


def _wait_for_rate_limit_slot(weight: int = 1):
    while True:
        with _rate_lock:
            now = time.monotonic()
            while _call_log and now - _call_log[0][0] >= 60:
                _call_log.pop(0)
            used = sum(w for _, w in _call_log)
            if used + weight <= _MAX_CREDITS_PER_MINUTE:
                _call_log.append((now, weight))
                return
            sleep_for = 60 - (now - _call_log[0][0]) + 0.1
        time.sleep(max(sleep_for, 0.1))

# تحويل رموز الفريمات المستخدمة في الموقع إلى الصيغة التي يفهمها Twelve Data
# (بعض الفريمات مثل 3m و75m غير مدعومة مباشرة، فنجلب فريمًا أصغر ونعيد تجميعه Resample)
TF_MAP = {
    "1m": ("1min", None),
    "3m": ("1min", "3min"),
    "5m": ("5min", None),
    "15m": ("15min", None),
    "30m": ("30min", None),
    "45m": ("45min", None),
    "1h": ("1h", None),
    "75m": ("15min", "75min"),
    "2h": ("2h", None),
    "4h": ("4h", None),
    "1D": ("1day", None),
}


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = df.resample(rule, label="right", closed="right").agg(agg).dropna()
    return out


def fetch_ohlcv(symbol: str, timeframe: str, outputsize: int = None) -> pd.DataFrame:
    """
    يُرجع DataFrame مفهرس بالوقت (UTC)، أعمدة: open, high, low, close, volume — مرتب تصاعديًا.
    """
    if timeframe not in TF_MAP:
        raise HTTPException(400, f"فريم زمني غير مدعوم: {timeframe}")

    if not settings.TWELVE_DATA_API_KEY:
        raise HTTPException(
            500,
            "مفتاح Twelve Data غير مُهيأ على السيرفر. أضف TWELVE_DATA_API_KEY في متغيرات البيئة.",
        )

    cache_key = (symbol, timeframe)
    ttl = _cache_ttl(timeframe)
    now = time.monotonic()
    with _cache_lock:
        cached = _ohlcv_cache.get(cache_key)
        if cached and (now - cached[0] < ttl):
            return cached[1].tail(outputsize or settings.DEFAULT_CANDLE_COUNT)

    interval, resample_rule = TF_MAP[timeframe]
    size = outputsize or settings.DEFAULT_CANDLE_COUNT
    # عند الحاجة لإعادة تجميع (resample) نطلب بيانات أكثر من الفريم الأصغر لتغطية نفس المدى الزمني
    fetch_size = size * 4 if resample_rule else size

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": min(fetch_size, 5000),
        "apikey": settings.TWELVE_DATA_API_KEY,
        "format": "JSON",
        "order": "ASC",
    }

    # ننتظر دورنا ضمن حد 8 طلبات/دقيقة بدل ما نضرب الـ API ونرجع خطأ للمستخدم
    _wait_for_rate_limit_slot()

    try:
        resp = httpx.get(f"{BASE_URL}/time_series", params=params, timeout=15)
        data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"فشل الاتصال بمزوّد البيانات: {e}")

    if data.get("status") == "error" or "values" not in data:
        raise HTTPException(404, f"تعذر جلب بيانات الرمز '{symbol}': {data.get('message', 'رمز غير معروف')}")

    rows = data["values"]
    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df["volume"] = df.get("volume", pd.Series(0, index=df.index)).astype(float)

    if resample_rule:
        df = _resample(df, resample_rule)

    with _cache_lock:
        _ohlcv_cache[cache_key] = (now, df)

    return df.tail(size)


def fetch_batch_quotes(symbols: list[str]) -> dict[str, dict]:
    """
    يجلب السعر الحالي ونسبة التغير لعدة رموز. Twelve Data يحسب credit مستقل لكل
    رمز حتى لو كانوا بنفس الطلب، فنقسمهم لمجموعات صغيرة (7 كحد أقصى) ونستخدم
    نفس محدّد المعدّل المستخدم في fetch_ohlcv لضمان عدم تجاوز حد الخطة المجانية.
    يُرجع dict: {symbol: {"price": float, "percent_change": float}} — الرموز الفاشلة تُستبعد بصمت.
    """
    if not settings.TWELVE_DATA_API_KEY or not symbols:
        return {}

    result: dict[str, dict] = {}
    chunk_size = 7  # يطابق _MAX_CREDITS_PER_MINUTE عشان مجموعة وحدة ما تتجاوز الحد لحالها
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i + chunk_size]
        params = {
            "symbol": ",".join(chunk),
            "apikey": settings.TWELVE_DATA_API_KEY,
        }
        _wait_for_rate_limit_slot(weight=len(chunk))
        try:
            resp = httpx.get(f"{BASE_URL}/quote", params=params, timeout=20)
            data = resp.json()
        except httpx.HTTPError:
            continue

        # عند رمز واحد Twelve Data يُرجع كائن مباشرة، وعند عدة رموز يُرجع dict برموز كمفاتيح.
        # لو تجاوزنا الحد رغم كل شي، Twelve Data يرجع كائن خطأ وحيد (status/code/message)
        # بدل dict برموز — نتحقق من هذا صراحة عشان ما نفسره غلط كأنه "رموز فاشلة".
        if isinstance(data, dict) and data.get("status") == "error":
            continue
        if len(chunk) == 1:
            data = {chunk[0]: data}

        for sym, entry in data.items():
            if not isinstance(entry, dict) or entry.get("status") == "error":
                continue
            try:
                price = float(entry.get("close")) if entry.get("close") is not None else None
                pct = float(entry.get("percent_change")) if entry.get("percent_change") is not None else None
            except (TypeError, ValueError):
                price, pct = None, None
            result[sym] = {"price": price, "percent_change": pct}

    return result


def search_symbols(query: str) -> list[dict]:
    if not settings.TWELVE_DATA_API_KEY:
        raise HTTPException(500, "مفتاح Twelve Data غير مُهيأ على السيرفر.")
    try:
        resp = httpx.get(
            f"{BASE_URL}/symbol_search",
            params={"symbol": query, "apikey": settings.TWELVE_DATA_API_KEY},
            timeout=10,
        )
        data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"فشل الاتصال بمزوّد البيانات: {e}")

    results = data.get("data", [])[:10]
    return [
        {
            "symbol": r.get("symbol"),
            "name": r.get("instrument_name"),
            "exchange": r.get("exchange"),
            "type": r.get("instrument_type"),
        }
        for r in results
    ]
