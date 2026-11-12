#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""音频 3A 教材 · 分卷分部、章节数据接口与全局约定。

全书按用户要求分上下两部分：
    上卷 · 传统算法（model-based）：信号模型 → 自适应滤波 → AEC/ANS/AGC → 级联与评测
    下卷 · AI 算法（data-driven）  ：数据与表示 → 网络 → 神经 3A → 实时部署与前沿
卷首给出共同语言与评价指标，附录给出公式、术语、命令与资源速查。
"""
from __future__ import annotations

BOOK_TITLE = "音频 3A 处理：从自适应滤波到神经增强"
SUBTITLE = "本科到研究生 · AEC 回声消除 / ANS 噪声抑制 / AGC 增益控制的传统与 AI 两条路线"
VERSION = "v0.1 · 2026-11"

V_PRE = "卷首 · 共同语言与问题定义"
V_TRAD = "上卷 · 传统算法（Model-based）"
V_AI = "下卷 · AI 算法（Data-driven）"
V_APP = "附录 · 速查与资源总表"

PARTS = [
    dict(id="p0", title="卷首 · 3A 问题全景", volume=V_PRE, key="pre", folder="part0"),
    dict(id="p1", title="第一篇 · 信号、系统与自适应滤波基础", volume=V_TRAD, key="foundation", folder="part1"),
    dict(id="p2", title="第二篇 · AEC / ANS / AGC 三类经典引擎", volume=V_TRAD, key="engines", folder="part2"),
    dict(id="p3", title="第三篇 · 级联、评测与工程链路", volume=V_TRAD, key="integration", folder="part3"),
    dict(id="p4", title="第四篇 · 数据、表示与学习基础", volume=V_AI, key="learning", folder="part4"),
    dict(id="p5", title="第五篇 · 神经 3A 与联合建模", volume=V_AI, key="neural", folder="part5"),
    dict(id="p6", title="第六篇 · 实时部署、评测与前沿", volume=V_AI, key="deployment", folder="part6"),
    dict(id="pa", title="附录 · 公式、术语、命令与资源总表", volume=V_APP, key="appendix", folder="appendix"),
]
PART_BY_ID = {p["id"]: p for p in PARTS}

VOLUME_CLASS = {V_PRE: "s1", V_TRAD: "s2", V_AI: "s4", V_APP: "s5"}
VOLUME_SHORT = {V_PRE: "卷首", V_TRAD: "上卷 · 传统算法", V_AI: "下卷 · AI 算法", V_APP: "附录"}
VOLUME_BADGE = {V_TRAD: "traditional", V_AI: "neural"}

VOLUME_NOTES = {
    V_PRE: "第 00～03 章。先建立一条实时语音链路的信号模型、时频语言与评价指标，"
           "把「3A 是什么、怎么算变好了」讲清楚，两卷共用这一套共同语言。",
    V_TRAD: "第 04～18 章。从房间冲激响应、自适应滤波与统计估计出发，"
            "分别实现回声消除、噪声抑制与增益控制，再讨论级联顺序、客观评测与 ffmpeg / WebRTC 工具链。",
    V_AI: "第 19～31 章。把 3A 重写成可学习的映射：数据合成、损失函数与网络骨架先行，"
          "再逐个替换三大模块，最后落到因果性、延迟、量化与泛化。",
    V_APP: "附录 A 汇总全书公式、中英术语、ffmpeg/WebRTC 命令、可运行示例与开源工程索引。",
}


def C(cid, part, folder, title, lede, *, hours="2 学时", goals=(), points=(),
      sections=(), demos=(), commands=(), highlights=(), repos=(), analogy="",
      bridge="", pitfalls=(), exercises=(), further=(), status="done"):
    """一章的全部数据。

    demos     : [demo(...), ...] 零依赖、自包含的 Python 实验脚本（生成 SVG 图 + WAV 试听样本）
    commands  : [(标题, shell 代码, 说明), ...] 可选的真机命令（ffmpeg / WebRTC / 开源工程）
                不参与批量运行，本机需自行安装对应工具，页面会明确标注
    highlights: [(资源 key, 推荐理由), ...] 本章必读参考资料
    repos     : [(工程名, 链接, 说明), ...] 下卷常见的开源实现卡片
    """
    return dict(id=cid, part=part, folder=folder, title=title, lede=lede,
                status=status, hours=hours, goals=list(goals), points=list(points),
                sections=list(sections), demos=list(demos), commands=list(commands),
                highlights=list(highlights), repos=list(repos), analogy=analogy,
                bridge=bridge, pitfalls=list(pitfalls), exercises=list(exercises),
                further=list(further))


def demo(file, title, code, steps, expect, params="", figs=(), audio=()):
    """一段可独立运行的 Python 实验脚本。

    figs : [(fig/xx.svg, 图注), ...] 由脚本运行时生成
    audio: [(audio/xx.wav, 试听说明), ...] 16 kHz / 16-bit 单声道合成样本，页面内可直接播放
    """
    return dict(file=file, title=title, code=code.strip("\n"), steps=steps,
                expect=expect, params=params, figs=list(figs), audio=list(audio))


def eq(text):
    """把一行公式排版成等宽公式块；text 里可以写 Unicode 数学符号。"""
    import html as html_mod
    return '<p class="eq">' + html_mod.escape(text, quote=False) + "</p>"


def table(headers, rows, widths=()):
    """生成一张对照表；rows 中的单元格已是 HTML。"""
    w = [' style="width:%s"' % widths[i] if i < len(widths) else ""
         for i in range(len(headers))]
    out = ["<table><thead><tr>" + "".join("<th" + w[i] + ">" + h + "</th>"
                                        for i, h in enumerate(headers)) + "</tr></thead><tbody>"]
    for row in rows:
        out.append("<tr>" + "".join("<td>" + cell + "</td>" for cell in row) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


DEMO_CONTRACT = """所有 Python 实验遵守同一契约：
  1. 只用 Python 3 标准库 + 仓库内 tools/dsp.py 与 tools/chart.py，无第三方包；
  2. 自包含：语音 / 噪声 / 房间冲激响应由代码合成，不联网、不读外部音频文件；
  3. random.seed(7) 固定随机数，采样率统一 16 kHz，可调量集中在「参数区」；
  4. 打印可手算核对的数值（ERLE、SNR、SI-SDR、收敛迭代数等）；
  5. 生成 fig/*.svg 矢量图与 audio/*.wav 试听样本，页面内可看波形、可听效果；
  6. 页面代码块与 code/*.py 由 tools/extract_code.py 自动同步。"""

DISCLAIMER_HTML = (
    '<div class="disclaimer"><p><strong>实验边界说明</strong>：本书为教学材料。'
    '全部语音、噪声与房间冲激响应都是<strong>代码合成的信号</strong>，不是真实录音，'
    '也不是任何厂商产品的性能数据；脚本中的 FFT、自适应滤波、谱减、小型网络等均为'
    '可读的教学实现，用于说明机制与量级，<strong>不能直接用于生产环境</strong>。'
    '书中提及 ffmpeg、WebRTC、SpeexDSP、RNNoise 等工具的版本与能力请以各自的官方文档'
    '与本机 <code>ffmpeg -filters</code> / <code>ffmpeg -version</code> 实际输出为准；'
    '本书与这些项目无从属关系，也不构成产品推荐。</p></div>'
)

STAGE_CLASS = {"p0": "s1", "p1": "s2", "p2": "s2", "p3": "s2",
               "p4": "s4", "p5": "s4", "p6": "s4", "pa": "s5"}
STAGE_SHORT = {"p0": "问题定义", "p1": "基础 · 自适应", "p2": "三大引擎",
               "p3": "级联 · 评测", "p4": "数据 · 表示", "p5": "神经 3A",
               "p6": "部署 · 前沿", "pa": "速查 · 附录"}
