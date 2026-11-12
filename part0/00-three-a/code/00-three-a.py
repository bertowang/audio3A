#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成一整段退化语音，依次施加理想 AEC、谱减 ANS 与 AGC，打印每步指标并生成可试听 WAV。

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
N = 16000                  # 1 秒 @ 16 kHz
NOISE_AMP = 0.020           # 环境噪声幅度
ECHO_GAIN = 2.00            # 回声路径整体增益
FAR_GAIN = 0.35             # 近端语音电平（模拟说话人忽远忽近）
SUB_FACTOR = 1.20           # 谱减过减因子
FLOOR = 0.12                # 谱增益下限（抑制音乐噪声）

# ---- 计算与作图 ----
rng = random.Random(7)
far = synthetic_speech(rng, N)            # 远端说话（将成为回声）
near = synthetic_speech(rng, N)           # 近端说话（目标）
h = rir(rng, 192, decay=0.012)
echo = [ECHO_GAIN * v for v in fft_convolve(far, h)[:N]]
noise = white_noise(rng, N, NOISE_AMP)
level = [FAR_GAIN * (0.6 + 0.4 * math.sin(2 * math.pi * i / N)) for i in range(N)]
clean = [near[i] * level[i] for i in range(N)]
mic = [clean[i] + echo[i] + noise[i] for i in range(N)]

# AEC：本实验用「已知真实 h」演示理想上界（真正的辨识从第 05 章开始）
after_aec = [mic[i] - echo[i] for i in range(N)]
# ANS：频域谱减 —— 每个频率箱一个增益，帧内恒定，不会逐样本调制语音
#      噪声谱用合成噪声的前 4 帧均值（理想上界，第 08 章再讲如何在线估计）
frames = stft(after_aec, 512, 256)
nf = stft(noise, 512, 256)[:4]
noise_mag = [sum(math.hypot(re[k], im[k]) for re, im in nf) / len(nf)
             for k in range(512)]
for re, im in frames:
    for k in range(512):
        mag = math.hypot(re[k], im[k])
        g = max(FLOOR, 1.0 - SUB_FACTOR * noise_mag[k] / (mag + 1e-9))
        re[k] *= g
        im[k] *= g
after_ans = istft(frames, 512, 256, N)
# AGC：概览章用静态归一化做上界（逐帧动态增益与攻击/释放见第 14 章）
target_rms = 0.16
gain = min(8.0, target_rms / (rms(after_ans) + 1e-6))
out = clip([v * gain for v in after_ans])

c = Chart(FIG / "00-waveform.svg", "3A 链路各阶段波形（前 2000 样本）",
          xlabel="样本", ylabel="幅度")
c.line(range(2000), mic[:2000], "#9aa6b2", label="麦克风信号 y[n]", opacity=0.85)
c.line(range(2000), clean[:2000], BLUE, label="目标近端语音 d[n]")
c.line(range(2000), out[:2000], GREEN, label="3A 输出", opacity=0.9)
print("波形图:", c.save())
b = Chart(FIG / "00-metrics.svg", "各阶段的客观指标变化", xlabel="阶段", ylabel="dB / 电平",
          xticks=[(0, "原始"), (1, "AEC后"), (2, "ANS后"), (3, "AGC后")])
stages = [mic, after_aec, after_ans, out]
scores = [seg_snr_db(clean, scale_align(s, clean)) for s in stages]
b.bars(range(4), scores, BLUE, label="分段 SNR (dB)")
b.hline(0.0, "#9aa6b2")
print("指标图:", b.save())
write_wav(AUDIO / "00-mic.wav", normalize_peak(mic))
write_wav(AUDIO / "00-processed.wav", normalize_peak(out))
write_wav(AUDIO / "00-clean.wav", normalize_peak(clean))
print("WAV: %d 帧 / %d Hz / %.2f s / %d 字节" % wav_info(AUDIO / "00-mic.wav"))
print("ERLE(理想AEC)=%.2f dB | segSNR 原始=%.2f → AEC后=%.2f → ANS后=%.2f → 3A输出=%.2f dB" %
      (erle_db(echo, [after_aec[i] - clean[i] for i in range(N)]), *scores))
print("RMS 原始=%.4f → 输出=%.4f | 目标=%.4f" % (rms(mic), rms(out), target_rms))
