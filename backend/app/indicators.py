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


# ==================== محرك جديد: إيشيموكو + VWAP + OBV + دعم/مقاومة (استبدال المثلث الذهبي) ====================
# ترجمة حرفية لمؤشر "بوصلة السوق v2.6 | Ichimoku + S/R Prices" من Pine Script.

def donchian_mid(high: pd.Series, low: pd.Series, length: int) -> pd.Series:
    return (high.rolling(length).max() + low.rolling(length).min()) / 2


def session_vwap(df: pd.DataFrame) -> pd.Series:
    """يطابق ta.vwap(close) — يتصفّر كل يوم تداول (Session) من جديد."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    tpv = typical * df["volume"]
    day_key = pd.Series(df.index.date, index=df.index)
    cum_tpv = tpv.groupby(day_key).cumsum()
    cum_vol = df["volume"].groupby(day_key).cumsum()
    return cum_tpv / cum_vol.replace(0, np.nan)


def obv_series(close: pd.Series, volume: pd.Series) -> pd.Series:
    """يطابق ta.obv."""
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def support_resistance_from_pivots(df: pd.DataFrame, sr_len: int = 50, sr_strength: int = 3) -> tuple[float, float]:
    """يطابق منطق lowBuffer/highBuffer (آخر 5 نقاط ارتكاز) مع fallback لأعلى/أدنى سعر بالنافذة."""
    ph = pivot_high(df["high"], sr_strength, sr_strength).dropna().tolist()[-5:]
    pl = pivot_low(df["low"], sr_strength, sr_strength).dropna().tolist()[-5:]
    sr_highest = float(df["high"].tail(sr_len).max())
    sr_lowest = float(df["low"].tail(sr_len).min())
    nearest_resistance = max(ph) if ph else sr_highest
    nearest_support = min(pl) if pl else sr_lowest
    return float(nearest_support), float(nearest_resistance)


# ==================== محرك جديد: نظام EMA المتعدد + رصد قمم/قيعان (استبدال الإيشيموكو) ====================
# ترجمة حرفية لمؤشر "المطور V02" من Pine Script (بدون جداول الفريمات المتعددة، بدون جداول القراءة).

EMA_PERIODS = (9, 26, 50, 100, 200, 380)


def crossover(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a < b) & (a.shift(1) >= b.shift(1))


def confirm_signal(cross_up: pd.Series, cross_dn: pd.Series, close: pd.Series,
                    high: pd.Series, low: pd.Series, max_bars: int = 10) -> dict:
    """
    ترجمة حرفية لدالة confirmSignal() في Pine — تأكيد الإشارة الخام بشمعتين متتاليتين
    تُغلقان فوق قمة شمعة الإشارة (للشراء) أو تحت قاع شمعة الإشارة (للبيع).
    آلة حالة تسلسلية (var) — يجب تشغيلها بار ببار مثل الأصل تمامًا.
    """
    n = len(close)
    cu, cd = cross_up.values, cross_dn.values
    c, h, l = close.values, high.values, low.values

    await_up = await_dn = False
    c_high = c_low = np.nan
    c_bar = None
    streak = 0

    confirmed_up = np.zeros(n, dtype=bool)
    confirmed_dn = np.zeros(n, dtype=bool)
    awaiting_up = np.zeros(n, dtype=bool)
    awaiting_dn = np.zeros(n, dtype=bool)
    bars_waited = np.zeros(n, dtype=int)

    for i in range(n):
        if cu[i]:
            await_up, await_dn, c_high, c_bar, streak = True, False, h[i], i, 0
        if cd[i]:
            await_dn, await_up, c_low, c_bar, streak = True, False, l[i], i, 0

        if await_up and not cu[i]:
            if c[i] > c_high:
                streak += 1
                if streak >= 2:
                    confirmed_up[i] = True
                    await_up, streak = False, 0
            else:
                streak = 0
            if await_up and c_bar is not None and (i - c_bar) >= max_bars:
                await_up, streak = False, 0

        if await_dn and not cd[i]:
            if c[i] < c_low:
                streak += 1
                if streak >= 2:
                    confirmed_dn[i] = True
                    await_dn, streak = False, 0
            else:
                streak = 0
            if await_dn and c_bar is not None and (i - c_bar) >= max_bars:
                await_dn, streak = False, 0

        awaiting_up[i], awaiting_dn[i] = await_up, await_dn
        bars_waited[i] = 0 if c_bar is None else i - c_bar

    idx = close.index
    return {
        "confirmed_up": pd.Series(confirmed_up, index=idx),
        "confirmed_dn": pd.Series(confirmed_dn, index=idx),
        "awaiting_up": pd.Series(awaiting_up, index=idx),
        "awaiting_dn": pd.Series(awaiting_dn, index=idx),
        "bars_waited": pd.Series(bars_waited, index=idx),
    }


def compute_ema_structure_signal(
    df: pd.DataFrame,
    pivot_left: int = 10, pivot_right: int = 5, max_confirm_bars: int = 10,
) -> dict:
    """
    يطابق منطق "المطور V02": 6 EMA (9/26/50/100/200/380)، قمة/قاع + منطقة منتصف،
    تقاطع سريع (9/26) وتقاطع ذهبي/موت (50/200) — كلاهما بتأكيد شمعتين متتاليتين.
    بدون جداول فريمات متعددة وبدون عرض أرقام المتوسطات كنص (بناءً على طلب العميل).
    """
    close, high, low = df["close"], df["high"], df["low"]
    emas = {p: ema(close, p) for p in EMA_PERIODS}

    ph = pivot_high(high, pivot_left, pivot_right)
    pl = pivot_low(low, pivot_left, pivot_right)
    last_top = ph.ffill()
    last_bot = pl.ffill()
    mid_price = (last_top + last_bot) / 2

    cross_up_fast = crossover(emas[9], emas[26])
    cross_dn_fast = crossunder(emas[9], emas[26])
    cross_up_slow = crossover(emas[50], emas[200])
    cross_dn_slow = crossunder(emas[50], emas[200])

    conf_fast = confirm_signal(cross_up_fast, cross_dn_fast, close, high, low, max_confirm_bars)
    conf_slow = confirm_signal(cross_up_slow, cross_dn_slow, close, high, low, max_confirm_bars)

    close_now = float(close.iloc[-1])
    ema_now = {p: float(emas[p].iloc[-1]) for p in EMA_PERIODS}
    top_now = float(last_top.iloc[-1]) if not pd.isna(last_top.iloc[-1]) else None
    bot_now = float(last_bot.iloc[-1]) if not pd.isna(last_bot.iloc[-1]) else None
    mid_now = float(mid_price.iloc[-1]) if not pd.isna(mid_price.iloc[-1]) else None

    # سلّم الاتجاه (نفس منطق advice/current_floor/next_target في الأصل)
    ladder = sorted(EMA_PERIODS)
    above_count = sum(1 for p in ladder if close_now >= ema_now[p])
    floor_val, target_val = bot_now, ema_now[9]
    for i, p in enumerate(ladder):
        if close_now >= ema_now[p]:
            floor_val = ema_now[p]
            target_val = top_now if p == ladder[-1] else ema_now[ladder[i + 1]]

    trend = "BULLISH" if close_now >= ema_now[26] else "BEARISH"
    strength = "STRONG" if above_count >= 5 or above_count <= 1 else "MODERATE" if above_count >= 4 or above_count <= 2 else "WEAK"
    confidence = round((above_count / 6) * 100) if trend == "BULLISH" else round(((6 - above_count) / 6) * 100)
    confidence = max(0, min(100, confidence))

    # آخر إشارة (الأحدث بين التقاطع السريع والبطيء المؤكدين، بحد أقصى 3 شمعات رجوعًا)
    signal = "WAIT"
    reasoning = []
    look_back = min(3, len(df))
    tail = slice(len(df) - look_back, len(df))
    if conf_slow["confirmed_up"].iloc[tail].any():
        signal = "CALL"
        reasoning.append("تأكد تقاطع ذهبي (EMA50 فوق EMA200) بشمعتين متتاليتين — إشارة صعود قوية.")
    elif conf_slow["confirmed_dn"].iloc[tail].any():
        signal = "PUT"
        reasoning.append("تأكد تقاطع موت (EMA50 تحت EMA200) بشمعتين متتاليتين — إشارة هبوط قوية.")
    elif conf_fast["confirmed_up"].iloc[tail].any():
        signal = "CALL"
        reasoning.append("تأكد تقاطع صعود سريع (EMA9 فوق EMA26) بشمعتين متتاليتين.")
    elif conf_fast["confirmed_dn"].iloc[tail].any():
        signal = "PUT"
        reasoning.append("تأكد تقاطع هبوط سريع (EMA9 تحت EMA26) بشمعتين متتاليتين.")
    elif bool(conf_fast["awaiting_up"].iloc[-1]):
        reasoning.append(f"بانتظار تأكيد إشارة صعود سريع منذ {int(conf_fast['bars_waited'].iloc[-1])} شمعة.")
    elif bool(conf_fast["awaiting_dn"].iloc[-1]):
        reasoning.append(f"بانتظار تأكيد إشارة هبوط سريع منذ {int(conf_fast['bars_waited'].iloc[-1])} شمعة.")
    elif bool(conf_slow["awaiting_up"].iloc[-1]):
        reasoning.append(f"بانتظار تأكيد تقاطع ذهبي منذ {int(conf_slow['bars_waited'].iloc[-1])} شمعة.")
    elif bool(conf_slow["awaiting_dn"].iloc[-1]):
        reasoning.append(f"بانتظار تأكيد تقاطع موت منذ {int(conf_slow['bars_waited'].iloc[-1])} شمعة.")
    else:
        reasoning.append("لا توجد إشارة تقاطع جديدة حاليًا — النظام في وضع المراقبة.")

    reasoning.append(f"السعر أعلى من {above_count} من أصل 6 متوسطات متحركة (EMA9→EMA380).")
    if trend == "BULLISH":
        reasoning.append(f"القرار: صاعد — الإغلاق فوق {floor_val:.4f} يستهدف {target_val:.4f}.")
    else:
        reasoning.append(f"القرار: سلبي — الإغلاق يستهدف {target_val:.4f} كمستوى أدنى.")

    structure_state = 1 if trend == "BULLISH" else -1

    return {
        "trend": trend, "trendStrength": strength, "structureState": structure_state,
        "confidenceScore": confidence, "reasoning": reasoning, "signal": signal,
        "support": bot_now, "resistance": top_now, "midpoint": mid_now,
        "target1": target_val, "target2": (top_now if trend == "BULLISH" else bot_now),
        "lastPivotHigh": {"price": top_now, "time": last_top.dropna().index[-1]} if top_now is not None and len(last_top.dropna()) else None,
        "lastPivotLow": {"price": bot_now, "time": last_bot.dropna().index[-1]} if bot_now is not None and len(last_bot.dropna()) else None,
        "emas": emas, "lastTop": last_top, "lastBot": last_bot, "midLine": mid_price,
    }


def compute_ichimoku_signal(
    df: pd.DataFrame,
    tenkan_len: int = 9, kijun_len: int = 26, senkou_b_len: int = 52, displacement: int = 26,
    sr_len: int = 50, sr_strength: int = 3, range_len: int = 20,
    vol_len: int = 20, obv_len: int = 10, vol_ratio_threshold: float = 1.2,
) -> dict:
    """
    يطابق شروط callSignal/putSignal في المؤشر الجديد:
    priceAboveCloud + cloudBull + tenkanBull + chikouBull + priceAboveVWAP + obvBull + strongVolume + breakout
    (والعكس للـ PUT). يُرجع حالة آخر شمعة فقط.
    """
    tenkan = donchian_mid(df["high"], df["low"], tenkan_len)
    kijun = donchian_mid(df["high"], df["low"], kijun_len)
    span_a = (tenkan + kijun) / 2
    span_b = donchian_mid(df["high"], df["low"], senkou_b_len)

    cloud_top = pd.concat([span_a.shift(displacement), span_b.shift(displacement)], axis=1).max(axis=1)
    cloud_bottom = pd.concat([span_a.shift(displacement), span_b.shift(displacement)], axis=1).min(axis=1)
    price_above_cloud = df["close"] > cloud_top
    price_below_cloud = df["close"] < cloud_bottom
    cloud_bull = span_a > span_b
    cloud_bear = span_a < span_b
    tenkan_bull = tenkan > kijun
    tenkan_bear = tenkan < kijun
    chikou_bull = df["close"] > df["close"].shift(displacement)
    chikou_bear = df["close"] < df["close"].shift(displacement)

    vwap = session_vwap(df)
    price_above_vwap = df["close"] > vwap
    price_below_vwap = df["close"] < vwap

    obv = obv_series(df["close"], df["volume"])
    obv_ma = sma(obv, obv_len)
    obv_bull = (obv > obv_ma) & (obv > obv.shift(1))
    obv_bear = (obv < obv_ma) & (obv < obv.shift(1))

    vol_avg = sma(df["volume"], vol_len)
    vol_ratio = df["volume"] / vol_avg.replace(0, np.nan)
    strong_volume = vol_ratio >= vol_ratio_threshold

    range_high = df["high"].shift(1).rolling(range_len).max()
    range_low = df["low"].shift(1).rolling(range_len).min()
    breakout = df["close"] > range_high
    breakdown = df["close"] < range_low

    def _b(series: pd.Series) -> bool:
        v = series.iloc[-1]
        return bool(v) if not pd.isna(v) else False

    bull_flags = {
        "priceAboveCloud": _b(price_above_cloud), "cloudBull": _b(cloud_bull),
        "tenkanBull": _b(tenkan_bull), "chikouBull": _b(chikou_bull),
        "priceAboveVWAP": _b(price_above_vwap), "obvBull": _b(obv_bull),
        "strongVolume": _b(strong_volume), "breakout": _b(breakout),
    }
    bear_flags = {
        "priceBelowCloud": _b(price_below_cloud), "cloudBear": _b(cloud_bear),
        "tenkanBear": _b(tenkan_bear), "chikouBear": _b(chikou_bear),
        "priceBelowVWAP": _b(price_below_vwap), "obvBear": _b(obv_bear),
        "strongVolume": _b(strong_volume), "breakdown": _b(breakdown),
    }
    bull_score = sum(bull_flags.values())
    bear_score = sum(bear_flags.values())

    call_signal = all(bull_flags.values())
    put_signal = all(bear_flags.values())
    signal = "CALL" if call_signal else ("PUT" if put_signal else "WAIT")

    if bull_score > bear_score and bull_score >= 5:
        trend, structure_state = "BULLISH", 1
    elif bear_score > bull_score and bear_score >= 5:
        trend, structure_state = "BEARISH", -1
    else:
        trend, structure_state = "NEUTRAL", 0

    confidence = max(0, min(100, round(50 + (bull_score - bear_score) * 6)))
    strength = "STRONG" if confidence >= 70 else "MODERATE" if confidence >= 45 else "WEAK"

    labels_ar = {
        "priceAboveCloud": "السعر فوق سحابة الإيشيموكو", "priceBelowCloud": "السعر تحت سحابة الإيشيموكو",
        "cloudBull": "السحابة صاعدة (Span A أعلى من Span B)", "cloudBear": "السحابة هابطة (Span A أدنى من Span B)",
        "tenkanBull": "خط Tenkan أعلى من Kijun", "tenkanBear": "خط Tenkan أدنى من Kijun",
        "chikouBull": "السعر الحالي أعلى من سعر قبل 26 شمعة", "chikouBear": "السعر الحالي أدنى من سعر قبل 26 شمعة",
        "priceAboveVWAP": "السعر فوق VWAP", "priceBelowVWAP": "السعر تحت VWAP",
        "obvBull": "OBV صاعد ومؤكد", "obvBear": "OBV هابط ومؤكد",
        "strongVolume": "حجم التداول قوي (≥1.2x المتوسط)",
        "breakout": "اختراق أعلى نطاق آخر 20 شمعة", "breakdown": "كسر أدنى نطاق آخر 20 شمعة",
    }
    active_flags = bull_flags if bull_score >= bear_score else bear_flags
    reasoning = [labels_ar[k] for k, v in active_flags.items() if v] or ["لا توجد محاذاة واضحة بين الشروط الثمانية حاليًا."]
    reasoning.append(f"عدد الشروط الصاعدة المتحققة: {bull_score}/8 — الهابطة: {bear_score}/8.")

    nearest_support, nearest_resistance = support_resistance_from_pivots(df, sr_len, sr_strength)
    close_now = float(df["close"].iloc[-1])

    target1 = float(tenkan.iloc[-1]) if not pd.isna(tenkan.iloc[-1]) else None
    target2 = float(kijun.iloc[-1]) if not pd.isna(kijun.iloc[-1]) else None
    target3_raw = cloud_top.iloc[-1] if trend == "BULLISH" else cloud_bottom.iloc[-1]
    target3 = float(target3_raw) if not pd.isna(target3_raw) else None

    atr14 = wilder_atr(df["high"], df["low"], df["close"], 14)
    atr_now = float(atr14.iloc[-1]) if not pd.isna(atr14.iloc[-1]) else None
    stop_loss = None
    if atr_now is not None:
        stop_loss = round(close_now - atr_now * 1.5, 4) if trend == "BULLISH" else round(close_now + atr_now * 1.5, 4)

    ph = pivot_high(df["high"], sr_strength, sr_strength).dropna()
    pl = pivot_low(df["low"], sr_strength, sr_strength).dropna()
    last_pivot_high = {"price": float(ph.iloc[-1]), "time": ph.index[-1]} if len(ph) else None
    last_pivot_low = {"price": float(pl.iloc[-1]), "time": pl.index[-1]} if len(pl) else None

    return {
        "trend": trend, "structureState": structure_state, "trendStrength": strength,
        "confidenceScore": confidence, "reasoning": reasoning, "signal": signal,
        "support": round(nearest_support, 4), "resistance": round(nearest_resistance, 4),
        "midpoint": round((nearest_support + nearest_resistance) / 2, 4),
        "tenkan": tenkan, "kijun": kijun, "vwap": vwap,
        "spanA": span_a, "spanB": span_b, "displacement": displacement,
        "target1": target1, "target2": target2, "target3": target3, "stopLoss": stop_loss,
        "lastPivotHigh": last_pivot_high, "lastPivotLow": last_pivot_low,
    }
