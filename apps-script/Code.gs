/**
 * Courtside Edge as a Google Apps Script web app.
 * Deploy > New deployment > Web app. Every open loads fresh NBA data.
 */
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Courtside Edge')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1, viewport-fit=cover');
}

// Server-side fetch, used only when the browser can't reach ESPN directly.
// Limited to ESPN's public NBA feeds and The Odds API's NBA odds so the web app can't be used as an open proxy.
var ALLOWED = /^https:\/\/((site\.api|site\.web\.api)\.espn\.com\/apis\/[^\s]*basketball\/nba\/|api\.the-odds-api\.com\/v4\/sports\/basketball_nba\/)/;

function proxy(url) {
  if (!ALLOWED.test(url)) throw new Error('URL not allowed');
  var cache = CacheService.getScriptCache();
  var key = Utilities.base64EncodeWebSafe(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, url));
  var hit = cache.get(key);
  if (hit) return hit;
  var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) throw new Error('HTTP ' + res.getResponseCode());
  var body = res.getContentText();
  if (body.length < 90000) cache.put(key, body, 300); // 5 minutes; cache values max out near 100 KB
  return body;
}
