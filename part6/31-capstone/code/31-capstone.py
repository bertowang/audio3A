#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用纯标准库构造 IRM 上界与四个可解释变体，打印指标三列、画出消融图与掩码热力图。

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
N = 4096                    # 0.256 s @ 16 kHz
N_FFT, HOP = 256, 128
NOISE_AMP = 0.040
THETA = 0.65                # 阈值掩码的过减系数
FLOOR = 0.12                # 消融项 B：增益下限
SMOOTH_A = 0.55             # 消融项 C：帧间平滑系数
ORACLE_FLOOR = 0.02

# ---- 计算与作图 ----
rng = random.Random(7)
clean = synthetic_speech(rng, N)
wn = white_noise(rng, N, NOISE_AMP)
nz = [wn[i] + 0.35 * NOISE_AMP * math.sin(2 * math.pi * 137 * i / SAMPLE_RATE)
      for i in range(N)]
noisy = [clean[i] + nz[i] for i in range(N)]

frames_y = stft(noisy, N_FFT, HOP)
frames_s = stft(clean, N_FFT, HOP)
frames_n = stft(nz, N_FFT, HOP)
half = N_FFT // 2
ns = [sum(math.hypot(re[k], im[k]) for re, im in frames_n) / len(frames_n)
      for k in range(N_FFT)]

# oracle：用真实干净谱与噪声谱构造理想比率掩码，只作为上界
oracle_frames = []
for (ry, iy), (rs, is_), (rn, in_) in zip(frames_y, frames_s, frames_n):
    rr, ii = list(ry), list(iy)
    for k in range(N_FFT):
        ms = math.hypot(rs[k], is_[k])
        mn = math.hypot(rn[k], in_[k])
        g = max(ORACLE_FLOOR, ms / (ms + mn + 1e-9))
        rr[k] *= g
        ii[k] *= g
    oracle_frames.append((rr, ii))


def masked(theta, floor, smoothing):
    out_frames, prev = [], [0.0] * N_FFT
    for re, im in frames_y:
        rr, ii = list(re), list(im)
        for k in range(N_FFT):
            mag = math.hypot(rr[k], ii[k])
            raw = max(floor, 1.0 - theta * ns[k] / (mag + 1e-9))
            g = smoothing * prev[k] + (1.0 - smoothing) * raw if smoothing > 0.0 else raw
            prev[k] = g
            rr[k] *= g
            ii[k] *= g
        out_frames.append((rr, ii))
    return istft(out_frames, N_FFT, HOP, N)


def metrics(est):
    aligned = scale_align(est, clean)
    return seg_snr_db(clean, aligned), si_sdr_db(est, clean), lufs_approx(est)


variants = [("v0 无处理", noisy),
            ("v1 纯阈值", masked(THETA, 0.0, 0.0)),
            ("v2 加下限", masked(THETA, FLOOR, 0.0)),
            ("v3 加平滑", masked(THETA, FLOOR, SMOOTH_A)),
            ("oracle IRM", istft(oracle_frames, N_FFT, HOP, N))]
scores = [metrics(v[1]) for v in variants]

c = Chart(FIG / "31-ablation.svg", "小型掩码估计器的消融对照", xlabel="变体", ylabel="dB",
          xticks=[(i, v[0]) for i, v in enumerate(variants)])
c.bars(range(len(variants)), [s[0] for s in scores], BLUE, label="分段 SNR (尺度对齐)")
c.bars(range(len(variants)), [s[1] for s in scores], GREEN, label="SI-SDR")
c.hline(0.0, "#9aa6b2")
print("消融图:", c.save())

# 掩码热力图：行是降采样后的频率箱，列是帧
grid, prev = [], [0.0] * half
for re, im in frames_y:
    row = []
    for k in range(0, half, 8):
        mag = math.hypot(re[k], im[k])
        raw = max(FLOOR, 1.0 - THETA * ns[k] / (mag + 1e-9))
        g = SMOOTH_A * prev[k] + (1.0 - SMOOTH_A) * raw
        prev[k] = g
        row.append(round(g, 3))
    grid.append(row)
matrix = [list(col) for col in zip(*grid)]
heatmap(FIG / "31-mask.svg", matrix,
        ["%d Hz" % int(k * SAMPLE_RATE / N_FFT) for k in range(0, half, 8)],
        ["t%d" % i for i in range(len(matrix[0]))],
        title="可解释阈值掩码（行=频率箱，列=帧）", vmin=0.0, vmax=1.0)
print("掩码图:", str(FIG / "31-mask.svg"))

write_wav(AUDIO / "31-clean.wav", normalize_peak(clean))
write_wav(AUDIO / "31-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "31-threshold.wav", normalize_peak(variants[3][1]))
write_wav(AUDIO / "31-oracle.wav", normalize_peak(variants[4][1]))
print("WAV: %d 帧 / %d Hz / %.2f s / %d 字节" % wav_info(AUDIO / "31-noisy.wav"))
for name, sc in zip([v[0] for v in variants], scores):
    print("%s: segSNR=%.2f dB SI-SDR=%.2f dB LUFS≈%.1f" % (name, sc[0], sc[1], sc[2]))
print("oracle 与阈值掩码 segSNR 差=%.2f dB | 下限增益=%.2f dB | 平滑增益=%.2f dB | SAMPLE_RATE=%d Hz" %
      (scores[4][0] - scores[3][0], scores[2][0] - scores[1][0],
       scores[3][0] - scores[2][0], SAMPLE_RATE))
