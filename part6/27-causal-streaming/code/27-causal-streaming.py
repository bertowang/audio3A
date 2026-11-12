#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实现三种滑动平均，验证流式与离线因果逐样本一致，并测量非因果前瞻。

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
N = 6000
K = 64                   # 平滑窗口（样本）
BLOCK = 256              # 流式分块大小（16 ms @ 16 kHz）

# ---- 计算与作图 ----
def causal_ma(x, k):
    out, acc = [], 0.0
    for i, v in enumerate(x):
        acc += v
        if i >= k:
            acc -= x[i - k]
        out.append(acc / min(i + 1, k))
    return out
def centered_ma(x, k):
    half, out = k // 2, []
    for i in range(len(x)):
        seg = x[max(0, i - half):min(len(x), i + half + 1)]
        out.append(sum(seg) / len(seg))
    return out
def stream_ma(x, k, block):
    out, hist = [], []
    for s in range(0, len(x), block):
        for v in x[s:s + block]:
            hist.append(v)
            if len(hist) > k:
                hist.pop(0)
            out.append(sum(hist) / len(hist))
    return out

step = [0.0 if i < N // 3 else 1.0 for i in range(N)]
env_c, env_n, env_s = causal_ma(step, K), centered_ma(step, K), stream_ma(step, K, BLOCK)
maxdiff = max(abs(a - b) for a, b in zip(env_c, env_s))
def cross(env):
    for i, v in enumerate(env):
        if v >= 0.5:
            return i
    return len(env)
lag = cross(env_c) - cross(env_n)
rng = random.Random(7)
speech = synthetic_speech(rng, N)
raw_env = rolling_rms(speech, 128)
smooth_c = causal_ma(raw_env, K)
smooth_n = centered_ma(raw_env, K)
c = Chart(FIG / "27-streaming.svg", "阶跃响应：因果 / 非因果 / 分块流式", xlabel="样本", ylabel="平滑值")
c.line(range(0, N, 20), [step[i] for i in range(0, N, 20)], "#9aa6b2", label="输入阶跃")
c.line(range(0, N, 20), [env_c[i] for i in range(0, N, 20)], BLUE, label="因果 / 流式")
c.line(range(0, N, 20), [env_n[i] for i in range(0, N, 20)], RED, label="中心化（非因果）")
print("阶跃图:", c.save())
e = Chart(FIG / "27-envelope.svg", "语音包络：因果平滑 vs 非因果平滑", xlabel="样本 / 40", ylabel="RMS")
e.line(range(0, N, 40), [raw_env[i] for i in range(0, N, 40)], "#9aa6b2", label="原始包络")
e.line(range(0, N, 40), [smooth_c[i] for i in range(0, N, 40)], BLUE, label="因果")
e.line(range(0, N, 40), [smooth_n[i] for i in range(0, N, 40)], RED, label="非因果")
print("包络图:", e.save())
carrier = tone(440, N, amp=0.30)
write_wav(AUDIO / "27-causal.wav", [carrier[i] * env_c[i] for i in range(N)])
write_wav(AUDIO / "27-noncausal.wav", [carrier[i] * env_n[i] for i in range(N)])
print("流式 vs 离线因果 最大误差=%.2e | 状态缓存=%d 样本 | 分块=%d 样本" %
      (maxdiff, K - 1, BLOCK))
print("非因果提前量=%d 样本 = %.2f ms | 阶跃位置=%d | SAMPLE_RATE=%d" %
      (lag, 1000.0 * lag / SAMPLE_RATE, N // 3, SAMPLE_RATE))
