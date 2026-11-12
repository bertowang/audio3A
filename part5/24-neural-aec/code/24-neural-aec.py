#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构造前半段有回声、后半段无回声的受控场景，量化静态系数与逐帧估计的差距。

全部语音 / 噪声 / 房间冲激响应均为代码合成信号，仅用于教学演示机制与量级。
"""
from __future__ import annotations

import math
import pathlib
import random
import statistics
import sys
import time

_here = pathlib.Path(__file__).resolve()
for _p in _here.parents:
    if (_p / "tools" / "dsp.py").exists():
        sys.path.insert(0, str(_p / "tools"))
        break
from dsp import (SAMPLE_RATE, fft, hann, stft, istft, magnitude_db, spectrum,
                 white_noise, tone, chirp, synthetic_speech, rir, convolve,
                 fft_convolve, delay, clip, normalize_peak, rms, rolling_rms,
                 smooth, db, energy_db, snr_db, erle_db, seg_snr_db,
                 scale_align, si_sdr_db, lufs_approx,
                 write_wav, read_wav, wav_info)
from chart import Chart, heatmap, BLUE, RED, GREEN, AMBER

FIG = _here.parents[1] / "fig"
AUDIO = _here.parents[1] / "audio"
FIG.mkdir(exist_ok=True)
AUDIO.mkdir(exist_ok=True)

random.seed(7)

# ---- 参数区 ----
N = 8000
LEAK_FIRST = 0.50        # 前半段线性 AEC 残留的回声比例
LEAK_SECOND = 0.00       # 后半段远端静音 / 路径变化后不再有回声
STATIC_ALPHA = 0.25      # 静态抵消固定使用的系数

# ---- 计算与作图 ----
rng = random.Random(7)
far = synthetic_speech(rng, N)
near = synthetic_speech(rng, N)
h = rir(rng, 128, decay=0.006)
echo_full = [1.4 * v for v in fft_convolve(far, h)[:N]]
alpha = [LEAK_FIRST if i < N // 2 else LEAK_SECOND for i in range(N)]
res_echo = [alpha[i] * echo_full[i] for i in range(N)]
noise = white_noise(rng, N, 0.003)

def run(near_gain, mode):
    clean = [near_gain * near[i] for i in range(N)]
    linear = [clean[i] + res_echo[i] + noise[i] for i in range(N)]
    if mode == "linear":
        out = linear
    elif mode == "static":
        out = [linear[i] - STATIC_ALPHA * echo_full[i] for i in range(N)]
    else:
        out = [linear[i] - alpha[i] * echo_full[i] for i in range(N)]
    residual = [out[i] - clean[i] for i in range(N)]
    return erle_db(res_echo, residual), seg_snr_db(clean, scale_align(out, clean)), out
conditions = (("单讲", 0.30), ("双讲", 0.90))
modes = (("线性AEC", "linear"), ("静态抵消", "static"), ("逐帧抵消", "adaptive"))
erles, snrs, labels = [], [], []
for cname, ng in conditions:
    for mname, mode in modes:
        e, s, out = run(ng, mode)
        erles.append(e)
        snrs.append(s)
        labels.append(cname + "-" + mname)
        if cname == "双讲" and mode == "linear":
            linear_dt = out
        if cname == "双讲" and mode == "adaptive":
            adaptive_dt = out
c = Chart(FIG / "24-aec.svg", "单讲/双讲下三种方案的 ERLE 与分段 SNR", xlabel="场景-方案", ylabel="dB",
          xticks=[(i, l) for i, l in enumerate(labels)])
c.bars(range(len(labels)), erles, BLUE, label="ERLE (dB)")
c.bars(range(len(labels)), snrs, GREEN, label="分段 SNR (dB)")
print("AEC图:", c.save())
heatmap(FIG / "24-matrix.svg", [erles, snrs], ["ERLE", "分段 SNR"], labels,
        title="六组实验的指标矩阵", vmin=-10, vmax=35, annotate=True)
print("矩阵图:", str(FIG / "24-matrix.svg"))
write_wav(AUDIO / "24-linear.wav", normalize_peak(linear_dt))
write_wav(AUDIO / "24-adaptive.wav", normalize_peak(adaptive_dt))
for l, e, s in zip(labels, erles, snrs):
    print("%s: ERLE=%.2f dB segSNR=%.2f dB" % (l, e, s))
print("SAMPLE_RATE=%d | 前半段泄漏=%.2f 后半段=%.2f 静态系数=%.2f" %
      (SAMPLE_RATE, LEAK_FIRST, LEAK_SECOND, STATIC_ALPHA))
