#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全书静态自检：目录数据、页面结构、内链、代码块、SVG、WAV 与实验实跑。

用法:
  python3 tools/check_book.py             # 静态自检
  python3 tools/check_book.py --run       # 额外实跑全部 code/*.py
  python3 tools/check_book.py --urls      # 额外联网探测外链（慢，默认不做）
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import subprocess
import sys
import wave
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from book_data import CHAPTERS, BY_ID, problems  # noqa: E402
from book_schema import PARTS  # noqa: E402

VOID = {"img", "meta", "link", "br", "hr", "input", "source", "area", "base", "col", "embed", "param"}
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*?)(/?)>", re.DOTALL)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']')
SRC_RE = re.compile(r'src=["\']([^"\']+)["\']')
ID_RE = re.compile(r'id="([^"]+)"')
CODE_RE = re.compile(r'<pre\s+class="code"\s+data-file="([^"]+)"[^>]*><code>(.*?)</code></pre>', re.DOTALL)
PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}|@DOC@|APPEND_CHAPTERS_HERE|APPEND_BUILD_HERE|TODO_|MISSING")

REQUIRED_IDS = ["map", "lab", "pitfalls", "exercises", "extra-links"]


def rel(p):
    return str(p.relative_to(ROOT))


def check_toc(errors, hints):
    path = ROOT / "assets/toc.js"
    if not path.exists():
        errors.append("缺少 assets/toc.js")
        return
    text = path.read_text(encoding="utf-8")
    m = re.search(r"window\.BOOK_TOC\s*=\s*(\{.*?\});\s*\n", text, re.DOTALL)
    if not m:
        errors.append("assets/toc.js 中找不到 window.BOOK_TOC")
        return
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        errors.append("assets/toc.js 的 JSON 无法解析: %s" % e)
        return
    parts = data.get("parts", [])
    if len(parts) != len(PARTS):
        errors.append("toc.js 分部数量与 book_schema.PARTS 不一致")
    ids = [c["id"] for p in parts for c in p.get("chapters", [])]
    if ids != [c["id"] for c in CHAPTERS]:
        errors.append("toc.js 章节顺序与 book_data.CHAPTERS 不一致")
    for p in parts:
        if not p.get("stage"):
            errors.append("toc.js 分部缺少卷信息: " + str(p.get("id")))
    if "window.BOOK_FLAT" not in text:
        errors.append("assets/toc.js 缺少 BOOK_FLAT 扁平目录")


def check_tag_balance(path, text, errors):
    stack = []
    for m in TAG_RE.finditer(text):
        closing, tag, attrs, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if tag in ("!doctype",):
            continue
        if tag in VOID or selfclose == "/":
            continue
        if not closing:
            stack.append((tag, m.start()))
        else:
            if not stack:
                errors.append("%s: 多余的 </%s>" % (rel(path), tag))
                return
            top, pos = stack.pop()
            if top != tag:
                errors.append("%s: 标签不匹配 <%s> 与 </%s>（约 %d 字节处）" %
                              (rel(path), top, tag, pos))
                return
    if stack:
        errors.append("%s: 未闭合标签 <%s>" % (rel(path), stack[-1][0]))


def check_links(path, text, errors, hints):
    base = path.parent
    ids = set(ID_RE.findall(text))
    urls = HREF_RE.findall(text) + SRC_RE.findall(text)
    for href in urls:
        if href.startswith(("http://", "https://", "mailto:", "data:")):
            continue
        if href.startswith("#"):
            if href[1:] not in ids:
                errors.append("%s: 页内锚点不存在 %s" % (rel(path), href))
            continue
        clean = href.split("#", 1)[0]
        if not clean:
            continue
        target = (base / clean).resolve()
        if not target.exists():
            errors.append("%s: 失效链接 %s" % (rel(path), href))
        elif "#" in href:
            anchor = href.split("#", 1)[1]
            try:
                other = target.read_text(encoding="utf-8")
                if anchor not in set(ID_RE.findall(other)):
                    hints.append("%s: 跨页锚点可能失效 %s" % (rel(path), href))
            except (OSError, UnicodeDecodeError):
                pass


def check_page(path, is_index, errors, hints):
    text = path.read_text(encoding="utf-8")
    if "<!DOCTYPE html>" not in text or "</html>" not in text:
        errors.append("%s: HTML 结构不完整" % rel(path))
    for fragment, label in (
        ('<aside id="sidebar">', "侧栏容器"),
        ('<main class="book-page">', "主内容容器"),
        ('class="breadcrumb', "面包屑"),
        ('class="site-foot"', "页脚"),
        ("本教材的知识框架", "作者与 AI 使用说明"),
        ("assets/toc.js", "目录脚本"),
        ("assets/app.js", "交互脚本"),
        ("assets/style.css", "样式表"),
    ):
        if fragment not in text:
            errors.append("%s: 缺少%s" % (rel(path), label))
    if not is_index:
        if 'class="pager"' not in text:
            errors.append("%s: 缺少上下章导航" % rel(path))
        for rid in REQUIRED_IDS:
            if 'id="' + rid + '"' not in text:
                errors.append("%s: 缺少栏目 #%s" % (rel(path), rid))
        if "知识点地图" not in text or "给程序员的翻译" not in text:
            errors.append("%s: 缺少知识点地图或程序员类比" % rel(path))
        if "常见误区" not in text or "习题与思考" not in text:
            errors.append("%s: 缺少误区或习题栏目" % rel(path))
    bad = PLACEHOLDER_RE.findall(text)
    if bad:
        errors.append("%s: 残留占位符 %s" % (rel(path), sorted(set(bad))[:3]))
    check_tag_balance(path, text, errors)
    check_links(path, text, errors, hints)


def check_code_sync(errors, hints):
    from extract_code import collect
    try:
        wanted = collect()
    except SystemExit as e:
        errors.append(str(e))
        return []
    for relpath, code in wanted.items():
        path = ROOT / relpath
        if not path.exists():
            errors.append("缺少实验脚本: " + relpath)
            continue
        if path.read_text(encoding="utf-8") != code:
            errors.append("代码块与磁盘脚本不一致: " + relpath)
        try:
            compile(code, relpath, "exec")
        except SyntaxError as e:
            errors.append("实验脚本语法错误 %s: %s" % (relpath, e))
    known = set(wanted)
    for path in sorted(ROOT.glob("part*/**/code/*.py")):
        if str(path.relative_to(ROOT)) not in known:
            errors.append("孤立的 code/*.py: " + rel(path))
    return list(wanted)


def check_assets(errors, hints):
    expected_figs, expected_wavs = set(), set()
    for ch in CHAPTERS:
        for d in ch["demos"]:
            for fname, _cap in d["figs"]:
                expected_figs.add(ch["folder"] + "/" + fname)
            for fname, _cap in d["audio"]:
                expected_wavs.add(ch["folder"] + "/" + fname)
    for f in sorted(expected_figs):
        path = ROOT / f
        if not path.exists():
            errors.append("缺少 SVG 插图: " + f)
            continue
        try:
            ET.parse(str(path))
        except ET.ParseError as e:
            errors.append("SVG 不是合法 XML %s: %s" % (f, e))
        if path.stat().st_size < 200:
            hints.append("SVG 文件过小，可能是空图: " + f)
    for f in sorted(expected_wavs):
        path = ROOT / f
        if not path.exists():
            errors.append("缺少 WAV 试听样本: " + f)
            continue
        try:
            with wave.open(str(path), "rb") as w:
                if w.getframerate() != 16000:
                    errors.append("WAV 采样率不是 16 kHz: %s (%d Hz)" % (f, w.getframerate()))
                if w.getnchannels() != 1 or w.getsampwidth() != 2:
                    errors.append("WAV 不是 16-bit 单声道: " + f)
                if w.getnframes() < 100:
                    errors.append("WAV 帧数过少: " + f)
        except (wave.Error, OSError) as e:
            errors.append("WAV 文件损坏 %s: %s" % (f, e))
    for path in sorted(ROOT.glob("part*/**/fig/*.svg")):
        if str(path.relative_to(ROOT)) not in expected_figs:
            hints.append("孤立的 SVG: " + rel(path))
    for path in sorted(ROOT.glob("part*/**/audio/*.wav")):
        if str(path.relative_to(ROOT)) not in expected_wavs:
            hints.append("孤立的 WAV: " + rel(path))
    return len(expected_figs), len(expected_wavs)


def check_urls(errors, hints):
    """并发探测外链；区分「明确 4xx/5xx」与「本机网络/站点策略不可达」。"""
    import concurrent.futures as cf
    import urllib.error
    import urllib.request
    from book_resources import R

    def probe(item):
        key, (_name, url, _desc, _cat) = item
        req = urllib.request.Request(
            url, method="GET",
            headers={"User-Agent": "Mozilla/5.0 (audio3A book link check)",
                     "Range": "bytes=0-0"})
        try:
            with urllib.request.urlopen(req, timeout=6) as r:
                return key, r.status, None
        except urllib.error.HTTPError as e:
            return key, e.code, None
        except Exception as e:
            return key, None, type(e).__name__

    bad, unreachable = 0, 0
    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        for key, status, exc in pool.map(probe, R.items()):
            if status is not None and status >= 400:
                errors.append("外链返回 %d: %s (%s)" % (status, key, R[key][1]))
                bad += 1
            elif status is None:
                hints.append("外链探测失败（本机网络或站点策略）: %s %s" % (key, exc))
                unreachable += 1
    print("外链探测: %d 条资源，%d 条明确错误，%d 条本机不可达" %
          (len(R), bad, unreachable))


def run_scripts(scripts, errors, hints):
    ok = 0
    for relpath in sorted(scripts):
        path = ROOT / relpath
        proc = subprocess.run([sys.executable, str(path)], cwd=str(ROOT),
                              capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            errors.append("实验运行失败 %s: %s" % (relpath, proc.stderr.strip()[-300:]))
        else:
            ok += 1
            if "Traceback" in proc.stdout:
                hints.append("实验输出含 Traceback 字样: " + relpath)
    print("实跑实验: 成功 %d / %d" % (ok, len(scripts)))


def main():
    ap = argparse.ArgumentParser(description="音频 3A 教材全书自检")
    ap.add_argument("--run", action="store_true", help="实跑全部 code/*.py")
    ap.add_argument("--urls", action="store_true", help="联网探测外部链接")
    args = ap.parse_args()

    errors, hints = [], []
    for p in problems():
        errors.append("数据层: " + p)
    check_toc(errors, hints)

    pages = [ROOT / "index.html"] + [ROOT / c["folder"] / "index.html" for c in CHAPTERS]
    for path in pages:
        if not path.exists():
            errors.append("缺少页面: " + rel(path))
            continue
        check_page(path, path == ROOT / "index.html", errors, hints)

    scripts = check_code_sync(errors, hints)
    nfig, nwav = check_assets(errors, hints)

    if args.run:
        run_scripts(scripts, errors, hints)
    if args.urls:
        check_urls(errors, hints)

    for e in errors:
        print("错误:", e)
    for h in hints:
        print("提示:", h)
    print("自检：%d 个 HTML 页面，%d 个章节，%d 个 Python 脚本，%d 张 SVG 图，"
          "%d 段 WAV，%d 条错误，%d 条提示" %
          (len(pages), len(CHAPTERS), len(scripts), nfig, nwav, len(errors), len(hints)))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
