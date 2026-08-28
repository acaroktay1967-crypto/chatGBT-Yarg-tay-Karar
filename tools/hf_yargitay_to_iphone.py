#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hugging Face Yargıtay Korpusu -> iPhone Veri Dönüştürücü

Bu script Hugging Face'ten Yargıtay ceza kararlarını çeker ve
iPhone/a-Shell mini için uygun formata dönüştürür.

Kullanım:
    python3 hf_yargitay_to_iphone.py [--limit N] [--output-dir DIR]

Gereksinimler:
    pip install datasets tqdm

Çıktı:
    - docs/*.txt: Her karar için ayrı metin dosyası
    - metadata.json: Tüm kararların meta verileri
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

try:
    from datasets import load_dataset
    from tqdm import tqdm
except ImportError:
    print("Gerekli paketler yüklü değil.")
    print("Yüklemek için: pip install datasets tqdm")
    sys.exit(1)


# Hugging Face dataset bilgileri
HF_DATASET = "mukayese/yargitay-kararlari"  # Örnek dataset adı
HF_SUBSET = "ceza"

# Türkçe karakter dönüşüm tablosu
TR_LOWER_MAP = {
    'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 
    'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç'
}


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


def clean_text(text):
    """Metin temizleme ve normalizasyon."""
    if not text:
        return ""
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text)
    # Başta ve sondaki boşlukları temizle
    text = text.strip()
    return text


def extract_metadata(record, doc_id):
    """
    Karar kaydından meta verileri çıkarır.
    Dataset yapısına göre bu fonksiyonu uyarlayın.
    """
    metadata = {
        "id": doc_id,
        "daire": "",
        "esas": "",
        "karar": "",
        "tarih": "",
        "yil": None,
        "ozet": "",
        "dosyaAdi": f"{doc_id}.txt"
    }
    
    # Dataset alanlarına göre uyarlayın
    if "daire" in record:
        metadata["daire"] = clean_text(record["daire"])
    elif "chamber" in record:
        metadata["daire"] = clean_text(record["chamber"])
    
    if "esas_no" in record:
        metadata["esas"] = clean_text(record["esas_no"])
    elif "esas" in record:
        metadata["esas"] = clean_text(record["esas"])
    
    if "karar_no" in record:
        metadata["karar"] = clean_text(record["karar_no"])
    elif "karar" in record:
        metadata["karar"] = clean_text(record["karar"])
    
    if "tarih" in record:
        metadata["tarih"] = clean_text(record["tarih"])
    elif "date" in record:
        metadata["tarih"] = clean_text(record["date"])
    
    # Yılı çıkar
    if metadata["tarih"]:
        year_match = re.search(r'(\d{4})', metadata["tarih"])
        if year_match:
            metadata["yil"] = int(year_match.group(1))
    
    # Özet oluştur (ilk 500 karakter)
    if "metin" in record:
        full_text = clean_text(record["metin"])
    elif "text" in record:
        full_text = clean_text(record["text"])
    elif "content" in record:
        full_text = clean_text(record["content"])
    else:
        full_text = ""
    
    metadata["ozet"] = full_text[:500] + "..." if len(full_text) > 500 else full_text
    
    return metadata, full_text


def process_dataset(dataset_name=HF_DATASET, subset=None, limit=None, output_dir=None):
    """
    Hugging Face datasetini işler ve dosyalara yazar.
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent
    else:
        output_dir = Path(output_dir)
    
    docs_dir = output_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Dataset yükleniyor: {dataset_name}")
    print(f"Çıktı dizini: {output_dir}")
    
    try:
        if subset:
            dataset = load_dataset(dataset_name, subset, split="train")
        else:
            dataset = load_dataset(dataset_name, split="train")
    except Exception as e:
        print(f"Dataset yükleme hatası: {e}")
        print("\nÖrnek dataset kullanılıyor (demo mod)...")
        dataset = generate_demo_dataset()
    
    if limit:
        dataset = dataset.select(range(min(limit, len(dataset))))
    
    print(f"İşlenecek kayıt sayısı: {len(dataset)}")
    
    all_metadata = {}
    
    for i, record in enumerate(tqdm(dataset, desc="Kararlar işleniyor")):
        doc_id = i + 1
        
        try:
            metadata, full_text = extract_metadata(record, doc_id)
            
            # Metin dosyasını yaz
            doc_path = docs_dir / f"{doc_id}.txt"
            with open(doc_path, "w", encoding="utf-8") as f:
                # Başlık bilgileri
                f.write(f"Daire: {metadata['daire']}\n")
                f.write(f"Esas No: {metadata['esas']}\n")
                f.write(f"Karar No: {metadata['karar']}\n")
                f.write(f"Tarih: {metadata['tarih']}\n")
                f.write("-" * 50 + "\n\n")
                f.write(full_text)
            
            all_metadata[doc_id] = metadata
            
        except Exception as e:
            print(f"\nKayıt {doc_id} işlenirken hata: {e}")
            continue
    
    # Meta veri dosyasını yaz
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, ensure_ascii=False, indent=2)
    
    print(f"\nToplam {len(all_metadata)} karar işlendi.")
    print(f"Metin dosyaları: {docs_dir}")
    print(f"Meta veriler: {metadata_path}")
    
    return all_metadata


def generate_demo_dataset():
    """Demo mod için örnek veri üretir."""
    print("Demo dataset oluşturuluyor...")
    
    daireler = [
        "1. Ceza Dairesi", "2. Ceza Dairesi", "3. Ceza Dairesi",
        "4. Ceza Dairesi", "5. Ceza Dairesi", "6. Ceza Dairesi",
        "Ceza Genel Kurulu"
    ]
    
    suc_tipleri = [
        "Hırsızlık suçundan sanık hakkında yapılan yargılama sonunda",
        "Kasten yaralama suçundan sanık hakkında",
        "Dolandırıcılık suçundan sanık hakkında verilen karar",
        "Uyuşturucu madde ticareti suçundan",
        "Tehdit suçundan sanık hakkında",
    ]
    
    demo_records = []
    for i in range(100):  # 100 örnek kayıt
        yil = 2020 + (i % 7)
        demo_records.append({
            "daire": daireler[i % len(daireler)],
            "esas_no": f"{yil}/{1000 + i}",
            "karar_no": f"{yil}/{2000 + i}",
            "tarih": f"{(i % 28) + 1:02d}.{(i % 12) + 1:02d}.{yil}",
            "metin": f"{suc_tipleri[i % len(suc_tipleri)]}. " * 20
        })
    
    class DemoDataset:
        def __init__(self, data):
            self.data = data
        def __len__(self):
            return len(self.data)
        def __iter__(self):
            return iter(self.data)
        def __getitem__(self, idx):
            return self.data[idx]
        def select(self, indices):
            return DemoDataset([self.data[i] for i in indices])
    
    return DemoDataset(demo_records)


def main():
    parser = argparse.ArgumentParser(
        description="Hugging Face Yargıtay korpusunu iPhone formatına dönüştürür."
    )
    parser.add_argument(
        "--dataset",
        default=HF_DATASET,
        help=f"Hugging Face dataset adı (varsayılan: {HF_DATASET})"
    )
    parser.add_argument(
        "--subset",
        default=None,
        help="Dataset alt kümesi (örn: ceza)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="İşlenecek maksimum kayıt sayısı"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Çıktı dizini (varsayılan: üst dizin)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo mod - gerçek dataset yerine örnek veri kullan"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Hugging Face -> iPhone Dönüştürücü")
    print("Hukukİçtihat+ Ceza V4.2")
    print("=" * 50)
    print()
    
    if args.demo:
        dataset = generate_demo_dataset()
        if args.limit:
            dataset = dataset.select(range(min(args.limit, len(dataset))))
        
        output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent.parent
        docs_dir = output_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        all_metadata = {}
        for i, record in enumerate(tqdm(dataset, desc="Demo kararlar işleniyor")):
            doc_id = i + 1
            metadata, full_text = extract_metadata(record, doc_id)
            
            doc_path = docs_dir / f"{doc_id}.txt"
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(f"Daire: {metadata['daire']}\n")
                f.write(f"Esas No: {metadata['esas']}\n")
                f.write(f"Karar No: {metadata['karar']}\n")
                f.write(f"Tarih: {metadata['tarih']}\n")
                f.write("-" * 50 + "\n\n")
                f.write(full_text)
            
            all_metadata[doc_id] = metadata
        
        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(all_metadata, f, ensure_ascii=False, indent=2)
        
        print(f"\nDemo tamamlandı: {len(all_metadata)} kayıt")
    else:
        process_dataset(
            dataset_name=args.dataset,
            subset=args.subset,
            limit=args.limit,
            output_dir=args.output_dir
        )
    
    print("\nİşlem tamamlandı!")
    print("Sonraki adım: python3 build_index.py")


if __name__ == "__main__":
    main()
