# Değişiklik Günlüğü

## v0.5.0 — Sürekli güncellenen sepet: sat/ekle/tut (2026-07-18)

### Added
- `analyzer/portfolio.py`: sepet durumunu (`data/basket_state.json`) kalıcı olarak tutan ve her güncellemede öncekiyle kıyaslayıp sat/ekle/tut listesi çıkaran mantık. BIST 100 evreninde, en güçlü %20'lik dilim takip ediliyor (geçmiş testle aynı parametre).
- `scripts/rebalance.py`: sepeti yeniden hesaplayıp durumu güncelleyen komut satırı script'i.
- `.github/workflows/rebalance.yml`: bu script'i ayda bir (her ayın 1'i) otomatik çalıştırıp sonucu depoya commit'leyen GitHub Actions iş akışı — elle de `workflow_dispatch` ile tetiklenebilir.
- Panelde yeni "Takip Edilen Sepet" bölümü: güncel sepet, son güncelleme tarihi, ve o ayki sat/ekle/tut listesi.
- İlk çalıştırma yapıldı (2026-07-18): 20 hisselik ilk sepet kuruldu (hepsi "ekle" — henüz kıyaslanacak önceki bir sepet yoktu, bu beklenen bir durum).

### Not
- Kalıcılık git deposu üzerinden sağlanıyor (basket_state.json her ay commit'leniyor) — ayrı bir veritabanı kurulmadı, bu ölçekte gereksiz olurdu.

## v0.4.0 — Seçilebilir BIST evreni (30/100/500/TÜM) (2026-07-17)

### Added
- `analyzer/universe.py`: artık statik bir liste yerine Borsa İstanbul'un resmi endeks bileşen verisini (`borsapy` kütüphanesi üzerinden) canlı çekiyor. Panelde BIST 30 / BIST 100 / BIST 500 / BIST TÜM arasında seçim yapılabiliyor; sepet motoru ve geçmiş test seçilen evrene göre çalışıyor.
- `analyzer/universe_seed.json`: yedek veri dosyası — canlı kaynak başarısız olursa buraya düşülüyor (aşağıya bak, nedeni önemli).
- Bonus bulgu: Borsa İstanbul'un endeks verisinde resmi bir "BIST Halka Arz" (XHARZ, 55 hisse) endeksi de var — ileride halka arz menüsü özelliği için doğrudan kullanılabilir.

### Fixed — veri kaynağı güvenilirliği
- Borsa İstanbul'un endeks bileşen CSV kaynağı test edilirken tutarsız davrandı: aynı istek art arda denendiğinde yaklaşık %25 başarı oranıyla çalıştı, geri kalanında bağlantı sıfırlandı (muhtemelen bot/otomatik istek koruması). `get_universe()` artık başarısız olursa birkaç kez tekrar dener, hâlâ olmazsa depoyla gelen son bilinen iyi listeye (`universe_seed.json`, 2026-07-17 tarihli) düşer ve panelde bunu açıkça belirtir. Canlı deploy ortamı (Streamlit Cloud) da bir "veri merkezi" IP'si kullandığından aynı sorun orada da çıkabilir — bu yüzden yedek mekanizması olmadan bu özellik güvenilir sayılmazdı.

## v0.3.0 — Sepet motorunun geçmiş testi (2026-07-17)

### Added
- `analyzer/backtest.py`: momentum sepetinin 2006'dan bugüne aylık geriye dönük testi — her ay yeniden sıralama, en güçlü %20'lik dilimi tutma, maliyet düşme (%0.4, BIST AI ile aynı), eşit ağırlıklı BIST ortalamasıyla kıyaslama. Look-ahead yok.
- Panelde yeni "Geçmiş Test" bölümü: sepet vs. benchmark kümülatif büyüme grafiği, aylık kazanma oranı, ortalama/medyan fazla getiri, ve teknik detaylar (t-istatistiği vb.) için ayrı bir açılır bölüm.

### Fixed — önemli veri hatası
- İlk çalıştırmada 2001'den itibaren test edilince bulgu çok daha güçlü çıkıyordu, ama araştırınca sebebi ortaya çıktı: **2005 başındaki Yeni Türk Lirası geçişi** (1.000.000 eski TL = 1 yeni TL) civarında yfinance verisinde gerçek olmayan bir sıçrama var (THYAO'da tek günde +%98.113 — imkansız). Bu, o dönemi içeren herhangi bir geriye dönük testi anlamsız şekilde şişiriyor. Test artık 2006-01-01'den başlıyor.

### Bulgu (dürüst değerlendirme)
- Hata düzeltildikten sonra: 235 ay, kazanma oranı %54, aylık ortalama fark +%0.28, **t-istatistiği ≈1.0** — projenin kendi koyduğu "ciddiye alınır" eşiği olan ≥2'nin altında. Yani bu ilk bulgu göründüğünden daha zayıf çıktı; BIST AI'daki orijinal t=+2.50 bulgusunun bir kısmı muhtemelen bu aynı veri hatasından kaynaklanıyordu (o proje bu düzeltmeyi hiç yapmamıştı).
- Sonuç: sepet motoru şu haliyle "kesin işe yarıyor" diyebileceğimiz bir eşiği henüz geçmiyor. Bir sonraki adımlarda (farklı vade/parametre denemeleri, kalite/temel katmanının eklenmesi vb.) bu tekrar değerlendirilecek.

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
