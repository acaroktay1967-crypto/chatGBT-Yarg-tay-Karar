# Hukukİçtihat+ Ceza

iPhone ve masaüstü için Yargıtay karar arama motoru.

## Özellikler

- 50.000 karar üzerinde yerel arama
- Ters indeks tabanlı hızlı arama (64 shard)
- Türkçe tam metin arama (İ/i, Ş/ş, Ğ/ğ, Ü/ü, Ö/ö, Ç/ç desteği)
- Daire filtresi
- Yıl filtresi
- İlgililik sıralaması
- En yeni karar sıralaması
- Tam Kararı Aç
- a-Shell mini desteği
- GitHub gerektirmeden iPhone üzerinde yerel çalışma

## Mimari

```
Hugging Face Yargıtay korpusu
        ↓
Python veri hazırlama (tools/)
        ↓
JSON ters indeks (64 shard)
        ↓
Safari JavaScript arama motoru (app.js)
```

## Dosya Yapısı

```
/
├── index.html          # Ana HTML arayüzü
├── app.js              # Arama motoru JavaScript
├── server.py           # a-Shell mini uyumlu HTTP sunucu
├── manifest.json       # Uygulama manifest
├── README.md           # Bu dosya
├── CHANGELOG.md        # Sürüm geçmişi
├── VERSION             # Sürüm numarası
├── .gitignore          # Git hariç tutma listesi
│
├── tools/
│   ├── hf_yargitay_to_iphone.py   # HuggingFace veri çekme
│   └── build_index.py              # Ters indeks oluşturma
│
├── docs/
│   ├── TEKNIK_NOTLAR.md    # Teknik dokümantasyon
│   └── IPHONE_KURULUM.md   # iPhone kurulum kılavuzu
│
├── meta.json           # [GIT HARİCİ] Karar meta verileri (6.4 MB)
├── index/              # [GIT HARİCİ] Ters indeks dosyaları (64 shard)
│   └── i-00.json ... i-63.json
│
└── docs/               # [GIT HARİCİ] Karar metin dosyaları (500 chunk)
    └── d-000.json ... d-499.json
```

## iPhone Çalıştırma (a-Shell mini)

1. ZIP paketini iPhone'a aktarın (iCloud, AirDrop, vb.)
2. Dosyalar uygulamasında ZIP'i açın
3. a-Shell mini'yi açın ve şunu çalıştırın:
   ```bash
   pickFolder
   ```
4. Açılan listeden HukukIctihat klasörünü seçin
5. Sunucuyu başlatın:
   ```bash
   python3 server.py
   ```
   veya:
   ```bash
   python3 -m http.server 8000
   ```
6. Safari'de açın:
   ```
   http://127.0.0.1:8000
   ```

**Beklenen:** "50.000 karar hazır." mesajı

**Not:** ConnectionResetError veya BrokenPipeError mesajları Safari bir isteği yarıda kestiğinde görülebilir. Sayfa ve arama çalışıyorsa bunlar kritik değildir.

## Masaüstü Kurulum

1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/acaroktay1967-crypto/chatGBT-Yarg-tay-Karar.git
   cd chatGBT-Yarg-tay-Karar
   ```

2. Veri paketini indirin ve açın (meta.json, index/, docs/ dosyaları)

3. Sunucuyu başlatın:
   ```bash
   python3 server.py
   ```

4. Tarayıcıda açın:
   ```
   http://127.0.0.1:8000
   ```

## Kullanım

### Arama

1. Arama kutusuna anahtar kelimeler girin:
   - Örnek: "olası kast"
   - Örnek: "uyuşturucu"
   - Örnek: "HTS"
   - Örnek: "2019/3931"
2. Filtreleri ayarlayın:
   - **Daire:** "1. Ceza" gibi
   - **Karar Yılı:** 2020, 2021, vb.
   - **Sıralama:** İlgililik veya En yeni tarih
3. "ARA" butonuna tıklayın

### Tam Kararı Görüntüleme

1. Arama sonuçlarında "Tam Kararı Aç" butonuna tıklayın
2. Karar metninin tamamı gösterilir

## Teknik Detaylar

### Ters İndeks Yapısı

64 shard'a bölünmüş delta-encoded posting listeleri:

```json
// index/i-XX.json
{
    "kelime": [delta1, delta2, delta3, ...],
    ...
}
```

### Meta Veri Yapısı

```json
// meta.json
[
    {
        "row_id": 1,
        "court": "1. Ceza Dairesi",
        "esas_no": "2020/1234",
        "karar_no": "2020/5678",
        "karar_tarihi": "2020-03-15",
        "year": 2020
    },
    ...
]
```

### Karar Metinleri

100'er kayıt içeren chunk dosyaları:

```json
// docs/d-XXX.json
[
    {"id": 1, "text": "Tam karar metni..."},
    ...
]
```

## Sürüm Bilgisi

- **Versiyon:** 4.3.0
- **Karar Sayısı:** 100.000
- **İndeks Shard:** 64
- **Doküman Chunk:** 500
- **Kapsam:** Yargıtay Ceza Daireleri (2020)
- **Kaynak:** Hugging Face Yargıtay Korpusu

## Lisans

Bu proje eğitim ve araştırma amaçlıdır. Yargıtay kararları kamuya açık belgelerdir.

## İletişim

GitHub Issues üzerinden soru ve önerilerinizi iletebilirsiniz.
