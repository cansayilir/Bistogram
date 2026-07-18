import borsapy as bp
import numpy as np
import pandas as pd
import yfinance as yf

from analyzer.basket import compute_momentum_table, to_yf_ticker

RED_FLAG_KEYWORDS = ["Devre Kesici", "İşlem Yasağı"]


def _momentum_scores(universe: list[str]) -> pd.DataFrame:
    """Momentum puanı (0-40): BIST100 içindeki 12-1 ay getiri sıralamasında
    nerede olduğu (üst dilim = yüksek puan).

    NOT: Burada eskiden bir de "trend puanı" (fiyatın 200 günlük ortalamaya
    yakınlığı) vardı, momentumla birlikte 20+20 ağırlıklandırılıyordu.
    2006-2026 geriye dönük testte bu bileşen momentumu İYİLEŞTİRMEDİ, tam
    tersine anlamlı şekilde KÖTÜLEŞTİRDİ (t=+0.95 → t=-2.37) — çünkü güçlü
    momentumlu hisseler tanım gereği 200 günlük ortalamalarının epey üzerinde
    olur, ama trend puanı "ortalamaya yakın" olanı ödüllendirip "uzak" olanı
    cezalandırıyordu; yani tam da işe yarayan sinyali sistematik olarak
    zayıflatıyordu. Bulgu analyzer/scoring_backtest.py'de kayıtlı. Bu yüzden
    trend bileşeni kaldırıldı, momentum tek başına 40 puana çıkarıldı.
    """
    momentum_table = compute_momentum_table(universe)
    if momentum_table.empty:
        return pd.DataFrame(columns=["Hisse", "Güncel Fiyat", "Momentum Puan"])

    n = len(momentum_table)
    if n > 1:
        momentum_table["Momentum Puan"] = 40 * (1 - (momentum_table.index - 1) / (n - 1))
    else:
        momentum_table["Momentum Puan"] = 40.0

    return momentum_table[["Hisse", "Güncel Fiyat", "Momentum Puan"]]


def _profit_trend_score(symbol: str) -> float:
    """Son yılların ilk yarısındaki ortalama net kâra kıyasla ikinci
    yarısındaki ortalama net kâr belirgin şekilde arttıysa tam puan, belirgin
    şekilde azaldıysa sıfır, aksi halde nötr.

    NOT: Önceki sürüm her yılın ÖNCEKİNDEN kesinlikle yüksek/düşük olmasını
    şart koşuyordu (katı monoton artış/azalış). Bu, elimizde sadece ~4 yıllık
    veri varken tek bir dalgalı yıl yüzünden temelde sağlam bir şirketi
    "karışık" (nötr) kategoriye düşürecek kadar kırılgandı. Ortalama
    karşılaştırması tek yıllık gürültüye karşı daha dayanıklı.
    """
    try:
        income = bp.Ticker(symbol).income_stmt
        net_income = income.loc["DÖNEM KARI (ZARARI)"]
        years = sorted(net_income.index)
        values = [net_income[y] for y in years]
        if len(values) < 2:
            return 10.0

        mid = len(values) // 2
        early_avg = np.mean(values[:mid]) if mid > 0 else values[0]
        late_avg = np.mean(values[mid:])

        if early_avg == 0:
            return 10.0
        change_pct = (late_avg - early_avg) / abs(early_avg)
        if change_pct > 0.10:
            return 20.0
        if change_pct < -0.10:
            return 0.0
        return 10.0
    except Exception:
        return 10.0


def _news_score(symbol: str) -> tuple[float, bool]:
    """Son 30 günde devre kesici / işlem yasağı gibi kırmızı bayrak varsa
    büyük puan kaybı."""
    try:
        news = bp.Ticker(symbol).news
        dates = pd.to_datetime(news["Date"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
        recent = news[dates >= (pd.Timestamp.now() - pd.Timedelta(days=30))]
        titles = " ".join(recent["Title"].astype(str).tolist())
        if any(keyword in titles for keyword in RED_FLAG_KEYWORDS):
            return 0.0, True
        return 20.0, False
    except Exception:
        return 10.0, False


def _valuation_scores(universe: list[str]) -> dict[str, float]:
    """Düşük F/K (ucuz) = yüksek puan, BIST100 içindeki sıralamaya göre."""
    pe_values = {}
    for symbol in universe:
        try:
            info = yf.Ticker(to_yf_ticker(symbol)).info
            pe = info.get("trailingPE")
            if pe is not None and pe > 0:
                pe_values[symbol] = pe
        except Exception:
            continue

    scores = {}
    if pe_values:
        sorted_symbols = sorted(pe_values, key=lambda s: pe_values[s])
        n = len(sorted_symbols)
        for rank, symbol in enumerate(sorted_symbols):
            scores[symbol] = 20 * (1 - rank / (n - 1)) if n > 1 else 20.0
    for symbol in universe:
        scores.setdefault(symbol, 10.0)
    return scores


def compute_scores(universe: list[str]) -> pd.DataFrame:
    """Her hisse için kompozit puan (0-100) + hedef alım/satış fiyatı çıkarır.

    Puanlama: momentum (40, geçmiş testte doğrulanan tek fiyat-bazlı sinyal) +
    kâr trendi (20) + değerleme (20) + haber/KAP temizliği (20). Skor
    eşiklerine göre hedef alım fiyatı (güncel fiyata indirim), hedef satış
    fiyatı (kâr hedefi) ve kaba bir vade tahmini üretiliyor.

    DÜRÜST NOT: Momentum bileşeni 2006-2026 verisiyle test edildi (t≈+0.95,
    zayıf ama pozitif). Kâr trendi + değerleme + haber bileşenleri, tarihsel
    (o anda bilinen) veri kaynağımız olmadığı için henüz backtest edilemedi —
    sadece ileriye dönük (günlük otomatik tarama) izleniyor.
    """
    base = _momentum_scores(universe)
    if base.empty:
        return base

    valuation_scores = _valuation_scores(universe)

    rows = []
    for _, row in base.iterrows():
        symbol = row["Hisse"]
        profit_score = _profit_trend_score(symbol)
        news_score, has_red_flag = _news_score(symbol)
        value_score = valuation_scores.get(symbol, 10.0)

        total = row["Momentum Puan"] + profit_score + value_score + news_score
        current_price = row["Güncel Fiyat"]

        if has_red_flag:
            # Kırmızı bayrak (devre kesici/işlem yasağı) varsa skor ne olursa
            # olsun şu an giriş yapılmaz — bu bir puan indirimi değil, sert kapı.
            discount = target_gain = horizon = None
        elif total >= 80:
            discount, target_gain, horizon = 0.03, 0.25, "3-6 ay"
        elif total >= 60:
            discount, target_gain, horizon = 0.06, 0.18, "4-8 ay"
        elif total >= 40:
            discount, target_gain, horizon = 0.12, 0.12, "6-12 ay"
        else:
            discount = target_gain = horizon = None

        entry_price = current_price * (1 - discount) if discount is not None else None
        exit_price = entry_price * (1 + target_gain) if entry_price is not None else None

        rows.append({
            "Hisse": symbol,
            "Güncel Fiyat": current_price,
            "Momentum Puan": row["Momentum Puan"],
            "Kâr Trend Puan": profit_score,
            "Değerleme Puan": value_score,
            "Haber Puan": news_score,
            "Toplam Puan": total,
            "Kırmızı Bayrak": has_red_flag,
            "Hedef Alım Fiyatı": entry_price,
            "Hedef Satış Fiyatı": exit_price,
            "Tahmini Vade": horizon,
        })

    result = pd.DataFrame(rows).sort_values("Toplam Puan", ascending=False).reset_index(drop=True)
    result.index += 1
    return result
