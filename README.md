# Bistogram

BIST hisseleri için kendi geliştirdiğimiz, dış indikatör/programlara bağımlı olmayan analiz ve karar-destek sistemi.

## Yaklaşım

BIST AI adlı önceki projede tek hisse üzerinde klasik gösterge tabanlı (RSI/MACD vb.) alım-satım zamanlaması genişçe test edildi ve gerçek bir kenar (edge) bulunamadı. Bulunan tek gerçek ipucu: hisseleri son dönem performanslarına göre sıralayıp güçlü olanlardan bir sepet kurmak (cross-sectional momentum) — hâlâ erken ama şimdiye kadarki en sağlam bulgu.

Bistogram bu bulgu üzerine, sıfırdan ve şu katmanlarla inşa ediliyor:

1. **Sepet motoru** — hisseleri sırala, güçlü sepeti kur, periyodik güncelle.
2. **Emsal/kıyas katmanı** — yeni halka arzları benzer geçmiş halka arzlarla kıyaslama.
3. **Temel + gündem katmanı** — sürekli güncellenen temel oranlar + haber/KAP taraması, AI ile yorumlanmış durum raporları.

Her katman bağımsız olarak kanıtlanmadan bir öncekinin üzerine binmez.

## Neden web sitesi formatında baştan?

Önceki projede arayüz en sona bırakılmıştı, ilerleme sadece konsol çıktısından takip edilebiliyordu. Bu sefer en başından basit bir canlı panel var, böylece her değişiklik anlık gözlemlenebiliyor.

## Çalıştırma

```
pip install -r requirements.txt
streamlit run app.py
```
