#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纯标准库 SVG 绘图库（教材专用，无第三方依赖）。

设计目标：
  1. 生成的 .svg 是文本矢量图，可提交进 Git、可离线浏览、可被浏览器直接 <img> 引用；
  2. 不弹窗口、不需要 GUI，脚本批量运行即可生成全书插图；
  3. API 尽量小：Chart（通用笛卡尔图）、candlestick（K 线+成交量）、heatmap（矩阵）。

脚本里的典型用法：
    import pathlib, sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools"))
    from chart import Chart
    FIG = pathlib.Path(__file__).resolve().parents[1] / "fig"
    FIG.mkdir(exist_ok=True)
    c = Chart(FIG / "demo.svg", "标题", xlabel="期数", ylabel="价格")
    c.line(range(len(xs)), series, "#245a7a", label="净值")
    print("图:", c.save())
"""
from __future__ import annotations

import html as _html
import math
import pathlib

FONT = "PingFang SC, Microsoft YaHei, Noto Sans CJK SC, -apple-system, sans-serif"
MONO = "SF Mono, JetBrains Mono, Menlo, Consolas, monospace"
INK = "#23262b"
MUTED = "#8a909b"
GRID = "#e8e6e0"
BG = "#ffffff"
BLUE = "#245a7a"
RED = "#8a3b26"
GREEN = "#2f6b4f"
AMBER = "#8a6316"
PALETTE = (BLUE, RED, GREEN, AMBER, "#6b4f8a", "#3b6b8a", "#a0522d")


def _esc(s):
    return _html.escape(str(s), quote=True)


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    a = abs(float(v))
    if a >= 10000:
        return "%.0f" % v
    if a >= 100:
        return "%.1f" % v
    if a >= 1:
        return "%.2f" % v
    if a == 0:
        return "0"
    return "%.3f" % v


def _color_scale(t, lo=BLUE, hi=RED):
    """t ∈ [0,1] 的两种颜色线性插值（十六进制）。"""
    def rgb(c):
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    a, b = rgb(lo), rgb(hi)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Chart:
    """通用二维图：折线 / 柱 / 散点 / 填充 / 参考线 / 标注。

    绘图调用先被记录，save() 时根据收集到的数据自动确定坐标范围再统一渲染，
    因此调用方不必手工计算 ylim。用 xlim / ylim 可显式覆盖。
    """

    def __init__(self, path, title="", *, width=780, height=430,
                 xlabel="", ylabel="", xlim=None, ylim=None,
                 xticks=None, grid=True, legend=True, zero_line=False):
        self.path = pathlib.Path(path)
        self.title = title
        self.width, self.height = width, height
        self.xlabel, self.ylabel = xlabel, ylabel
        self.xlim, self.ylim = xlim, ylim
        self.xticks = list(xticks) if xticks else []
        self.grid, self.legend, self.zero_line = grid, legend, zero_line
        self._ops, self._xs, self._ys, self._legend = [], [], [], []
        self.pad_l, self.pad_r, self.pad_t, self.pad_b = 76, 24, 46, 58

    # ---------------- 记录绘图指令 ----------------
    def _collect(self, xs, ys):
        for x, y in zip(xs, ys):
            if x is not None and y is not None:
                self._xs.append(float(x))
                self._ys.append(float(y))

    def line(self, xs, ys, color=BLUE, label="", width=2, dash=None, opacity=1.0):
        xs, ys = list(xs), list(ys)
        self._ops.append(("line", xs, ys, color, width, dash, opacity))
        self._collect(xs, ys)
        if label:
            self._legend.append((color, label, "line"))
        return self

    def area(self, xs, ys, color=BLUE, label="", opacity=0.18, baseline=0.0):
        xs, ys = list(xs), list(ys)
        self._ops.append(("area", xs, ys, color, opacity, baseline))
        self._collect(xs, ys)
        self._ys.append(float(baseline))
        if label:
            self._legend.append((color, label, "area"))
        return self

    def bars(self, xs, heights, color=BLUE, label="", opacity=0.85, baseline=0.0):
        xs, hs = list(xs), list(heights)
        self._ops.append(("bars", xs, hs, color, opacity, baseline))
        self._collect(xs, hs)
        self._ys.append(float(baseline))
        if label:
            self._legend.append((color, label, "bars"))
        return self

    def scatter(self, xs, ys, color=RED, label="", radius=3.2, opacity=0.9):
        xs, ys = list(xs), list(ys)
        self._ops.append(("scatter", xs, ys, color, radius, opacity))
        self._collect(xs, ys)
        if label:
            self._legend.append((color, label, "scatter"))
        return self

    def hline(self, y, color=MUTED, label="", dash="4 4", width=1.2):
        self._ops.append(("hline", float(y), color, dash, width))
        self._ys.append(float(y))
        if label:
            self._legend.append((color, label, "line"))
        return self

    def vline(self, x, color=MUTED, label="", dash="4 4", width=1.2):
        self._ops.append(("vline", float(x), color, dash, width))
        self._xs.append(float(x))
        return self

    def text(self, x, y, s, color=INK, size=12, anchor="start"):
        self._ops.append(("text", float(x), float(y), s, color, size, anchor))
        self._collect([x], [y])
        return self

    def _range(self):
        if not self._xs or not self._ys:
            x0, x1, y0, y1 = 0.0, 1.0, 0.0, 1.0
        else:
            x0, x1 = min(self._xs), max(self._xs)
            y0, y1 = min(self._ys), max(self._ys)
            if x1 <= x0:
                x1 = x0 + 1.0
            if y1 <= y0:
                y1 = y0 + 1.0
            dx, dy = (x1 - x0) * 0.04, (y1 - y0) * 0.10
            x0, x1, y0, y1 = x0 - dx, x1 + dx, y0 - dy, y1 + dy
        if self.xlim:
            x0, x1 = self.xlim
        if self.ylim:
            y0, y1 = self.ylim
        return x0, x1, y0, y1

    # ---------------- 渲染 ----------------
    def save(self):
        x0, x1, y0, y1 = self._range()
        W, H = self.width, self.height
        pl, pr, pt, pb = self.pad_l, self.pad_r, self.pad_t, self.pad_b
        pw, ph = W - pl - pr, H - pt - pb

        def px(x):
            return pl + (float(x) - x0) / (x1 - x0) * pw

        def py(y):
            return pt + (y1 - float(y)) / (y1 - y0) * ph

        out = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img">'
            % (W, H, W, H),
            "<title>" + _esc(self.title) + "</title>",
            '<desc>由 tools/chart.py 生成的教材示意插图，数据为合成数据。</desc>',
            '<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (W, H, BG),
        ]
        if self.title:
            out.append('<text x="%.1f" y="24" font-family="%s" font-size="15" '
                       'font-weight="600" fill="%s">%s</text>'
                       % (pl, FONT, INK, _esc(self.title)))

        # 网格与坐标轴
        for i in range(6):
            yy = y0 + (y1 - y0) * i / 5
            ypx = py(yy)
            if self.grid:
                out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                           'stroke="%s" stroke-width="1"/>' % (pl, ypx, pl + pw, ypx, GRID))
            out.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="11" '
                       'fill="%s" text-anchor="end">%s</text>'
                       % (pl - 8, ypx + 4, MONO, MUTED, _esc(_fmt(yy))))
        ticks = self.xticks
        if not ticks:
            ticks = [(x0 + (x1 - x0) * i / 5, None) for i in range(6)]
        for xv, lab in ticks:
            xpx = px(xv)
            if self.grid:
                out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                           'stroke="%s" stroke-width="1"/>' % (xpx, pt, xpx, pt + ph, GRID))
            out.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="11" '
                       'fill="%s" text-anchor="middle">%s</text>'
                       % (xpx, pt + ph + 18, MONO, MUTED,
                          _esc(_fmt(xv) if lab is None else lab)))
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.4"/>'
                   % (pl, pt + ph, pl + pw, pt + ph, MUTED))
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.4"/>'
                   % (pl, pt, pl, pt + ph, MUTED))
        if self.zero_line and y0 < 0 < y1:
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                       'stroke="%s" stroke-width="1.2" stroke-dasharray="5 4"/>'
                       % (pl, py(0), pl + pw, py(0), MUTED))
        if self.xlabel:
            out.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="12" '
                       'fill="%s" text-anchor="middle">%s</text>'
                       % (pl + pw / 2, H - 12, FONT, MUTED, _esc(self.xlabel)))
        if self.ylabel:
            out.append('<text x="14" y="%.1f" font-family="%s" font-size="12" '
                       'fill="%s" transform="rotate(-90 14 %.1f)" text-anchor="middle">%s</text>'
                       % (pt + ph / 2, FONT, MUTED, pt + ph / 2, _esc(self.ylabel)))

        # 图形元素
        bar_count = sum(1 for op in self._ops if op[0] == "bars")
        bar_i = 0
        for op in self._ops:
            kind = op[0]
            if kind == "line":
                _, xs, ys, color, lw, dash, opacity = op
                pts = " ".join("%.2f,%.2f" % (px(x), py(y)) for x, y in zip(xs, ys))
                d = ' stroke-dasharray="%s"' % dash if dash else ""
                out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" '
                           'stroke-linejoin="round" opacity="%s"%s/>'
                           % (pts, color, lw, opacity, d))
            elif kind == "area":
                _, xs, ys, color, opacity, base = op
                pts = " ".join("%.2f,%.2f" % (px(x), py(y)) for x, y in zip(xs, ys))
                out.append('<polygon points="%.2f,%.2f %s %.2f,%.2f" fill="%s" opacity="%s"/>'
                           % (px(xs[0]), py(base), pts, px(xs[-1]), py(base), color, opacity))
            elif kind == "bars":
                _, xs, hs, color, opacity, base = op
                bar_i += 1
                slot = pw / max(len(xs), 1)
                bw = max(2.0, min(slot * 0.72 / max(bar_count, 1), 26.0))
                off = (bar_i - 1 - (bar_count - 1) / 2) * bw
                for x, h in zip(xs, hs):
                    yp, yb = py(h), py(base)
                    top, bot = min(yp, yb), max(yp, yb)
                    out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" '
                               'fill="%s" opacity="%s"/>'
                               % (px(x) + off - bw / 2, top, bw, max(bot - top, 0.6),
                                  color, opacity))
            elif kind == "scatter":
                _, xs, ys, color, r, opacity = op
                for x, y in zip(xs, ys):
                    out.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" opacity="%s"/>'
                               % (px(x), py(y), r, color, opacity))
            elif kind == "hline":
                _, y, color, dash, lw = op
                out.append('<line x1="%.1f" y1="%.2f" x2="%.1f" y2="%.2f" stroke="%s" '
                           'stroke-width="%s" stroke-dasharray="%s"/>'
                           % (pl, py(y), pl + pw, py(y), color, lw, dash or "4 4"))
            elif kind == "vline":
                _, x, color, dash, lw = op
                out.append('<line x1="%.2f" y1="%.1f" x2="%.2f" y2="%.1f" stroke="%s" '
                           'stroke-width="%s" stroke-dasharray="%s"/>'
                           % (px(x), pt, px(x), pt + ph, color, lw, dash or "4 4"))
            elif kind == "text":
                _, x, y, s, color, size, anchor = op
                out.append('<text x="%.2f" y="%.2f" font-family="%s" font-size="%s" '
                           'fill="%s" text-anchor="%s">%s</text>'
                           % (px(x), py(y), FONT, size, color, anchor, _esc(s)))

        # 图例
        if self.legend and self._legend:
            lx, ly = pl + 10, pt + 8
            out.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" fill="#ffffff" '
                       'fill-opacity="0.86" stroke="%s" rx="3"/>'
                       % (lx - 6, ly - 4, 178, 20 * len(self._legend) + 8, GRID))
            for i, (color, label, _kind) in enumerate(self._legend):
                yy = ly + 12 + 20 * i
                out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                           'stroke-width="3"/>' % (lx, yy, lx + 18, yy, color))
                out.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="11" fill="%s">%s</text>'
                           % (lx + 24, yy + 4, FONT, INK, _esc(label)))
        out.append("</svg>")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(out) + "\n", encoding="utf-8")
        return str(self.path)


def candlestick(path, ohlcv, *, title="", overlays=(), xticks=None,
                width=820, height=460, up_color="#c0392b", down_color="#2f6b4f",
                volume_color="#9aa6b2"):
    """K 线 + 成交量 + 均线叠加。

    ohlcv   : [(open, high, low, close, volume), ...]
    overlays: [(values, color, label), ...]，values 长度需与 ohlcv 一致
    xticks  : [(index, label), ...]
    """
    path = pathlib.Path(path)
    n = len(ohlcv)
    W, H = width, height
    pl, pr, pt, pb = 70, 22, 44, 52
    pw = W - pl - pr
    main_h = (H - pt - pb) * 0.70
    vol_top = pt + main_h + 26
    vol_h = (H - pt - pb) * 0.22

    lows = [r[2] for r in ohlcv]
    highs = [r[1] for r in ohlcv]
    for vals, _c, _l in overlays:
        lows += [v for v in vals if v is not None]
        highs += [v for v in vals if v is not None]
    y0, y1 = min(lows), max(highs)
    pad = (y1 - y0) * 0.08 or 1.0
    y0, y1 = y0 - pad, y1 + pad
    vmax = max([r[4] for r in ohlcv] + [1.0])
    slot = pw / max(n, 1)
    bw = max(2.0, min(slot * 0.62, 18.0))

    def px(i):
        return pl + (i + 0.5) * slot

    def py(v):
        return pt + (y1 - v) / (y1 - y0) * main_h

    def vy(v):
        return vol_top + vol_h - (v / vmax) * vol_h

    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img">'
           % (W, H, W, H), "<title>" + _esc(title) + "</title>",
           '<desc>由 tools/chart.py 生成的合成 K 线示意插图，非真实行情。</desc>',
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG)]
    if title:
        out.append('<text x="%.1f" y="24" font-family="%s" font-size="15" '
                   'font-weight="600" fill="%s">%s</text>' % (pl, FONT, INK, _esc(title)))
    for i in range(5):
        yy = y0 + (y1 - y0) * i / 4
        ypx = py(yy)
        out.append('<line x1="%.1f" y1="%.2f" x2="%.1f" y2="%.2f" stroke="%s" stroke-width="1"/>'
                   % (pl, ypx, pl + pw, ypx, GRID))
        out.append('<text x="%.1f" y="%.2f" font-family="%s" font-size="11" fill="%s" text-anchor="end">%s</text>'
                   % (pl - 8, ypx + 4, MONO, MUTED, _esc(_fmt(yy))))
    for i, r in enumerate(ohlcv):
        o, h, l, c, v = r
        col = up_color if c >= o else down_color
        cx = px(i)
        out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1.2"/>'
                   % (cx, py(h), cx, py(l), col))
        top, bot = py(max(o, c)), py(min(o, c))
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                   'fill-opacity="%s" stroke="%s" stroke-width="1"/>'
                   % (cx - bw / 2, top, bw, max(bot - top, 1.2), col,
                      "0.25" if c >= o else "0.9", col))
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" opacity="0.55"/>'
                   % (cx - bw / 2, vy(v), bw, max(vol_top + vol_h - vy(v), 0.6),
                      up_color if c >= o else volume_color))
    out.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="11" fill="%s">成交量</text>'
               % (pl + 4, vol_top - 6, FONT, MUTED))
    for vals, color, label in overlays:
        pts = " ".join("%.2f,%.2f" % (px(i), py(v)) for i, v in enumerate(vals) if v is not None)
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.8" '
                   'stroke-linejoin="round" opacity="0.9"/>' % (pts, color))
        if label:
            last = vals[-1]
            out.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="11" fill="%s">%s</text>'
                       % (pl + pw + 2, py(last) + 4, FONT, color, _esc(label)))
    ticks = xticks or [(int(n * i / 5), "T%d" % int(n * i / 5)) for i in range(6)]
    for idx, lab in ticks:
        out.append('<text x="%.2f" y="%.1f" font-family="%s" font-size="11" fill="%s" '
                   'text-anchor="middle">%s</text>'
                   % (px(min(idx, n - 1)), vol_top + vol_h + 18, MONO, MUTED, _esc(lab)))
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.2"/>'
               % (pl, pt + main_h, pl + pw, pt + main_h, MUTED))
    out.append('<text x="%.1f" y="%d" font-family="%s" font-size="11" fill="%s">'
               '红=收≥开（A 股习惯）· 绿=收&lt;开 · 数据为合成示意</text>'
               % (pl, H - 8, FONT, MUTED))
    out.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return str(path)


def heatmap(path, matrix, row_labels, col_labels, *, title="", width=640, height=460,
            vmin=-1.0, vmax=1.0, annotate=True):
    """矩阵热力图：相关性矩阵、月度收益表等。"""
    path = pathlib.Path(path)
    R, C = len(matrix), len(matrix[0])
    W, H = width, height
    pl, pt = 108, 56
    cell_w = min((W - pl - 24) / C, 76)
    cell_h = min((H - pt - 30) / R, 44)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img">'
           % (W, H, W, H), "<title>" + _esc(title) + "</title>",
           '<desc>由 tools/chart.py 生成的矩阵热力图。</desc>',
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG)]
    if title:
        out.append('<text x="20" y="26" font-family="%s" font-size="15" font-weight="600" '
                   'fill="%s">%s</text>' % (FONT, INK, _esc(title)))
    for j, lab in enumerate(col_labels):
        out.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="11" fill="%s" '
                   'text-anchor="middle">%s</text>'
                   % (pl + (j + 0.5) * cell_w, pt - 8, FONT, MUTED, _esc(lab)))
    for i, row in enumerate(matrix):
        out.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="11" fill="%s" '
                   'text-anchor="end">%s</text>'
                   % (pl - 8, pt + (i + 0.6) * cell_h, FONT, MUTED, _esc(row_labels[i])))
        for j, v in enumerate(row):
            t = (v - vmin) / (vmax - vmin)
            t = max(0.0, min(1.0, t))
            col = _color_scale(t, "#2f6b4f", "#8a3b26")
            x, y = pl + j * cell_w, pt + i * cell_h
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                       'fill-opacity="0.78" stroke="#ffffff" stroke-width="1"/>'
                       % (x, y, cell_w - 2, cell_h - 2, col))
            if annotate:
                out.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="11" '
                           'fill="#ffffff" text-anchor="middle">%s</text>'
                           % (x + (cell_w - 2) / 2, y + (cell_h - 2) / 2 + 4,
                              MONO, _esc(_fmt(v))))
    out.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return str(path)
