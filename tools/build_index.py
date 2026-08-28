#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ters İndeks Oluşturucu

Bu script metin dosyalarından ters indeks oluşturur.
Oluşturulan indeks JavaScript arama motoru tarafından kullanılır.

Kullanım:
    python3 build_index.py [--docs-dir DIR] [--output-dir DIR]

Çıktı:
    - index/inverted_index.json: Ters indeks
    - index/doc_meta.json: Doküman meta verileri

Gereksinimler:
    - Python 3.8+
    - tqdm (opsiyonel, ilerleme çubuğu için)
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from collections import defaultdict

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("tqdm yüklü değil, ilerleme çubuğu gösterilmeyecek.")


# Türkçe karakter dönüşüm tablosu
TR_LOWER_MAP = {
    'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 
    'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç'
}

# Türkçe stop words (yaygın, anlamsız kelimeler)
STOP_WORDS = {
    've', 'veya', 'ile', 'için', 'de', 'da', 'den', 'dan',
    'bir', 'bu', 'şu', 'o', 'ne', 'ki', 'mi', 'mı', 'mu', 'mü',
    'ise', 'gibi', 'kadar', 'daha', 'en', 'hem', 'ya', 'ancak',
    'fakat', 'lakin', 'ama', 'oysa', 'halbuki', 'çünkü', 'zira',
    'üzere', 'göre', 'karşı', 'rağmen', 'dolayı', 'ötürü',
    'olan', 'olarak', 'olup', 'olmak', 'olmuş', 'olduğu',
    'edilmiş', 'edilmek', 'edilen', 'edildiği', 'edilir',
    'yapılmış', 'yapılmak', 'yapılan', 'yapılır',
    'sanık', 'sanığın', 'sanığa', 'sanıklar', 'sanıkların',
    'mahkeme', 'mahkemesi', 'mahkemece', 'mahkemesince',
    'karar', 'kararı', 'kararın', 'kararına',
    'ceza', 'cezası', 'cezanın', 'cezaya',
    'yargıtay', 'daire', 'dairesi',
    'madde', 'maddesi', 'maddenin',
    'yıl', 'ay', 'gün',
    'tarih', 'tarihli', 'tarihinde',
    'sayılı', 'numaralı',
}

# Minimum kelime uzunluğu
MIN_WORD_LENGTH = 2


def turkish_lower(text):
    """Türkçe karakterleri doğru şekilde küçük harfe çevirir."""
    if not text:
        return ""
    result = []
    for ch in text:
        if ch in TR_LOWER_MAP:
            result.append(TR_LOWER_MAP[ch])
        else:
            result.append(ch.lower())
    return "".join(result)


def tokenize(text):
    """
    Metni kelimelere ayırır.
    Türkçe karakterleri korur, noktalama işaretlerini kaldırır.
    """
    # Küçük harfe çevir
    text = turkish_lower(text)
    
    # Kelime olmayan karakterleri boşlukla değiştir
    text = re.sub(r'[^\wıİşŞğĞüÜöÖçÇ]+', ' ', text)
    
    # Kelimelere ayır
    words = text.split()
    
    # Filtrele
    tokens = []
    for word in words:
        # Minimum uzunluk kontrolü
        if len(word) < MIN_WORD_LENGTH:
            continue
        # Sadece sayı olanları atla
        if word.isdigit():
            continue
        # Stop words kontrolü
        if word in STOP_WORDS:
            continue
        tokens.append(word)
    
    return tokens


def parse_doc_file(filepath):
    """
    Karar dosyasını parse eder.
    Başlık bilgilerini ve metni ayırır.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Dosya okuma hatası {filepath}: {e}")
        return None, ""
    
    lines = content.split('\n')
    
    metadata = {
        'daire': '',
        'esas': '',
        'karar': '',
        'tarih': '',
        'yil': None,
        'ozet': '',
        'dosyaAdi': os.path.basename(filepath)
    }
    
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith('Daire:'):
            metadata['daire'] = line.replace('Daire:', '').strip()
        elif line.startswith('Esas No:'):
            metadata['esas'] = line.replace('Esas No:', '').strip()
        elif line.startswith('Karar No:'):
            metadata['karar'] = line.replace('Karar No:', '').strip()
        elif line.startswith('Tarih:'):
            metadata['tarih'] = line.replace('Tarih:', '').strip()
            # Yılı çıkar
            year_match = re.search(r'(\d{4})', metadata['tarih'])
            if year_match:
                metadata['yil'] = int(year_match.group(1))
        elif line.startswith('-' * 10):
            body_start = i + 1
            break
    
    # Gövde metni
    body_text = '\n'.join(lines[body_start:]).strip()
    
    # Özet (ilk 500 karakter)
    clean_body = ' '.join(body_text.split())
    metadata['ozet'] = clean_body[:500] + '...' if len(clean_body) > 500 else clean_body
    
    return metadata, body_text


def build_inverted_index(docs_dir, output_dir):
    """
    Ters indeks oluşturur.
    """
    docs_path = Path(docs_dir)
    output_path = Path(output_dir)
    
    # Çıktı dizinini oluştur
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Tüm .txt dosyalarını bul
    doc_files = sorted(docs_path.glob('*.txt'))
    
    if not doc_files:
        print(f"Hata: {docs_dir} dizininde .txt dosyası bulunamadı.")
        return
    
    print(f"Bulunan dosya sayısı: {len(doc_files)}")
    
    # Ters indeks: kelime -> [(doc_id, frequency), ...]
    inverted_index = defaultdict(list)
    
    # Doküman meta verileri: doc_id -> metadata
    doc_metadata = {}
    
    # İlerleme çubuğu
    if HAS_TQDM:
        file_iter = tqdm(doc_files, desc="İndeksleniyor")
    else:
        file_iter = doc_files
        print("İndeksleme başlıyor...")
    
    for doc_file in file_iter:
        # Dosya adından doc_id çıkar
        try:
            doc_id = int(doc_file.stem)
        except ValueError:
            # Sayısal olmayan dosya adları için hash kullan
            doc_id = hash(doc_file.stem) % 1000000
        
        # Dosyayı parse et
        metadata, body_text = parse_doc_file(doc_file)
        
        if metadata is None:
            continue
        
        # Meta veriyi kaydet
        doc_metadata[doc_id] = metadata
        
        # Metni tokenize et
        tokens = tokenize(body_text)
        
        # Kelime frekanslarını hesapla
        word_freq = defaultdict(int)
        for token in tokens:
            word_freq[token] += 1
        
        # Ters indekse ekle
        for word, freq in word_freq.items():
            inverted_index[word].append([doc_id, freq])
    
    if not HAS_TQDM:
        print("İndeksleme tamamlandı.")
    
    # İstatistikler
    print(f"\nİstatistikler:")
    print(f"  Toplam doküman: {len(doc_metadata)}")
    print(f"  Benzersiz kelime: {len(inverted_index)}")
    
    # En sık geçen 20 kelime
    top_words = sorted(
        inverted_index.items(), 
        key=lambda x: sum(p[1] for p in x[1]), 
        reverse=True
    )[:20]
    
    print(f"\nEn sık kelimeler:")
    for word, postings in top_words:
        total_freq = sum(p[1] for p in postings)
        doc_count = len(postings)
        print(f"  {word}: {total_freq} kez, {doc_count} dokümanda")
    
    # Ters indeksi JSON'a yaz
    index_file = output_path / 'inverted_index.json'
    print(f"\nTers indeks yazılıyor: {index_file}")
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(dict(inverted_index), f, ensure_ascii=False)
    
    # Meta verileri JSON'a yaz
    meta_file = output_path / 'doc_meta.json'
    print(f"Meta veriler yazılıyor: {meta_file}")
    
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(doc_metadata, f, ensure_ascii=False)
    
    # Dosya boyutları
    index_size = index_file.stat().st_size / (1024 * 1024)
    meta_size = meta_file.stat().st_size / (1024 * 1024)
    
    print(f"\nDosya boyutları:")
    print(f"  inverted_index.json: {index_size:.2f} MB")
    print(f"  doc_meta.json: {meta_size:.2f} MB")
    
    return dict(inverted_index), doc_metadata


def main():
    parser = argparse.ArgumentParser(
        description="Ters indeks oluşturur."
    )
    parser.add_argument(
        "--docs-dir",
        default=None,
        help="Doküman dizini (varsayılan: ../docs)"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Çıktı dizini (varsayılan: ../index)"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Sadece istatistikleri göster, indeks oluşturma"
    )
    
    args = parser.parse_args()
    
    # Varsayılan dizinler
    base_dir = Path(__file__).parent.parent
    docs_dir = Path(args.docs_dir) if args.docs_dir else base_dir / "docs"
    output_dir = Path(args.output_dir) if args.output_dir else base_dir / "index"
    
    print("=" * 50)
    print("Ters İndeks Oluşturucu")
    print("Hukukİçtihat+ Ceza V4.2")
    print("=" * 50)
    print()
    print(f"Doküman dizini: {docs_dir}")
    print(f"Çıktı dizini: {output_dir}")
    print()
    
    if not docs_dir.exists():
        print(f"Hata: Doküman dizini bulunamadı: {docs_dir}")
        print("Önce hf_yargitay_to_iphone.py çalıştırın.")
        sys.exit(1)
    
    if args.stats_only:
        doc_files = list(docs_dir.glob('*.txt'))
        print(f"Doküman sayısı: {len(doc_files)}")
        
        if doc_files:
            total_size = sum(f.stat().st_size for f in doc_files)
            print(f"Toplam boyut: {total_size / (1024 * 1024):.2f} MB")
    else:
        build_inverted_index(docs_dir, output_dir)
    
    print("\nİşlem tamamlandı!")


if __name__ == "__main__":
    main()
