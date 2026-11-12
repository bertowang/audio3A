/* 全书交互：侧栏目录（按学习阶段分组）、面包屑、上下章、代码复制、主题、章节搜索。
   纯原生 JS，无外部依赖，file:// 直接双击即可工作。 */
(function () {
  "use strict";

  var root = document.body.dataset.root || "./";
  var chapterId = document.body.dataset.chapter || "";
  var pageId = document.body.dataset.page || "";
  var flat = window.BOOK_FLAT || [];
  var parts = (window.BOOK_TOC && window.BOOK_TOC.parts) || [];

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  /* ---------- 主题 ---------- */
  var savedTheme = null;
  try { savedTheme = localStorage.getItem("a3book-theme"); } catch (e) { /* ignore */ }
  if (savedTheme === "dark") document.documentElement.setAttribute("data-theme", "dark");

  function toggleTheme() {
    var isDark = document.documentElement.getAttribute("data-theme") === "dark";
    if (isDark) document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", "dark");
    try { localStorage.setItem("a3book-theme", isDark ? "light" : "dark"); } catch (e) { /* ignore */ }
    document.querySelectorAll(".theme-toggle").forEach(function (b) {
      b.textContent = isDark ? "深色" : "浅色";
    });
  }

  /* ---------- 侧边目录 ---------- */
  var sidebar = document.getElementById("sidebar");
  var themeBtn = null;
  if (sidebar && window.BOOK_TOC) {
    var brand = el("div", "side-brand");
    var brandLink = el("a", "", window.BOOK_TOC.title);
    brandLink.href = root + "index.html";
    brand.appendChild(brandLink);
    sidebar.appendChild(brand);
    sidebar.appendChild(el("div", "side-sub", window.BOOK_TOC.subtitle));

    var tools = el("div", "side-tools");
    var search = el("input");
    search.type = "search";
    search.placeholder = "筛选章节…";
    search.setAttribute("aria-label", "筛选章节");
    themeBtn = el("button", "theme-toggle", savedTheme === "dark" ? "浅色" : "深色");
    themeBtn.title = "切换深色 / 浅色";
    themeBtn.addEventListener("click", toggleTheme);
    tools.appendChild(search);
    tools.appendChild(themeBtn);
    sidebar.appendChild(tools);

    var lastVolume = "";
    parts.forEach(function (part) {
      if (part.stage && part.stage !== lastVolume) {
        sidebar.appendChild(el("div", "side-volume", part.stage));
        lastVolume = part.stage;
      }
      var h = el("div", "side-part", part.title);
      h.dataset.part = part.id;
      sidebar.appendChild(h);
      var ul = el("ul");
      ul.dataset.part = part.id;
      part.chapters.forEach(function (ch) {
        var li = el("li");
        var a = el("a");
        a.href = root + ch.path;
        a.appendChild(el("span", "num", ch.id));
        a.appendChild(document.createTextNode(ch.title));
        a.dataset.search = (ch.id + " " + ch.title + " " + part.title).toLowerCase();
        if (ch.id === chapterId || (pageId === "appendix" && ch.id === "A")) a.classList.add("active");
        li.appendChild(a);
        ul.appendChild(li);
      });
      sidebar.appendChild(ul);
    });

    var foot = el("div", "side-foot");
    foot.innerHTML = '每章附可运行的 <code>code/*.py</code> 实验脚本、<code>fig/*.svg</code> 图表与 <code>audio/*.wav</code> 试听样本<br>由 <code>tools/extract_code.py</code> 从 HTML 同步生成';
    sidebar.appendChild(foot);

    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      sidebar.querySelectorAll("ul[data-part]").forEach(function (ul) {
        var visible = 0;
        ul.querySelectorAll("li").forEach(function (li) {
          var a = li.querySelector("a");
          var hit = !q || (a.dataset.search || "").indexOf(q) >= 0;
          li.style.display = hit ? "" : "none";
          if (hit) visible++;
        });
        var head = sidebar.querySelector('.side-part[data-part="' + ul.dataset.part + '"]');
        if (head) head.style.display = q && !visible ? "none" : "";
      });
    });
  }

  /* ---------- 移动端菜单 ---------- */
  var menuBtn = el("button", "icon-btn", "目录");
  menuBtn.id = "menu-toggle";
  menuBtn.setAttribute("aria-label", "打开目录");
  menuBtn.addEventListener("click", function () { document.body.classList.toggle("nav-open"); });
  document.body.appendChild(menuBtn);
  document.querySelectorAll("#sidebar a").forEach(function (a) {
    a.addEventListener("click", function () { document.body.classList.remove("nav-open"); });
  });
  document.querySelectorAll(".theme-toggle").forEach(function (b) {
    if (b !== themeBtn && themeBtn) {
      b.textContent = savedTheme === "dark" ? "浅色" : "深色";
      b.addEventListener("click", toggleTheme);
    }
  });

  /* ---------- 面包屑 / 上下章 ---------- */
  var idx = -1;
  for (var i = 0; i < flat.length; i++) {
    if (flat[i].id === chapterId || (pageId === "appendix" && flat[i].id === "A")) { idx = i; break; }
  }
  var current = idx >= 0 ? flat[idx] : null;

  var crumb = document.querySelector(".breadcrumb[data-autofill]");
  if (crumb) {
    if (pageId === "index") {
      crumb.textContent = "总目录 · 全书入口";
    } else {
      crumb.innerHTML = "";
      var home = el("a", "", "总目录"); home.href = root + "index.html";
      crumb.appendChild(home);
      crumb.appendChild(document.createTextNode(" / "));
      crumb.appendChild(el("span", "", current ? current.partTitle : "附录"));
      if (current) {
        crumb.appendChild(document.createTextNode(" / "));
        crumb.appendChild(el("span", "", current.id === "A" ? "附录 A" : "第 " + current.id + " 章"));
      }
    }
  }

  var pager = document.querySelector(".pager[data-autofill]");
  if (pager && idx >= 0) {
    pager.innerHTML = "";
    function pageLink(item, label, cls) {
      if (!item) return el("span", "");
      var a = el("a", cls);
      a.href = root + item.path;
      a.appendChild(el("span", "lbl", label));
      a.appendChild(document.createTextNode(item.id + " · " + item.title));
      return a;
    }
    pager.appendChild(pageLink(flat[idx - 1], "← 上一章", "prev"));
    var toToc = el("a", "toc-link"); toToc.href = root + "index.html";
    toToc.appendChild(el("span", "lbl", "目录"));
    toToc.appendChild(document.createTextNode("总目录"));
    pager.appendChild(toToc);
    pager.appendChild(pageLink(flat[idx + 1], "下一章 →", "next"));
  }

  /* ---------- 代码块：文件名条 + 一键复制 ---------- */
  document.querySelectorAll("pre.code").forEach(function (pre) {
    var wrap = document.createElement("div");
    wrap.className = "code-wrap";
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);
    var bar = el("div", "code-bar");
    var lang = pre.dataset.lang || "Python 3 · 标准库";
    var fname = el("span", "fname", (pre.dataset.file || "snippet") + "  ·  " + lang);
    var btn = el("button", "", "复制");
    btn.type = "button";
    btn.addEventListener("click", function () {
      var text = pre.querySelector("code") ? pre.querySelector("code").textContent : pre.textContent;
      function done() { btn.textContent = "已复制"; setTimeout(function () { btn.textContent = "复制"; }, 1400); }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
      } else { fallback(text, done); }
    });
    bar.appendChild(fname);
    bar.appendChild(btn);
    wrap.insertBefore(bar, pre);
  });

  function fallback(text, done) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); done(); } catch (e) { btnFail(); }
    document.body.removeChild(ta);
  }
  function btnFail() {
    document.querySelectorAll(".code-bar button").forEach(function (b) { b.textContent = "请手动选中"; });
  }

  /* ---------- 首页进度统计 ---------- */
  document.querySelectorAll("[data-count]").forEach(function (node) {
    var kind = node.dataset.count;
    var n = flat.filter(function (c) { return c.status === kind && c.id !== "A"; }).length;
    node.textContent = n;
  });

  /* ---------- 页内目录（可选） ---------- */
  var localToc = document.querySelector("[data-local-toc]");
  if (localToc) {
    var list = el("ol");
    document.querySelectorAll(".book-page h2[id]").forEach(function (h) {
      var li = el("li");
      var a = el("a", "", h.textContent.replace(/^\d+(\.\d+)*\s*/, ""));
      a.href = "#" + h.id;
      li.appendChild(a); list.appendChild(li);
    });
    localToc.appendChild(list);
  }
})();
