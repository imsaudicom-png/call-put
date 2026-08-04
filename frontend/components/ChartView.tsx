"use client";
import { useEffect, useRef, useState } from "react";
import {
  createChart, ColorType, IChartApi, LineStyle, UTCTimestamp,
} from "lightweight-charts";
import type { AnalysisResult } from "@/lib/types";

type Badge = { left: number; top: number; text: string; color: string; above: boolean };

export default function ChartView({ result }: { result: AnalysisResult }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [badges, setBadges] = useState<Badge[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: "#0a0d12" }, textColor: "#7d8494" },
      grid: { vertLines: { color: "#151a22" }, horzLines: { color: "#151a22" } },
      width: containerRef.current.clientWidth,
      height: 480,
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#1f2530" },
      rightPriceScale: { borderColor: "#1f2530" },
      crosshair: {
        mode: 1,
        vertLine: { visible: false, labelVisible: false },
        horzLine: { visible: false, labelVisible: false },
      },
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#0a0d12", downColor: "#f23645",
      borderUpColor: "#089981", borderDownColor: "#f23645",
      wickUpColor: "#089981", wickDownColor: "#f23645",
      borderVisible: true,
    });
    candleSeries.setData(
      result.candles.map((c) => ({
        time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close,
      }))
    );

    // 6 متوسطات متحركة (EMA9→EMA380) — بدون عناوين وبدون أرقام على محور السعر،
    // فقط الخطوط الملوّنة نفسها على الشارت (نفس ألوان الأصل على TradingView)
    const emaLines: [keyof AnalysisResult, string][] = [
      ["ema9", "#f23645"], ["ema26", "#089981"], ["ema50", "#e8b84b"],
      ["ema100", "#ff9800"], ["ema200", "#2962ff"], ["ema380", "#ff66cc"],
    ];
    for (const [key, color] of emaLines) {
      const data = result[key] as { time: number; value: number }[];
      if (!data?.length) continue;
      const s = chart.addLineSeries({
        color, lineWidth: 1,
        priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(data.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }

    // خط منطقة المنتصف (أبيض متقطع)
    if (result.midLine.length) {
      const s = chart.addLineSeries({
        color: "rgba(255,255,255,0.6)", lineWidth: 1, lineStyle: LineStyle.Dashed,
        priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(result.midLine.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }

    // خط القمة الممتد (سماوي) وخط القاع الممتد (أحمر فاتح)
    if (result.resistanceLine.length === 2) {
      const s = chart.addLineSeries({
        color: "#00e5ff", lineWidth: 2,
        priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(result.resistanceLine.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }
    if (result.supportLine.length === 2) {
      const s = chart.addLineSeries({
        color: "#ff5252", lineWidth: 2,
        priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(result.supportLine.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }

    const addHLine = (value: number | null | undefined, color: string, title: string, dashed = true) => {
      if (value === null || value === undefined) return;
      candleSeries.createPriceLine({
        price: value, color, lineWidth: 1,
        lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid,
        axisLabelVisible: true, title,
      });
    };
    addHLine(result.resistance, "#00e5ff", "القمة", false);
    addHLine(result.support, "#ff5252", "القاع", false);
    addHLine(result.midpoint, "#ffffff", "المنتصف");

    // ملصقات إشارات التقاطع كصناديق ملوّنة (Badges) فوق الشارت — نحسب مواضعها يدويًا
    // لأن مكتبة الرسم ما تدعم خلفية ملوّنة خلف نص الملصق الافتراضي
    const recomputeBadges = () => {
      const next: Badge[] = [];
      for (const m of result.markers) {
        const x = chart.timeScale().timeToCoordinate(m.time as UTCTimestamp);
        const y = candleSeries.priceToCoordinate(m.price);
        if (x === null || y === null) continue;
        next.push({ left: x, top: y, text: m.text, color: m.color, above: m.above });
      }
      setBadges(next);
    };

    chart.timeScale().subscribeVisibleLogicalRangeChange(recomputeBadges);
    chart.timeScale().fitContent();
    recomputeBadges();

    const onResize = () => {
      chart.applyOptions({ width: containerRef.current?.clientWidth ?? 0 });
      recomputeBadges();
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(recomputeBadges);
      chart.remove();
    };
  }, [result]);

  return (
    <div className="relative rounded-xl overflow-hidden border border-panelBorder">
      <div ref={containerRef} />
      <div className="absolute inset-0 pointer-events-none">
        {badges.map((b, i) => (
          <div
            key={i}
            className="absolute font-bold whitespace-nowrap px-2 py-0.5 rounded text-xs"
            style={{
              left: b.left,
              top: b.above ? b.top - 22 : b.top + 8,
              transform: "translateX(-50%)",
              backgroundColor: b.color,
              color: "#0a0d12",
            }}
          >
            {b.text}
          </div>
        ))}
      </div>
    </div>
  );
}
