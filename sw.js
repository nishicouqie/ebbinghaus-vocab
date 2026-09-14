/* 艾宾浩斯单词本 Service Worker：缓存壳（app-shell），数据永远走网络 */
var CACHE = "ehvocab-v3";
var SHELL = ["./", "./index.html", "./manifest.json", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var url = e.request.url;
  /* GitHub API（云同步）永远直连，不缓存 */
  if (url.indexOf("https://api.github.com") === 0) return;
  /* 页面与静态资源：缓存优先，后台刷新（stale-while-revalidate） */
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(function (hit) {
      var fetching = fetch(e.request).then(function (res) {
        if (res && res.ok && e.request.method === "GET") {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        }
        return res;
      }).catch(function () { return hit; });
      return hit || fetching;
    })
  );
});
