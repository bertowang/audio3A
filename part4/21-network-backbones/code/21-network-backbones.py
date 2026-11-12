#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 SGD 训练小型 sigmoid 掩码估计器，打印损失曲线、测试集指标与主流骨架参数量估算。

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
N = 4000
N_FFT, HOP = 128, 64
NOISE_AMP = 0.035
EPOCHS, LR = 14, 0.20
CONTEXT_FRAMES, HIDDEN, LAYERS = 5, 128, 3

# ---- 计算与作图 ----
tr_s = synthetic_speech(random.Random(11), N)
tr_n = white_noise(random.Random(12), N, NOISE_AMP)
te_s = synthetic_speech(random.Random(21), N)
te_n = white_noise(random.Random(22), N, NOISE_AMP)
tr_y = [tr_s[i] + tr_n[i] for i in range(N)]
te_y = [te_s[i] + te_n[i] for i in range(N)]
fy, fs, fn = stft(tr_y, N_FFT, HOP), stft(tr_s, N_FFT, HOP), stft(tr_n, N_FFT, HOP)

def feats(mag, avg):
    l, la = math.log10(mag + 1e-6), math.log10(avg + 1e-6)
    return [1.0, max(-2.0, min(1.0, l + 2.0)), max(-2.0, min(2.0, la - l))]
def predict(fv, w):
    z = max(-20.0, min(20.0, sum(w[j] * fv[j] for j in range(3))))
    return 1.0 / (1.0 + math.exp(-z))

train_set = []
for idx, (ry, iy) in enumerate(fy):
    rs, is_ = fs[idx]
    rn, in_ = fn[idx]
    mags = [math.hypot(ry[k], iy[k]) for k in range(N_FFT)]
    avg = sum(mags) / N_FFT
    for k in range(N_FFT):
        ms, mn = math.hypot(rs[k], is_[k]), math.hypot(rn[k], in_[k])
        train_set.append((feats(mags[k], avg), ms / (ms + mn + 1e-9)))
w, losses = [0.0, 0.0, 0.0], []
for ep in range(EPOCHS):
    total = 0.0
    for fv, t in train_set:
        p = predict(fv, w)
        err = p - t
        total += err * err
        d = err * p * (1.0 - p)
        for j in range(3):
            w[j] -= LR * d * fv[j]
    losses.append(total / len(train_set))

def apply_model(signal, gain_fn):
    frames = stft(signal, N_FFT, HOP)
    for ry, iy in frames:
        mags = [math.hypot(ry[k], iy[k]) for k in range(N_FFT)]
        avg = sum(mags) / N_FFT
        for k in range(N_FFT):
            g = gain_fn(feats(mags[k], avg))
            ry[k] *= g
            iy[k] *= g
    return istft(frames, N_FFT, HOP, N)
learned = apply_model(te_y, lambda fv: predict(fv, w))
ts, tn = stft(te_s, N_FFT, HOP), stft(te_n, N_FFT, HOP)
def oracle(idx, k):
    rs, is_ = ts[idx]
    rn, in_ = tn[idx]
    ms, mn = math.hypot(rs[k], is_[k]), math.hypot(rn[k], in_[k])
    return ms / (ms + mn + 1e-9)
frames = stft(te_y, N_FFT, HOP)
for idx, (ry, iy) in enumerate(frames):
    for k in range(N_FFT):
        g = oracle(idx, k)
        ry[k] *= g
        iy[k] *= g
irm = istft(frames, N_FFT, HOP, N)
scores = [seg_snr_db(te_s, scale_align(s, te_s)) for s in (te_y, learned, irm)]
c = Chart(FIG / "21-training.svg", "掩码估计器的训练损失（MSE）", xlabel="epoch", ylabel="MSE")
c.line(range(EPOCHS), losses, BLUE, label="训练 MSE")
print("训练图:", c.save())
b = Chart(FIG / "21-models.svg", "测试集：未处理 / 学习掩码 / IRM oracle", xlabel="方法", ylabel="dB",
          xticks=[(0, "未处理"), (1, "学习掩码"), (2, "IRM oracle")])
b.bars(range(3), scores, GREEN, label="分段 SNR (dB)")
print("模型图:", b.save())
dnn_params = (N_FFT // 2) * CONTEXT_FRAMES * HIDDEN + (LAYERS - 1) * HIDDEN * HIDDEN + HIDDEN * (N_FFT // 2)
write_wav(AUDIO / "21-test-noisy.wav", normalize_peak(te_y))
write_wav(AUDIO / "21-test-learned.wav", normalize_peak(learned))
print("训练 MSE 首=%.5f 末=%.5f | 学得权重 w=%s" %
      (losses[0], losses[-1], "[" + ", ".join("%.3f" % v for v in w) + "]"))
print("测试 segSNR 未处理=%.2f 学习掩码=%.2f IRM oracle=%.2f dB" % tuple(scores))
print("参数量估算: 本实验=3 | 帧级DNN(C=%d,L=%d,ctx=%d)≈%d | SAMPLE_RATE=%d" %
      (HIDDEN, LAYERS, CONTEXT_FRAMES, dnn_params, SAMPLE_RATE))
