# iPhone Kurulum Kılavuzu

Bu kılavuz Hukukİçtihat+ Ceza V4.2 uygulamasını iPhone'da nasıl kuracağınızı ve kullanacağınızı açıklar.

## Gereksinimler

- iPhone (iOS 14.0 veya üstü)
- a-Shell mini uygulaması (App Store'dan ücretsiz)
- Safari tarayıcı
- Yeterli depolama alanı (~1-2 GB)

## Adım 1: a-Shell mini Kurulumu

1. App Store'u açın
2. "a-Shell mini" arayın
3. Ücretsiz olarak indirin ve kurun

**Not:** Tam sürüm "a-Shell" da kullanılabilir, ancak "a-Shell mini" daha hafiftir.

## Adım 2: Proje Dosyalarını iPhone'a Aktarma

### Seçenek A: iCloud Drive

1. Mac/PC'de proje klasörünü iCloud Drive'a kopyalayın
2. iPhone'da Dosyalar uygulamasını açın
3. iCloud Drive > proje klasörüne gidin
4. Tüm dosyaları iPhone'a indirin

### Seçenek B: AirDrop

1. Mac'te proje klasörünü seçin
2. Sağ tık > Paylaş > AirDrop
3. iPhone'unuzu seçin
4. iPhone'da kabul edin

### Seçenek C: Files App ile Aktarma

1. Proje klasörünü ZIP olarak sıkıştırın
2. E-posta veya mesaj ile kendinize gönderin
3. iPhone'da ZIP'i indirin ve açın
4. Dosyalar uygulamasında uygun konuma taşıyın

## Adım 3: a-Shell mini Yapılandırması

1. a-Shell mini uygulamasını açın
2. İlk açılışta terminal görünecek
3. Proje dizinine gidin:

```bash
cd ~/Documents/chatGBT-Yarg-tay-Karar
```

veya iCloud'daysa:

```bash
cd ~/Documents/iCloud/chatGBT-Yarg-tay-Karar
```

4. Dosyaları kontrol edin:

```bash
ls -la
```

Şunları görmelisiniz:
- `index.html`
- `app.js`
- `server.py`
- `manifest.json`
- `index/` (dizin)
- `docs/` (dizin)

## Adım 4: Veri Hazırlama (İlk Kurulum)

Eğer `index/` ve `docs/` dizinleri yoksa, veri oluşturmanız gerekir:

```bash
cd tools
python3 hf_yargitay_to_iphone.py --demo
python3 build_index.py
cd ..
```

**Not:** Demo mod 100 örnek karar oluşturur.
Gerçek 50.000 karar için `--demo` parametresini kaldırın.

## Adım 5: Sunucuyu Başlatma

```bash
python3 server.py
```

Başarılı başlatma çıktısı:

```
==================================================
Hukukİçtihat+ Ceza V4.2
a-Shell mini uyumlu HTTP Sunucusu
==================================================

Dizin: /path/to/project
Port: 8000

Tarayıcıda aç:
  http://127.0.0.1:8000
  http://localhost:8000

Durdurmak için: Ctrl+C
==================================================
```

## Adım 6: Safari'de Açma

1. Safari'yi açın
2. Adres çubuğuna yazın: `http://127.0.0.1:8000`
3. Enter tuşuna basın
4. Hukukİçtihat+ arayüzü açılacak

## Kullanım İpuçları

### Arama Yapma

1. Arama kutusuna anahtar kelimeler girin
   - Örnek: "hırsızlık"
   - Örnek: "kasten yaralama"
   - Örnek: "uyuşturucu madde"

2. Filtreleri ayarlayın:
   - **Daire:** Belirli bir Yargıtay dairesi seçin
   - **Yıl:** Başlangıç ve bitiş yılı belirleyin
   - **Sıralama:** İlgililik veya tarih

3. "Ara" butonuna tıklayın

### Karar Kaydetme

1. Arama sonuçlarında "Kaydet" butonuna tıklayın
2. Karar IndexedDB'ye (yerel depolama) kaydedilir
3. İnternet bağlantısı olmadan erişilebilir
4. Sunucu kapatılsa bile kayıtlı kararlar korunur

### Kaydedilenleri Görüntüleme

1. "Kaydedilenler" butonuna tıklayın
2. Tüm kayıtlı kararları listeleyin
3. "Görüntüle" ile tam metni okuyun
4. "Sil" ile gereksiz kararları kaldırın

### JSON Dışa Aktarma

1. "JSON Dışa Aktar" butonuna tıklayın
2. Tüm kayıtlı kararlar JSON dosyası olarak indirilir
3. Yedekleme için kullanın
4. Başka uygulamalara aktarın

## Sorun Giderme

### Sunucu Başlamıyor

**Sorun:** Port zaten kullanımda
```
Hata: Port 8000 zaten kullanımda.
```

**Çözüm:** Önceki sunucu işlemini kapatın veya a-Shell'i yeniden başlatın

### Safari Bağlanamıyor

**Sorun:** "Sayfa açılamıyor" hatası

**Çözüm:**
1. Sunucunun çalıştığından emin olun (a-Shell'de logları kontrol edin)
2. Adresi tam olarak yazın: `http://127.0.0.1:8000`
3. `https://` değil `http://` kullanın

### İndeks Yüklenemiyor

**Sorun:** "İndeks yüklenemedi" hatası

**Çözüm:**
1. `index/` dizininin var olduğunu kontrol edin
2. `inverted_index.json` ve `doc_meta.json` dosyalarını kontrol edin
3. Gerekirse `build_index.py` scriptini yeniden çalıştırın

### Dosya Bulunamadı

**Sorun:** Kararlar yüklenemiyor

**Çözüm:**
1. `docs/` dizininin var olduğunu kontrol edin
2. `.txt` dosyalarının bu dizinde olduğunu kontrol edin
3. Dosya izinlerini kontrol edin

## İleri Düzey: Arka Planda Çalıştırma

a-Shell mini uygulaması arka plana alındığında sunucu durabilir.
Uzun süreli kullanım için:

1. Safari'yi kullanırken a-Shell'i ön planda tutmaya çalışın
2. Split View kullanarak her iki uygulamayı da açık tutun
3. Gerekirse sunucuyu yeniden başlatın

## Depolama Yönetimi

Uygulama iki tür veri depolar:

1. **Proje dosyaları** (Files app'te):
   - `index/` ve `docs/` dizinleri
   - Kaynak kodlar

2. **IndexedDB verileri** (Safari'de):
   - Kaydedilen kararlar
   - Ayarlar

Safari verilerini temizlemek için:
- Ayarlar > Safari > Geçmişi ve Web Sitesi Verilerini Sil

## Güncelleme

Yeni sürüm çıktığında:

1. Yeni dosyaları indirin
2. Mevcut `index/` ve `docs/` dizinlerini koruyun
3. Kaynak kodları (`app.js`, `server.py`, vb.) güncelleyin
4. IndexedDB verileri (kaydedilen kararlar) korunur

## SSS

**S: İnternet bağlantısı gerekli mi?**
C: Hayır. Tüm veriler yerel olarak saklanır ve arama yerel olarak yapılır.

**S: Kaç karar kaydedebilirim?**
C: IndexedDB limitleri dahilinde binlerce karar kaydedebilirsiniz.

**S: Verilerimi nasıl yedeklerim?**
C: "JSON Dışa Aktar" özelliğini kullanın.

**S: Başka cihazda kullanabilir miyim?**
C: Evet, aynı proje dosyalarını ve JSON yedeğini kullanarak.
