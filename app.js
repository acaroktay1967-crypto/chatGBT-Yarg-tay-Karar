/**
 * Hukukİçtihat+ Ceza V4.2
 * iPhone + a-Shell mini için Yargıtay Karar Arama Motoru
 * 
 * Özellikler:
 * - 50.000 karar üzerinde ters indeks araması
 * - Türkçe tam metin arama
 * - Daire ve yıl filtreleri
 * - İlgililik ve tarih sıralaması
 * - IndexedDB yerel karar arşivi
 * - Korpustan Çek ve Kaydet
 * - JSON dışa aktarma
 */

// =====================================================
// GLOBAL DEĞİŞKENLER
// =====================================================

let idx = null;          // Ters indeks verisi
let docMeta = null;      // Doküman meta verileri
let db = null;           // IndexedDB referansı
const DB_NAME = 'HukukIctihatArsiv';
const STORE_NAME = 'kararlar';
const DB_VERSION = 1;

// Türkçe karakter dönüşüm tablosu
const TR_LOWER_MAP = {
    'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç'
};

// =====================================================
// TÜRKÇE METİN İŞLEMLERİ
// =====================================================

/**
 * Türkçe karakterleri doğru şekilde küçük harfe çevirir
 */
function turkishLowerCase(str) {
    if (!str) return '';
    let result = '';
    for (let i = 0; i < str.length; i++) {
        const ch = str[i];
        if (TR_LOWER_MAP[ch]) {
            result += TR_LOWER_MAP[ch];
        } else {
            result += ch.toLowerCase();
        }
    }
    return result;
}

/**
 * Metni normalize eder (Türkçe lowercase + trim)
 */
function normalizeText(text) {
    return turkishLowerCase(text).trim();
}

/**
 * Arama terimlerini tokenize eder
 */
function tokenize(query) {
    return normalizeText(query)
        .split(/\s+/)
        .filter(t => t.length > 0);
}

// =====================================================
// TERS İNDEKS FONKSİYONLARI
// =====================================================

/**
 * İndeks dosyasını yükler
 */
async function getIdx() {
    if (idx !== null) return idx;
    try {
        const response = await fetch('index/inverted_index.json');
        if (!response.ok) throw new Error('İndeks yüklenemedi');
        idx = await response.json();
        return idx;
    } catch (error) {
        console.error('İndeks yükleme hatası:', error);
        throw error;
    }
}

/**
 * Doküman meta verilerini yükler
 */
async function getDoc() {
    if (docMeta !== null) return docMeta;
    try {
        const response = await fetch('index/doc_meta.json');
        if (!response.ok) throw new Error('Doküman meta verileri yüklenemedi');
        docMeta = await response.json();
        return docMeta;
    } catch (error) {
        console.error('Doküman meta yükleme hatası:', error);
        throw error;
    }
}

/**
 * Bir terim için posting listesini döndürür
 * Her posting: [docId, termFrequency, positions]
 */
function postings(index, term) {
    const normalizedTerm = normalizeText(term);
    return index[normalizedTerm] || [];
}

/**
 * İki posting listesini kesiştirir (AND işlemi)
 */
function intersect(list1, list2) {
    const result = [];
    let i = 0, j = 0;
    
    // Posting listeleri docId'ye göre sıralı varsayılır
    const sorted1 = [...list1].sort((a, b) => a[0] - b[0]);
    const sorted2 = [...list2].sort((a, b) => a[0] - b[0]);
    
    while (i < sorted1.length && j < sorted2.length) {
        const docId1 = sorted1[i][0];
        const docId2 = sorted2[j][0];
        
        if (docId1 === docId2) {
            // Frekansları topla
            const combinedFreq = sorted1[i][1] + sorted2[j][1];
            result.push([docId1, combinedFreq]);
            i++;
            j++;
        } else if (docId1 < docId2) {
            i++;
        } else {
            j++;
        }
    }
    
    return result;
}

/**
 * Birden fazla posting listesini kesiştirir
 */
function intersectMultiple(lists) {
    if (lists.length === 0) return [];
    if (lists.length === 1) return lists[0];
    
    // En kısa listeyle başla (optimizasyon)
    lists.sort((a, b) => a.length - b.length);
    
    let result = lists[0];
    for (let i = 1; i < lists.length; i++) {
        result = intersect(result, lists[i]);
        if (result.length === 0) break;
    }
    
    return result;
}

// =====================================================
// ARAMA FONKSİYONLARI
// =====================================================

/**
 * Ana arama fonksiyonu
 */
async function search(query, options = {}) {
    const {
        daire = null,
        yilBaslangic = null,
        yilBitis = null,
        siralama = 'ilgililik', // 'ilgililik' veya 'tarih'
        limit = 100
    } = options;
    
    try {
        const index = await getIdx();
        const docs = await getDoc();
        
        const tokens = tokenize(query);
        if (tokens.length === 0) {
            return { results: [], total: 0, query: query };
        }
        
        // Her terim için posting listelerini al
        const postingLists = tokens.map(token => postings(index, token));
        
        // Boş liste varsa sonuç yok
        if (postingLists.some(list => list.length === 0)) {
            return { results: [], total: 0, query: query };
        }
        
        // Posting listelerini kesiştirir (AND mantığı)
        let matchedDocs = intersectMultiple(postingLists);
        
        // Sonuçları zenginleştir
        let results = matchedDocs.map(([docId, score]) => {
            const meta = docs[docId] || {};
            return {
                id: docId,
                score: score,
                daire: meta.daire || '',
                esas: meta.esas || '',
                karar: meta.karar || '',
                tarih: meta.tarih || '',
                yil: meta.yil || extractYear(meta.tarih),
                ozet: meta.ozet || '',
                dosyaAdi: meta.dosyaAdi || `${docId}.txt`
            };
        });
        
        // Daire filtresi
        if (daire && daire !== 'tumu') {
            results = results.filter(r => r.daire === daire);
        }
        
        // Yıl filtresi
        if (yilBaslangic) {
            results = results.filter(r => r.yil >= yilBaslangic);
        }
        if (yilBitis) {
            results = results.filter(r => r.yil <= yilBitis);
        }
        
        // Sıralama
        if (siralama === 'tarih') {
            results.sort((a, b) => {
                const dateA = parseDate(a.tarih);
                const dateB = parseDate(b.tarih);
                return dateB - dateA; // En yeni önce
            });
        } else {
            // İlgililik sıralaması (score'a göre)
            results.sort((a, b) => b.score - a.score);
        }
        
        const total = results.length;
        results = results.slice(0, limit);
        
        return { results, total, query };
        
    } catch (error) {
        console.error('Arama hatası:', error);
        throw error;
    }
}

/**
 * Tarihten yılı çıkarır
 */
function extractYear(tarih) {
    if (!tarih) return null;
    const match = tarih.match(/(\d{4})/);
    return match ? parseInt(match[1]) : null;
}

/**
 * Tarih stringini Date objesine çevirir
 */
function parseDate(tarih) {
    if (!tarih) return new Date(0);
    // DD.MM.YYYY formatı
    const parts = tarih.split('.');
    if (parts.length === 3) {
        return new Date(parts[2], parts[1] - 1, parts[0]);
    }
    return new Date(tarih);
}

// =====================================================
// TAM KARAR İŞLEMLERİ
// =====================================================

/**
 * Tam karar metnini yükler
 */
async function loadFullDecision(docId) {
    try {
        const docs = await getDoc();
        const meta = docs[docId];
        if (!meta || !meta.dosyaAdi) {
            throw new Error('Karar bulunamadı');
        }
        
        const response = await fetch(`docs/${meta.dosyaAdi}`);
        if (!response.ok) throw new Error('Karar metni yüklenemedi');
        
        const text = await response.text();
        return {
            id: docId,
            meta: meta,
            content: text
        };
    } catch (error) {
        console.error('Karar yükleme hatası:', error);
        throw error;
    }
}

/**
 * Tam Kararı Aç - Modal gösterimi için
 */
async function openFullDecision(docId) {
    const modal = document.getElementById('decisionModal');
    const content = document.getElementById('decisionContent');
    const loading = document.getElementById('decisionLoading');
    
    if (modal) modal.style.display = 'block';
    if (loading) loading.style.display = 'block';
    if (content) content.innerHTML = '';
    
    try {
        const decision = await loadFullDecision(docId);
        
        if (content) {
            content.innerHTML = `
                <div class="decision-header">
                    <h3>${decision.meta.daire || 'Yargıtay'}</h3>
                    <p><strong>Esas:</strong> ${decision.meta.esas || '-'}</p>
                    <p><strong>Karar:</strong> ${decision.meta.karar || '-'}</p>
                    <p><strong>Tarih:</strong> ${decision.meta.tarih || '-'}</p>
                </div>
                <div class="decision-body">
                    <pre>${escapeHtml(decision.content)}</pre>
                </div>
            `;
        }
    } catch (error) {
        if (content) {
            content.innerHTML = `<p class="error">Karar yüklenirken hata oluştu: ${error.message}</p>`;
        }
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

/**
 * HTML karakterlerini escape eder
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Modalı kapatır
 */
function closeModal() {
    const modal = document.getElementById('decisionModal');
    if (modal) modal.style.display = 'none';
}

// =====================================================
// INDEXEDDB - YEREL ARŞİV
// =====================================================

/**
 * IndexedDB'yi başlatır
 */
function initDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        
        request.onerror = () => {
            console.error('IndexedDB açılamadı');
            reject(request.error);
        };
        
        request.onsuccess = () => {
            db = request.result;
            resolve(db);
        };
        
        request.onupgradeneeded = (event) => {
            const database = event.target.result;
            
            if (!database.objectStoreNames.contains(STORE_NAME)) {
                const store = database.createObjectStore(STORE_NAME, { keyPath: 'id' });
                store.createIndex('daire', 'daire', { unique: false });
                store.createIndex('tarih', 'tarih', { unique: false });
                store.createIndex('savedAt', 'savedAt', { unique: false });
            }
        };
    });
}

/**
 * Karar kaydeder (Korpustan Çek ve Kaydet)
 */
async function saveDecision(docId) {
    try {
        if (!db) await initDB();
        
        const decision = await loadFullDecision(docId);
        
        const record = {
            id: docId,
            daire: decision.meta.daire || '',
            esas: decision.meta.esas || '',
            karar: decision.meta.karar || '',
            tarih: decision.meta.tarih || '',
            ozet: decision.meta.ozet || '',
            content: decision.content,
            savedAt: new Date().toISOString()
        };
        
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.put(record);
            
            request.onsuccess = () => {
                showNotification('Karar arşive kaydedildi');
                resolve(record);
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    } catch (error) {
        console.error('Kaydetme hatası:', error);
        showNotification('Karar kaydedilemedi: ' + error.message, 'error');
        throw error;
    }
}

/**
 * Kaydedilen kararları listeler
 */
async function getSavedDecisions() {
    try {
        if (!db) await initDB();
        
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.getAll();
            
            request.onsuccess = () => {
                const results = request.result || [];
                // En son kaydedilenler önce
                results.sort((a, b) => new Date(b.savedAt) - new Date(a.savedAt));
                resolve(results);
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    } catch (error) {
        console.error('Kayıtlı kararlar alınamadı:', error);
        return [];
    }
}

/**
 * Kaydedilen kararı siler
 */
async function deleteSavedDecision(docId) {
    try {
        if (!db) await initDB();
        
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.delete(docId);
            
            request.onsuccess = () => {
                showNotification('Karar arşivden silindi');
                resolve();
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    } catch (error) {
        console.error('Silme hatası:', error);
        throw error;
    }
}

/**
 * Kararın kaydedilip kaydedilmediğini kontrol eder
 */
async function isDecisionSaved(docId) {
    try {
        if (!db) await initDB();
        
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.get(docId);
            
            request.onsuccess = () => {
                resolve(!!request.result);
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    } catch (error) {
        return false;
    }
}

// =====================================================
// JSON DIŞA AKTARMA
// =====================================================

/**
 * Kaydedilen kararları JSON olarak dışa aktarır
 */
async function exportToJSON() {
    try {
        const decisions = await getSavedDecisions();
        
        if (decisions.length === 0) {
            showNotification('Dışa aktarılacak karar bulunamadı', 'warning');
            return;
        }
        
        const exportData = {
            exportDate: new Date().toISOString(),
            appVersion: '4.2.0',
            totalDecisions: decisions.length,
            decisions: decisions
        };
        
        const jsonStr = JSON.stringify(exportData, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `hukuk_ictihat_arsiv_${formatDateForFilename()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showNotification(`${decisions.length} karar JSON olarak dışa aktarıldı`);
    } catch (error) {
        console.error('Dışa aktarma hatası:', error);
        showNotification('Dışa aktarma başarısız: ' + error.message, 'error');
    }
}

/**
 * Dosya adı için tarih formatlar
 */
function formatDateForFilename() {
    const now = new Date();
    return `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;
}

// =====================================================
// UI FONKSİYONLARI
// =====================================================

/**
 * Bildirim gösterir
 */
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    if (notification) {
        notification.textContent = message;
        notification.className = `notification ${type}`;
        notification.style.display = 'block';
        
        setTimeout(() => {
            notification.style.display = 'none';
        }, 3000);
    }
}

/**
 * Arama sonuçlarını render eder
 */
function renderResults(results, total) {
    const container = document.getElementById('results');
    if (!container) return;
    
    if (results.length === 0) {
        container.innerHTML = '<p class="no-results">Sonuç bulunamadı</p>';
        return;
    }
    
    const header = document.createElement('div');
    header.className = 'results-header';
    header.innerHTML = `<p>Toplam ${total} sonuç bulundu</p>`;
    
    const list = document.createElement('div');
    list.className = 'results-list';
    
    results.forEach(result => {
        const item = document.createElement('div');
        item.className = 'result-item';
        item.innerHTML = `
            <div class="result-meta">
                <span class="daire">${result.daire || 'Bilinmiyor'}</span>
                <span class="tarih">${result.tarih || ''}</span>
            </div>
            <div class="result-esas">
                <strong>Esas:</strong> ${result.esas || '-'} 
                <strong>Karar:</strong> ${result.karar || '-'}
            </div>
            <div class="result-ozet">${truncate(result.ozet, 200)}</div>
            <div class="result-actions">
                <button onclick="openFullDecision(${result.id})" class="btn btn-primary">Tam Kararı Aç</button>
                <button onclick="saveDecision(${result.id})" class="btn btn-secondary">Kaydet</button>
            </div>
        `;
        list.appendChild(item);
    });
    
    container.innerHTML = '';
    container.appendChild(header);
    container.appendChild(list);
}

/**
 * Metni belirli uzunlukta keser
 */
function truncate(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Kaydedilenler ekranını gösterir
 */
async function showSavedDecisions() {
    const container = document.getElementById('results');
    if (!container) return;
    
    container.innerHTML = '<p class="loading">Kaydedilen kararlar yükleniyor...</p>';
    
    try {
        const decisions = await getSavedDecisions();
        
        if (decisions.length === 0) {
            container.innerHTML = '<p class="no-results">Henüz kaydedilmiş karar yok</p>';
            return;
        }
        
        const header = document.createElement('div');
        header.className = 'results-header';
        header.innerHTML = `
            <p>Kaydedilen Kararlar (${decisions.length})</p>
            <button onclick="exportToJSON()" class="btn btn-export">JSON Olarak Dışa Aktar</button>
        `;
        
        const list = document.createElement('div');
        list.className = 'results-list';
        
        decisions.forEach(decision => {
            const item = document.createElement('div');
            item.className = 'result-item saved';
            item.innerHTML = `
                <div class="result-meta">
                    <span class="daire">${decision.daire || 'Bilinmiyor'}</span>
                    <span class="tarih">${decision.tarih || ''}</span>
                    <span class="saved-date">Kaydedilme: ${formatSavedDate(decision.savedAt)}</span>
                </div>
                <div class="result-esas">
                    <strong>Esas:</strong> ${decision.esas || '-'} 
                    <strong>Karar:</strong> ${decision.karar || '-'}
                </div>
                <div class="result-ozet">${truncate(decision.ozet, 200)}</div>
                <div class="result-actions">
                    <button onclick="viewSavedDecision(${decision.id})" class="btn btn-primary">Görüntüle</button>
                    <button onclick="deleteSavedDecision(${decision.id}).then(showSavedDecisions)" class="btn btn-danger">Sil</button>
                </div>
            `;
            list.appendChild(item);
        });
        
        container.innerHTML = '';
        container.appendChild(header);
        container.appendChild(list);
        
    } catch (error) {
        container.innerHTML = `<p class="error">Hata: ${error.message}</p>`;
    }
}

/**
 * Kaydedilen kararı görüntüler
 */
async function viewSavedDecision(docId) {
    try {
        if (!db) await initDB();
        
        const transaction = db.transaction([STORE_NAME], 'readonly');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.get(docId);
        
        request.onsuccess = () => {
            const decision = request.result;
            if (!decision) {
                showNotification('Karar bulunamadı', 'error');
                return;
            }
            
            const modal = document.getElementById('decisionModal');
            const content = document.getElementById('decisionContent');
            
            if (modal) modal.style.display = 'block';
            if (content) {
                content.innerHTML = `
                    <div class="decision-header">
                        <h3>${decision.daire || 'Yargıtay'}</h3>
                        <p><strong>Esas:</strong> ${decision.esas || '-'}</p>
                        <p><strong>Karar:</strong> ${decision.karar || '-'}</p>
                        <p><strong>Tarih:</strong> ${decision.tarih || '-'}</p>
                    </div>
                    <div class="decision-body">
                        <pre>${escapeHtml(decision.content)}</pre>
                    </div>
                `;
            }
        };
    } catch (error) {
        console.error('Görüntüleme hatası:', error);
    }
}

/**
 * Kayıt tarihini formatlar
 */
function formatSavedDate(isoString) {
    const date = new Date(isoString);
    return `${date.toLocaleDateString('tr-TR')} ${date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}`;
}

/**
 * Daire listesini yükler
 */
async function loadDaireOptions() {
    try {
        const docs = await getDoc();
        const daireler = new Set();
        
        Object.values(docs).forEach(doc => {
            if (doc.daire) daireler.add(doc.daire);
        });
        
        const select = document.getElementById('daireFilter');
        if (select) {
            const sortedDaireler = Array.from(daireler).sort();
            sortedDaireler.forEach(daire => {
                const option = document.createElement('option');
                option.value = daire;
                option.textContent = daire;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Daire listesi yüklenemedi:', error);
    }
}

// =====================================================
// EVENT HANDLERS
// =====================================================

/**
 * Arama formunu işler
 */
async function handleSearch(event) {
    if (event) event.preventDefault();
    
    const queryInput = document.getElementById('searchQuery');
    const daireSelect = document.getElementById('daireFilter');
    const yilBaslangic = document.getElementById('yilBaslangic');
    const yilBitis = document.getElementById('yilBitis');
    const siralamaSelect = document.getElementById('siralama');
    const resultsContainer = document.getElementById('results');
    
    const query = queryInput ? queryInput.value.trim() : '';
    
    if (!query) {
        if (resultsContainer) {
            resultsContainer.innerHTML = '<p class="info">Lütfen bir arama terimi girin</p>';
        }
        return;
    }
    
    if (resultsContainer) {
        resultsContainer.innerHTML = '<p class="loading">Aranıyor...</p>';
    }
    
    try {
        const options = {
            daire: daireSelect ? daireSelect.value : null,
            yilBaslangic: yilBaslangic && yilBaslangic.value ? parseInt(yilBaslangic.value) : null,
            yilBitis: yilBitis && yilBitis.value ? parseInt(yilBitis.value) : null,
            siralama: siralamaSelect ? siralamaSelect.value : 'ilgililik'
        };
        
        const { results, total } = await search(query, options);
        renderResults(results, total);
        
    } catch (error) {
        if (resultsContainer) {
            resultsContainer.innerHTML = `<p class="error">Arama hatası: ${error.message}</p>`;
        }
    }
}

// =====================================================
// UYGULAMA BAŞLATMA
// =====================================================

/**
 * Uygulamayı başlatır
 */
async function initApp() {
    try {
        // IndexedDB'yi başlat
        await initDB();
        
        // Daire filtresi seçeneklerini yükle
        await loadDaireOptions();
        
        // Event listener'ları ekle
        const searchForm = document.getElementById('searchForm');
        if (searchForm) {
            searchForm.addEventListener('submit', handleSearch);
        }
        
        const savedBtn = document.getElementById('showSavedBtn');
        if (savedBtn) {
            savedBtn.addEventListener('click', showSavedDecisions);
        }
        
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', exportToJSON);
        }
        
        // Modal kapatma
        const closeBtn = document.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
        }
        
        // Modal dışına tıklama
        window.addEventListener('click', (event) => {
            const modal = document.getElementById('decisionModal');
            if (event.target === modal) {
                closeModal();
            }
        });
        
        console.log('Hukukİçtihat+ Ceza V4.2 başlatıldı');
        
    } catch (error) {
        console.error('Uygulama başlatma hatası:', error);
    }
}

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', initApp);

// Global fonksiyonları window'a ekle (HTML onclick için)
window.openFullDecision = openFullDecision;
window.closeModal = closeModal;
window.saveDecision = saveDecision;
window.showSavedDecisions = showSavedDecisions;
window.viewSavedDecision = viewSavedDecision;
window.deleteSavedDecision = deleteSavedDecision;
window.exportToJSON = exportToJSON;
window.handleSearch = handleSearch;
