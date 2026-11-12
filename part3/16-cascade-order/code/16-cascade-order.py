#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在同一条合成链路上交换 3A 顺序；线性 AEC 用已知 h 加 3% 受控泄漏，量化顺序错误造成的指标塌陷。

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
ECHO_GAIN = 1.5
NOISE_AMP = 0.020
LEAK = 0.03              # 故意留 3% 线性泄漏，避免「理想相减」得到不真实的无限 ERLE
TARGET = 0.16

# ---- 计算与作图 ----
rng = random.Random(7)
far = synthetic_speech(rng, N)
near = synthetic_speech(rng, N)
h = rir(rng, 128, decay=0.006)
echo = [ECHO_GAIN * v for v in fft_convolve(far, h)[:N]]
noise = white_noise(rng, N, NOISE_AMP)
clean = [0.5 * v for v in near]
y = [clean[i] + echo[i] + noise[i] for i in range(N)]
nf = stft(noise, N_FFT, HOP)[:8]
nmag = [sum(math.hypot(re[k], im[k]) for re, im in nf) / len(nf) for k in range(N_FFT)]

def aec(sig):
    return [sig[i] - (1.0 - LEAK) * echo[i] for i in range(N)]
def ans(sig):
    frames = stft(sig, N_FFT, HOP)
    for re, im in frames:
        for k in range(N_FFT):
            g = max(0.15, 1.0 - 1.2 * nmag[k] / (math.hypot(re[k], im[k]) + 1e-9))
            re[k] *= g
            im[k] *= g
    return istft(frames, N_FFT, HOP, N)
def agc(sig):
    g = min(6.0, TARGET / (rms(sig) + 1e-6))
    return clip([v * g for v in sig])

a1, a2, a3 = aec(y), None, None
a2, a3 = ans(a1), None
a3 = agc(a2)
b0 = agc(y)
b1, b2 = aec(b0), None
b2 = ans(b1)
c1 = ans(y)
c2 = aec(c1)
c3 = agc(c2)
chains = [("AEC-ANS-AGC", a1, a3), ("AGC-AEC-ANS", b1, b2), ("ANS-AEC-AGC", c2, c3)]
erles, snrs = [], []
for _name, stage1, final in chains:
    residual = [stage1[i] - clean[i] - noise[i] for i in range(N)]
    erles.append(erle_db(echo, residual))
    snrs.append(seg_snr_db(clean, scale_align(final, clean)))
c = Chart(FIG / "16-order.svg", "三种级联排列的 ERLE 与分段 SNR",
          xlabel="排列", ylabel="dB", xticks=[(i, n) for i, (n, _a, _b) in enumerate(chains)])
c.bars(range(3), erles, BLUE, label="ERLE (dB)")
c.bars(range(3), snrs, GREEN, label="分段 SNR (dB)")
print("顺序图:", c.save())
w = Chart(FIG / "16-waveform.svg", "正确顺序与 AGC 前置的输出波形（前 1200 样本）",
          xlabel="样本", ylabel="幅度")
w.line(range(1200), a3[:1200], GREEN, label="AEC-ANS-AGC")
w.line(range(1200), b2[:1200], RED, label="AGC-AEC-ANS")
print("波形图:", w.save())
write_wav(AUDIO / "16-correct.wav", normalize_peak(a3))
write_wav(AUDIO / "16-wrong.wav", normalize_peak(b2))
for (name, _a, _b), e, s in zip(chains, erles, snrs):
    print("%s: ERLE=%.2f dB segSNR=%.2f dB" % (name, e, s))
print("RMS 输入=%.4f 正确输出=%.4f | SAMPLE_RATE=%d N_FFT=%d" %
      (rms(y), rms(a3), SAMPLE_RATE, N_FFT))
