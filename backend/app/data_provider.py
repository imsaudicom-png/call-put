"""
طبقة جلب بيانات الشموع (OHLCV) من Twelve Data — مزوّد واحد يدعم الأسهم والفوركس والعملات الرقمية
بنفس نقطة الاتصال، وهذا يبسّط الـ backend كثيرًا مقارنة باستخدام مزوّد منفصل لكل فئة أصول.

سجّل مفتاحًا مجانيًا من: https://twelvedata.com/
ثم ضعه في متغير البيئة TWELVE_DATA_API_KEY
"""
import httpx
import pandas as pd
from fastapi import HTTPException

from .config import settings

BASE_URL = "https://api.twelvedata.com"

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

    return df.tail(size)


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
