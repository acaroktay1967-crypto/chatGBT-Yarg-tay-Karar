#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hugging Face'ten 2024-2025-2026 Yargıtay Ceza Kararlarını Çekme

Bu script hamzabagirsakci/turkish-court-decisions datasetinden
Yargıtay Ceza Dairesi kararlarını çeker ve V4 formatına dönüştürür.

Dataset: 9.8 milyon Yargıtay kararı (1997-2026)

Kullanım:
    python3 fetch_yargitay_2024_2026.py --years 2024,2025,2026 --limit 100000

Gereksinimler:
    pip install datasets tqdm
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from collections import defaultdict

try:
    from datasets import load_dataset
    from tqdm import tqdm
except ImportError:
    print("Gerekli paketler yüklü değil.")
    print("Yüklemek için: pip install datasets tqdm")
    sys.exit(1)


# Hugging Face dataset
HF_DATASET = "hamzabagirsakci/turkish-court-decisions"
HF_CONFIG = "yargitay"  # Sadece Yargıtay kararları

# Ceza Daireleri
CEZA_DAIRELERI = [
    "1. Ceza Dairesi", "2. Ceza Dairesi", "3. Ceza Dairesi",
    "4. Ceza Dairesi", "5. Ceza Dairesi", "6. Ceza Dairesi",
    "7. Ceza Dairesi", "8. Ceza Dairesi", "9. Ceza Dairesi",
    "10. Ceza Dairesi", "11. Ceza Dairesi", "12. Ceza Dairesi",
    "13. Ceza Dairesi", "14. Ceza Dairesi", "15. Ceza Dairesi",
    "16. Ceza Dairesi", "17. Ceza Dairesi", "18. Ceza Dairesi",
    "19. Ceza Dairesi", "20. Ceza Dairesi", "21. Ceza Dairesi",
    "Ceza Genel Kurulu", "CGK"
]


def is_ceza_dairesi(court):
    """Ceza dairesi mi kontrol eder."""
    if not court:
        return False
    court_lower = court.lower()
    return "ceza" in court_lower


def shard(tok):
    """Kelime için shard numarası hesaplar (app.js ile uyumlu)."""
    h = 5381
    for ch in tok:
        h = (((h << 5) + h) + ord(ch)) & 0xFFFFFFFF
    return h % 64


def tokenize(text):
    """Metni tokenize eder (Türkçe uyumlu)."""
    if not text:
        return []
    
    # Türkçe lowercase
    text = text.replace("İ", "i").replace("I", "ı")
    text = text.lower()
    
    # Kelimeleri çıkar
    tokens = re.findall(r'[0-9a-zçğıöşü]+', text)
    
    # Min 3 karakter, unique
    tokens = list(set(t for t in tokens if len(t) >= 3))
    return tokens


def build_v4_format(records, output_dir):
    """
    V4 formatında çıktı oluşturur:
    - meta.json: Tüm meta veriler
    - index/i-XX.json: 64 shard'lı ters indeks
    - docs/d-XXX.json: 100'er kayıtlık chunk'lar
    """
    output_dir = Path(output_dir)
    index_dir = output_dir / "index"
    docs_dir = output_dir / "docs"
    
    index_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nV4 formatı oluşturuluyor...")
    print(f"Çıktı: {output_dir}")
    
    # Meta veriler
    meta_list = []
    
    # Ters indeks (shard -> kelime -> [doc_ids])
    inverted_index = defaultdict(lambda: defaultdict(list))
    
    # Doküman chunk'ları
    doc_chunks = []
    current_chunk = []
    chunk_size = 100
    
    for i, record in enumerate(tqdm(records, desc="V4 formatı oluşturuluyor")):
        row_id = i + 1
        
        # Meta veri
        meta = {
            "row_id": row_id,
            "court": record.get("court", ""),
            "esas_no": record.get("esas_no", ""),
            "karar_no": record.get("karar_no", ""),
            "karar_tarihi": record.get("karar_tarihi", ""),
            "year": record.get("year", 0)
        }
        meta_list.append(meta)
        
        # Metin
        text = record.get("text", "")
        
        # Ters indeks oluştur
        tokens = tokenize(text)
        for tok in tokens:
            s = shard(tok)
            inverted_index[s][tok].append(row_id)
        
        # Doküman chunk'ına ekle
        current_chunk.append({"id": row_id, "text": text})
        
        if len(current_chunk) >= chunk_size:
            doc_chunks.append(current_chunk)
            current_chunk = []
    
    # Son chunk
    if current_chunk:
        doc_chunks.append(current_chunk)
    
    # meta.json yaz
    print("meta.json yazılıyor...")
    with open(output_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta_list, f, ensure_ascii=False)
    
    # manifest.json yaz
    manifest = {
        "count": len(meta_list),
        "index_shards": 64,
        "doc_chunk": chunk_size,
        "doc_chunks": len(doc_chunks),
        "year_min": min(m["year"] for m in meta_list if m["year"]),
        "year_max": max(m["year"] for m in meta_list if m["year"]),
        "version": "4.3-2024-2026"
    }
    with open(output_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    
    # Ters indeks shard'larını yaz (delta-encoded)
    print("İndeks shard'ları yazılıyor...")
    for s in tqdm(range(64), desc="Shard"):
        shard_data = {}
        for tok, doc_ids in inverted_index[s].items():
            # Sırala ve delta-encode
            sorted_ids = sorted(set(doc_ids))
            if sorted_ids:
                deltas = [sorted_ids[0]]
                for i in range(1, len(sorted_ids)):
                    deltas.append(sorted_ids[i] - sorted_ids[i-1])
                shard_data[tok] = deltas
        
        shard_file = index_dir / f"i-{s:02d}.json"
        with open(shard_file, "w", encoding="utf-8") as f:
            json.dump(shard_data, f, ensure_ascii=False)
    
    # Doküman chunk'larını yaz
    print("Doküman chunk'ları yazılıyor...")
    for i, chunk in enumerate(tqdm(doc_chunks, desc="Chunk")):
        chunk_file = docs_dir / f"d-{i:03d}.json"
        with open(chunk_file, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False)
    
    print(f"\nTamamlandı!")
    print(f"  Toplam karar: {len(meta_list)}")
    print(f"  İndeks shard: 64")
    print(f"  Doküman chunk: {len(doc_chunks)}")
    
    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Hugging Face'ten Yargıtay Ceza kararlarını çeker."
    )
    parser.add_argument(
        "--years",
        default="2024,2025,2026",
        help="Çekilecek yıllar (virgülle ayrılmış)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maksimum karar sayısı"
    )
    parser.add_argument(
        "--output-dir",
        default="./output_v4",
        help="Çıktı dizini"
    )
    parser.add_argument(
        "--include-all-years",
        action="store_true",
        help="Tüm yılları dahil et (2020-2026)"
    )
    
    args = parser.parse_args()
    
    # Yılları parse et
    if args.include_all_years:
        target_years = set(range(2020, 2027))
    else:
        target_years = set(int(y.strip()) for y in args.years.split(","))
    
    print("=" * 60)
    print("Hugging Face Yargıtay Ceza Kararları Çekici")
    print("=" * 60)
    print(f"Dataset: {HF_DATASET}")
    print(f"Config: {HF_CONFIG}")
    print(f"Hedef yıllar: {sorted(target_years)}")
    print(f"Limit: {args.limit or 'Yok'}")
    print()
    
    print("Dataset yükleniyor (bu biraz sürebilir)...")
    
    try:
        # Streaming modda yükle (bellek tasarrufu)
        dataset = load_dataset(
            HF_DATASET, 
            HF_CONFIG, 
            split="train",
            streaming=True
        )
    except Exception as e:
        print(f"Dataset yükleme hatası: {e}")
        sys.exit(1)
    
    print("Ceza dairesi kararları filtreleniyor...")
    
    filtered_records = []
    total_scanned = 0
    
    for record in tqdm(dataset, desc="Taranıyor"):
        total_scanned += 1
        
        # Yıl kontrolü
        year = record.get("year", 0)
        if year not in target_years:
            continue
        
        # Ceza dairesi kontrolü
        court = record.get("court", "")
        if not is_ceza_dairesi(court):
            continue
        
        # Metin kontrolü
        text = record.get("text", "")
        if len(text) < 500:  # Çok kısa metinleri atla
            continue
        
        filtered_records.append(record)
        
        # Limit kontrolü
        if args.limit and len(filtered_records) >= args.limit:
            break
        
        # İlerleme göster
        if len(filtered_records) % 10000 == 0:
            print(f"  {len(filtered_records)} ceza kararı bulundu...")
    
    print(f"\nToplam taranan: {total_scanned}")
    print(f"Ceza kararları: {len(filtered_records)}")
    
    if not filtered_records:
        print("Hiç karar bulunamadı!")
        sys.exit(1)
    
    # Yıllara göre dağılım
    year_counts = defaultdict(int)
    for r in filtered_records:
        year_counts[r.get("year", 0)] += 1
    
    print("\nYıllara göre dağılım:")
    for year in sorted(year_counts.keys()):
        print(f"  {year}: {year_counts[year]} karar")
    
    # V4 formatında kaydet
    build_v4_format(filtered_records, args.output_dir)
    
    print(f"\nÇıktı dizini: {args.output_dir}")
    print("iPhone'a aktarmak için bu klasörü ZIP'leyin.")


if __name__ == "__main__":
    main()
