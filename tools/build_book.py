#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态教材生成器：从结构化章节数据生成全部 HTML 与 assets/toc.js。

单一数据源：
  tools/book_data.py        -> CHAPTERS（正文与 Python 实验，分散在 chapters_*.py）
  tools/book_schema.py      -> PARTS（分卷、分部与全局约定）
  tools/book_resources.py   -> R / TOPIC_RULES / CHAPTER_RESOURCES（链接库）

用法:
  python3 tools/build_book.py            # 生成缺失的章节页（总目录与 toc.js 总是重建）
  python3 tools/build_book.py --force    # 全部重建（会覆盖手工修改的章节页）
  python3 tools/build_book.py --list     # 列出章节清单
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import pathlib
import posixpath
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from book_schema import (BOOK_TITLE, SUBTITLE, VERSION, PARTS, PART_BY_ID,  # noqa: E402
                         STAGE_CLASS, STAGE_SHORT, VOLUME_NOTES, VOLUME_BADGE,
                         DEMO_CONTRACT, DISCLAIMER_HTML)
from book_data import (CHAPTERS, BY_ID, chapters_of, demo_count,  # noqa: E402
                       fig_count, audio_count, command_count, link_count, problems)
from book_resources import (R, anchor, links_for_point, chapter_links_html,  # noqa: E402
                            all_resources_html, resource_card, repo_card)

STATUS_LABEL = {"done": "已完稿", "skeleton": "框架待补", "todo": "待建"}

CREDITS_HTML = (
    '<p class="credits"><strong>作者</strong>：汪亮（bertonwang）　'
    '<strong>联系邮箱</strong>：<a href="mailto:47608843@qq.com">47608843@qq.com</a></p>\n'
    '<p class="ai-note"><strong>AI 使用说明</strong>：本教材的知识框架、正文、Python 实验脚本与'
    '参考资料清单在 AI 辅助下整理生成，并经人工校订、实际运行与静态自检。公式、数值与运行结果请以'
    'Python 3 实际输出及权威教材、官方文档为准；发现错漏欢迎通过上方邮箱勘误。</p>'
)

RESOURCE_KEYS = [
    "webrtc-src", "ffmpeg-filters", "speexdsp", "rnnoise", "dns-challenge",
    "aec-challenge", "pyroomacoustics", "dspguide", "ccrma", "itu-g168",
    "ebu-r128", "python-docs",
]

REF_RE = re.compile(r"\{\{ch:([0-9]{2}|A)\}\}")


def esc(s):
    return html_mod.escape(str(s), quote=False)


def lih(items):
    """保留行内 <code> 等标记的列表项。"""
    return "\n".join("<li>" + x + "</li>" for x in items)


def head(title, root, index=False):
    title_text = (BOOK_TITLE + " · 总目录") if index else (esc(title) + " | " + BOOK_TITLE)
    return [
        "<!DOCTYPE html>", '<html lang="zh-CN">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>" + title_text + "</title>",
        '<link rel="stylesheet" href="' + root + 'assets/style.css">',
        '<script src="' + root + 'assets/toc.js" defer></script>',
        '<script src="' + root + 'assets/app.js" defer></script>',
        "</head>",
    ]


def footer(root="../../"):
    out = []
    if root != "./":
        out.append('<footer class="pager" data-autofill></footer>')
    out += ['<footer class="site-foot">', CREDITS_HTML,
            '<p class="imprint">' + BOOK_TITLE +
            ' · 每章一个 <code>code/*.py</code> 实验脚本、<code>fig/*.svg</code> 矢量图与'
            ' <code>audio/*.wav</code> 试听样本（由 <code>tools/extract_code.py</code> 与脚本运行同步）'
            ' · 只用 Python 3 标准库 · 教学材料，信号全部由代码合成。</p>',
            "</footer>", "</main>", "</body>", "</html>"]
    return out


def resolve_refs(text, root="./", start=""):
    """把 {{ch:NN}} / {{home}} / {{home#anchor}} 占位符解析成正确的相对链接。"""
    def repl(m):
        cid = m.group(1)
        target = BY_ID.get(cid)
        if target is None:
            raise KeyError("章节内链指向不存在的章节: " + cid)
        rel = posixpath.relpath(target["folder"] + "/index.html", start=start or ".")
        label = ("附录 A · " + target["title"]) if cid == "A" else (
            "第 " + cid + " 章 · " + target["title"])
        return "<a href='" + rel + "'>" + esc(label) + "</a>"
    text = REF_RE.sub(repl, text)
    for token, href, label in (
        ("{{home#roadmap}}", root + "index.html#roadmap", "全书学习路线"),
        ("{{home#toc}}", root + "index.html#toc", "全书目录"),
        ("{{home#howto}}", root + "index.html#howto", "使用说明"),
        ("{{home#python}}", root + "index.html#python", "运行实验"),
        ("{{home#contribute}}", root + "index.html#contribute", "维护约定"),
        ("{{home#resources}}", root + "index.html#resources", "参考资源"),
        ("{{home}}", root + "index.html", "总目录"),
    ):
        text = text.replace(token, "<a href='" + href + "'>" + label + "</a>")
    return text


# ---------------------------------------------------------------- 目录数据
def toc_js_text():
    parts = []
    for p in PARTS:
        parts.append({
            "id": p["id"], "title": p["title"], "stage": p["volume"],
            "chapters": [
                {"id": c["id"], "title": c["title"],
                 "path": c["folder"] + "/index.html", "status": c["status"]}
                for c in chapters_of(p["id"])
            ],
        })
    data = {"title": BOOK_TITLE, "subtitle": SUBTITLE, "parts": parts}
    flat = (
        "window.BOOK_FLAT = (function () {\n"
        "  const out = [];\n"
        "  (window.BOOK_TOC.parts || []).forEach(function (part) {\n"
        "    (part.chapters || []).forEach(function (ch) {\n"
        "      out.push(Object.assign({ partId: part.id, partTitle: part.title }, ch));\n"
        "    });\n"
        "  });\n"
        "  return out;\n"
        "})();\n"
    )
    return ("/* 由 tools/build_book.py 生成，请勿手工编辑。\n"
            "   目录、侧栏、面包屑、上下章导航共用这一份数据。 */\n"
            "window.BOOK_TOC = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n\n" + flat)


def toc_entry(c):
    path = c["folder"] + "/index.html"
    out = ["<li>", '<div class="toc-head"><span class="num">' + c["id"] + "</span>"
           '<a class="toc-title" href="' + path + '">' + esc(c["title"]) + "</a> "
           '<a class="toc-extra" href="' + path + '#extra-links">扩展阅读 →</a>'
           '<span class="badge ' + c["status"] + '">' + STATUS_LABEL[c["status"]] + "</span></div>",
           '<p class="toc-desc">' + c["lede"] + "</p>",
           '<ul class="toc-points">' + "".join("<li>" + esc(p) + "</li>" for p in c["points"]) + "</ul>",
           "</li>"]
    return "\n".join(out)


def toc_html():
    out = []
    last_volume = ""
    for p in PARTS:
        volume = p["volume"]
        if volume != last_volume:
            cls = " ai" if "AI" in volume else (" lower" if "附录" in volume else "")
            out.append('<div class="volume-banner' + cls + '"><h2>' + esc(volume) + "</h2>"
                       "<p>" + esc(VOLUME_NOTES.get(volume, "")) + "</p></div>")
            last_volume = volume
        pid = "卷首" if p["key"] == "pre" else ("附录" if p["key"] == "appendix"
                                             else p["title"].split(" · ")[0])
        out.append('<section class="toc-part"><h2><span class="part-id">' + pid + "</span>" +
                   esc(p["title"].split(" · ", 1)[-1]) + "</h2>")
        out.append('<ul class="toc-list">')
        out.extend(toc_entry(c) for c in chapters_of(p["id"]))
        out.append("</ul></section>")
    return "\n".join(out)


def resource_cards():
    out = ['<div class="repo-grid">']
    for k in RESOURCE_KEYS:
        name, url, desc, cat = R[k]
        out.append('<div class="repo-card"><h3>' + anchor(k, name) + "</h3>"
                   '<span class="tag">' + esc(cat) + "</span>"
                   "<p>" + esc(desc) + "</p>"
                   '<p style="margin:0"><code>' + esc(url) + "</code></p></div>")
    out.append("</div>")
    return "\n".join(out)


# ---------------------------------------------------------------- 首页
def render_index():
    out = head("", "./", index=True)
    out.append('<body data-root="./" data-page="index">')
    out.append('<aside id="sidebar"></aside>')
    out.append('<main class="book-page">')
    out.append('<nav class="breadcrumb" data-autofill>总目录</nav>')
    out.append('<header class="chapter-head">')
    out.append('<span class="kicker">Undergraduate → Graduate · AEC / ANS / AGC · Model-based & Data-driven</span>')
    out.append("<h1>" + BOOK_TITLE + "</h1>")
    out.append('<p class="lede">面向<strong>爱好音频处理的计算机专业学生</strong>的一本 3A 教材。'
               '全书不按「工具使用技巧」拼盘，而沿<strong>信号模型 → 时频工具 → 评价指标 → '
               '传统三大引擎 → 级联与工程链路 → 可学习掩码 → 神经 3A → 实时部署</strong>一条主线展开：'
               '把回声消除、噪声抑制与自动增益控制都还原成可推导的估计问题，'
               '再逐个替换为可学习的函数。每章给出原理、公式、可运行的 Python 实验、'
               '自绘 SVG 图与可试听的合成 WAV。</p>')
    out.append('<div class="meta">')
    out.append('<span class="badge done">全部 ' + str(len(CHAPTERS) - 1) + ' 章已完稿</span>')
    out.append('<span class="badge traditional">上卷 · 传统算法</span>')
    out.append('<span class="badge neural">下卷 · AI 算法</span>')
    out.append("<span>共 " + str(len(CHAPTERS) - 1) + " 章 · 4 卷 · 1 附录 · " +
               str(demo_count()) + " 个 Python 实验 · " + str(fig_count()) +
               " 张 SVG 图 · " + str(audio_count()) + " 段 WAV · " +
               str(command_count()) + " 条命令片段 · " + str(link_count()) + " 条参考链接</span>")
    out.append("<span>版本 " + VERSION + "</span>")
    out.append("</div></header>")

    out.append('<div class="card note"><span class="card-label">本书的主张</span>'
               '<p><strong>3A 是一套可验证的流式估计系统</strong>：房间是 FIR 滤波器，'
               'AEC 是在线系统辨识，ANS 是谱上的统计估计，AGC 是反馈控制器；'
               '下卷把同一批估计器换成网络，但链路结构、因果约束与评价指标完全不变。</p>'
               '<p style="margin-bottom:0">每章学习闭环固定为四步：'
               '<strong>读模型 → 跑代码 → 改参数 → 写结论</strong>；'
               '脚本用固定随机种子合成全部信号，打印可手算核对的数值，并画出可提交的 SVG 图与 WAV 样本。</p></div>')
    out.append(DISCLAIMER_HTML)

    out.append('<h2 id="howto">如何使用这本教材</h2>')
    out.append('<table><thead><tr><th style="width:24%">栏目</th><th>作用</th></tr></thead><tbody>'
               '<tr><td>本章位置 / 给程序员的翻译</td><td>说明承接什么、引出什么，并把概念映射到计算概念</td></tr>'
               '<tr><td>学习目标</td><td>学完应能做什么，用可检验的动词描述</td></tr>'
               '<tr><td>知识点地图</td><td>逐条列出知识点，每条挂 1～2 个直达参考链接</td></tr>'
               '<tr><td>原理小节 §x.y</td><td>概念、公式、对照表、边界条件与常见误区</td></tr>'
               '<tr><td>Python 实验</td><td>完整脚本 + 操作步骤 + 预期数值 + SVG 图 + 可试听 WAV</td></tr>'
               '<tr><td>命令片段</td><td>ffmpeg / WebRTC / 开源工程的可选真机实验，明确「以本机自查为准」</td></tr>'
               '<tr><td>参考资料 / 扩展学习</td><td>按知识点挑选的标准、课程、数据集与工具链接</td></tr>'
               '<tr><td>常见误区 / 习题</td><td>典型错误与可动手验证的思考题</td></tr>'
               '</tbody></table>')

    out.append('<h2 id="python">运行 Python 实验（30 秒）</h2>')
    out.append('<ol>'
               '<li>需要 Python 3.8+，<strong>不需要安装任何第三方包</strong>：'
               '实验只用 <code>math</code>、<code>random</code>、<code>statistics</code>、'
               '<code>wave</code> 等标准库，以及仓库内的 <code>tools/dsp.py</code>（纯标准库 DSP）'
               '与 <code>tools/chart.py</code>（纯标准库 SVG 绘图）。</li>'
               '<li>直接运行某一章脚本：<code>python3 part0/00-three-a/code/00-three-a.py</code>；'
               '或从页面代码块右上角「复制」。</li>'
               '<li>批量运行并生成全书插图与试听样本：<code>./tools/run_python.sh</code>；'
               '只跑某几个：<code>./tools/run_python.sh part1/05-adaptive-filter/code/05-nlms.py</code>。</li>'
               '<li>页面代码块与磁盘 <code>code/*.py</code> 由 <code>tools/extract_code.py</code> 自动同步，永远一致。</li>'
               '</ol>')
    out.append('<div class="card contract"><span class="card-label">给程序员的代码契约</span><ul style="margin-bottom:0">')
    for line in DEMO_CONTRACT.strip().splitlines()[1:]:
        out.append("<li>" + esc(line.strip()) + "</li>")
    out.append("</ul></div>")
    out.append('<p class="code-hint">为什么不用 <code>numpy</code> / <code>torch</code> / <code>matplotlib</code>？'
               '教材要展示的是算法本身与「图、声音是怎么生成的」。下卷涉及真实训练时，'
               '各章会给出 PyTorch / ONNX Runtime / 开源工程的进阶入口；'
               '附录 A.6 给出手写实现与工业库的对照表，学完之后应能无缝切换。</p>')
    out.append('<p class="code-hint">本机没有 ffmpeg 也能读完全书：'
               'ffmpeg / WebRTC 命令片段是<strong>可选真机实验</strong>，'
               '一律要求先用 <code>ffmpeg -filters</code> 与 <code>ffmpeg -version</code> 自查，'
               '本书不假定任何特定版本具备某项能力。</p>')

    out.append('<h2 id="roadmap">学习路线（建议两个学期）</h2>')
    out.append('<ol class="roadmap">'
               '<li><strong>卷首 · 共同语言（00～03）</strong>：3A 问题、房间冲激响应、'
               '采样与 STFT、ERLE / SI-SDR / LUFS 等指标族，先把「怎么算变好了」讲清楚。</li>'
               '<li><strong>上卷 · 传统算法（04～18）</strong>：卷积与 FFT、LMS/NLMS、FDAF、'
               '双讲与噪声估计，再分别实现 AEC / ANS / AGC，最后讨论级联顺序、'
               'ffmpeg/WebRTC 工具链与综合评测。</li>'
               '<li><strong>下卷 · AI 算法（19～31）</strong>：时频掩码、数据合成、网络骨架、'
               '复数域与相位，再逐个替换三大模块，最后落到因果流式、延迟预算、量化与泛化。</li>'
               '<li><strong>附录 A</strong>：公式、术语、命令与全书资源速查。</li>'
               '</ol>')
    short = ["00", "01", "02", "03", "05", "10", "12", "14", "16", "18",
             "19", "23", "26", "28", "30", "31"]
    out.append('<p>时间有限时的最短路径：' +
               " → ".join('<a href="' + BY_ID[c]["folder"] + '/index.html">' + c + "</a>"
                          for c in short) + ' → <a href="appendix/index.html">A</a>。</p>')

    out.append('<h2 id="toc">全书目录</h2>')
    out.append('<p class="lede">每一章一个文件夹，内含 <code>index.html</code>（知识讲解）、'
               '<code>code/*.py</code>（可直接运行的实验脚本）、<code>fig/*.svg</code>（脚本生成的矢量图）'
               '与 <code>audio/*.wav</code>（16 kHz 合成试听样本）。'
               '状态徽章：<span class="badge done">已完稿</span> 表示正文、知识点地图、'
               '参考链接、实验与插图齐备。</p>')
    out.append(toc_html())

    out.append('<h2 id="resources">参考资源</h2>')
    out.append('<p class="lede">以下为全书高频引用的标准、工具、开源工程与教材；'
               '完整清单（含数据集、百科条目与检索入口）见'
               '<a href="appendix/index.html#sA-7">附录 A.7 扩展学习链接总表</a>。'
               '书中提及的 ffmpeg 滤镜、WebRTC 模块与开源项目仅作技术说明，'
               '本书与这些项目无从属关系，也不构成产品推荐。</p>')
    out.append(resource_cards())

    out.append('<h2 id="contribute">维护约定</h2>')
    out.append('<p>全书由结构化数据生成，<strong>不要直接编辑章节 HTML</strong>，'
               '否则下次重建会被覆盖。改完数据后依次运行：'
               '<code>python3 tools/build_book.py --force</code> → '
               '<code>python3 tools/extract_code.py</code> → '
               '<code>./tools/run_python.sh</code> → '
               '<code>python3 tools/check_book.py --run</code>。</p>')
    out.append('<table><thead><tr><th style="width:28%">想改什么</th><th>编辑哪里</th></tr></thead><tbody>'
               '<tr><td>细化某章正文或 Python 实验</td><td><code>tools/chapters_*.py</code> 中对应的 <code>C(...)</code> / <code>mk_demo(...)</code></td></tr>'
               '<tr><td>加参考资料链接</td><td><code>tools/book_resources.py</code> 的 <code>R</code>、<code>TOPIC_RULES</code>、<code>CHAPTER_RESOURCES</code>，以及章节的 <code>highlights</code></td></tr>'
               '<tr><td>调整页面结构与总目录</td><td><code>tools/build_book.py</code> 的 <code>render()</code> / <code>render_index()</code></td></tr>'
               '<tr><td>样式与交互</td><td><code>assets/style.css</code>、<code>assets/app.js</code></td></tr>'
               '<tr><td>新增章节或分部</td><td><code>tools/book_schema.py</code> 的 <code>PARTS</code> + 对应 <code>chapters_*.py</code>，再重建</td></tr>'
               '<tr><td>新增 DSP 原语 / 图表类型</td><td><code>tools/dsp.py</code>、<code>tools/chart.py</code></td></tr>'
               "</tbody></table>")
    out.extend(footer("./"))
    return resolve_refs("\n".join(out) + "\n", root="./", start="")


# ---------------------------------------------------------------- 章节页
def appendix_sections(ch):
    """附录 A.5 / A.6 / A.7 由全书数据动态生成，保证与其它章节永远一致。"""
    rows = []
    for c in CHAPTERS:
        for d in c["demos"]:
            rel = "../" + c["folder"] + "/" + d["file"]
            label = "附录 A" if c["id"] == "A" else ("第 " + c["id"] + " 章")
            rows.append("<tr><td>" + label + " · " + esc(c["title"]) +
                        "</td><td><a href='" + rel + "'><code>" + esc(d["file"]) +
                        "</code></a></td><td>" + esc(d["title"]) + "</td></tr>")
    a5 = ("<p>全书 " + str(demo_count()) + " 个实验脚本、" + str(fig_count()) +
          " 张 SVG 图、" + str(audio_count()) + " 段 WAV 试听样本，"
          "全部只用 Python 3 标准库与 <code>tools/dsp.py</code>、<code>tools/chart.py</code>，"
          "固定 <code>random.seed(7)</code>，参数集中在「参数区」，结尾打印可核对的数值。"
          "点击文件名可直接查看源码。</p>"
          '<table><thead><tr><th style="width:34%">章节</th><th style="width:30%">脚本</th>'
          '<th>演示内容</th></tr></thead><tbody>' + "\n".join(rows) + "</tbody></table>")
    a6 = ("<p>本书为教学而手写实现，工业项目应切换到成熟库。下表给出迁移路径；"
          "所有脚本保持零第三方依赖，正是为了让这一步「看得见」。</p>"
          '<table><thead><tr><th style="width:34%">本书手写</th><th>工业实现</th><th>对应章节</th></tr></thead><tbody>'
          '<tr><td>radix-2 FFT / STFT / WOLA</td><td><code>numpy.fft</code>、<code>scipy.signal.stft</code>、'
          '<code>torchaudio.transforms.Spectrogram</code></td><td>02、19</td></tr>'
          '<tr><td>手写卷积 / overlap-add</td><td><code>scipy.signal.fftconvolve</code>、'
          '<code>pyroomacoustics</code> 的 RIR 与分块卷积</td><td>01、04</td></tr>'
          '<tr><td>NLMS / 频域自适应</td><td>WebRTC <code>aec3</code>、SpeexDSP '
          '<code>speex_echo_cancellation</code></td><td>05、06、10、11</td></tr>'
          '<tr><td>谱减 / Wiener / MMSE 增益</td><td>ffmpeg <code>afftdn</code> / <code>anlmdn</code>、'
          'RNNoise 频带增益</td><td>12、13、23</td></tr>'
          '<tr><td>包络 AGC / 响度近似</td><td>ffmpeg <code>dynaudnorm</code> / '
          '<code>loudnorm</code> / <code>speechnorm</code>、WebRTC AGC2</td><td>03、14、17、25</td></tr>'
          '<tr><td>oracle 掩码与 3 参数估计器</td><td>SpeechBrain、Asteroid、'
          'ClearerVoice-Studio 的掩码/映射配方</td><td>19、21、23、31</td></tr>'
          '<tr><td>因果滑动平均与状态缓存</td><td>ONNX Runtime 有状态推理、'
          'torchaudio 流式 STFT</td><td>27、28</td></tr>'
          '<tr><td>均匀量化扫描</td><td>ONNX Runtime 量化工具、各硬件 SDK 的 int8 后端</td><td>29</td></tr>'
          '<tr><td>纯标准库 SVG 绘图 / WAV 读写</td><td>Matplotlib、Plotly、'
          '<code>soundfile</code> / <code>librosa</code></td><td>全书</td></tr>'
          "</tbody></table>")
    sections = list(ch["sections"])
    sections.append(("A.5", "Python 实验、SVG 插图与 WAV 样本索引", a5))
    sections.append(("A.6", "手写实现 → 工业库对照", a6))
    sections.append(("A.7", "扩展学习链接总表", all_resources_html()))
    return sorted(sections, key=lambda x: x[0])


def figure_block(demo_data):
    figs = demo_data["figs"]
    if not figs:
        return []
    out = ['<div class="chart-grid">']
    for i, (fname, caption) in enumerate(figs, 1):
        out.append('<figure class="chart-figure">'
                   '<img src="' + esc(fname) + '" alt="' + esc(caption) + '" loading="lazy">'
                   '<figcaption>图 ' + str(i) + '　' + esc(caption) +
                   '（代码合成信号 / 教学示意）</figcaption></figure>')
    out.append("</div>")
    return out


def audio_block(demo_data):
    items = demo_data["audio"]
    if not items:
        return []
    out = ['<div class="audio-grid">']
    for fname, caption in items:
        out.append('<div class="audio-card"><h4>' + esc(fname.split("/")[-1]) + "</h4>"
                   '<audio controls preload="none" src="' + esc(fname) + '">'
                   '浏览器不支持 audio 元素，请直接打开 ' + esc(fname) + "。</audio>"
                   "<p>" + esc(caption) + "（16 kHz / 16-bit 单声道，代码合成信号，不是真实录音）</p>"
                   "</div>")
    out.append("</div>")
    return out


def command_block(ch):
    if not ch["commands"]:
        return []
    out = ['<section id="commands"><h2><span class="sec-num">§</span>可选真机命令片段</h2>',
           '<div class="card note"><p style="margin-bottom:0">以下命令<strong>不参与批量运行</strong>，'
           '需要本机自行安装对应工具。滤镜是否可用取决于本机 ffmpeg 版本与编译选项，'
           '请先用 <code>ffmpeg -filters</code> / <code>ffmpeg -version</code> 自查，'
           '并以 https://ffmpeg.org/ffmpeg-filters.html 与各自官方文档为准；'
           '本书不假定任何特定版本具备某项能力。</p></div>']
    for title, code, note in ch["commands"]:
        out.append("<h3>" + esc(title) + "</h3>")
        out.append('<pre class="cmd" data-lang="shell"><code>' + esc(code) + "</code></pre>")
        out.append('<p class="code-hint"><strong>说明：</strong>' + note + "</p>")
    out.append("</section>")
    return out


def render(ch):
    folder = pathlib.PurePosixPath(ch["folder"])
    root = "../" * len(folder.parts)
    part = PART_BY_ID[ch["part"]]
    is_appendix = ch["id"] == "A"
    chapter_attr = ' data-chapter="' + ch["id"] + '"'
    if is_appendix:
        chapter_attr += ' data-page="appendix"'
    head_title = ("附录 A · " + ch["title"]) if is_appendix else ("第 " + ch["id"] + " 章 · " + ch["title"])

    out = head(head_title, root)
    out.append('<body data-root="' + root + '"' + chapter_attr + ">")
    out.append('<aside id="sidebar"></aside>')
    out.append('<main class="book-page">')
    if is_appendix:
        out.append('<nav class="breadcrumb"><a href="' + root + 'index.html">总目录</a> / 附录</nav>')
    else:
        out.append('<nav class="breadcrumb" data-autofill>总目录</nav>')

    out.append('<header class="chapter-head">')
    out.append('<span class="kicker">' + esc(part["title"]) + " · " + esc(part["volume"]) + "</span>")
    label = "附录 A" if is_appendix else ("第 " + ch["id"] + " 章")
    out.append('<h1><span class="ch-num">' + label + "</span>" + esc(ch["title"]) + "</h1>")
    out.append('<p class="lede">' + ch["lede"] + "</p>")
    out.append('<div class="meta">')
    out.append('<span class="badge ' + ch["status"] + '">' + STATUS_LABEL[ch["status"]] + "</span>")
    out.append('<span class="badge ' + STAGE_CLASS[ch["part"]] + '">' +
               esc(STAGE_SHORT[ch["part"]]) + "</span>")
    vbadge = VOLUME_BADGE.get(part["volume"])
    if vbadge:
        out.append('<span class="badge ' + vbadge + '">' +
                   esc("上卷 · 传统算法" if vbadge == "traditional" else "下卷 · AI 算法") + "</span>")
    out.append("<span>建议 " + esc(ch["hours"]) + "</span>")
    if is_appendix:
        out.append("<span>全书速查入口</span>")
    else:
        out.append("<span>" + str(len(ch["demos"])) + " 个 Python 实验 · " +
                   str(sum(len(d["figs"]) for d in ch["demos"])) + " 张图 · " +
                   str(sum(len(d["audio"]) for d in ch["demos"])) + " 段试听</span>")
    out.append("<span>" + BOOK_TITLE + "</span>")
    out.append("</div></header>")
    out.append('<p class="bridge"><strong>本章位置：</strong>' + ch["bridge"] + "</p>")
    out.append('<div class="analogy"><span class="card-label">给程序员的翻译</span>'
               '<p style="margin-bottom:0">' + ch["analogy"] + "</p></div>")
    if ch["goals"]:
        out.append('<div class="card objectives"><span class="card-label">学习目标</span><ul>')
        out.append(lih(ch["goals"]))
        out.append("</ul></div>")

    out.append('<section id="map"><h2><span class="sec-num">§</span>知识点地图</h2>')
    out.append('<p class="code-hint">每个知识点都配了 1～2 个扩展学习链接；'
               '本章完整资源清单见 <a href="#extra-links">扩展学习</a>。</p>')
    out.append('<table><thead><tr><th style="width:44px">#</th><th style="width:26%">知识点</th>'
               '<th>扩展学习</th><th style="width:100px">状态</th></tr></thead><tbody>')
    for i, pt in enumerate(ch["points"], 1):
        out.append("<tr><td>" + str(i) + "</td><td>" + esc(pt) + "</td><td>" +
                   links_for_point(ch["id"], pt) + "</td><td>正文已覆盖</td></tr>")
    out.append("</tbody></table></section>")

    sections = appendix_sections(ch) if is_appendix else ch["sections"]
    for num, title, body in sections:
        out.append('<section id="s' + num.replace(".", "-") + '"><h2><span class="sec-num">§' +
                   num + "</span>" + esc(title) + "</h2>")
        out.append(body)
        out.append("</section>")

    if is_appendix:
        out.append('<section id="lab"><h2><span class="sec-num">§</span>全书实验与工具</h2>'
                   '<div class="card note"><p style="margin-bottom:0">附录不新增实验脚本；'
                   '全部可运行实例见 <a href="#sA-5">A.5 实验索引</a>，'
                   '手写实现与工业库的迁移对照见 <a href="#sA-6">A.6</a>。'
                   '生成、抽取、批量运行与自检命令见 {{home#contribute}}。</p></div></section>')
    else:
        out.append('<section id="lab"><h2><span class="sec-num">§</span>Python 实验</h2>')
        for s in ch["demos"]:
            out.append("<h3>" + esc(s["title"]) + "</h3>")
            out.append('<pre class="code" data-file="' + s["file"] +
                       '" data-lang="Python 3 · 标准库"><code>' + esc(s["code"]) + "</code></pre>")
            out.append('<p class="code-hint"><strong>操作：</strong>' + s["steps"] +
                       "　<strong>预期与判读：</strong>" + s["expect"] + "</p>")
            out.append('<p class="code-hint"><strong>改参数看趋势：</strong>' + s["params"] +
                       "　文件位置：<code>" + esc(ch["folder"] + "/" + s["file"]) + "</code></p>")
            out.extend(figure_block(s))
            out.extend(audio_block(s))
        out.append('<div class="card note"><p style="margin-bottom:0">代码块右上角可一键复制；'
                   '仓库里的 <code>code/*.py</code> 由 <code>tools/extract_code.py</code> 从这些代码块自动抽取。'
                   '脚本只用标准库、固定 <code>random.seed(7)</code>，运行后写出 '
                   '<code>fig/*.svg</code> 与 <code>audio/*.wav</code>；'
                   '批量运行用 <code>./tools/run_python.sh</code>。</p></div>')
        out.append("</section>")
    out.extend(command_block(ch))

    if ch["highlights"]:
        out.append('<section id="highlights"><h2><span class="sec-num">§</span>本章参考资料</h2>'
                   '<p>按本章知识点挑选的精读资料；更多检索入口见 '
                   '<a href="#extra-links">扩展学习</a>。</p><div class="repo-grid">')
        out.extend(resource_card(k, why) for k, why in ch["highlights"])
        out.append("</div></section>")
    if ch["repos"]:
        out.append('<section id="repos"><h2><span class="sec-num">§</span>相关开源工程</h2>'
                   '<p>下列工程仅作技术参照，版权与许可证归各自维护者所有。'
                   '本书实验不依赖它们，也与之无从属关系。</p><div class="repo-grid">')
        out.extend(repo_card(*r) for r in ch["repos"])
        out.append("</div></section>")
    if ch["pitfalls"]:
        out.append('<section id="pitfalls"><h2><span class="sec-num">§</span>常见误区</h2>'
                   '<div class="card warn"><ul>' + lih(ch["pitfalls"]) + "</ul></div></section>")
    if ch["exercises"]:
        out.append('<section id="exercises"><h2><span class="sec-num">§</span>习题与思考</h2><ol>' +
                   lih(ch["exercises"]) + "</ol></section>")
    out.append('<section id="extra-links"><h2><span class="sec-num">§</span>扩展学习</h2>')
    out.append(chapter_links_html(ch["id"], root))
    out.append("</section>")
    if ch["further"]:
        out.append('<section id="further"><h2><span class="sec-num">§</span>延伸阅读与内链</h2><ul>' +
                   lih(ch["further"]) + "</ul></section>")
    out.extend(footer(root))
    return resolve_refs("\n".join(out) + "\n", root=root, start=ch["folder"])


# ---------------------------------------------------------------- 生成
def build(force=False):
    created, skipped = [], []
    (ROOT / "assets/toc.js").write_text(toc_js_text(), encoding="utf-8")
    (ROOT / "index.html").write_text(render_index(), encoding="utf-8")
    created += ["assets/toc.js", "index.html"]
    for ch in CHAPTERS:
        target = ROOT / ch["folder"] / "index.html"
        if target.exists() and not force:
            skipped.append(str(target.relative_to(ROOT)))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(ch), encoding="utf-8")
        created.append(str(target.relative_to(ROOT)))
    return created, skipped


def main():
    ap = argparse.ArgumentParser(description="生成音频 3A 教材 HTML")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的章节页（会丢失手工修改）")
    ap.add_argument("--list", action="store_true", help="只列出章节清单")
    args = ap.parse_args()
    if args.list:
        for ch in CHAPTERS:
            p = PART_BY_ID[ch["part"]]
            print(ch["id"].rjust(2), p["key"].ljust(10), ch["folder"].ljust(38), ch["title"])
        print("共 %d 章（含附录）/ %d 个 Python 实验 / %d 张 SVG 图 / %d 段 WAV / %d 条参考链接" %
              (len(CHAPTERS), demo_count(), fig_count(), audio_count(), link_count()))
        return
    issues = problems()
    if issues:
        for x in issues:
            print("数据问题:", x)
        sys.exit(1)
    created, skipped = build(force=args.force)
    for p in created:
        print("生成", p)
    print("共 %d 个页面：新建/重建 %d，跳过 %d（章节页使用 --force 可重建）" %
          (len(CHAPTERS) + 1, len(created), len(skipped)))


if __name__ == "__main__":
    main()
