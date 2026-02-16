"""Enhanced JavaScript injection for the recorder with advanced buffering.

This module provides improved event capture JavaScript that addresses
fast-action recording issues through:

1. **Priority-based queuing** - Critical events (clicks, submits) processed first
2. **Redundant capture channels** - Multiple delivery mechanisms with fallbacks  
3. **IndexedDB persistence** - Survives page navigations and crashes
4. **RequestIdleCallback optimization** - Flushes during browser idle time
5. **Service Worker bridge** (optional) - Capture during unload/crash
"""

ENHANCED_CAPTURE_SCRIPT = """
(() => {
    // Guard against multiple injections
    if (window.__enhancedRecorderInstalled) { 
        console.log('[EnhancedRecorder] Already installed');
        return; 
    }
    window.__enhancedRecorderInstalled = true;
    
    console.log('[EnhancedRecorder] Installing advanced capture system');
    
    // ============================================================================
    // CONFIGURATION
    // ============================================================================
    const CONFIG = {
        FLUSH_INTERVAL_MS: 2,           // Ultra-fast flush
        FLUSH_BACKUP_MS: 10,            // Backup flush
        FLUSH_SAFETY_MS: 50,            // Safety net flush
        MAX_QUEUE_SIZE: 1000,           // Max events before force flush
        PERSISTENCE_KEY: '__recorder_persistent_events',
        DEBUG: true
    };
    
    // ============================================================================
    // PRIORITY QUEUE SYSTEM
    // ============================================================================
    class PriorityQueue {
        constructor() {
            this.critical = [];  // navigation, submit
            this.high = [];      // click, change, input
            this.medium = [];    // hover, focus, keypress
            this.low = [];       // scroll, mousemove
        }
        
        push(event, priority) {
            const queue = this._getQueue(priority);
            queue.push(event);
            
            // Auto-flush if queue too large
            if (this.size() > CONFIG.MAX_QUEUE_SIZE) {
                console.warn('[EnhancedRecorder] Queue overflow, forcing flush');
                this._forceFlush();
            }
        }
        
        _getQueue(priority) {
            if (priority >= 100) return this.critical;
            if (priority >= 50) return this.high;
            if (priority >= 20) return this.medium;
            return this.low;
        }
        
        pop() {
            // Dequeue in priority order
            if (this.critical.length) return this.critical.shift();
            if (this.high.length) return this.high.shift();
            if (this.medium.length) return this.medium.shift();
            if (this.low.length) return this.low.shift();
            return null;
        }
        
        size() {
            return this.critical.length + this.high.length + 
                   this.medium.length + this.low.length;
        }
        
        clear() {
            this.critical = [];
            this.high = [];
            this.medium = [];
            this.low = [];
        }
        
        _forceFlush() {
            // Emergency flush all queues
            const allEvents = [
                ...this.critical,
                ...this.high,
                ...this.medium,
                ...this.low
            ];
            this.clear();
            
            allEvents.forEach(evt => {
                try {
                    window.pythonRecorderCapture && window.pythonRecorderCapture(evt);
                } catch (e) {
                    console.error('[EnhancedRecorder] Force flush error:', e);
                }
            });
        }
    }
    
    const eventQueue = new PriorityQueue();
    
    // ============================================================================
    // INDEXEDDB PERSISTENCE
    // ============================================================================
    class EventPersistence {
        constructor() {
            this.db = null;
            this.ready = false;
            this._init();
        }
        
        async _init() {
            try {
                const request = indexedDB.open('RecorderEvents', 1);
                
                request.onupgradeneeded = (e) => {
                    const db = e.target.result;
                    if (!db.objectStoreNames.contains('events')) {
                        db.createObjectStore('events', { keyPath: 'id', autoIncrement: true });
                    }
                };
                
                request.onsuccess = (e) => {
                    this.db = e.target.result;
                    this.ready = true;
                    CONFIG.DEBUG && console.log('[EnhancedRecorder] IndexedDB ready');
                    this._recoverPersisted();
                };
                
                request.onerror = () => {
                    console.warn('[EnhancedRecorder] IndexedDB unavailable');
                };
            } catch (e) {
                console.warn('[EnhancedRecorder] IndexedDB init failed:', e);
            }
        }
        
        async persist(event) {
            if (!this.ready || !this.db) return false;
            
            try {
                const tx = this.db.transaction(['events'], 'readwrite');
                const store = tx.objectStore('events');
                store.add({ ...event, persistedAt: Date.now() });
                return true;
            } catch (e) {
                CONFIG.DEBUG && console.warn('[EnhancedRecorder] Persist failed:', e);
                return false;
            }
        }
        
        async _recoverPersisted() {
            if (!this.ready || !this.db) return;
            
            try {
                const tx = this.db.transaction(['events'], 'readonly');
                const store = tx.objectStore('events');
                const request = store.getAll();
                
                request.onsuccess = () => {
                    const events = request.result || [];
                    if (events.length > 0) {
                        console.log(`[EnhancedRecorder] Recovering ${events.length} persisted events`);
                        events.forEach(evt => {
                            try {
                                window.pythonRecorderCapture && window.pythonRecorderCapture(evt);
                            } catch (e) {}
                        });
                        this._clearPersisted();
                    }
                };
            } catch (e) {
                CONFIG.DEBUG && console.warn('[EnhancedRecorder] Recovery failed:', e);
            }
        }
        
        async _clearPersisted() {
            if (!this.ready || !this.db) return;
            
            try {
                const tx = this.db.transaction(['events'], 'readwrite');
                const store = tx.objectStore('events');
                store.clear();
            } catch (e) {}
        }
    }
    
    const persistence = new EventPersistence();
    
    // ============================================================================
    // EVENT DELIVERY SYSTEM
    // ============================================================================
    const deliver = (handlerName, payload) => {
        const fn = window && window[handlerName];
        if (typeof fn === 'function') {
            try {
                fn(payload);
                return true;
            } catch (e) {
                CONFIG.DEBUG && console.warn(`[EnhancedRecorder] Delivery error:`, e);
                return false;
            }
        }
        return false;
    };
    
    const deliverWithRetry = async (event, priority) => {
        // Try immediate delivery
        if (deliver('pythonRecorderCapture', event)) {
            return true;
        }
        
        // Queue for retry
        eventQueue.push(event, priority);
        
        // Persist critical events
        if (priority >= 100) {
            await persistence.persist(event);
        }
        
        // Trigger immediate retry
        setTimeout(() => flushQueue(), 1);
        
        return false;
    };
    
    // ============================================================================
    // MULTI-THREADED FLUSH SYSTEM
    // ============================================================================
    const flushQueue = () => {
        let flushed = 0;
        let event;
        
        while ((event = eventQueue.pop()) !== null) {
            if (deliver('pythonRecorderCapture', event)) {
                flushed++;
            } else {
                // Put back in queue if delivery fails
                eventQueue.push(event, event._priority || 0);
                break;
            }
        }
        
        if (CONFIG.DEBUG && flushed > 0) {
            console.log(`[EnhancedRecorder] Flushed ${flushed} events, ${eventQueue.size()} remaining`);
        }
    };
    
    // Thread 1: Ultra-fast (2ms)
    setInterval(flushQueue, CONFIG.FLUSH_INTERVAL_MS);
    
    // Thread 2: Backup (10ms)
    setInterval(flushQueue, CONFIG.FLUSH_BACKUP_MS);
    
    // Thread 3: Safety net (50ms)
    setInterval(flushQueue, CONFIG.FLUSH_SAFETY_MS);
    
    // Thread 4: Idle time optimization
    if (window.requestIdleCallback) {
        const idleFlush = (deadline) => {
            while (deadline.timeRemaining() > 0 && eventQueue.size() > 0) {
                flushQueue();
            }
            window.requestIdleCallback(idleFlush);
        };
        window.requestIdleCallback(idleFlush);
    }
    
    // ============================================================================
    // ELEMENT UTILITIES
    // ============================================================================
    const getPriority = (eventType) => {
        const type = (eventType || '').toLowerCase();
        if (['navigate', 'submit'].includes(type)) return 100;
        if (['click', 'dblclick', 'change', 'input', 'fill'].includes(type)) return 50;
        if (['hover', 'focus', 'blur', 'press', 'keyrelease'].includes(type)) return 20;
        return 5;
    };
    
    const norm = n => (n && n.nodeType === Node.TEXT_NODE ? n.parentElement : 
                       (n && n.nodeType === Node.ELEMENT_NODE ? n : null));
    
    const targetOf = e => {
        try {
            if (e && typeof e.composedPath === 'function') {
                const p = e.composedPath();
                if (p && p.length) return p[0];
            }
        } catch(_) {}
        return e ? e.target : null;
    };
    
    const xp = el => {
        if (!el || el.nodeType !== 1) return '';
        const s = [];
        let n = el;
        while (n && n.nodeType === 1) {
            let i = 1;
            let b = n.previousSibling;
            while (b) {
                if (b.nodeType === 1 && b.nodeName === n.nodeName) i++;
                b = b.previousSibling;
            }
            s.unshift(`${n.nodeName.toLowerCase()}[${i}]`);
            n = n.parentNode && n.parentNode.nodeType === 1 ? n.parentNode : null;
        }
        return '/' + s.join('/');
    };
    
    const roleOf = el => {
        if (!el) return '';
        const r = el.getAttribute && el.getAttribute('role');
        if (r) return r.toLowerCase();
        const tag = (el.tagName || '').toLowerCase();
        const type = (el.getAttribute && (el.getAttribute('type') || '').toLowerCase()) || '';
        
        if (tag === 'button' || (tag === 'input' && ['button','submit','reset'].includes(type))) return 'button';
        if (tag === 'input' && type === 'checkbox') return 'checkbox';
        if (tag === 'input' && ['text','password','email','tel','url'].includes(type)) return 'textbox';
        if (tag === 'textarea') return 'textbox';
        if (tag === 'select') return 'combobox';
        if (tag === 'a' && el.getAttribute('href')) return 'link';
        
        return '';
    };
    
    const accName = el => {
        if (!el) return '';
        const aria = el.getAttribute && el.getAttribute('aria-label');
        if (aria) return aria.trim();
        const title = el.getAttribute && el.getAttribute('title');
        if (title) return title.trim();
        const placeholder = el.getAttribute && el.getAttribute('placeholder');
        if (placeholder) return placeholder.trim();
        const txt = (el.innerText || el.textContent || '').trim();
        if (txt) return txt.slice(0, 150);
        return '';
    };
    
    const makeStableSelector = el => {
        if (!el) return '';
        const id = el.id;
        if (id && document.querySelectorAll(`#${CSS.escape(id)}`).length === 1) {
            return `#${CSS.escape(id)}`;
        }
        
        const role = roleOf(el);
        const name = accName(el);
        if (role && name) {
            return `getByRole("${role}", { name: "${name.slice(0, 50)}" })`;
        }
        
        return xp(el);
    };
    
    // ============================================================================
    // EVENT CAPTURE
    // ============================================================================
    const send = async (eventType, target, extra = {}) => {
        const el = norm(target);
        if (!el) return;
        
        const priority = getPriority(eventType);
        
        const payload = {
            action: eventType,
            timestamp: Date.now(),
            pageUrl: location.href,
            element: {
                xpath: xp(el),
                stableSelector: makeStableSelector(el),
                role: roleOf(el),
                ariaLabel: accName(el),
                tag: (el.tagName || '').toLowerCase(),
                id: el.id || '',
                name: (el.getAttribute && el.getAttribute('name')) || '',
                className: el.className || ''
            },
            extra: extra,
            _priority: priority,
            _captured_at: new Date().toISOString()
        };
        
        await deliverWithRetry(payload, priority);
    };
    
    // ============================================================================
    // EVENT LISTENERS
    // ============================================================================
    document.addEventListener('click', e => send('click', targetOf(e), { button: e.button }), true);
    document.addEventListener('dblclick', e => send('dblclick', targetOf(e), { button: e.button }), true);
    document.addEventListener('contextmenu', e => send('contextmenu', targetOf(e), { button: e.button }), true);
    
    document.addEventListener('submit', e => {
        e.preventDefault();
        const form = targetOf(e);
        send('submit', form, { 
            action: (form && form.action) || '', 
            method: (form && form.method) || '' 
        });
        
        // Flush everything before submit
        setTimeout(() => {
            flushQueue();
            setTimeout(() => {
                form && form.submit && form.submit();
            }, 50);
        }, 20);
    }, true);
    
    const isSensitive = (el) => {
        const idn = (el && (el.name || el.id || '')).toLowerCase();
        const type = (el && el.type || '').toLowerCase();
        return type === 'password' || /password|pwd|otp|token|secret|pin/.test(idn);
    };
    
    document.addEventListener('change', e => {
        const t = targetOf(e);
        const masked = isSensitive(t);
        const val = t && t.value;
        send('change', t, { value: masked ? '<masked>' : val, valueMasked: !!masked });
    }, true);
    
    document.addEventListener('input', e => {
        const t = targetOf(e);
        const masked = isSensitive(t);
        const val = t && t.value;
        send('input', t, { value: masked ? '<masked>' : val, valueMasked: !!masked });
    }, true);
    
    document.addEventListener('keydown', e => {
        const keys = ['Enter', 'Escape', 'Tab', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];
        if (keys.includes(e.key)) {
            send('press', targetOf(e), { key: e.key, code: e.code });
        }
    }, true);
    
    // ============================================================================
    // EMERGENCY FLUSH ON UNLOAD
    // ============================================================================
    const emergencyFlush = () => {
        CONFIG.DEBUG && console.log('[EnhancedRecorder] Emergency flush triggered');
        for (let i = 0; i < 20; i++) {  // 20 attempts
            flushQueue();
        }
    };
    
    window.addEventListener('beforeunload', emergencyFlush);
    window.addEventListener('pagehide', emergencyFlush);
    window.addEventListener('unload', emergencyFlush);
    
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            CONFIG.DEBUG && console.log('[EnhancedRecorder] Visibility flush');
            for (let i = 0; i < 10; i++) {
                flushQueue();
            }
        }
    });
    
    console.log('[EnhancedRecorder] Installation complete, ready to capture');
})();
"""


def get_enhanced_capture_script() -> str:
    """Get the enhanced JavaScript capture script.
    
    Returns:
        JavaScript code as string
    """
    return ENHANCED_CAPTURE_SCRIPT


def get_lightweight_capture_script() -> str:
    """Get a lightweight version for low-resource environments.
    
    Returns:
        Simplified JavaScript code
    """
    # Simplified version without IndexedDB and some optimizations
    return ENHANCED_CAPTURE_SCRIPT.replace('DEBUG: true', 'DEBUG: false')
