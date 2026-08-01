"""
محرك التحليل — ترجمة حرفية لمنطق مؤشر "بوصلة المثلث الذهبية" من Pine Script.
كل دالة هنا تقابل قسمًا محددًا من التوثيق الفني (الأقسام 1.1 حتى 1.8).

المرجع: مؤشر_المثلثات_20026.txt
"""
from __future__ import annotations
import numpy as np
import pandas as pd


# ==================== 1.1 المؤشرات الفنية الأساسية (Wilder smoothing) ====================

def wilder_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """RSI بصيغة Wilder الأصلية — تطابق ta.rsi() في Pine Script (وليس RSI بـ EMA بسيطة)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def wilder_atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """ATR بصيغة Wilder — تطابق ta.atr() في Pine Script."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length).mean()


# ==================== 1.2 كاشف القمة/القاع (Pivot) ====================

def pivot_high(series: pd.Series, left: int, right: int) -> pd.Series:
    """
    يطابق ta.pivothigh(source, left, right):
    القيمة عند الموقع (i - right) تُعتبر قمة إن كانت الأعلى ضمن نافذة [i-left-right, i].
    النتيجة NaN في كل مكان إلا عند الشمعة التي تحققت فيها القمة (مع تأخر متعمد = right شمعة).
    """
    n = len(series)
    result = pd.Series(np.nan, index=series.index)
    values = series.values
    for i in range(left + right, n):
        window = values[i - left - right: i + 1]
        center_idx = i - right
        center_val = values[center_idx]
        if center_val == np.nanmax(window) and not np.isnan(center_val):
            result.iloc[center_idx] = center_val
    return result


def pivot_low(series: pd.Series, left: int, right: int) -> pd.Series:
    n = len(series)
    result = pd.Series(np.nan, index=series.index)
    values = series.values
    for i in range(left + right, n):
        window = values[i - left - right: i + 1]
        center_idx = i - right
        center_val = values[center_idx]
        if center_val == np.nanmin(window) and not np.isnan(center_val):
            result.iloc[center_idx] = center_val
    return result


# ==================== 1.4 محرك الهيكل / المثلث الرئيسي ====================

def compute_structure(df: pd.DataFrame, length: int = 8) -> dict:
    """
    يطابق f_draw_main_triangle() + current_structure_state في الكود الأصلي.
    df يجب أن يحتوي على أعمدة: high, low, close (مرتبة زمنيًا تصاعديًا).
    يُرجع حالة الهيكل عند آخر شمعة (index = -1).
    """
    ph = pivot_high(df["high"], length, length)
    pl = pivot_low(df["low"], length, length)

    ph_idx = ph.dropna().index.tolist()
    pl_idx = pl.dropna().index.tolist()

    if len(ph_idx) < 2 or len(pl_idx) < 2:
        return {
            "state": 0, "upper": None, "lower": None, "height": None,
            "resistance_line": None, "support_line": None,
            "last_pivot_high": None, "last_pivot_low": None,
        }

    ph1_x, ph2_x = ph_idx[-1], ph_idx[-2]
    pl1_x, pl2_x = pl_idx[-1], pl_idx[-2]
    ph1, ph2 = ph.loc[ph1_x], ph.loc[ph2_x]
    pl1, pl2 = pl.loc[pl1_x], pl.loc[pl2_x]

    ph1_pos, ph2_pos = df.index.get_loc(ph1_x), df.index.get_loc(ph2_x)
    pl1_pos, pl2_pos = df.index.get_loc(pl1_x), df.index.get_loc(pl2_x)
    current_pos = len(df) - 1

    m1 = (ph1 - ph2) / max(1, ph1_pos - ph2_pos)   # ميل خط المقاومة
    m2 = (pl1 - pl2) / max(1, pl1_pos - pl2_pos)   # ميل خط الدعم

    upper_now = m1 * (current_pos - ph1_pos) + ph1
    lower_now = m2 * (current_pos - pl1_pos) + pl1
    height = abs(ph1 - pl1)

    close_now = df["close"].iloc[-1]
    if close_now > upper_now:
        state = 1
    elif close_now < lower_now:
        state = -1
    else:
        state = 0

    return {
        "state": state,
        "upper": float(upper_now),
        "lower": float(lower_now),
        "height": float(height),
        "resistance_line": {"x1": ph2_x, "y1": float(ph2), "x2": df.index[-1], "y2": float(upper_now)},
        "support_line": {"x1": pl2_x, "y1": float(pl2), "x2": df.index[-1], "y2": float(lower_now)},
        "last_pivot_high": {"price": float(ph1), "time": ph1_x},
        "last_pivot_low": {"price": float(pl1), "time": pl1_x},
    }


# ==================== 1.5 محرك الأهداف الذكية (Measured Move) ====================

def compute_targets(df: pd.DataFrame, structure: dict, rsi: pd.Series, ema50: pd.Series, is_vol_ok: pd.Series) -> dict:
    """
    يطابق منطق target1/target2 في الكود الأصلي (الشروط: اختراق + RSI + سيولة + EMA50).
    يُحسب فقط عند آخر شمعة (الحالة اللحظية المطلوبة للـ API)، وليس تتبعًا تاريخيًا كاملاً،
    لأن هدف الـ API هو "ما هي الأهداف الفعالة الآن" فقط.
    """
    if structure["state"] == 0 or structure["height"] is None:
        return {"bullish": None, "bearish": None}

    close_now = df["close"].iloc[-1]
    rsi_now = rsi.iloc[-1]
    ema50_now = ema50.iloc[-1]
    vol_ok_now = bool(is_vol_ok.iloc[-1])

    bullish, bearish = None, None

    real_breakout = close_now > structure["upper"]
    real_breakdown = close_now < structure["lower"]

    if real_breakout and rsi_now > 45 and vol_ok_now and close_now > ema50_now:
        bullish = [
            round(close_now + structure["height"] * 0.5, 4),
            round(close_now + structure["height"] * 1.0, 4),
        ]

    if real_breakdown and rsi_now < 55 and vol_ok_now and close_now < ema50_now:
        bearish = [
            round(close_now - structure["height"] * 0.5, 4),
            round(close_now - structure["height"] * 1.0, 4),
        ]

    return {"bullish": bullish, "bearish": bearish}


# ==================== 1.3 محرك تأكيد الزخم عند نقطة الارتكاز (المسمى "ديفرجنس" في الأصل) ====================

def compute_hidden_signal(
    df: pd.DataFrame, rsi: pd.Series, atr: pd.Series,
    lb_left: int = 5, lb_right: int = 5,
    range_lower: int = 5, range_upper: int = 60,
    atr_mult: float = 2.0,
) -> dict | None:
    """
    يطابق hiddenBullCond / hiddenBearCond في الكود الأصلي.
    ⚠️ تنويه: الشرط الفعلي هو تزامن اتجاه RSI مع السعر (وليس تباينًا كلاسيكيًا) — انظر التوثيق الفني قسم 1.3.
    يُرجع آخر إشارة فقط (الأحدث زمنيًا بين النوعين).
    """
    ph = pivot_high(df["high"], lb_left, lb_right)
    pl = pivot_low(df["low"], lb_left, lb_right)

    pl_positions = [df.index.get_loc(t) for t in pl.dropna().index]
    ph_positions = [df.index.get_loc(t) for t in ph.dropna().index]

    last_signal = None

    # فحص القيعان (احتمال إشارة صاعدة)
    for k in range(1, len(pl_positions)):
        i_pos, j_pos = pl_positions[k], pl_positions[k - 1]
        bars_between = i_pos - j_pos
        if not (range_lower <= bars_between <= range_upper):
            continue
        price_i, price_j = df["low"].iloc[i_pos], df["low"].iloc[j_pos]
        rsi_i, rsi_j = rsi.iloc[i_pos], rsi.iloc[j_pos]
        if price_i > price_j and rsi_i > rsi_j:  # قاع أعلى في السعر و RSI معًا
            entry = df["close"].iloc[i_pos]
            atr_at_signal = atr.iloc[i_pos]
            target = entry + atr_at_signal * atr_mult
            stop = entry - atr_at_signal * atr_mult
            candidate = {
                "type": "HIDDEN_BULL", "price": float(price_i),
                "time": int(df.index[i_pos].timestamp()), "target": float(target),
                "stop": float(stop), "midPrice": float((target + stop) / 2),
            }
            if last_signal is None or candidate["time"] >= last_signal["time"]:
                last_signal = candidate

    # فحص القمم (احتمال إشارة هابطة)
    for k in range(1, len(ph_positions)):
        i_pos, j_pos = ph_positions[k], ph_positions[k - 1]
        bars_between = i_pos - j_pos
        if not (range_lower <= bars_between <= range_upper):
            continue
        price_i, price_j = df["high"].iloc[i_pos], df["high"].iloc[j_pos]
        rsi_i, rsi_j = rsi.iloc[i_pos], rsi.iloc[j_pos]
        if price_i < price_j and rsi_i < rsi_j:  # قمة أدنى في السعر و RSI معًا
            entry = df["close"].iloc[i_pos]
            atr_at_signal = atr.iloc[i_pos]
            target = entry - atr_at_signal * atr_mult
            stop = entry + atr_at_signal * atr_mult
            candidate = {
                "type": "HIDDEN_BEAR", "price": float(price_i),
                "time": int(df.index[i_pos].timestamp()), "target": float(target),
                "stop": float(stop), "midPrice": float((target + stop) / 2),
            }
            if last_signal is None or candidate["time"] >= last_signal["time"]:
                last_signal = candidate

    return last_signal


# ==================== 1.8 توليد سبب التحليل + درجة الثقة (تحسين مضاف) ====================

def compute_confidence_and_reasoning(
    structure: dict, rsi_now: float, vol_ok_now: bool,
    close_now: float, ema50_now: float, ema200_now: float,
    hidden_signal: dict | None,
) -> tuple[int, list[str], str]:
    reasoning: list[str] = []
    score = 50  # نقطة بداية محايدة

    if structure["state"] == 1:
        reasoning.append(
            f"السعر أغلق فوق خط المقاومة الديناميكي المرسوم من آخر قمتين، عند مستوى {structure['upper']:.4f}، "
            "مما يعني اختراقًا فعليًا لهيكل المثلث الحالي."
        )
        score += 15
    elif structure["state"] == -1:
        reasoning.append(
            f"السعر أغلق تحت خط الدعم الديناميكي المرسوم من آخر قاعين، عند مستوى {structure['lower']:.4f}، "
            "مما يعني كسرًا فعليًا لهيكل المثلث الحالي."
        )
        score += 15
    else:
        reasoning.append(
            f"السعر لا يزال داخل حدود المثلث بين الدعم عند {structure['lower']:.4f} "
            f"والمقاومة عند {structure['upper']:.4f}، لا توجد إشارة اتجاه حاسمة بعد."
        )
        score -= 10

    if structure["state"] == 1 and rsi_now > 45:
        reasoning.append(f"مؤشر RSI عند {rsi_now:.1f}، أعلى من عتبة 45 المطلوبة لتأكيد الزخم الصاعد.")
        score += 10
    elif structure["state"] == -1 and rsi_now < 55:
        reasoning.append(f"مؤشر RSI عند {rsi_now:.1f}، أدنى من عتبة 55 المطلوبة لتأكيد الزخم الهابط.")
        score += 10

    if vol_ok_now:
        reasoning.append("حجم التداول الحالي أعلى من 80% من متوسطه لآخر 20 شمعة، أي سيولة كافية لدعم الحركة.")
        score += 10
    else:
        reasoning.append("حجم التداول الحالي ضعيف نسبيًا مقارنة بمتوسطه، ما يقلل من موثوقية استمرار الحركة.")
        score -= 10

    if close_now > ema50_now > ema200_now:
        reasoning.append("السعر فوق EMA50 وEMA50 فوق EMA200 — محاذاة تدعم اتجاهًا صاعدًا قويًا.")
        score += 10
    elif close_now < ema50_now < ema200_now:
        reasoning.append("السعر تحت EMA50 وEMA50 تحت EMA200 — محاذاة تدعم اتجاهًا هابطًا قويًا.")
        score += 10
    else:
        reasoning.append("لا يوجد محاذاة واضحة بين EMA50 وEMA200 حاليًا، الاتجاه العام متذبذب.")
        score -= 5

    if hidden_signal is not None:
        label = "صاعد" if hidden_signal["type"] == "HIDDEN_BULL" else "هابط"
        reasoning.append(
            f"عند آخر نقطة ارتكاز، تحرك RSI والسعر معًا في اتجاه {label}، "
            "وهو ما يعتبره النظام تأكيدًا إضافيًا لاستمرار الحركة."
        )
        score += 5

    score = max(0, min(100, score))

    if score >= 70:
        strength = "STRONG"
    elif score >= 45:
        strength = "MODERATE"
    else:
        strength = "WEAK"

    return score, reasoning, strength
