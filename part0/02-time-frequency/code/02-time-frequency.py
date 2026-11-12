#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手写 FFT 验证能量守恒，测量不同位深的量化 SNR，并画出时频热力图。

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
N_FFT, HOP = 512, 256
N = 8000
BITS = (4, 8, 12, 16)      # 对比的量化位深

# ---- 计算与作图 ----
rng = random.Random(7)
sig = [0.45 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE) +
       0.25 * math.sin(2 * math.pi * 1310 * i / SAMPLE_RATE) for i in range(N_FFT)]
re, im = fft(sig[:], [0.0] * N_FFT)
time_energy = sum(v * v for v in sig)
freq_energy = sum(re[k] ** 2 + im[k] ** 2 for k in range(N_FFT)) / N_FFT
peak_bin = max(range(N_FFT // 2), key=lambda k: math.hypot(re[k], im[k]))

sp = spectrum(sig, N_FFT)
c = Chart(FIG / "02-spectrum.svg", "双正弦的幅度谱（dB）", xlabel="频率箱 k", ylabel="dB")
c.line(range(len(sp)), sp, BLUE, label="幅度谱")
c.vline(peak_bin, RED, label="峰值箱")
print("频谱图:", c.save())

speech = synthetic_speech(rng, N)
frames = stft(speech, N_FFT, HOP)
spec = magnitude_db(frames, N_FFT)
rows = [row[::2] for row in spec[::8]]        # 降采样，便于 SVG 阅读
heatmap(FIG / "02-spectrogram.svg", rows,
        ["%d Hz" % int(k * SAMPLE_RATE / N_FFT) for k in range(0, N_FFT // 2, 8)][:len(rows)],
        ["t%d" % (i * 4) for i in range(len(rows[0]))][::4],
        title="合成语音的时频谱（dB，降采样显示）", vmin=-75, vmax=-15)
print("时频图:", str(FIG / "02-spectrogram.svg"))

def quantize(x, bits):
    step = 2.0 / (2 ** bits)
    return [round(v / step) * step for v in x]

snrs = []
for b in BITS:
    q = quantize(speech, b)
    noise = [q[i] - speech[i] for i in range(N)]
    snrs.append(snr_db(speech, noise))
qchart = Chart(FIG / "02-quantization.svg", "量化位深与量化噪声 SNR", xlabel="位深 (bit)", ylabel="dB",
               xticks=[(i, "%d bit" % b) for i, b in enumerate(BITS)])
qchart.bars(range(len(BITS)), snrs, GREEN, label="实测 SNR")
qchart.line(range(len(BITS)), [6.02 * b + 1.76 - 12.0 for b in BITS], RED,
            label="理论趋势（相对偏移）")
print("量化图:", qchart.save())
write_wav(AUDIO / "02-4bit.wav", quantize(speech, 4))
write_wav(AUDIO / "02-16bit.wav", quantize(speech, 16))
print("Parseval 时域=%.6f 频域=%.6f 相对误差=%.2e | 峰值箱=%d 对应 %.0f Hz" %
      (time_energy, freq_energy, abs(time_energy - freq_energy) / time_energy,
       peak_bin, peak_bin * SAMPLE_RATE / N_FFT))
print("量化 SNR: " + " ".join("%dbit=%.1fdB" % (b, s) for b, s in zip(BITS, snrs)) +
      " | 每增 1 bit 约 +6 dB")
