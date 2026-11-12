#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 oracle 频带增益扫描 4～64 个频带，比较分段 SNR 与全分辨率 IRM 上界。

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
BANDS = (4, 8, 16, 22, 32, 64)
FLOOR = 0.10

# ---- 计算与作图 ----
rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
fs, fn = stft(clean, N_FFT, HOP), stft(noise, N_FFT, HOP)
HALF = N_FFT // 2
def band_index(k, B):
    kk = k if k <= HALF else N_FFT - k
    return min(B - 1, kk * B // HALF)
def enhance(B, record=False):
    frames = stft(noisy, N_FFT, HOP)
    rows = []
    for idx, (ry, iy) in enumerate(frames):
        rs, is_ = fs[idx]
        rn, in_ = fn[idx]
        ps, py = [0.0] * B, [0.0] * B
        for k in range(N_FFT):
            b = band_index(k, B)
            ps[b] += rs[k] ** 2 + is_[k] ** 2
            py[b] += ry[k] ** 2 + iy[k] ** 2
        gains = [max(FLOOR, min(1.0, math.sqrt(ps[b] / (py[b] + 1e-12)))) for b in range(B)]
        for k in range(N_FFT):
            g = gains[band_index(k, B)]
            ry[k] *= g
            iy[k] *= g
        if record:
            rows.append(gains)
    return istft(frames, N_FFT, HOP, N), rows
scores, outputs = [], []
for B in BANDS:
    out, _ = enhance(B)
    outputs.append(out)
    scores.append(seg_snr_db(clean, scale_align(out, clean)))
full_frames = stft(noisy, N_FFT, HOP)
for idx, (ry, iy) in enumerate(full_frames):
    rs, is_ = fs[idx]
    rn, in_ = fn[idx]
    for k in range(N_FFT):
        g = math.hypot(rs[k], is_[k]) / (math.hypot(rs[k], is_[k]) + math.hypot(rn[k], in_[k]) + 1e-9)
        ry[k] *= g
        iy[k] *= g
irm = istft(full_frames, N_FFT, HOP, N)
irm_score = seg_snr_db(clean, scale_align(irm, clean))
_, rows22 = enhance(22, record=True)
c = Chart(FIG / "23-bands.svg", "频带数量与分段 SNR（oracle 增益）", xlabel="频带数", ylabel="dB",
          xticks=[(i, "%d" % B) for i, B in enumerate(BANDS)])
c.line(range(len(BANDS)), scores, BLUE, label="频带增益 segSNR")
c.line(range(len(BANDS)), [irm_score] * len(BANDS), RED, label="全分辨率 IRM 上界")
print("频带图:", c.save())
mat = rows22[::4]
heatmap(FIG / "23-gains.svg", mat,
        ["frame%d" % (i * 4) for i in range(len(mat))],
        ["b%d" % j for j in range(22)],
        title="22 频带 oracle 增益（降采样显示）", vmin=0.0, vmax=1.0, annotate=False)
print("增益热力图:", str(FIG / "23-gains.svg"))
write_wav(AUDIO / "23-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "23-22band.wav", normalize_peak(outputs[3]))
print("频带数→segSNR: " + " ".join("%d=%.2f" % (B, s) for B, s in zip(BANDS, scores)))
print("全分辨率 IRM=%.2f dB | 22 频带相对上界差=%.2f dB | SAMPLE_RATE=%d" %
      (irm_score, irm_score - scores[3], SAMPLE_RATE))
