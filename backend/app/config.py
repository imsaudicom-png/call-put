"""
إعدادات المشروع — تُقرأ من متغيرات البيئة (Environment Variables).
لا تضع أي مفتاح API مباشرة في الكود.
"""
import os


class Settings:
    # مفتاح Twelve Data المجاني — سجّل واحصل عليه من https://twelvedata.com/
    TWELVE_DATA_API_KEY: str = os.getenv("TWELVE_DATA_API_KEY", "")

    # نطاقات مسموح لها بالاتصال بالـ API (رابط موقع الواجهة الأمامية بعد نشره)
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # مدة صلاحية التخزين المؤقت لكل فريم زمني (ثوانٍ) — تقريبًا = مدة الشمعة نفسها
    CACHE_TTL_SECONDS: dict[str, int] = {
        "1m": 30, "3m": 60, "5m": 90, "15m": 300, "30m": 600,
        "45m": 900, "1h": 1200, "75m": 1500, "2h": 2400,
        "4h": 4800, "1D": 21600,
    }

    # عدد الشموع التي تُجلب افتراضيًا لكل تحليل (كافٍ لحساب EMA200 + Pivot بدقة)
    DEFAULT_CANDLE_COUNT: int = 400


settings = Settings()
