#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计算理想二值掩码与理想比值掩码，量化它们的 oracle 上界并画出时频掩码。

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

# ---- 计算与作图 ----
rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
fs, fn = stft(clean, N_FFT, HOP), stft(noise, N_FFT, HOP)

def apply_mask(kind):
    frames = stft(noisy, N_FFT, HOP)
    rows = []
    for idx, (ry, iy) in enumerate(frames):
        rs, is_ = fs[idx]
        rn, in_ = fn[idx]
        gains = []
        for k in range(N_FFT):
            ms = math.hypot(rs[k], is_[k])
            mn = math.hypot(rn[k], in_[k])
            g = (1.0 if ms > mn else 0.0) if kind == "IBM" else ms / (ms + mn + 1e-9)
            ry[k] *= g
            iy[k] *= g
            gains.append(g)
        rows.append(gains[::8])
    return istft(frames, N_FFT, HOP, N), rows

ibm, _ = apply_mask("IBM")
irm, mask_rows = apply_mask("IRM")
methods = ("未处理", "IBM oracle", "IRM oracle")
signals = (noisy, ibm, irm)
s_snr = [seg_snr_db(clean, scale_align(s, clean)) for s in signals]
s_sdr = [si_sdr_db(s, clean) for s in signals]
c = Chart(FIG / "19-masks.svg", "三种情形的分段 SNR 与 SI-SDR", xlabel="方法", ylabel="dB",
          xticks=[(i, m) for i, m in enumerate(methods)])
c.bars(range(3), s_snr, BLUE, label="分段 SNR (dB)")
c.bars(range(3), s_sdr, GREEN, label="SI-SDR (dB)")
print("掩码对比图:", c.save())
mat = mask_rows[::4]
heatmap(FIG / "19-irm.svg", mat,
        ["frame%d" % (i * 4) for i in range(len(mat))],
        ["f%d" % (k * 8) for k in range(len(mat[0]))],
        title="IRM 理想掩码（降采样显示）", vmin=0.0, vmax=1.0, annotate=False)
print("掩码热力图:", str(FIG / "19-irm.svg"))
write_wav(AUDIO / "19-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "19-irm.wav", normalize_peak(irm))
for m, a, b in zip(methods, s_snr, s_sdr):
    print("%s: segSNR=%.2f dB SI-SDR=%.2f dB" % (m, a, b))
print("IRM 相对未处理提升=%.2f dB | SAMPLE_RATE=%d N_FFT=%d HOP=%d" %
      (s_snr[2] - s_snr[0], SAMPLE_RATE, N_FFT, HOP))
