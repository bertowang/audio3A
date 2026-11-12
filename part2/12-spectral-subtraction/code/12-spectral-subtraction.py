#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在合成带噪语音上扫描过减因子，测量分段 SNR 与孤立谱洞数量。

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
N_FFT, HOP = 256, 128
NOISE_AMP = 0.035
FACTORS = (0.5, 1.0, 1.5, 2.0, 3.0)
FLOOR = 0.15

# ---- 计算与作图 ----
rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
nf = stft(noise, N_FFT, HOP)[:8]
nmag = [sum(math.hypot(re[k], im[k]) for re, im in nf) / len(nf) for k in range(N_FFT)]

def enhance(sub, floor):
    frames = stft(noisy, N_FFT, HOP)
    floored = 0
    for re, im in frames:
        gains = []
        for k in range(N_FFT):
            mag = math.hypot(re[k], im[k])
            g = max(floor, 1.0 - sub * nmag[k] / (mag + 1e-9))
            gains.append(g)
            re[k] *= g
            im[k] *= g
        floored += sum(1 for v in gains if v <= floor + 1e-9)
    return istft(frames, N_FFT, HOP, N), floored / max(1, len(frames) * N_FFT)

scores, clipped = [], []
for f in FACTORS:
    out, h = enhance(f, FLOOR)
    scores.append(seg_snr_db(clean, scale_align(out, clean)))
    clipped.append(h)
best = scores.index(max(scores))
out_best, _ = enhance(FACTORS[best], FLOOR)

c = Chart(FIG / "12-subtraction.svg", "过减因子与分段 SNR", xlabel="过减因子 beta", ylabel="dB",
          xticks=[(i, "%.1f" % f) for i, f in enumerate(FACTORS)])
c.line(range(len(FACTORS)), scores, BLUE, label="分段 SNR (dB)")
c.line(range(len(FACTORS)), [seg_snr_db(clean, noisy)] * len(FACTORS), RED, label="未处理")
print("SNR图:", c.save())
b = Chart(FIG / "12-distortion.svg", "过减因子与谱增益触底比例（语音失真代理量）",
          xlabel="过减因子 beta", ylabel="触底频率箱比例",
          xticks=[(i, "%.1f" % f) for i, f in enumerate(FACTORS)])
b.bars(range(len(FACTORS)), clipped, RED, label="触底比例")
print("失真图:", b.save())
write_wav(AUDIO / "12-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "12-enhanced.wav", normalize_peak(out_best))
print("segSNR 未处理=%.2f | 谱减: " % seg_snr_db(clean, noisy) +
      " ".join("b=%.1f->%.2f" % (f, s) for f, s in zip(FACTORS, scores)))
print("触底比例: " + " ".join("b=%.1f->%.3f" % (f, c) for f, c in zip(FACTORS, clipped)))
print("最佳 beta=%.1f | SAMPLE_RATE=%d N_FFT=%d" % (FACTORS[best], SAMPLE_RATE, N_FFT))
