#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全书章节数据的唯一汇总入口，兼做数据层一致性校验。

正文分散在 chapters_*.py 六个文件里便于定位；build_book.py / check_book.py
都只从这里取 CHAPTERS。
"""
from __future__ import annotations

from chapters_00_05 import CH as CH_00_05
from chapters_06_11 import CH as CH_06_11
from chapters_12_17 import CH as CH_12_17
from chapters_18_23 import CH as CH_18_23
from chapters_24_29 import CH as CH_24_29
from chapters_30_A import CH as CH_30_A
from book_schema import PARTS, PART_BY_ID
from book_resources import R, REPOS, CHAPTER_RESOURCES, TOPIC_RULES, DEFAULT_KEYS

CHAPTERS = (CH_00_05 + CH_06_11 + CH_12_17 + CH_18_23 +
            CH_24_29 + CH_30_A)
BY_ID = {ch["id"]: ch for ch in CHAPTERS}

BANNED_IMPORTS = ("import numpy", "import pandas", "import scipy", "import torch",
                  "import matplotlib", "import soundfile", "import librosa",
                  "from numpy", "from scipy", "from torch", "from matplotlib",
                  "from soundfile", "from librosa")
REQUIRED_TOKENS = ("#!/usr/bin/env python3", "random.seed(7)", "参数区",
                   "print(", "from dsp import", "SAMPLE_RATE")


def problems():
    """返回数据层面的问题列表，供自检脚本使用。"""
    out = []
    ids = [c["id"] for c in CHAPTERS]
    folders = [c["folder"] for c in CHAPTERS]
    if len(ids) != len(set(ids)):
        out.append("章节 id 重复")
    if len(folders) != len(set(folders)):
        out.append("章节目录重复")
    for cid in CHAPTER_RESOURCES:
        if cid not in BY_ID:
            out.append("参考链接库指向不存在的章节: " + cid)
    for cid, (keys, _q) in CHAPTER_RESOURCES.items():
        for k in keys:
            if k not in R:
                out.append("参考链接库存在未知 key [%s]: 章节 %s" % (k, cid))
    for k in DEFAULT_KEYS:
        if k not in R:
            out.append("默认资源存在未知 key: " + k)
    for _kw, keys in TOPIC_RULES:
        for k in keys:
            if k not in R:
                out.append("知识点规则存在未知 key [%s]" % k)
    for _name, _url, _desc, _tag in REPOS:
        if not _url.startswith("https://"):
            out.append("开源工程链接不规范: " + _name)

    demo_files = []
    for ch in CHAPTERS:
        cid = ch["id"]
        part = PART_BY_ID.get(ch["part"])
        if not part:
            out.append("未知分部: " + cid)
            continue
        if not (ch["folder"] == part["folder"] or
                ch["folder"].startswith(part["folder"] + "/")):
            out.append("章节目录与分部不匹配: " + cid + " -> " + ch["folder"])
        if ch["status"] != "done":
            out.append("章节状态不是 done: " + cid)
        for field in ("goals", "points", "sections", "pitfalls", "exercises",
                      "further", "highlights"):
            if not ch[field]:
                out.append("章节缺少 %s: %s" % (field, cid))
        if not ch["bridge"] or not ch["analogy"]:
            out.append("章节缺少承接或程序员类比: " + cid)
        if cid not in CHAPTER_RESOURCES:
            out.append("参考链接库缺少章节: " + cid)
        for key, _why in ch["highlights"]:
            if key not in R:
                out.append("未知参考资源 key [%s]: %s" % (key, cid))
        for title, code, note in ch["commands"]:
            if not title or not code or not note:
                out.append("命令片段三元组不完整: " + cid)
            if "\n" not in code and " " not in code:
                out.append("命令片段看起来不是可执行命令: " + cid)
        if cid != "A" and not ch["demos"]:
            out.append("章节缺少 Python 实验: " + cid)
        for d in ch["demos"]:
            code = d["code"]
            demo_files.append((cid, d["file"]))
            if not d["file"].startswith("code/") or not d["file"].endswith(".py"):
                out.append("示例文件名不规范: %s -> %s" % (cid, d["file"]))
            for token in REQUIRED_TOKENS:
                if token not in code:
                    out.append("示例缺少 %s: %s -> %s" % (token, cid, d["file"]))
            for banned in BANNED_IMPORTS:
                if banned in code:
                    out.append("示例使用了第三方依赖 %s: %s" % (banned, d["file"]))
            if not d["figs"]:
                out.append("示例未声明插图: " + d["file"])
            for fname, _cap in d["figs"]:
                if not fname.startswith("fig/") or not fname.endswith(".svg"):
                    out.append("插图路径不规范: %s -> %s" % (d["file"], fname))
                if fname.split("/")[-1] not in code:
                    out.append("插图未在脚本中生成: %s -> %s" % (d["file"], fname))
            for wname, _cap in d["audio"]:
                if not wname.startswith("audio/") or not wname.endswith(".wav"):
                    out.append("试听样本路径不规范: %s -> %s" % (d["file"], wname))
                if wname.split("/")[-1] not in code:
                    out.append("试听样本未在脚本中生成: %s -> %s" % (d["file"], wname))
            try:
                compile(code, d["file"], "exec")
            except SyntaxError as e:
                out.append("示例语法错误 %s: %s" % (d["file"], e))
    files = [f for _cid, f in demo_files]
    if len(files) != len(set(files)):
        out.append("示例文件名重复")
    for part in PARTS:
        if not chapters_of(part["id"]):
            out.append("分部没有章节: " + part["id"])
    return out


def chapters_of(part_id):
    return [c for c in CHAPTERS if c["part"] == part_id]


def demo_count():
    return sum(len(c["demos"]) for c in CHAPTERS)


def fig_count():
    return sum(len(d["figs"]) for c in CHAPTERS for d in c["demos"])


def audio_count():
    return sum(len(d["audio"]) for c in CHAPTERS for d in c["demos"])


def command_count():
    return sum(len(c["commands"]) for c in CHAPTERS)


def link_count():
    return len(R)


if __name__ == "__main__":
    print("章节数:", len(CHAPTERS), "| Python 实验:", demo_count(),
          "| SVG 插图:", fig_count(), "| WAV 试听:", audio_count(),
          "| 命令片段:", command_count(), "| 外部资源:", link_count())
    for p in PARTS:
        print(p["id"], p["volume"], p["title"], "->", len(chapters_of(p["id"])), "章")
    for x in problems():
        print("问题:", x)
