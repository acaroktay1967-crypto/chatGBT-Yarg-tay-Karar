# Hukukİçtihat+ Ceza

iPhone ve masaüstü için Yargıtay karar arama motoru.

## Özellikler

- 50.000 karar üzerinde yerel arama
- Ters indeks tabanlı hızlı arama
- Türkçe tam metin arama (İ/i, Ş/ş, Ğ/ğ, Ü/ü, Ö/ö, Ç/ç desteği)
- Daire filtresi
- Yıl filtresi
- İlgililik sıralaması
- En yeni karar sıralaması
- Tam Kararı Aç
- Korpustan Çek ve Kaydet
- iPhone IndexedDB yerel karar arşivi
- Kaydedilenler ekranı
- JSON olarak dışa aktarma
- a-Shell mini desteği
- GitHub gerektirmeden iPhone üzerinde yerel çalışma

## Mimari

```
Hugging Face Yargıtay korpusu
        ↓
Python veri hazırlama (tools/)
        ↓
SQLite / FTS5
        ↓
JSON ters indeks
        ↓
Safari JavaScript arama motoru (app.js)
        ↓
IndexedDB kişisel karar arşivi
```

## Dosya Yapısı

```
/
├── index.html          # Ana HTML arayüzü
├── app.js              # Arama motoru ve UI JavaScript
├── server.py           # a-Shell mini uyumlu HTTP sunucu
├── manifest.json       # PWA manifest
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
├── index/              # [GIT HARİCİ] Ters indeks dosyaları
│   ├── inverted_index.json
│   └── doc_meta.json
│
└── docs/               # [GIT HARİCİ] Karar metin dosyaları
    └── *.txt
```

## Kurulum

### Gereksinimler

- Python 3.8+
- iOS: a-Shell mini (App Store'dan)
- Masaüstü: Herhangi bir modern tarayıcı

### Masaüstü Kurulum

1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/acaroktay1967-crypto/chatGBT-Yarg-tay-Karar.git
   cd chatGBT-Yarg-tay-Karar
   ```

2. Veri hazırlayın (ilk seferde):
   ```bash
   cd tools
   python3 hf_yargitay_to_iphone.py
   python3 build_index.py
   ```

3. Sunucuyu başlatın:
   ```bash
   python3 server.py
   ```

4. Tarayıcıda açın:
   ```
   http://127.0.0.1:8000
   ```

### iPhone Kurulum (a-Shell mini)

1. Proje klasörünü iPhone'a aktarın (iCloud, AirDrop, vb.)

2. a-Shell mini uygulamasını açın

3. Proje klasörüne gidin:
   ```bash
   cd /path/to/chatGBT-Yarg-tay-Karar
   ```

4. Sunucuyu başlatın:
   ```bash
   python3 server.py
   ```

5. Safari'de açın:
   ```
   http://127.0.0.1:8000
   ```

**ÖNEMLİ:** Standart `python3 -m http.server` kullanmayın. 
`server.py` dosyası a-Shell mini'nin iOS sandbox ortamında oluşan özel hataları
(NoneType client_address, BrokenPipeError, ConnectionResetError) tolere edecek 
şekilde tasarlanmıştır.

## Kullanım

### Arama

1. Arama kutusuna anahtar kelimeler girin (örn: "hırsızlık", "kasten yaralama")
2. İsteğe bağlı filtreleri ayarlayın:
   - **Daire:** Belirli bir Yargıtay dairesi
   - **Yıl:** Başlangıç ve bitiş yılı
   - **Sıralama:** İlgililik veya tarih
3. "Ara" butonuna tıklayın

### Karar Kaydetme

1. Arama sonuçlarında "Kaydet" butonuna tıklayın
2. Karar IndexedDB'ye (yerel depolama) kaydedilir
3. İnternet bağlantısı olmadan erişilebilir

### Kaydedilenleri Görüntüleme

1. "Kaydedilenler" butonuna tıklayın
2. Kayıtlı kararları listeleyin
3. "Görüntüle" veya "Sil" işlemlerini yapın

### JSON Dışa Aktarma

1. "JSON Dışa Aktar" butonuna tıklayın
2. Tüm kayıtlı kararlar JSON formatında indirilir
3. Yedekleme veya başka uygulamalarda kullanım için

## Teknik Detaylar

### Ters İndeks Yapısı

```json
{
    "kelime": [[docId, termFrequency], ...],
    ...
}
```

### Doküman Meta Yapısı

```json
{
    "docId": {
        "daire": "1. Ceza Dairesi",
        "esas": "2023/1234",
        "karar": "2023/5678",
        "tarih": "15.03.2023",
        "ozet": "...",
        "dosyaAdi": "1234.txt"
    }
}
```

### IndexedDB Yapısı

- **Veritabanı:** HukukIctihatArsiv
- **Object Store:** kararlar
- **Indeksler:** daire, tarih, savedAt

## Sürüm Bilgisi

- **Versiyon:** 4.2.0
- **Karar Sayısı:** ~50.000
- **Kapsam:** Yargıtay Ceza Daireleri (2020-2026)
- **Kaynak:** Hugging Face Yargıtay Korpusu

## Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/yenilik`)
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik eklendi'`)
4. Branch'i push edin (`git push origin feature/yenilik`)
5. Pull Request açın

## Lisans

Bu proje eğitim ve araştırma amaçlıdır. Yargıtay kararları kamuya açık belgelerdir.

## İletişim

GitHub Issues üzerinden soru ve önerilerinizi iletebilirsiniz.
