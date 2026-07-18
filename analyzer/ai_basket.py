import json
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

STATE_PATH = Path(__file__).parent.parent / "data" / "ai_basket_state.json"

MAX_POSITIONS = 10
CAPITAL_PER_POSITION_PCT = 100.0 / MAX_POSITIONS
BENCHMARK_INDEX = "XU100.IS"


def _current_index_level() -> float | None:
    """Kapanan işlemleri adil bir şekilde kıyaslamak için BIST100 endeks
    seviyesi (pozisyon açılırken ve kapanırken)."""
    try:
        data = yf.download(BENCHMARK_INDEX, period="5d", progress=False)["Close"]
        return float(data[BENCHMARK_INDEX].dropna().iloc[-1])
    except Exception:
        return None


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"active": {}, "watchlist": {}, "closed": [], "last_updated": None}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    state.setdefault("watchlist", {})
    return state


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _rationale(row: pd.Series) -> str:
    return (
        f"Momentum {row['Momentum Puan']:.0f}, Kâr Trendi {row['Kâr Trend Puan']:.0f}, "
        f"Değerleme {row['Değerleme Puan']:.0f}, Haber {row['Haber Puan']:.0f} puan — "
        f"toplam {row['Toplam Puan']:.0f}/100"
    )


def update_ai_basket(scores_df: pd.DataFrame) -> dict:
    """scores_df: analyzer.scoring.compute_scores() çıktısı.

    Önemli: hedef alım/satış fiyatları bir hisse ilk izlemeye alındığında
    DONDURULUR — her gün o günün fiyatına göre yeniden hesaplanmaz. Aksi
    halde hedef her zaman "bugünün fiyatının biraz altı" olur ve asla
    yakalanamaz (hedef kendi kendini kovalar).

    Akış: aktif pozisyonlar → hedef satışa ulaştıysa kapat. İzleme
    listesindeki hisseler → dondurulmuş hedef alıma ulaştıysa (boş slot
    varsa) pozisyona çevir. Ne izlemede ne aktif olan yeni adaylar →
    izleme listesine hedefleri dondurularak eklenir.
    """
    state = load_state()
    active = state["active"]
    watchlist = state["watchlist"]
    closed = state["closed"]
    today = date.today().isoformat()
    index_level = _current_index_level()

    scores_by_symbol = {row["Hisse"]: row for _, row in scores_df.iterrows()}

    # 1. Aktif pozisyonlar: hedef satış fiyatına ulaşan var mı?
    for symbol in list(active.keys()):
        position = active[symbol]
        current_row = scores_by_symbol.get(symbol)
        if current_row is None:
            continue
        current_price = current_row["Güncel Fiyat"]
        if current_price >= position["hedef_satis_fiyati"]:
            realized_return = (current_price / position["giris_fiyati"] - 1) * 100
            entry_index = position.get("giris_endeks_seviyesi")
            index_return = (
                (index_level / entry_index - 1) * 100
                if entry_index and index_level
                else None
            )
            closed.append({
                "hisse": symbol,
                "giris_tarihi": position["giris_tarihi"],
                "giris_fiyati": position["giris_fiyati"],
                "cikis_fiyati": current_price,
                "cikis_tarihi": today,
                "getiri_pct": realized_return,
                "bist100_getiri_pct": index_return,
                "gerekce": position["gerekce"],
            })
            del active[symbol]

    # 2. İzleme listesi: dondurulmuş hedef alım fiyatına ulaşan var mı?
    open_slots = MAX_POSITIONS - len(active)
    for symbol in list(watchlist.keys()):
        if symbol in active:
            del watchlist[symbol]
            continue
        if open_slots <= 0:
            break
        current_row = scores_by_symbol.get(symbol)
        if current_row is None:
            continue
        current_price = current_row["Güncel Fiyat"]
        watch_item = watchlist[symbol]
        if current_price <= watch_item["hedef_alim_fiyati"]:
            active[symbol] = {
                "giris_tarihi": today,
                "giris_fiyati": current_price,
                "giris_endeks_seviyesi": index_level,
                "hedef_satis_fiyati": watch_item["hedef_satis_fiyati"],
                "tahmini_vade": watch_item["tahmini_vade"],
                "gerekce": watch_item["gerekce"],
                "sermaye_payi_pct": CAPITAL_PER_POSITION_PCT,
            }
            del watchlist[symbol]
            open_slots -= 1

    # 3. Yeni adayları izleme listesine ekle (hedefleri burada donuyor)
    candidates = scores_df[
        scores_df["Hedef Alım Fiyatı"].notna()
        & ~scores_df["Hisse"].isin(active.keys())
        & ~scores_df["Hisse"].isin(watchlist.keys())
    ]
    for _, row in candidates.iterrows():
        symbol = row["Hisse"]
        watchlist[symbol] = {
            "eklenme_tarihi": today,
            "hedef_alim_fiyati": row["Hedef Alım Fiyatı"],
            "hedef_satis_fiyati": row["Hedef Satış Fiyatı"],
            "tahmini_vade": row["Tahmini Vade"],
            "toplam_puan": row["Toplam Puan"],
            "gerekce": _rationale(row),
        }

    state["active"] = active
    state["watchlist"] = watchlist
    state["closed"] = closed
    state["last_updated"] = today
    save_state(state)
    return state
