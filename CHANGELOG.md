# Değişiklik Günlüğü

Tüm önemli değişiklikler bu dosyada belgelenmektedir.

## [4.2.0] - 2026-08-28

### Eklenen
- V4 FINAL kompakt app.js (5KB)
- 64 shard'lı ters indeks yapısı
- Delta-encoded posting listeleri
- 500 chunk'lık karar metin yapısı
- Daire ve yıl filtreleri
- İlgililik ve tarih sıralaması

### Değiştirilen
- app.js tamamen yeniden yazıldı (kompakt versiyon)
- index.html basitleştirildi
- manifest.json güncellendi

### Korunan
- a-Shell mini uyumlu server.py (SafeTCPServer/QuietHandler)
- Türkçe karakter desteği
- 50.000 karar üzerinde arama

## [4.1.0] - 2024

### Eklenen
- Türkçe karakter desteği (İ/i, Ş/ş, Ğ/ğ, Ü/ü, Ö/ö, Ç/ç)
- Ters indeks yapısı
- Daire ve yıl filtreleri

## [4.0.0] - 2024

### Eklenen
- İlk ters indeks tabanlı arama motoru
- 50.000 Yargıtay ceza kararı
- Safari uyumlu JavaScript arama motoru

## [3.x.x] - 2023

### Önceki Sürümler
- Temel arama fonksiyonları
- SQLite tabanlı arama
- Masaüstü desteği
