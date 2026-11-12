#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实现先验 SNR 递推与 Wiener 增益，扫描平滑系数并与未处理信号对照。

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
ALPHAS = (0.0, 0.50, 0.90, 0.98)

# ---- 计算与作图 ----
rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
nf = stft(noise, N_FFT, HOP)[:8]
npow = [sum(re[k]**2 + im[k]**2 for re, im in nf) / len(nf) for k in range(N_FFT)]

def wiener(alpha):
    frames = stft(noisy, N_FFT, HOP)
    prev_g, prev_gamma = [1.0] * N_FFT, [1.0] * N_FFT
    first = None
    for re, im in frames:
        new_g, new_gamma = [], []
        for k in range(N_FFT):
            gamma = (re[k]**2 + im[k]**2) / (npow[k] + 1e-12)
            xi = alpha * prev_g[k]**2 * prev_gamma[k] + (1.0 - alpha) * max(gamma - 1.0, 0.0)
            g = xi / (1.0 + xi + 1e-12)
            re[k] *= g
            im[k] *= g
            new_g.append(g)
            new_gamma.append(gamma)
        if first is None:
            first = new_g
        prev_g, prev_gamma = new_g, new_gamma
    return istft(frames, N_FFT, HOP, N), first

scores, outputs = [], []
for a in ALPHAS:
    out, _g = wiener(a)
    outputs.append(out)
    scores.append(seg_snr_db(clean, scale_align(out, clean)))
_, gains = wiener(0.98)
c = Chart(FIG / "13-wiener.svg", "决策导向平滑系数与分段 SNR", xlabel="平滑系数 a", ylabel="dB",
          xticks=[(i, "%.2f" % a) for i, a in enumerate(ALPHAS)])
c.line(range(len(ALPHAS)), scores, BLUE, label="Wiener segSNR (dB)")
c.line(range(len(ALPHAS)), [seg_snr_db(clean, noisy)] * len(ALPHAS), RED, label="未处理")
print("Wiener图:", c.save())
g = Chart(FIG / "13-gains.svg", "a=0.98 时首帧各频率箱的 Wiener 增益", xlabel="频率箱 k", ylabel="增益")
g.line(range(N_FFT // 2), gains[:N_FFT // 2], GREEN, label="G[k]")
print("增益图:", g.save())
write_wav(AUDIO / "13-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "13-wiener.wav", normalize_peak(outputs[-1]))
print("未处理 segSNR=%.2f | Wiener: " % seg_snr_db(clean, noisy) +
      " ".join("a=%.2f->%.2f" % (a, s) for a, s in zip(ALPHAS, scores)))
print("SI-SDR 未处理=%.2f -> a=0.98 后=%.2f | SAMPLE_RATE=%d N_FFT=%d" %
      (si_sdr_db(noisy, clean), si_sdr_db(outputs[-1], clean), SAMPLE_RATE, N_FFT))
