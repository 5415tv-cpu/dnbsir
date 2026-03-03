// App Logic
let db;
const request = indexedDB.open("AIStoreDB", 1);

request.onupgradeneeded = function (event) {
    db = event.target.result;
    if (!db.objectStoreNames.contains("products")) {
        db.createObjectStore("products", { keyPath: "id" });
    }
};

request.onsuccess = function (event) {
    db = event.target.result;
    console.log("IndexedDB initialized successfully for Offline Caching.");
};

function saveProductToLocalDB(product) {
    if (!db) return;
    const tx = db.transaction("products", "readwrite");
    const store = tx.objectStore("products");
    store.put(product);
}

function loadProductsFromLocalDB(callback) {
    if (!db) return;
    const tx = db.transaction("products", "readonly");
    const store = tx.objectStore("products");
    const req = store.getAll();
    req.onsuccess = function () {
        callback(req.result);
    };
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('Mobile App Loaded');

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/service-worker.js')
            .then(reg => console.log('Service Worker Registered'))
            .catch(err => console.error('Service Worker Registration Failed', err));
    }

    // Check network status to load offline data
    if (!navigator.onLine) {
        console.warn("Offline mode active. Loading local products.");
        loadProductsFromLocalDB(products => {
            console.log("Loaded offline products:", products);
            // Example: Document.dispatchEvent to trigger UI render
            document.dispatchEvent(new CustomEvent("offlineProductsLoaded", { detail: products }));
        });
    }
});
