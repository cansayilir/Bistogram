import pandas as pd

from analyzer.basket import fetch_prices, to_yf_ticker
from analyzer.universe import get_index_components

IPO_INDEX = "XHARZ"


def get_ipo_table() -> tuple[pd.DataFrame, bool, str | None]:
    """Borsa İstanbul'un resmi "BIST Halka Arz" (XHARZ) endeksindeki
    hisseler için, ilk işlem gününden bugüne performansı hesaplar.

    Not: gerçek halka arz (arz) fiyatı değil, yfinance'te bulunan ilk
    işlem günü kapanış fiyatı kullanılıyor — bu ilk gün prim/iskonto
    etkisini içerebilir, bu yüzden "ilk işlem gününden getiri" olarak
    etiketleniyor, "halka arz fiyatından getiri" değil.
    """
    components, is_live, seed_date = get_index_components(IPO_INDEX)
    if not components:
        return pd.DataFrame(), is_live, seed_date

    symbols = [c["symbol"] for c in components]
    names = {c["symbol"]: c["name"] for c in components}
    prices = fetch_prices(symbols, period="max")

    rows = []
    for symbol in symbols:
        col = to_yf_ticker(symbol)
        if col not in prices.columns:
            continue
        series = prices[col].dropna()
        if series.empty:
            continue
        first_price = series.iloc[0]
        current_price = series.iloc[-1]
        if first_price <= 0:
            continue
        # Tek günlük veri = daha yeni yfinance'e düşmemiş / dün işleme başlamış
        # demek; bu durumda getiri hesaplamak yanıltıcı (hep %0 çıkar).
        return_pct = (current_price / first_price - 1) * 100 if len(series) > 1 else None
        rows.append({
            "Hisse": symbol,
            "Şirket": names.get(symbol, symbol),
            "İlk İşlem Günü": series.index[0].date(),
            "İlk Fiyat": first_price,
            "Güncel Fiyat": current_price,
            "İlk Günden Getiri (%)": return_pct,
        })

    table = pd.DataFrame(rows)
    if not table.empty:
        table = table.sort_values("İlk İşlem Günü", ascending=False).reset_index(drop=True)
        table.index += 1
    return table, is_live, seed_date
