# Değişiklik Günlüğü

## v0.13.0 — AI Sepeti: sanal test için sağlamlaştırma (2026-07-18)

### Added
- Kapanan işlemler artık aynı dönemdeki **BIST100 endeksiyle (XU100)** kıyaslanıyor — pozisyon açılırken ve kapanırken endeks seviyesi kaydediliyor, böylece "işlem kârlı mıydı" değil "BIST'i geçti mi" sorusuna cevap veriliyor (projenin geri kalanıyla aynı disiplin).
- Panelde "Kapanan İşlemler — Performans" özeti: kazanma oranı, ortalama getiri, BIST100'e göre fark. Az işlemle bunun henüz bir şey kanıtlamayacağı açıkça belirtiliyor.

### Fixed
- `_profit_trend_score`: eskiden her yılın bir öncekinden kesinlikle yüksek/düşük olmasını şart koşuyordu (katı monoton artış/azalış) — elimizde sadece ~4 yıllık veri varken bu, tek dalgalı bir yıl yüzünden sağlam bir şirketi "nötr" kategoriye düşürecek kadar kırılgandı. Artık yılların ilk yarısı ortalaması ile ikinci yarısı ortalaması kıyaslanıyor — tek yıllık gürültüye karşı daha dayanıklı.

### Not
- Kullanıcı ile netleşen çerçeve: temel+haber bileşenleri geriye dönük test edilemediği için, bundan sonra sistem gerçek parayla değil bu sanal (paper trading) ortamda, zaman içinde biriken gerçek sonuçlarla değerlendirilecek.

## v0.12.0 — AI Sepeti: trend bileşeni test edildi, kaldırıldı (2026-07-18)

### Added
- `analyzer/scoring_backtest.py`: AI Sepeti'nin fiyat-bazlı bileşenlerini (momentum + trend/MA200) 2006-2026 verisiyle geriye dönük test eden modül. Temel + haber bileşenleri için tarihsel (o anda bilinen) veri kaynağı olmadığından bunlar dışarıda tutuldu — dahil etmek look-ahead hatası yaratırdı.

### Fixed — önemli bulgu
- Geriye dönük test sonucu: **sadece momentum** t=+0.95 (önceki bulgularla tutarlı, kod doğrulandı) ama **momentum + trend birlikte** t=**-2.37** — yani trend bileşeni eklenince sonuç BIST'ten anlamlı şekilde daha kötü çıktı, ve bu üç alt dönemde de (2007-2018, 2019-2022, 2023-bugün) tutarlıydı.
- Sebep: güçlü momentumlu hisseler tanım gereği 200 günlük ortalamalarının epey üzerinde olur, ama trend puanı formülü "ortalamaya yakın" olanı ödüllendirip "uzak" olanı cezalandırıyordu — yani tam da işe yarayan sinyali (momentum) sistematik olarak zayıflatıyordu.
- **Trend bileşeni kaldırıldı.** `analyzer/scoring.py`'de momentum tek başına 40 puana çıkarıldı (eskiden momentum 20 + trend 20). Toplam puan hâlâ 100: Momentum (40) + Kâr Trendi (20) + Değerleme (20) + Haber (20).
- Formül değiştiği için izleme listesi sıfırlanıp yeni ağırlıklarla yeniden tarandı (43 hisse, 0 aktif pozisyon — beklenen).

## v0.11.0 — AI Sepeti: puanlama tabanlı ikinci sepet sistemi (2026-07-18)

### Added
- `analyzer/scoring.py`: her BIST 100 hissesi için 100 üzerinden kompozit puan hesaplıyor — Momentum (20, BIST100 içindeki 12-1 ay getiri sıralaması), Trend (20, fiyatın 200 günlük ortalamaya göre konumu), Kâr Trendi (20, son yılların net kâr yönü), Değerleme (20, F/K'nın BIST100 içindeki ucuzluk sıralaması, yfinance'ten), Haber (20, son 30 günde devre kesici/işlem yasağı gibi kırmızı bayrak varsa sert kesinti — puan indirimi değil, giriş engeli).
- `analyzer/ai_basket.py`: izleme listesi → aktif pozisyon → kapanan işlem akışını yöneten durum makinesi. **Önemli tasarım kararı:** hedef alım/satış fiyatları bir hisse ilk izlemeye alındığında donduruluyor, her gün güncel fiyata göre yeniden hesaplanmıyor (aksi halde hedef "bugünün fiyatının biraz altı" olarak sürekli kayar ve hiç yakalanamaz — ilk denemede bu hatayı yapıp fark ettik).
- `scripts/update_ai_basket.py` + `.github/workflows/ai_basket_update.yml`: BIST 100'ü günde bir tarayıp durumu güncelleyen otomatik iş akışı (momentum sepetiyle aynı git-tabanlı kalıcılık deseni).
- Panelde yeni "AI Sepeti (Deneysel)" bölümü: aktif pozisyonlar (giriş tarihi/fiyatı, kaç gündür tutulduğu, güncel %kâr/zarar, hedef satış, tahmini vade, gerekçe, sermaye payı), izleme listesi (hedefine henüz ulaşmamış adaylar), kapanan işlemler geçmişi (gerçekleşen kâr/zarar).
- İlk tarama yapıldı: 64 hisse izleme listesine eklendi, hedefleri donduruldu; 0 aktif pozisyon (beklenen — ilk turda hiçbir hisse henüz kendi donmuş hedefine karşı test edilmedi).

### Not
- Bu sistem kullanıcının isteği üzerine LLM (Gemini) kullanmadan, tamamen kodlanmış/kural tabanlı bir puanlama olarak tasarlandı — momentum sepeti gibi ayrı, ikinci bir sepet.
- **DÜRÜST UYARI:** Bu puanlama mantıklı bir çerçeve ama henüz momentum sepeti gibi geçmiş veriyle test edilmedi — kanıtlanmış değil, deneysel. Sıradaki adım bunun bir backtest'ini yapmak.

## v0.10.0 — AI Hisse Yorumu: yükleniyor göstergesi + tarih hatası düzeltmesi (2026-07-18)

### Fixed
- Kullanıcının BETAE (yeni halka arz) için aldığı yorumda AI'nın kendisi bir çelişki fark etti: "18 ay önceki fiyat" diye etiketlenen veri aslında sadece 3 haftalık bir geçmişti (hisse 29 Haziran 2026'da halka arz olmuş). Sebep: `gather_stock_context` her zaman "~18 ay önceki fiyat" diye etiketliyordu, mevcut verinin gerçekte hangi tarihten başladığını kontrol etmiyordu. Artık gerçek tarihler ("mevcut en eski veri (2026-07-01)" gibi) kullanılıyor — yeni halka arzlarda kısa geçmiş dürüstçe kısa gösteriliyor.

### Added
- "Yorum al" butonuna basınca artık hiçbir şey olmuyormuş gibi görünmüyor: veri toplanırken ("... veri toplanıyor") ve Gemini ilk yanıtı üretirken ("Gemini yorum üretiyor...") ayrı ayrı yükleniyor göstergeleri var.

## v0.9.0 — AI Hisse Yorumu: iki gerçek iyileştirme (2026-07-18)

### Fixed
- Kullanıcının PGSUS için aldığı ilk canlı yorumu inceleyince iki sorun bulundu:
  1. **Net kâr verisi kayboluyordu.** `gather_stock_context` gelir tablosunun sadece ilk 6 satırını alıyordu (`income.head(6)`), ama "DÖNEM KARI (ZARARI)" (net kâr) satırı 43 satırlık tablonun 35. sırasında — hiç AI'ya gönderilmiyordu. Artık pozisyona göre değil, isme göre (Satış Gelirleri, Satışların Maliyeti, Brüt Kâr, Faaliyet Kârı, Dönem Kârı) belirli kalemler seçiliyor.
  2. **Yüksek enflasyon uyarısı eksikti.** Sistem promptuna, TL bazlı gelir/kâr büyümesinin nominal olduğunu ve enflasyon düşülünce gerçek büyümenin çok daha zayıf olabileceğini belirtme kuralı eklendi — "gelirler X kat arttı" tek başına olumlu bir sinyal gibi sunulmuyor artık.
- PGSUS örneğinde net kâr verisi eklenince ortaya çıkan bulgu: 2023-2025 arası net kâr aslında düşüyor (20.9B → 17.4B → 15.1B TL), gelir artışına rağmen — önceki yorumda hiç görünmeyen bir sinyal.

## v0.8.0 — AI Hisse Yorumu: Claude'dan ücretsiz Gemini'ye geçiş (2026-07-18)

### Changed
- Canlıda test edilirken Anthropic hesabında kredi olmadığı ortaya çıktı (`insufficient_quota`). Kullanıcı ücretli kalmak istemedi — `analyzer/commentary.py` artık Google Gemini API (`gemini-3.5-flash`, `google-genai` SDK) kullanıyor: kredi kartı gerektirmeyen gerçek bir ücretsiz katmanı var (günde 1.500 istek).
- `app.py`: API anahtarı kontrolü `ANTHROPIC_API_KEY` yerine `GEMINI_API_KEY` okuyor; uyarı mesajı `aistudio.google.com`'dan ücretsiz anahtar alma talimatına güncellendi.
- `requirements.txt`: `anthropic` çıkarıldı, `google-genai` eklendi.

### Güvenlik notu
- Kullanıcı bir Anthropic API anahtarını yanlışlıkla sohbete yapıştırdı — anahtar kullanılmadı, iptal edilip yeniden oluşturulması söylendi. Anahtarlar sadece Streamlit Cloud'un Secrets arayüzüne girilmeli, sohbete değil.

## v0.7.0 — AI Hisse Yorumu (2026-07-18)

### Added
- `analyzer/commentary.py`: bir hisse kodu için haberler (KAP açıklamaları, `borsapy` üzerinden), temel finansal göstergeler (gelir tablosu) ve fiyat performansını toplayıp Claude Opus 4.8'e gönderen, dengeli bir durum değerlendirmesi (olumlu/olumsuz senaryo + riskler) üreten modül. Sistem promptu kesin yön tahmini yapmayı açıkça yasaklıyor.
- Panelde yeni "AI Hisse Yorumu" bölümü: hisse kodu gir, "Yorum al" butonuna bas, yanıt akış halinde (streaming) geliyor.
- API anahtarı yönetimi: `st.secrets["ANTHROPIC_API_KEY"]` (Streamlit Cloud) veya `ANTHROPIC_API_KEY` ortam değişkeni (yerel) — anahtar yoksa panel çökmüyor, nasıl ekleneceğini gösteren bir uyarı çıkıyor.

### Not
- Bu özelliğin çalışması için Streamlit Cloud'da bir Anthropic API anahtarı eklenmesi gerekiyor (uygulama ayarları → Secrets). Anahtar eklenene kadar bu bölüm sadece kurulum talimatı gösteriyor.

## v0.6.0 — Halka Arz Menüsü (ilk sürüm) (2026-07-18)

### Added
- `analyzer/ipo.py`: Borsa İstanbul'un resmi "BIST Halka Arz" (XHARZ, 55 hisse) endeksindeki şirketleri, ilk işlem gününden bugüne performanslarıyla listeliyor.
- `analyzer/universe.py` refactor: `get_index_components()` artık sembol + şirket ismini birlikte döndürüyor (öncesinde sadece sembol vardı) — hem evren seçici hem halka arz menüsü aynı fonksiyonu paylaşıyor. `universe_seed.json` yedek dosyası da isimlerle yeniden oluşturuldu.
- Panelde yeni "Halka Arz Menüsü" bölümü: şirket adı, ilk işlem günü, ilk fiyat, güncel fiyat, ilk günden getiri. Tek günlük verisi olan (dün halka arz olmuş) hisseler için yanıltıcı %0 yerine "Yeni" etiketi kullanılıyor.

### Not
- Bu ilk sürüm sadece ham listeyi gösteriyor — henüz AI yorumu / benzer geçmiş halka arzlarla emsal kıyaslaması yok (planın 3. maddesi, AI hisse yorumlama aracıyla birlikte gelecek — bir LLM API anahtarı gerektiriyor).
- "İlk Fiyat" gerçek halka arz fiyatı değil, yfinance'teki ilk işlem günü kapanışı — ilk gün primi/iskontosunu içerebilir, ileride gerçek arz fiyatı bulunursa değiştirilecek.

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
