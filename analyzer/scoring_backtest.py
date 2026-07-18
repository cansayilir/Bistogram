import numpy as np
import pandas as pd

from analyzer.backtest import _monthly_rebalance_positions
from analyzer.basket import fetch_prices


def _summarize(monthly: pd.DataFrame) -> dict:
    n = len(monthly)
    if n == 0:
        return {}
    mean_excess = monthly["Fark"].mean()
    std_excess = monthly["Fark"].std()
    t_stat = (mean_excess / (std_excess / np.sqrt(n))) if std_excess > 0 and n > 1 else float("nan")
    return {
        "ay_sayisi": n,
        "kazanma_orani": (monthly["Fark"] > 0).mean(),
        "ortalama_fark": mean_excess,
        "medyan_fark": monthly["Fark"].median(),
        "t_stat": t_stat,
    }


def run_technical_score_backtest(
    universe: list[str],
    top_frac: float = 0.2,
    lookback_days: int = 252,
    skip_days: int = 21,
    ma_window: int = 200,
    cost_pct: float = 0.004,
    start_date: str = "2007-06-01",
) -> tuple[pd.DataFrame, dict]:
    """AI Sepeti'nin fiyat-bazlı bileşenlerini (momentum + trend/MA200 puanı)
    2006 sonrası veriyle geriye dönük test eder.

    Temel (kâr trendi) ve haber (KAP kırmızı bayrağı) bileşenleri burada YOK:
    bu ikisi için tarihsel (o tarihte bilinen) veri kaynağımız yok, sadece
    borsapy'nin bugünün anlık görüntüsü var — geçmişe uygulamaya çalışmak
    look-ahead hatası yaratırdı (tam olarak eski projede bir kere düzelttiğimiz
    hata türü). Bu iki bileşen bu yüzden sadece ileriye dönük, günlük otomatik
    taramayla (scripts/update_ai_basket.py) izleniyor.

    Metodoloji notu: ağırlıklar (momentum 20 + trend 20 puan) veriye bakılarak
    fit edilmedi, mantıkla belirlendi — yani klasik "eğitim dönemi" diye bir
    adım yok. Bu yüzden tam bir yeniden-eğitim döngüsü (walk-forward refit)
    yerine, her ayı sadece o ana kadar bilinen veriyle değerlendiren tek bir
    kayan test yapılıyor, sonuç ayrıca alt dönemlere bölünerek tutarlılığı
    kontrol ediliyor.
    """
    prices = fetch_prices(universe, period="max")
    prices = prices.loc[prices.index >= "2006-01-01"]
    rebalance_positions = _monthly_rebalance_positions(prices.index)

    min_lookback = max(lookback_days, ma_window)
    rows = []
    for i in range(len(rebalance_positions) - 1):
        pos_t = rebalance_positions[i]
        pos_next = rebalance_positions[i + 1]
        if pos_t < min_lookback:
            continue
        if prices.index[pos_t] < pd.Timestamp(start_date):
            continue

        momentum_returns = {}
        trend_scores = {}
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
            ma_window_prices = series.iloc[pos_t - ma_window : pos_t]

            if any(pd.isna(v) for v in (past_price, recent_price, current_price, next_price)):
                continue
            if ma_window_prices.isna().any() or len(ma_window_prices) < ma_window:
                continue
            if past_price <= 0 or current_price <= 0:
                continue

            momentum_returns[symbol] = (recent_price / past_price) - 1
            forward_returns[symbol] = (next_price / current_price) - 1

            ma200 = ma_window_prices.mean()
            if current_price < ma200:
                trend_scores[symbol] = 0.0
            else:
                distance_pct = (current_price / ma200 - 1) * 100
                trend_scores[symbol] = max(0.0, 20.0 * (1 - max(0.0, distance_pct - 5) / 15))

        pool = list(momentum_returns.keys())
        if len(pool) < 10:
            continue

        sorted_by_momentum = sorted(pool, key=lambda s: momentum_returns[s])
        n = len(sorted_by_momentum)
        momentum_scores = {
            symbol: (20 * (rank / (n - 1)) if n > 1 else 20.0)
            for rank, symbol in enumerate(sorted_by_momentum)
        }

        composite = {s: momentum_scores[s] + trend_scores[s] for s in pool}
        pool_sorted = sorted(pool, key=lambda s: composite[s], reverse=True)
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

    summary = _summarize(monthly)

    sub_periods = {
        "2007-2018 (erken dönem)": monthly[monthly["Tarih"] < "2019-01-01"],
        "2019-2022 (doğrulama benzeri)": monthly[
            (monthly["Tarih"] >= "2019-01-01") & (monthly["Tarih"] < "2023-01-01")
        ],
        "2023-bugün (son dönem)": monthly[monthly["Tarih"] >= "2023-01-01"],
    }
    summary["alt_donemler"] = {
        name: _summarize(df) for name, df in sub_periods.items() if len(df) >= 6
    }

    return monthly, summary
