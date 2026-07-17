import pandas as pd
import yfinance as yf


def to_yf_ticker(symbol: str) -> str:
    return f"{symbol}.IS"


def fetch_prices(universe: list[str], period: str = "18mo") -> pd.DataFrame:
    tickers = [to_yf_ticker(s) for s in universe]
    data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    return data["Close"]


def compute_momentum_table(
    universe: list[str],
    lookback_days: int = 252,
    skip_days: int = 21,
) -> pd.DataFrame:
    """Her hisse için 12-1 ay momentum getirisini hesaplar (son 1 ay hariç, son 12 ay).

    Kaynak: BIST AI projesindeki araştırma (2026-07-07) bu tanımın BIST100'de
    istatistiksel olarak anlamlı bir bulgu verdiğini gösterdi. Bu, o bulgunun
    Bistogram'da sıfırdan yazılmış ilk canlı uygulamasıdır — henüz bu kod
    tabanında ayrıca geriye dönük doğrulanmadı.
    """
    prices = fetch_prices(universe)

    rows = []
    for symbol in universe:
        col = to_yf_ticker(symbol)
        if col not in prices.columns:
            continue
        series = prices[col].dropna()
        if len(series) <= lookback_days:
            continue
        past_price = series.iloc[-lookback_days]
        recent_price = series.iloc[-skip_days]
        if past_price <= 0:
            continue
        momentum_return = (recent_price / past_price) - 1
        rows.append({
            "Hisse": symbol,
            "12-1 Ay Getiri (%)": momentum_return * 100,
            "Güncel Fiyat": series.iloc[-1],
        })

    table = pd.DataFrame(rows)
    if not table.empty:
        table = table.sort_values("12-1 Ay Getiri (%)", ascending=False).reset_index(drop=True)
        table.index += 1
    return table
