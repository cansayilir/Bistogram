import json
import time
from pathlib import Path

import borsapy as bp

UNIVERSE_OPTIONS = {
    "BIST 30": "XU030",
    "BIST 100": "XU100",
    "BIST 500": "XU500",
    "BIST TÜM": "XUTUM",
}

_SEED_PATH = Path(__file__).parent / "universe_seed.json"


def _fetch_live(index_symbol: str, attempts: int = 4, delay: float = 3.0) -> list[str]:
    """Borsa İstanbul'un resmi CSV kaynağı zaman zaman bağlantıyı reddediyor
    (gözlemlenen başarı oranı ~%25) — bu yüzden birkaç kez deneniyor.
    """
    for _ in range(attempts):
        symbols = bp.Index(index_symbol).component_symbols
        if symbols:
            return symbols
        time.sleep(delay)
    return []


def _load_seed(index_symbol: str) -> tuple[list[str], str | None]:
    if not _SEED_PATH.exists():
        return [], None
    seed = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    return seed.get("indices", {}).get(index_symbol, []), seed.get("generated_at")


def get_universe(tier: str) -> tuple[list[str], bool, str | None]:
    """BIST evren listesini döner.

    Dönüş: (hisse_listesi, canli_mi, yedek_tarihi)
    - canli_mi=True ise veri az önce borsaistanbul.com'dan çekildi.
    - canli_mi=False ise kaynak o an ulaşılamaz olduğu için depoyla gelen
      son bilinen iyi listeye (universe_seed.json) düşüldü; yedek_tarihi
      o listenin ne zaman alındığını gösterir.
    """
    index_symbol = UNIVERSE_OPTIONS[tier]
    symbols = _fetch_live(index_symbol)
    if symbols:
        return symbols, True, None

    seed_symbols, generated_at = _load_seed(index_symbol)
    return seed_symbols, False, generated_at
