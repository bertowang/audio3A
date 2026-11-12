#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从生成的 HTML 中抽取 <pre class="code" data-file="..."> 代码块，同步 code/*.py。

页面是唯一展示源，磁盘脚本是运行产物；两者必须逐字一致（check_book.py 会核对）。

用法:
  python3 tools/extract_code.py           # 写入全部 code/*.py
  python3 tools/extract_code.py --check  # 只检查是否一致，不写文件
  python3 tools/extract_code.py --clean  # 删除不在页面里出现的 code/*.py
"""
from __future__ import annotations

import argparse
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

BLOCK = re.compile(
    r'<pre\s+class="code"\s+data-file="([^"]+)"[^>]*><code>(.*?)</code></pre>',
    re.DOTALL,
)


def collect():
    """返回 {相对路径: 源码文本}，并检查重复定义。"""
    out = {}
    for page in sorted(ROOT.glob("**/index.html")):
        if page.parent == ROOT:
            continue
        text = page.read_text(encoding="utf-8")
        for fname, code in BLOCK.findall(text):
            rel = str(page.parent.relative_to(ROOT)) + "/" + fname
            if rel in out:
                raise SystemExit("代码块重复定义: " + rel)
            out[rel] = html.unescape(code).strip("\n") + "\n"
    return out


def main():
    ap = argparse.ArgumentParser(description="从 HTML 同步 Python 实验脚本")
    ap.add_argument("--check", action="store_true", help="只比对，不写文件")
    ap.add_argument("--clean", action="store_true", help="删除页面里不再存在的脚本")
    args = ap.parse_args()

    wanted = collect()
    errors = []
    for rel, code in wanted.items():
        path = ROOT / rel
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != code:
                errors.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code, encoding="utf-8")

    known = set(wanted)
    stale = []
    for path in sorted(ROOT.glob("part*/**/code/*.py")):
        rel = str(path.relative_to(ROOT))
        if rel not in known:
            stale.append(path)
    if args.clean:
        for path in stale:
            path.unlink()
            print("删除孤立脚本", rel_of(path))
        stale = []
    for path in stale:
        errors.append("孤立的 code/*.py: " + str(path.relative_to(ROOT)))

    if args.check:
        for e in errors:
            print("不一致:", e)
        print("检查 %d 个代码块，%d 处不一致" % (len(wanted), len(errors)))
        sys.exit(1 if errors else 0)
    if errors and not args.clean:
        for e in errors:
            print("提示:", e)
    print("同步 %d 个 Python 实验脚本" % len(wanted))


def rel_of(path):
    return str(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
