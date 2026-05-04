import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import "@/chartStyles.css";
import App from "@/App.js";

// Fix lightweight-charts locale issue with POSIX suffix
// Override Date.prototype.toLocaleString to use valid locale
const originalToLocaleString = Date.prototype.toLocaleString;
const originalToLocaleDateString = Date.prototype.toLocaleDateString;
const originalToLocaleTimeString = Date.prototype.toLocaleTimeString;

const fixLocale = (locale) => {
  if (typeof locale === 'string' && locale.includes('@posix')) {
    return locale.replace('@posix', '');
  }
  return locale;
};

Date.prototype.toLocaleString = function(locale, options) {
  return originalToLocaleString.call(this, fixLocale(locale), options);
};

Date.prototype.toLocaleDateString = function(locale, options) {
  return originalToLocaleDateString.call(this, fixLocale(locale), options);
};

Date.prototype.toLocaleTimeString = function(locale, options) {
  return originalToLocaleTimeString.call(this, fixLocale(locale), options);
};

// Also patch Intl.DateTimeFormat
const OriginalDateTimeFormat = Intl.DateTimeFormat;
Intl.DateTimeFormat = function(locale, options) {
  return new OriginalDateTimeFormat(fixLocale(locale), options);
};
Intl.DateTimeFormat.prototype = OriginalDateTimeFormat.prototype;
Intl.DateTimeFormat.supportedLocalesOf = OriginalDateTimeFormat.supportedLocalesOf;

// Suppress MetaMask errors until we implement Web3 integration
const originalError = console.error;
console.error = (...args) => {
  const errorMessage = args[0]?.toString() || '';
  
  // Ignore MetaMask-related errors (we'll implement this later)
  if (
    errorMessage.includes('MetaMask') ||
    errorMessage.includes('ethereum') && errorMessage.includes('connect')
  ) {
    return; // Silently ignore
  }
  
  originalError.apply(console, args);
};

// Global error handler for MetaMask runtime errors
window.addEventListener('error', (event) => {
  const msg = event.message || '';
  if (msg.includes('MetaMask') || msg.includes('Failed to connect')) {
    event.preventDefault();
    return true;
  }
});

window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason?.message || event.reason?.toString() || '';
  if (reason.includes('MetaMask') || reason.includes('Failed to connect')) {
    event.preventDefault();
    return true;
  }
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
