const DB_NAME = "sevakai_offline";
const STORE = "pending_visits";

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "localId" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function queueVisit(record) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const localId = `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    tx.objectStore(STORE).put({ ...record, localId, queuedAt: new Date().toISOString() });
    tx.oncomplete = () => resolve(localId);
    tx.onerror = () => reject(tx.error);
  });
}

export async function getQueuedVisits() {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function removeQueuedVisit(localId) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(localId);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
