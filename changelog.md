# Değişiklik Günlüğü

## v0.2.0 — Sepet motorunun ilk sürümü (2026-07-17)

### Added
- `analyzer/universe.py`: BIST evreni listesi (97 hisse) — BIST AI'daki aynı roster'dan alındı, bu sadece hangi hisselerin BIST100'de olduğuna dair bir gerçek listesi, strateji kodu değil.
- `analyzer/basket.py`: 12-1 ay cross-sectional momentum hesabı (son 1 ay hariç tutularak son 12 aylık getiri) — BIST AI'daki araştırmada tek anlamlı bulgu (t≈2.50) burada sıfırdan yazıldı. Panelde hisseleri bu ölçüye göre sıralıyor.
- Panel artık en güçlü 10 hisseyi ve tam sıralamayı gösteriyor (`app.py`).

### Fixed
- İlk denemede aşırı yüksek getirili hisseleri (KTLEV, ODINE vb.) "veri hatası" sanıp eleyen bir filtre eklenmişti; kontrol edince KTLEV'in +%16643 halka arz sonrası getirisinin gerçek olduğu anlaşıldı (kullanıcı doğruladı). Filtre kaldırıldı — momentum stratejisinin amacı zaten en güçlü çıkanları bulmak, büyük diye elemek mantıksız.

### Not
- Bu sıralama henüz sadece anlık bir görünüm; bu kod tabanında geçmişe dönük olarak ayrıca doğrulanmadı (sıradaki adımlardan biri).

## v0.1.0 — İlk iskelet (2026-07-17)

### Added
- Proje tanımı ve yaklaşımı (`README.md`): BIST AI'daki tek-hisse gösterge tabanlı zamanlamanın neden işe yaramadığı, bunun yerine hangi katmanlarla (sepet motoru, emsal/kıyas, temel+gündem) ilerleneceği.
- Canlı panel iskeleti (`app.py`, Streamlit) — henüz sadece bir yer tutucu sayfa, ama en başından itibaren çalışıyor ve tarayıcıda açılabiliyor. Amaç: sonraki her adımı anlık gözlemleyebilmek, arayüzü en sona bırakmamak.
- Bağımlılıklar (`requirements.txt`): streamlit, pandas, yfinance.
