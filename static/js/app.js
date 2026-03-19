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

    // Show PWA banner for all mobile devices natively fallback
    const isMobile = window.innerWidth <= 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
    
    if (isMobile && !isStandalone && localStorage.getItem('hidePWA') !== 'true') {
        const banner = document.getElementById('pwaInstallBanner');
        if(banner) banner.style.display = 'flex';
    }
});

// PWA Install Logic
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    if (window.matchMedia('(display-mode: standalone)').matches || navigator.standalone) return;
    if(localStorage.getItem('hidePWA') === 'true') return;
    
    const banner = document.getElementById('pwaInstallBanner');
    if(banner) banner.style.display = 'flex';
});

function installPWA() {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    if (isIOS) {
        alert("아이폰(iPad) 설치 방법:\n1. 화면 하단의 공유(📤) 버튼을 누릅니다.\n2. 메뉴에서 '홈 화면에 추가(➕)'를 선택해주세요.");
        return;
    }

    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') hidePWABanner();
            deferredPrompt = null;
        });
    } else {
        alert("현재 브라우저 설정 메뉴(보통 우측 상단 ⋮)에서 '홈 화면에 추가' 또는 '앱 설치' 버튼을 눌러주세요.");
    }
}

function hidePWABanner() {
    const banner = document.getElementById('pwaInstallBanner');
    if(banner) banner.style.display = 'none';
    localStorage.setItem('hidePWA', 'true');
}
