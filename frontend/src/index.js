import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// Mitigate Chrome's ResizeObserver loop warning by deferring observer callbacks.
if (typeof window !== 'undefined' && typeof window.ResizeObserver === 'function') {
  console.log('🔧 [ResizeObserver] Patching ResizeObserver...');
  const NativeResizeObserver = window.ResizeObserver;

  window.ResizeObserver = class ResizeObserver {
    constructor(callback) {
      this._callback = callback;
      this._observer = new NativeResizeObserver((entries) => {
        window.requestAnimationFrame(() => this._callback(entries, this));
      });
    }

    observe(target, options) {
      this._observer.observe(target, options);
    }

    unobserve(target) {
      this._observer.unobserve(target);
    }

    disconnect() {
      this._observer.disconnect();
    }
  };
  console.log('✅ [ResizeObserver] Patched successfully');
}

// Ignore benign ResizeObserver loop errors triggered by Chrome devtools/react overlays.
const isResizeObserverLoopError = (error) => {
  if (!error) return false;
  if (typeof error === 'string') return error.includes('ResizeObserver loop');
  if (typeof error === 'object' && typeof error.message === 'string') {
    return error.message.includes('ResizeObserver loop');
  }
  return false;
};

window.addEventListener(
  'error',
  (event) => {
    if (isResizeObserverLoopError(event) || isResizeObserverLoopError(event?.message) || isResizeObserverLoopError(event?.error)) {
      console.log('🚫 [ResizeObserver] Blocked error event:', event?.message || event?.error?.message);
      event.stopImmediatePropagation();
      event.preventDefault();
    }
  },
  true
);
console.log('✅ [ResizeObserver] Error event listener registered');

window.addEventListener('unhandledrejection', (event) => {
  if (isResizeObserverLoopError(event?.reason)) {
    event.preventDefault();
  }
});

const originalConsoleError = window.console.error.bind(window.console);
window.console.error = (...args) => {
  if (args.some((arg) => isResizeObserverLoopError(arg))) {
    console.log('🚫 [ResizeObserver] Blocked console.error:', args[0]);
    return;
  }
  originalConsoleError(...args);
};
console.log('✅ [ResizeObserver] Console.error patched');

const patchReactErrorOverlay = () => {
  const overlay = window.ReactErrorOverlay;
  if (!overlay) {
    console.log('⚠️ [ResizeObserver] ReactErrorOverlay not found yet');
    return;
  }
  if (overlay.__hasResizeObserverPatch) {
    console.log('✅ [ResizeObserver] ReactErrorOverlay already patched');
    return;
  }

  console.log('🔧 [ResizeObserver] Patching ReactErrorOverlay...');

  const originalReportRuntimeError = overlay.reportRuntimeError?.bind(overlay);
  const originalHandleRuntimeError = overlay.handleRuntimeError?.bind(overlay);

  if (originalReportRuntimeError) {
    overlay.reportRuntimeError = (error, ...rest) => {
      if (isResizeObserverLoopError(error)) {
        console.log('🚫 [ResizeObserver] Blocked reportRuntimeError:', error?.message);
        return undefined;
      }
      return originalReportRuntimeError(error, ...rest);
    };
    console.log('✅ [ResizeObserver] Patched reportRuntimeError');
  }

  if (originalHandleRuntimeError) {
    overlay.handleRuntimeError = (error, ...rest) => {
      if (isResizeObserverLoopError(error)) {
        console.log('🚫 [ResizeObserver] Blocked handleRuntimeError:', error?.message);
        return undefined;
      }
      return originalHandleRuntimeError(error, ...rest);
    };
    console.log('✅ [ResizeObserver] Patched handleRuntimeError');
  }

  overlay.__hasResizeObserverPatch = true;
  console.log('✅ [ResizeObserver] ReactErrorOverlay patched successfully');
};

const ensureOverlayPatched = () => {
  if (window.ReactErrorOverlay) {
    patchReactErrorOverlay();
    return true;
  }
  return false;
};

if (!ensureOverlayPatched()) {
  console.log('⏳ [ResizeObserver] Waiting for ReactErrorOverlay to load...');

  const tryPatch = () => {
    if (ensureOverlayPatched()) {
      console.log('✅ [ResizeObserver] ReactErrorOverlay found and patched (via load event)');
      window.removeEventListener('load', tryPatch);
    }
  };

  window.addEventListener('load', tryPatch);

  const overlayInterval = setInterval(() => {
    if (ensureOverlayPatched()) {
      console.log('✅ [ResizeObserver] ReactErrorOverlay found and patched (via interval)');
      clearInterval(overlayInterval);
    }
  }, 250);
} else {
  console.log('✅ [ResizeObserver] ReactErrorOverlay already available and patched');
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
