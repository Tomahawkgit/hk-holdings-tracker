// loader.js —— 数据加载：先渲染内联兜底，再按「云端 raw → jsDelivr → 站内文件」三级拉取最新数据。
// 用法：loadData({ remoteUrls, localUrl, fallback, render, valid?, merge?, onFail? })
//   valid: 校验函数（默认 d && d.stocks && d.stocks.length）
//   merge: true 使用默认合并策略（保留 cache 里有、云端没有的标的），或传自定义 function(remote, cache)
//   onFail: 全部数据源都失败时回调（可选）
(function (global) {
  function defaultValid(d) { return d && d.stocks && d.stocks.length; }

  function defaultMerge(remote, cache) {
    var codes = {};
    (remote && remote.stocks || []).forEach(function (s) { codes[s.code] = true; });
    var extras = (cache && cache.stocks || []).filter(function (s) { return !codes[s.code]; });
    if (!extras.length) return remote;
    return { updated: remote.updated, stocks: remote.stocks.concat(extras) };
  }

  function loadData(opts) {
    var fallback = opts.fallback;
    var render = opts.render;
    var valid = opts.valid || defaultValid;
    var merge = opts.merge === true ? defaultMerge : (opts.merge || null);
    var remoteUrls = opts.remoteUrls || [];
    var localUrl = opts.localUrl;
    var onFail = opts.onFail;
    var cache = fallback;

    function safeRender(d) {
      cache = d;
      try { render(d); } catch (e) {}
    }
    function merged(d) { return merge ? merge(d, cache) : d; }
    function fail() { if (onFail) { try { onFail(); } catch (e) {} } }

    safeRender(fallback);
    if (typeof fetch !== 'function') return;

    function loadLocal() {
      fetch(localUrl, { cache: 'no-store' }).then(function (r) {
        if (!r.ok) throw new Error('http ' + r.status);
        return r.json();
      }).then(function (d) {
        if (valid(d)) safeRender(merged(d)); else fail();
      }).catch(fail);
    }
    function loadRemote(i) {
      if (i >= remoteUrls.length) { loadLocal(); return; }
      fetch(remoteUrls[i] + '?t=' + Date.now(), { cache: 'no-store' }).then(function (r) {
        if (!r.ok) throw new Error('http ' + r.status);
        return r.json();
      }).then(function (d) {
        if (valid(d)) safeRender(merged(d)); else loadRemote(i + 1);
      }).catch(function () { loadRemote(i + 1); });
    }
    loadRemote(0);
  }

  global.loadData = loadData;
})(window);
