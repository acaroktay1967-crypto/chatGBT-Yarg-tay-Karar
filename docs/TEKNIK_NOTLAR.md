# Teknik Notlar

Bu doküman Hukukİçtihat+ Ceza V4 uygulamasının teknik detaylarını açıklar.

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
│    │  Arama      │   Shard      │   UI            │     │
│    │  Motoru     │   Yönetimi   │   Fonksiyonları │     │
│    └─────────────┴──────────────┴─────────────────┘     │
└─────────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ meta.json   │ │ index/      │ │ docs/       │
│ (6.4 MB)    │ │ i-00..i-63  │ │ d-000..499  │
│ 50K kayıt   │ │ 64 shard    │ │ 500 chunk   │
└─────────────┘ └─────────────┘ └─────────────┘
```

## Ters İndeks Yapısı

### Shard Sistemi

64 shard'a bölünmüş indeks yapısı. Her kelime hash fonksiyonuyla bir shard'a atanır:

```javascript
function shard(tok) {
    let h = 5381;
    for (const ch of tok) {
        h = (((h << 5) + h) + ch.codePointAt(0)) >>> 0;
    }
    return h % 64;
}
```

### Delta Encoding

Posting listeleri delta-encoded olarak saklanır (yer tasarrufu):

```json
// Orijinal: [5, 12, 15, 28]
// Delta:    [5, 7, 3, 13]
{
    "hırsızlık": [5, 7, 3, 13],
    "kasten": [2, 10, 5, 8]
}
```

Decode fonksiyonu:

```javascript
function decode(a) {
    let x = 0;
    return a.map(d => (x += d));
}
```

### Arama Algoritması

1. **Tokenizasyon**: Sorgu kelimelere ayrılır (min 3 karakter)
2. **Shard Belirleme**: Her kelime için shard hesaplanır
3. **Posting Listesi**: İlgili shard'dan posting listesi alınır
4. **Delta Decode**: Posting listesi decode edilir
5. **Kesişim (AND)**: Tüm kelimelerin geçtiği dokümanlar bulunur
6. **Skorlama**: Metin içinde kelime frekansına göre sıralama

## Türkçe Karakter Desteği

### Lowercase Fonksiyonu

```javascript
const low = s => String(s || "")
    .replaceAll("İ", "i")
    .replaceAll("I", "ı")
    .toLocaleLowerCase("tr-TR");
```

### Tokenizasyon

```javascript
function toks(s) {
    const a = low(s).match(/[0-9a-zçğıöşü]+/g) || [];
    return [...new Set(a.filter(x => x.length >= 3))];
}
```

## Veri Yapıları

### manifest.json

```json
{
    "count": 50000,
    "index_shards": 64,
    "doc_chunk": 100,
    "doc_chunks": 500,
    "year_min": 2020,
    "year_max": 2020,
    "version": "4.1-final"
}
```

### meta.json

50.000 karar için meta veri dizisi:

```json
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

### index/i-XX.json (64 dosya)

Her shard'da kelime -> delta-encoded posting listesi:

```json
{
    "hırsızlık": [5, 7, 3, 13, ...],
    "kasten": [2, 10, 5, 8, ...],
    ...
}
```

### docs/d-XXX.json (500 dosya)

Her chunk'ta 100 karar metni:

```json
[
    {"id": 1, "text": "T.C. YARGITAY 1. Ceza Dairesi..."},
    {"id": 2, "text": "T.C. YARGITAY 2. Ceza Dairesi..."},
    ...
]
```

## a-Shell mini Uyumluluğu

### Sorunlar

a-Shell mini iOS sandbox ortamında çalışırken bazı Python HTTP server sorunları yaşanır:

1. **NoneType client_address**: Bazen `client_address` None olarak gelir
2. **BrokenPipeError**: Bağlantı koptuğunda hata fırlatılır
3. **ConnectionResetError**: İstemci bağlantıyı aniden kapatır

### Çözüm: server.py

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

### Lazy Loading

- Shard'lar sadece ihtiyaç duyulduğunda yüklenir
- Doküman chunk'ları sadece görüntülendiğinde yüklenir
- Yüklenen veriler bellekte önbelleğe alınır

```javascript
const IDX = new Map();  // Shard önbelleği
const DOC = new Map();  // Doküman önbelleği

async function getIdx(s) {
    if (IDX.has(s)) return IDX.get(s);
    const r = await fetch(`index/i-${String(s).padStart(2, "0")}.json`);
    const d = await r.json();
    IDX.set(s, d);
    return d;
}
```

### Kesişim Optimizasyonu

En kısa posting listesiyle başlanır:

```javascript
lists.sort((a, b) => a.length - b.length);
ids = lists[0];
for (let i = 1; i < lists.length; i++) {
    ids = intersect(ids, lists[i]);
    if (!ids.length) break;  // Erken çıkış
}
```

## Veri Boyutları

| Dosya/Klasör | Boyut |
|--------------|-------|
| meta.json | ~6.4 MB |
| index/ (64 shard) | ~15 MB |
| docs/ (500 chunk) | ~85 MB |
| **Toplam** | ~106 MB |

## Güvenlik Notları

1. **CORS**: Yerel sunucu tüm originlere izin verir
2. **XSS**: Kullanıcı girdileri escape edilir
3. **Veri Gizliliği**: Tüm veriler yerel kalır, sunucuya gönderilmez

## Hata Ayıklama

### Console Logları

Tarayıcı konsolunda:
- Shard yükleme hataları
- Doküman yükleme hataları
- Arama sonuç sayısı

### a-Shell Logları

Terminal çıktısında:
- HTTP istekleri
- Bağlantı hataları (genellikle zararsız)
