// shell.js —— 三个壳页共用：侧栏渲染（自动）+ 侧边栏滚动高亮 + iframe 自适应高度
(function (global) {
  // ---- 侧栏数据（三页共用，改这里即可同步三页） ----
  var NAV = [
    { href: "index.html", label: "宏观信号观察", icon: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M1.5 8h2.6l1.8-4.2 3 8.4 1.8-4.2h2.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
    { href: "holdings.html", label: "港股资金结构", icon: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6.4" stroke="currentColor" stroke-width="1.4"/><path d="M8 1.6V8l5.1 3.4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>' },
    { href: "ashare.html", label: "A股资金结构", icon: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><rect x="1.6" y="1.6" width="12.8" height="12.8" rx="2.5" stroke="currentColor" stroke-width="1.4"/><path d="M5 11.2V8.6M8 11.2V5M11 11.2V7.2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>' }
  ];
  var INDEX_SUBS = [
    { href: "#clocks", label: "两钟定位仪" },
    { href: "#states", label: "六态定位" },
    { href: "#metrics", label: "核心指标" },
    { href: "#alerts", label: "反向警报" },
    { href: "#calendar", label: "发布日历" }
  ];
  var SIDE_FOOT = '数据截至 2026-10-23<br>来源：东方财富·公开信息交叉验证<br>v3 · 三板块';
  var LOGO_SVG = '<svg width="17" height="17" viewBox="0 0 18 18" fill="none"><rect x="1.5" y="1.5" width="15" height="15" rx="3.5" stroke="#fff" stroke-width="1.6"/><line x1="9" y1="1.5" x2="9" y2="16.5" stroke="#fff" stroke-width="1.2" opacity=".7"/><line x1="1.5" y1="9" x2="16.5" y2="9" stroke="#fff" stroke-width="1.2" opacity=".7"/><circle cx="5.6" cy="5.4" r="2.1" fill="#fff"/></svg>';

  function currentPage() {
    var segs = (global.location.pathname || "").split("/").filter(Boolean);
    return segs[segs.length - 1] || "index.html";
  }

  function renderSidebar(active) {
    var aside = document.getElementById("sidebar");
    if (!aside) return;
    var html = '<div class="logo"><span class="lg-icon">' + LOGO_SVG + '</span>'
      + '<span><div class="lg-name">宏观股债观察</div><div class="lg-sub">Macro Sentinel</div></span></div>';
    html += '<nav class="nav"><div class="nav-label">看板板块</div>';
    NAV.forEach(function (item) {
      html += '<a href="' + item.href + '" class="lvl1' + (item.href === active ? ' active' : '') + '">' + item.icon + item.label + '</a>';
      if (active === "index.html" && item.href === "index.html") {
        INDEX_SUBS.forEach(function (s) {
          html += '<a href="' + s.href + '" class="sub">' + s.label + '</a>';
        });
      }
    });
    html += '</nav><div class="side-foot">' + SIDE_FOOT + '</div>';
    aside.innerHTML = html;
  }

  // ---- 侧边栏滚动高亮（仅当存在页内锚点导航时生效，如 index.html） ----
  function initScrollSpy() {
    var links = document.querySelectorAll('.nav a[href^="#"]');
    if (!links.length) return;
    var secs = [];
    links.forEach(function (a) {
      var el = document.querySelector(a.getAttribute('href'));
      if (el) secs.push({ a: a, el: el });
    });
    function onScroll() {
      var y = window.scrollY + 120;
      var cur = secs[0];
      secs.forEach(function (s) { if (s.el.offsetTop <= y) cur = s; });
      links.forEach(function (a) { a.classList.remove('active'); });
      if (cur) cur.a.classList.add('active');
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ---- iframe 自适应高度（仅当存在 #hf iframe 时生效，如 holdings/ashare） ----
  function initIframe() {
    var f = document.getElementById('hf');
    if (!f) return;
    function rs() {
      try {
        var h = f.contentDocument.documentElement.scrollHeight;
        if (h > 300) f.style.height = (h + 8) + 'px';
      } catch (e) { f.style.height = '1400px'; }
    }
    f.addEventListener('load', function () { rs(); setTimeout(rs, 600); setTimeout(rs, 1800); });
    window.addEventListener('resize', rs);
  }

  renderSidebar(currentPage());
  initScrollSpy();
  initIframe();

  global.Shell = { renderSidebar: renderSidebar };
})(window);
