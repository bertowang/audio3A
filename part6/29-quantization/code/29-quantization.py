#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 oracle 掩码量化到 2～16 bit，测量掩码 SNR、分段 SNR 与模型体积估算。

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
BITS = (2, 4, 6, 8, 12, 16)
MODEL_PARAMS = 100000

# ---- 计算与作图 ----
rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
fs, fn = stft(clean, N_FFT, HOP), stft(noise, N_FFT, HOP)

def quantize(v, bits):
    levels = 2 ** bits - 1
    return round(max(0.0, min(1.0, v)) * levels) / levels
def enhance(bits):
    frames = stft(noisy, N_FFT, HOP)
    err2, energy, count = 0.0, 0.0, 0
    for idx, (ry, iy) in enumerate(frames):
        rs, is_ = fs[idx]
        rn, in_ = fn[idx]
        for k in range(N_FFT):
            ms = math.hypot(rs[k], is_[k])
            mn = math.hypot(rn[k], in_[k])
            g0 = ms / (ms + mn + 1e-9)
            g = quantize(g0, bits)
            err2 += (g - g0) ** 2
            energy += g0 ** 2
            count += 1
            ry[k] *= g
            iy[k] *= g
    return istft(frames, N_FFT, HOP, N), 10 * math.log10((energy / count) / (err2 / count + 1e-12))
outputs, segs, mask_snrs = [], [], []
for b in BITS:
    out, m = enhance(b)
    outputs.append(out)
    segs.append(seg_snr_db(clean, scale_align(out, clean)))
    mask_snrs.append(m)
c = Chart(FIG / "29-bits.svg", "掩码位深与增强后分段 SNR", xlabel="位深 (bit)", ylabel="dB",
          xticks=[(i, "%d" % b) for i, b in enumerate(BITS)])
c.line(range(len(BITS)), segs, BLUE, label="分段 SNR (dB)")
print("位深图:", c.save())
m = Chart(FIG / "29-mask.svg", "掩码位深与掩码量化 SNR", xlabel="位深 (bit)", ylabel="dB",
          xticks=[(i, "%d" % b) for i, b in enumerate(BITS)])
m.line(range(len(BITS)), mask_snrs, GREEN, label="掩码 SNR (dB)")
m.line(range(len(BITS)), [6.02 * b + 1.76 - 6.02 for b in BITS], RED, label="理论趋势（相对偏移）")
print("掩码图:", m.save())
write_wav(AUDIO / "29-4bit.wav", normalize_peak(outputs[1]))
write_wav(AUDIO / "29-12bit.wav", normalize_peak(outputs[4]))
sizes = [MODEL_PARAMS * b / 8.0 / 1024.0 for b in BITS]
print("分段 SNR: " + " ".join("%dbit=%.2f" % (b, s) for b, s in zip(BITS, segs)))
print("掩码 SNR: " + " ".join("%dbit=%.2f" % (b, s) for b, s in zip(BITS, mask_snrs)))
print("模型体积(估算, %d 参数): " % MODEL_PARAMS +
      " ".join("%dbit=%.1fKB" % (b, z) for b, z in zip(BITS, sizes)))
print("SAMPLE_RATE=%d | 低比特省内存但可能引入音乐噪声" % SAMPLE_RATE)
