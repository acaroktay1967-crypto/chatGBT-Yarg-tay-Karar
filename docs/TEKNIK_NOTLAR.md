# Teknik Notlar

Bu doküman Hukukİçtihat+ Ceza V4.2 uygulamasının teknik detaylarını açıklar.

## Mimari Genel Bakış

```
┌─────────────────────────────────────────────────────────┐
│                    KULLANICI                             │
│                  (Safari/Chrome)                         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   index.html                             │
│              (Arayüz ve Stil)                            │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    app.js                                │
│    ┌─────────────┬──────────────┬─────────────────┐     │
│    │  Arama      │   IndexedDB  │   UI            │     │
│    │  Motoru     │   İşlemleri  │   Fonksiyonları │     │
│    └─────────────┴──────────────┴─────────────────┘     │
└─────────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────────┐   ┌─────────────────────┐
│   index/            │   │   docs/             │
│   ├─ inverted_      │   │   ├─ 1.txt          │
│   │  index.json     │   │   ├─ 2.txt          │
│   └─ doc_meta.json  │   │   └─ ...            │
└─────────────────────┘   └─────────────────────┘
```

## Ters İndeks Yapısı

### Temel Konsept

Ters indeks, her kelime için o kelimenin geçtiği dokümanların listesini tutar.
Bu yapı, tam metin aramasını son derece hızlı hale getirir.

### JSON Formatı

```json
{
    "hırsızlık": [[1, 5], [23, 3], [156, 8]],
    "kasten": [[2, 2], [45, 1], [890, 4]],
    "yaralama": [[2, 1], [45, 1], [890, 3]]
}
```

Her eleman: `[doküman_id, terim_frekansı]`

### Arama Algoritması

1. **Tokenizasyon**: Sorgu kelimelere ayrılır
2. **Posting Listesi**: Her kelime için posting listesi alınır
3. **Kesişim (AND)**: Tüm kelimelerin geçtiği dokümanlar bulunur
4. **Skorlama**: Terim frekanslarına göre sıralama yapılır

```javascript
function search(query) {
    const tokens = tokenize(query);
    const postingLists = tokens.map(t => postings(index, t));
    const matchedDocs = intersectMultiple(postingLists);
    return matchedDocs.sort((a, b) => b.score - a.score);
}
```

## Türkçe Karakter Desteği

### Sorun

JavaScript'in `toLowerCase()` fonksiyonu Türkçe karakterleri doğru işlemez:
- `"İSTANBUL".toLowerCase()` = "i̇stanbul" (yanlış)
- `"IŞIK".toLowerCase()` = "ışık" (yanlış - büyük I küçük i olmalı)

### Çözüm

Özel Türkçe lowercase fonksiyonu:

```javascript
const TR_LOWER_MAP = {
    'İ': 'i', 'I': 'ı', 'Ş': 'ş', 
    'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç'
};

function turkishLowerCase(str) {
    let result = '';
    for (let ch of str) {
        result += TR_LOWER_MAP[ch] || ch.toLowerCase();
    }
    return result;
}
```

## IndexedDB Yapısı

### Veritabanı Şeması

```
Veritabanı: HukukIctihatArsiv
└── Object Store: kararlar
    ├── keyPath: id
    └── Indeksler:
        ├── daire (unique: false)
        ├── tarih (unique: false)
        └── savedAt (unique: false)
```

### Kayıt Formatı

```json
{
    "id": 12345,
    "daire": "1. Ceza Dairesi",
    "esas": "2023/1234",
    "karar": "2023/5678",
    "tarih": "15.03.2023",
    "ozet": "...",
    "content": "Tam karar metni...",
    "savedAt": "2024-01-15T10:30:00.000Z"
}
```

## a-Shell mini Uyumluluğu

### Sorunlar

a-Shell mini iOS sandbox ortamında çalışırken bazı Python HTTP server sorunları yaşanır:

1. **NoneType client_address**: Bazen `client_address` None olarak gelir
2. **BrokenPipeError**: Bağlantı koptuğunda hata fırlatılır
3. **ConnectionResetError**: İstemci bağlantıyı aniden kapatır

### Çözüm: SafeTCPServer

```python
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError):
            pass  # Sessizce geç

class SafeTCPServer(socketserver.TCPServer):
    def get_request(self):
        conn, addr = self.socket.accept()
        if addr is None:
            addr = ("127.0.0.1", 0)  # Varsayılan değer
        return conn, addr
```

## Performans Optimizasyonları

### İndeks Yükleme

- İndeks dosyaları sadece ilk aramada yüklenir
- Yüklenen indeks bellekte tutulur (memoization)

```javascript
let idx = null;
async function getIdx() {
    if (idx !== null) return idx;
    idx = await fetch('index/inverted_index.json').then(r => r.json());
    return idx;
}
```

### Kesişim Optimizasyonu

- En kısa posting listesiyle başlanır
- Erken çıkış: Kesişim boşsa döngü kesilir

```javascript
function intersectMultiple(lists) {
    lists.sort((a, b) => a.length - b.length);  // En kısa önce
    let result = lists[0];
    for (let list of lists.slice(1)) {
        result = intersect(result, list);
        if (result.length === 0) break;  // Erken çıkış
    }
    return result;
}
```

## Veri Boyutu Tahminleri

50.000 karar için yaklaşık boyutlar:

| Dosya | Boyut |
|-------|-------|
| inverted_index.json | 15-30 MB |
| doc_meta.json | 5-10 MB |
| docs/*.txt (toplam) | 500-1000 MB |

**Not:** Büyük veri dosyaları GitHub'a yüklenmez.
Kullanıcı kendi verilerini oluşturmalıdır.

## Güvenlik Notları

1. **CORS**: Sunucu tüm originlere izin verir (yerel kullanım için)
2. **XSS**: Kullanıcı girdileri escape edilir
3. **Veri Gizliliği**: Tüm veriler yerel kalır, sunucuya gönderilmez

## Hata Ayıklama

### Console Logları

```javascript
console.log('İndeks yüklendi:', Object.keys(idx).length, 'kelime');
console.log('Arama sonucu:', results.length, 'doküman');
```

### IndexedDB İnceleme

Safari: Geliştirici > Storage > IndexedDB
Chrome: DevTools > Application > IndexedDB

## Gelecek Geliştirmeler

- [ ] Web Worker ile arka plan arama
- [ ] Phrase arama (tırnak içi)
- [ ] Fuzzy matching (yaklaşık eşleşme)
- [ ] Otomatik tamamlama
- [ ] Offline PWA desteği
