import numpy as np
import pandas as pd

from analyzer.basket import fetch_prices


def _monthly_rebalance_positions(index: pd.DatetimeIndex) -> list[int]:
    """Her takvim ayının son işlem gününe denk gelen pozisyonları döner."""
    frame = pd.Series(range(len(index)), index=index)
    month_ends = frame.groupby([index.year, index.month]).last()
    return sorted(month_ends.tolist())


def run_momentum_backtest(
    universe: list[str],
    top_frac: float = 0.2,
    lookback_days: int = 252,
    skip_days: int = 21,
    cost_pct: float = 0.004,
    start_date: str = "2006-01-01",
) -> tuple[pd.DataFrame, dict]:
    """BIST AI'daki cross-sectional momentum bulgusunu bu kod tabanında sıfırdan
    doğrular: her ay, o ana kadarki 12-1 ay getirisine göre en güçlü %20'lik
    dilimi seç (BIST AI'daki `quintile_frac=0.2` ile aynı), bir sonraki aya
    kadar tut, maliyet düş (%0.4, aynı proje), eşit-ağırlıklı BIST
    ortalamasıyla kıyasla. Look-ahead yok — her ayın sepeti sadece o ana kadar
    bilinen fiyatlarla seçiliyor.

    start_date varsayılan olarak 2006'dan başlıyor: 2005 başındaki Yeni Türk
    Lirası geçişi (1.000.000 eski TL = 1 yeni TL) civarında yfinance verisinde
    gerçek olmayan bir sıçrama tespit edildi (THYAO'da tek günde +%98.113) —
    bu dönem öncesi veri güvenilir kabul edilmiyor.
    """
    prices = fetch_prices(universe, period="max")
    prices = prices.loc[prices.index >= start_date]
    rebalance_positions = _monthly_rebalance_positions(prices.index)

    rows = []
    for i in range(len(rebalance_positions) - 1):
        pos_t = rebalance_positions[i]
        pos_next = rebalance_positions[i + 1]
        if pos_t < lookback_days:
            continue

        momentum_scores = {}
        forward_returns = {}
        for symbol in universe:
            col = f"{symbol}.IS"
            if col not in prices.columns:
                continue
            series = prices[col]
            past_price = series.iloc[pos_t - lookback_days]
            recent_price = series.iloc[pos_t - skip_days]
            current_price = series.iloc[pos_t]
            next_price = series.iloc[pos_next]
            if any(pd.isna(v) for v in (past_price, recent_price, current_price, next_price)):
                continue
            if past_price <= 0 or current_price <= 0:
                continue
            momentum_scores[symbol] = (recent_price / past_price) - 1
            forward_returns[symbol] = (next_price / current_price) - 1

        pool = list(momentum_scores.keys())
        if len(pool) < 10:
            continue

        pool_sorted = sorted(pool, key=lambda s: momentum_scores[s], reverse=True)
        basket_size = max(1, round(len(pool_sorted) * top_frac))
        basket = pool_sorted[:basket_size]

        basket_return = np.mean([forward_returns[s] for s in basket]) - cost_pct
        benchmark_return = np.mean([forward_returns[s] for s in pool])

        rows.append({
            "Tarih": prices.index[pos_next],
            "Sepet Getiri": basket_return,
            "Benchmark Getiri": benchmark_return,
            "Fark": basket_return - benchmark_return,
            "Hisse Sayısı": len(pool),
        })

    monthly = pd.DataFrame(rows)
    if monthly.empty:
        return monthly, {}

    monthly["Sepet Kümülatif"] = (1 + monthly["Sepet Getiri"]).cumprod()
    monthly["Benchmark Kümülatif"] = (1 + monthly["Benchmark Getiri"]).cumprod()

    n = len(monthly)
    win_rate = (monthly["Fark"] > 0).mean()
    mean_excess = monthly["Fark"].mean()
    median_excess = monthly["Fark"].median()
    std_excess = monthly["Fark"].std()
    t_stat = (mean_excess / (std_excess / np.sqrt(n))) if std_excess > 0 else float("nan")

    summary = {
        "ay_sayisi": n,
        "kazanma_orani": win_rate,
        "ortalama_fark": mean_excess,
        "medyan_fark": median_excess,
        "sepet_kumulatif_son": monthly["Sepet Kümülatif"].iloc[-1],
        "benchmark_kumulatif_son": monthly["Benchmark Kümülatif"].iloc[-1],
        "t_stat": t_stat,
    }
    return monthly, summary
