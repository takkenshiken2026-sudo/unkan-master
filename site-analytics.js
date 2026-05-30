// Google Analytics 4 — window.__GA4_MEASUREMENT_ID__ で上書き可（未設定・空なら下記の既定ID）
// 測定IDの正: tools/html_footer.GA4_MEASUREMENT_ID と揃えること
(function () {
  var DEFAULT_MID = "G-Q47X42S88D";
  var raw = "";
  try {
    if (typeof window !== "undefined" && window.__GA4_MEASUREMENT_ID__ != null) {
      raw = String(window.__GA4_MEASUREMENT_ID__).trim();
    }
    if (!raw && typeof window !== "undefined" && window.SITE_CONFIG && window.SITE_CONFIG.ga4MeasurementId != null) {
      raw = String(window.SITE_CONFIG.ga4MeasurementId).trim();
    }
  } catch (_e) {}
  if (!raw) raw = DEFAULT_MID;
  var MID = /^G-[A-Za-z0-9]+$/.test(raw) ? raw : "";
  if (!MID) return;

  /**
   * SPA 等で URL・title が変わったあとに呼ぶ。index.html の gotoPage / popstate から利用。
   * 引数省略時は現在の location + document.title。
   */
  function ga4PageView(pagePath, pageTitle) {
    if (typeof window.gtag !== "function") return;
    var path = pagePath != null && String(pagePath) ? String(pagePath) : "";
    if (!path && typeof location !== "undefined") {
      path = location.pathname + location.search + location.hash;
    }
    var title = pageTitle != null ? String(pageTitle) : typeof document !== "undefined" ? document.title : "";
    try {
      var o = { page_path: path, page_title: title };
      if (typeof location !== "undefined" && location.href) {
        o.page_location = location.href;
      }
      window.gtag("config", MID, o);
    } catch (_e) {}
  }
  window.ga4PageView = ga4PageView;

  if (window.__GA4_SNIPPET_INIT__ === MID) return;
  window.__GA4_SNIPPET_INIT__ = MID;

  try {
    if (document.querySelector('script[src*="googletagmanager.com/gtag/js"][data-ga4-mid="' + MID + '"]')) {
      ga4PageView();
      return;
    }
  } catch (_e) {}

  window.dataLayer = window.dataLayer || [];
  function gtag() {
    window.dataLayer.push(arguments);
  }
  window.gtag = gtag;
  gtag("js", new Date());

  var s = document.createElement("script");
  s.async = true;
  s.setAttribute("data-ga4-mid", MID);
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(MID);
  document.head.appendChild(s);

  try {
    var cfg0 = {};
    if (typeof location !== "undefined" && location.href) {
      cfg0.page_location = location.href;
      cfg0.page_path = location.pathname + location.search + location.hash;
    }
    if (typeof document !== "undefined" && document.title) {
      cfg0.page_title = document.title;
    }
    gtag("config", MID, cfg0);
  } catch (_e2) {}
})();
