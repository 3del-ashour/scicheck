# Member 2 — RAG & Vector DB Engineering Report

> **Author:** Salih Özgür Seçen — RAG / Vector DB Engineer
> **Project:** SciCheck — Scientific Claim Verification System

---

## 1. Giriş (Introduction)

Bu belge, SciCheck projesinin **Knowledge Base Construction**, **Vector Indexing** ve **RAG (Retrieval-Augmented Generation) Pipeline** bileşenlerini teknik olarak açıklamaktadır. Projede bilimsel iddiaların doğrulanması için kullanılan kanıt tabanının nasıl oluşturulduğu, vektör indeksleme stratejisi ve gerçek zamanlı benzerlik aramasının nasıl çalıştığı detaylandırılmıştır.

## 2. Knowledge Base Construction (Bilgi Tabanı Oluşturma)

### 2.1 Veri Seti: SciFact Corpus

Bilgi tabanı olarak Allen AI'ın **SciFact** veri seti (`allenai/scifact`) kullanılmıştır. Bu veri seti HuggingFace Hub üzerinden `datasets` kütüphanesiyle indirilmektedir.

| Özellik | Değer |
|---------|-------|
| **Kaynak** | HuggingFace — `allenai/scifact` (corpus split) |
| **Doküman sayısı** | ~5,183 bilimsel abstract |
| **Alan** | Biyomedikal / sağlık bilimleri |
| **Format** | Her döküman: `doc_id`, `title`, `abstract` (cümle listesi), `structured` flag |
| **Lisans** | CC BY-NC 2.0 |

**Neden SciFact?**
- Projenin değerlendirme pipeline'ı (Member 6) da SciFact benchmark'ını kullanmaktadır; bu sayede retrieval ve end-to-end metrikler aynı veri seti üzerinde tutarlı ölçülebilir.
- Abstract'lar zaten kısa ve öz olduğundan ek bir preprocessing gerektirmez.
- Claim-evidence eşleştirmeleri doğrulanmış olduğundan gold-standard retrieval testi yapılabilir.

### 2.2 Chunking Stratejisi

SciFact abstract'ları ortalama **~150 kelime** uzunluğundadır ve bu değer kullandığımız embedding modelinin ideal giriş uzunluğuyla (256 token penceresi, 512'ye kadar destek) uyumludur. Bu nedenle:

- **Her abstract tek bir passage olarak işlenmiştir.** Cümle listesi (`abstract` alanı) boşluk ile birleştirilerek (`" ".join(abstract)`) tek bir string elde edilir.
- Alt bölmelere ayırma (sub-chunking) uygulanmamıştır çünkü bu uzunluktaki metinlerde anlamsal bütünlük kaybolabilir.
- Daha uzun dökümanlar (örn. PubMed tam metinleri) eklenecek olursa, 512-token sliding window + 50-token overlap stratejisi önerilir.

```python
def to_passage(row: dict) -> dict:
    abstract_text = " ".join(row["abstract"]) if row.get("abstract") else ""
    return {
        "source_id": str(row["doc_id"]),
        "title": row.get("title", ""),
        "text": abstract_text,
        "metadata": {"structured": row.get("structured", False)},
    }
```

### 2.3 Veri Ön İşleme ve Depolama

İşlenmiş passage'lar `data/processed/passages.jsonl` dosyasına kaydedilir. Bu sayede:
- Tekrarlı denemelerde HuggingFace'den yeniden indirmeye gerek kalmaz.
- Passage yapısı JSON formatında denetlenebilir.
- Re-ingestion işlemi hızlanır.

## 3. Vector Indexing (Vektör İndeksleme)

### 3.1 Embedding Modeli

| Parametre | Değer |
|-----------|-------|
| **Model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Boyut** | 384 boyutlu vektörler |
| **Normalizasyon** | L2-normalize (cosine similarity == inner product) |
| **Eğitim verisi** | 1B+ cümle çifti (NLI, paraphrase, QA) |
| **Hız** | CPU üzerinde ~14,000 cümle/saniye |

Bu model seçilmesinin nedenleri:
1. **Düşük boyut (384-d)**: Depolama ve sorgu maliyetini düşürür.
2. **Yüksek performans**: MTEB benchmark'ında boyutuna göre en iyi performans/hız oranı.
3. **CPU uyumluluğu**: GPU gerektirmez; geliştirme ortamında kolayca çalışır.
4. **Normalizasyon desteği**: `normalize_embeddings=True` ile vektörler birim uzunluğa çekilir; bu da cosine similarity hesabını dot-product'a indirger.

### 3.2 Vektör Veritabanı: ChromaDB

| Parametre | Değer |
|-----------|-------|
| **Veritabanı** | ChromaDB (PersistentClient) |
| **Depolama yolu** | `./data/chroma` (konfigüre edilebilir) |
| **Koleksiyon adı** | `scicheck` |
| **İndeks tipi** | HNSW (Hierarchical Navigable Small World) |
| **Mesafe metriği** | Cosine distance |
| **Sorgu karmaşıklığı** | O(log n) — milyon ölçeğinde bile sub-ms yanıt süresi |

**Neden HNSW?**
ChromaDB varsayılan olarak HNSW indeks kullanır. Alternatiflerle karşılaştırma:

| İndeks Tipi | Avantaj | Dezavantaj |
|-------------|---------|------------|
| **Flat (Brute-force)** | %100 kesin sonuç | O(n) — büyük veri setlerinde yavaş |
| **IVF (Inverted File)** | Orta hız, düşük bellek | Eğitim aşaması gerekir, düşük recall riski |
| **HNSW** ✅ | O(log n) sorgu, yüksek recall (~98%+) | Daha fazla bellek kullanımı |

5K doküman ölçeğinde flat search da yeterli olurdu, ancak HNSW ölçeklenebilirlik ve ChromaDB entegrasyonu açısından doğal tercihdir.

### 3.3 Cosine Distance → Cosine Similarity Dönüşümü

ChromaDB cosine **distance** döndürür (0 = aynı, 2 = zıt). Biz bunu **similarity** skoruna çeviririz:

```
similarity = 1.0 - distance
```

Bu skor `Evidence.score` alanında [0, 1] aralığında normalize edilmiş olarak döndürülür.

## 4. RAG Pipeline

### 4.1 Mimari Genel Bakış

```
User Claim
    │
    ▼
┌───────────────────┐
│  Embedding Model  │  ← sentence-transformers/all-MiniLM-L6-v2
│  (query encode)   │
└────────┬──────────┘
         │ 384-d vector
         ▼
┌───────────────────┐
│    ChromaDB       │  ← HNSW index, cosine distance
│  (similarity      │
│   search, top-k)  │
└────────┬──────────┘
         │ ids, documents, metadatas, distances
         ▼
┌───────────────────┐
│  Evidence Mapper  │  ← ChromaDB results → contracts.Evidence
│  (score norm.)    │
└────────┬──────────┘
         │ list[Evidence]
         ▼
   Orchestrator / Agents
```

### 4.2 `retrieve()` Fonksiyonu — Contract Surface

```python
def retrieve(query: str, k: int = 5) -> list[Evidence]:
```

Bu fonksiyon projenin **tek retrieval arayüzüdür**. Diğer üyeler (özellikle Member 4 — Evidence Retriever) ChromaDB'ye doğrudan erişmez; sadece bu fonksiyonu çağırır.

**Davranış:**
1. Query string'ini embedding modeli ile vektörleştirir.
2. ChromaDB koleksiyonunda cosine similarity araması yapar.
3. Ham sonuçları `contracts.Evidence` Pydantic modeline dönüştürür.
4. Benzerlik skoruna göre sıralı liste döndürür.

**Hata yönetimi:**
- Herhangi bir embedding veya veritabanı hatası `RAGError` exception'ına sarılarak fırlatılır.
- Orchestrator bu hatayı yakalayıp graceful degradation uygular.

### 4.3 Lazy Singleton Pattern

Embedding modeli ilk çağrıda yüklenir ve sonraki çağrılarda yeniden kullanılır:

```python
_embedder: Embedder | None = None

def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
```

Bu pattern:
- Cold-start süresini sadece ilk sorguya sınırlar (~2-3 saniye model yükleme).
- Sonraki sorgularda ~10ms latency sağlar.
- Bellek kullanımını optimize eder (tek model instance).

### 4.4 Structured Logging

Tüm operasyonlar `structlog` ile JSON formatında loglanır:

```json
{"event": "rag.retrieve.start", "query": "vaccines cause autism", "k": 5, "timestamp": "..."}
{"event": "rag.retrieve.done", "n_results": 5, "top_score": 0.87, "timestamp": "..."}
```

`trace_id` context variable olarak propagate edilir, böylece tek bir kullanıcı sorgusunun tüm logları ilişkilendirilebilir.

## 5. Ingestion Pipeline

### 5.1 Çalıştırma

```bash
# Tam ingestion
python scripts/ingest.py

# Geliştirme/test amaçlı — sadece ilk 100 doküman
python scripts/ingest.py --limit 100
```

### 5.2 Pipeline Adımları

| Adım | Açıklama | Süre (yaklaşık) |
|------|----------|-----------------|
| 1. Dataset yükleme | HuggingFace'den SciFact corpus indirme | ~5s (ilk kez), cache sonrası <1s |
| 2. Passage dönüşüm | Abstract cümleleri birleştirme, filtreleme | <1s |
| 3. Embedding | Tüm passage'ları batch halinde vektörleştirme | ~15-30s (CPU) |
| 4. ChromaDB upsert | Vektörleri batch halinde veritabanına yazma | ~5s |
| 5. JSONL kayıt | İşlenmiş passage'ları diske yazma | <1s |
| **Toplam** | | **~25-40s** |

### 5.3 Batch Processing

Hem embedding hem de ChromaDB upsert işlemleri 256'lık batch'ler halinde yapılır:
- Bellek taşmasını önler.
- İlerleme loglanır.
- Büyük veri setlerine ölçeklenebilir.

## 6. Test Stratejisi

### 6.1 Unit Tests (CI-Safe)

`monkeypatch` ile ChromaDB ve embedding modeli mock'lanarak gerçek veritabanı veya model yüklemesi gerektirmeyen testler:

| Test | Doğrulanan Davranış |
|------|---------------------|
| `test_retrieve_returns_evidence_list` | Dönüş tipi `list[Evidence]` |
| `test_retrieve_scores_are_valid` | Skorlar [0, 1] aralığında |
| `test_retrieve_maps_source_id_correctly` | ChromaDB ID'leri doğru eşlenir |
| `test_retrieve_maps_title_correctly` | Metadata'dan title alınır |
| `test_retrieve_cosine_distance_to_similarity` | Distance → similarity dönüşümü doğru |
| `test_retrieve_handles_empty_results` | Boş sonuç durumu |
| `test_retrieve_raises_rag_error_on_failure` | Hatalar `RAGError`'a sarılır |

### 6.2 Integration Tests

`@pytest.mark.integration` ile işaretlenen testler gerçek ChromaDB ve embedding modeliyle çalışır:

```bash
pytest tests/test_rag.py -m integration
```

## 7. Dosya Yapısı

```
src/rag/
├── __init__.py          # Package init
├── embeddings.py        # Embedding model wrapper (Embedder class)
├── store.py             # ChromaDB wrapper (get_collection)
└── service.py           # Public API: retrieve() — CONTRACT

scripts/
└── ingest.py            # One-shot ingestion pipeline

tests/
└── test_rag.py          # Unit + integration tests

data/
├── chroma/              # ChromaDB persistent storage (gitignored)
└── processed/
    └── passages.jsonl   # Processed passages cache (gitignored)
```

## 8. Konfigürasyon

Tüm ayarlar `src/config.py` üzerinden environment variable olarak okunur:

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding modeli |
| `CHROMA_PATH` | `./data/chroma` | ChromaDB depolama yolu |
| `TOP_K` | `5` | Varsayılan retrieval sonuç sayısı |

## 9. Sonuç ve Gelecek Çalışmalar

Mevcut RAG pipeline'ı SciFact corpus ile tutarlı ve güvenilir bir retrieval altyapısı sunmaktadır. Gelecekte:

- **PubMed genişlemesi**: Daha geniş biyomedikal kapsam için PubMed abstract'ları eklenebilir.
- **Hybrid search**: Sparse (BM25) + dense (embedding) retrieval birleştirilebilir.
- **Re-ranking**: Cross-encoder ile top-k sonuçlar yeniden sıralanabilir.
- **Chunk stratejisi**: Uzun dökümanlar için sliding window chunking eklenebilir.
