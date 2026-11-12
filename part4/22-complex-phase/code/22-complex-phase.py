#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计算 IRM 与 oracle CRM，比较二者的 SI-SDR，并画出干净谱与带噪谱的相位误差直方图。

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
NOISE_AMP = 0.040
MASK_NOISE = 0.06       # 模拟网络预测误差，避免 oracle 精确重建
BINS = 12

# ---- 计算与作图 ----
rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
fs, fn = stft(clean, N_FFT, HOP), stft(noise, N_FFT, HOP)
hist = [0] * BINS
phase_vals = []
for idx, (ry, iy) in enumerate(stft(noisy, N_FFT, HOP)):
    rs, is_ = fs[idx]
    rn, in_ = fn[idx]
    for k in range(1, N_FFT // 2):
        d = (math.atan2(is_[k], rs[k]) - math.atan2(iy[k], ry[k]) + math.pi) % (2 * math.pi) - math.pi
        phase_vals.append(abs(d))
        b = min(BINS - 1, int(abs(d) / math.pi * BINS))
        hist[b] += 1

def masked(kind):
    frames = stft(noisy, N_FFT, HOP)
    for idx, (ry, iy) in enumerate(frames):
        rs, is_ = fs[idx]
        rn, in_ = fn[idx]
        for k in range(N_FFT):
            ms, mn = math.hypot(rs[k], is_[k]), math.hypot(rn[k], in_[k])
            if kind == "IRM":
                g = ms / (ms + mn + 1e-9)
                ry[k] *= g
                iy[k] *= g
            else:
                y2 = ry[k] ** 2 + iy[k] ** 2 + 1e-12
                cr = (rs[k] * ry[k] + is_[k] * iy[k]) / y2
                ci = (is_[k] * ry[k] - rs[k] * iy[k]) / y2
                cr += rng.gauss(0, MASK_NOISE)
                ci += rng.gauss(0, MASK_NOISE)
                ry[k], iy[k] = cr * ry[k] - ci * iy[k], cr * iy[k] + ci * ry[k]
    return istft(frames, N_FFT, HOP, N)

irm, crm = masked("IRM"), masked("CRM")
labels = ("未处理", "IRM oracle", "CRM+预测误差")
signals = (noisy, irm, crm)
snrs = [seg_snr_db(clean, scale_align(s, clean)) for s in signals]
sdrs = [si_sdr_db(s, clean) for s in signals]
c = Chart(FIG / "22-masks.svg", "三种情形的分段 SNR 与 SI-SDR", xlabel="方法", ylabel="dB",
          xticks=[(i, m) for i, m in enumerate(labels)])
c.bars(range(3), snrs, BLUE, label="分段 SNR (dB)")
c.bars(range(3), sdrs, GREEN, label="SI-SDR (dB)")
print("掩码图:", c.save())
h = Chart(FIG / "22-phase.svg", "干净谱与带噪谱的相位误差分布", xlabel="|Δφ| 区间 / π", ylabel="频点计数")
h.bars(range(BINS), hist, RED, label="相位误差")
print("相位图:", h.save())
write_wav(AUDIO / "22-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "22-irm.wav", normalize_peak(irm))
write_wav(AUDIO / "22-crm.wav", normalize_peak(crm))
for m, a, b in zip(labels, snrs, sdrs):
    print("%s: segSNR=%.2f dB SI-SDR=%.2f dB" % (m, a, b))
print("平均 |Δφ|=%.3f rad | IRM→CRM SI-SDR 增益=%.2f dB | SAMPLE_RATE=%d N_FFT=%d" %
      (sum(phase_vals) / len(phase_vals), sdrs[2] - sdrs[1], SAMPLE_RATE, N_FFT))
