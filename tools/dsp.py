#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""音频 3A 教材 · 纯标准库 DSP 基础库。

只依赖 math / cmath / random / array / struct / wave，不安装任何第三方包。
提供：radix-2 FFT、STFT/ISTFT、信号与房间冲激响应合成、卷积、
      常用客观度量（ERLE / SNR / SI-SDR / RMS / LUFS 近似）、16-bit PCM WAV 读写。

所有合成信号均由 random.Random(seed) 生成，因此每次运行的数值与波形完全一致。
"""
from __future__ import annotations

import array
import cmath
import math
import random
import struct
import wave

SAMPLE_RATE = 16000          # 全书统一采样率（宽带语音）
EPS = 1e-12


# ---------------------------------------------------------------- FFT
def fft(re, im, inverse=False):
    """原地迭代 radix-2 Cooley-Tukey FFT；长度必须是 2 的幂。"""
    n = len(re)
    if n == 0 or (n & (n - 1)):
        raise ValueError("FFT 长度必须是 2 的幂，实际为 %d" % n)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            re[i], re[j] = re[j], re[i]
            im[i], im[j] = im[j], im[i]
    length = 2
    while length <= n:
        ang = (2.0 if inverse else -2.0) * math.pi / length
        wr, wi = math.cos(ang), math.sin(ang)
        half = length >> 1
        for start in range(0, n, length):
            cr, ci = 1.0, 0.0
            for k in range(half):
                a, b = start + k, start + k + half
                tr, ti = cr * re[b] - ci * im[b], cr * im[b] + ci * re[b]
                re[b], im[b] = re[a] - tr, im[a] - ti
                re[a], im[a] = re[a] + tr, im[a] + ti
                cr, ci = cr * wr - ci * wi, cr * wi + ci * wr
        length <<= 1
    if inverse:
        for i in range(n):
            re[i] /= n
            im[i] /= n
    return re, im


def spectrum(x, n_fft=512, *, db_floor=-80.0):
    """取信号首帧的幅度谱（dB），返回前半频谱。"""
    seg = list(x[:n_fft]) + [0.0] * max(0, n_fft - len(x))
    re, im = fft(seg[:], [0.0] * n_fft)
    half = n_fft // 2
    out = []
    for k in range(half):
        mag = math.hypot(re[k], im[k]) / n_fft
        out.append(max(db_floor, 20 * math.log10(mag + EPS)))
    return out


def hann(n):
    return [0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)) for i in range(n)] if n > 1 else [1.0]


def stft(x, n_fft=512, hop=256):
    """短时傅里叶变换；返回 [(re_list, im_list), ...]，Hann 窗 + 50% 重叠。

    前后各补 n_fft/2 个零，保证首尾样本也被两帧完整覆盖，
    这样 istft 在频谱被掩码/谱减修改后不会在边界放大（WOLA 的标准做法）。
    """
    w = hann(n_fft)
    pad = n_fft // 2
    xp = [0.0] * pad + list(x) + [0.0] * pad
    frames = []
    for start in range(0, len(xp) - n_fft + 1, hop):
        re = [xp[start + i] * w[i] for i in range(n_fft)]
        frames.append(fft(re, [0.0] * n_fft))
    return frames


def istft(frames, n_fft=512, hop=256, length=None):
    """加权 overlap-add 重建；用窗平方和归一化，再裁掉 stft 的前置补零。"""
    w = hann(n_fft)
    total = hop * (len(frames) - 1) + n_fft if frames else 0
    out, norm = [0.0] * total, [0.0] * total
    for f, (re, im) in enumerate(frames):
        rr, _ii = fft(re[:], im[:], inverse=True)
        base = f * hop
        for i in range(n_fft):
            if base + i < total:
                out[base + i] += rr[i] * w[i]
                norm[base + i] += w[i] * w[i]
    for i in range(total):
        if norm[i] > EPS:
            out[i] /= norm[i]
    core = out[n_fft // 2:]
    if length is None:
        return core
    if len(core) < length:
        core.extend([0.0] * (length - len(core)))
    return core[:length]


def magnitude_db(frames, n_fft=512, db_floor=-80.0):
    """时频谱（dB）矩阵，行 = 频率箱（只取前半），列 = 帧；供 SVG 热力图使用。"""
    half = n_fft // 2
    rows = [[] for _ in range(half)]
    for re, im in frames:
        for k in range(half):
            mag = math.hypot(re[k], im[k]) / n_fft
            rows[k].append(max(db_floor, 20 * math.log10(mag + EPS)))
    return rows


# ---------------------------------------------------------------- 信号合成
def white_noise(rng, n, amp=0.1):
    return [rng.gauss(0.0, amp) for _ in range(n)]


def tone(freq, n, sr=SAMPLE_RATE, amp=0.3, phase=0.0):
    return [amp * math.sin(2 * math.pi * freq * i / sr + phase) for i in range(n)]


def chirp(f0, f1, n, sr=SAMPLE_RATE, amp=0.3):
    out = []
    for i in range(n):
        t = i / sr
        f = f0 + (f1 - f0) * t / (n / sr)
        out.append(amp * math.sin(2 * math.pi * (f0 * t + 0.5 * (f - f0) * t)))
    return out


def synthetic_speech(rng, n, sr=SAMPLE_RATE, *, seed_syllable=0.22):
    """合成「类语音」：缓变基频 + 谐波共振峰 + 音节包络 + 少量清音噪声。

    不是真实语音，但具备语音的三个关键统计特征（谐波结构、短时平稳、
    音节级能量起伏），足以用来演示 AEC / ANS / AGC 的机制与指标变化。
    """
    out = [0.0] * n
    syl = max(1, int(seed_syllable * sr))
    weights = [(1.0 / h ** 1.15) * (1.0 + 0.55 * math.sin(2 * math.pi * h * 380.0 / 1000.0))
               for h in range(1, 9)]
    formant = sum(weights)
    phase = 0.0
    f0 = 120.0
    for i in range(n):
        if i % 64 == 0:
            f0 = 108.0 + 34.0 * math.sin(2 * math.pi * i / (1.7 * sr)) + rng.gauss(0, 1.2)
        pos = i % syl
        env = math.sin(math.pi * pos / syl) ** 1.5
        v = 0.0
        for h, wh in enumerate(weights, 1):
            v += wh * math.sin(h * phase)
        v /= formant
        phase += 2 * math.pi * f0 / sr
        breath = rng.gauss(0, 0.035) if env > 0.25 else 0.0
        out[i] = 0.55 * env * (v + breath)
    return out


def rir(rng, length=256, *, decay=0.008, direct_delay=24, reflections=3, sr=SAMPLE_RATE):
    """合成房间冲激响应：强直达声 + 稀疏早期反射 + 指数衰减混响尾。

    decay 为能量衰减时间常数（秒）；直达声幅度固定为 1，尾噪声幅度较小，
    以保证互相关能在真实延迟处出现清晰峰值。
    """
    h = [0.0] * length
    if 0 <= direct_delay < length:
        h[direct_delay] = 1.0
    for i in range(min(reflections, 6)):
        d = direct_delay + int((i + 1) * 0.011 * sr) + rng.randint(0, 8)
        if d < length:
            h[d] += (0.45 ** (i + 1)) * (1.0 if rng.random() > 0.5 else -1.0)
    tau = max(1.0, decay * sr)
    for i in range(direct_delay + 1, length):
        h[i] += rng.gauss(0, 0.14) * math.exp(-(i - direct_delay) / tau)
    return h


def convolve(x, h):
    """朴素线性卷积（教学用，直观但 O(NM)）。"""
    out = [0.0] * (len(x) + len(h) - 1)
    for i, a in enumerate(x):
        if abs(a) < EPS:
            continue
        for j, b in enumerate(h):
            out[i + j] += a * b
    return out


def fft_convolve(x, h):
    """overlap-add 分块频域卷积；与 convolve 数值一致但快得多。"""
    block = 128
    n_fft = 1
    while n_fft < block + len(h) - 1:
        n_fft <<= 1
    hr, hi = fft(list(h) + [0.0] * (n_fft - len(h)), [0.0] * n_fft)
    out = [0.0] * (len(x) + len(h) - 1)
    for start in range(0, len(x), block):
        seg = x[start:start + block]
        re = seg + [0.0] * (n_fft - len(seg))
        fr, fi = fft(re, [0.0] * n_fft)
        pr, pi = [fr[k] * hr[k] - fi[k] * hi[k] for k in range(n_fft)], \
                 [fr[k] * hi[k] + fi[k] * hr[k] for k in range(n_fft)]
        rr, _ii = fft(pr, pi, inverse=True)
        for k in range(n_fft):
            if start + k < len(out):
                out[start + k] += rr[k]
    return out


def delay(x, samples, length=None):
    """整数延迟（前置补零）。"""
    n = length if length is not None else len(x)
    return [x[i - samples] if 0 <= i - samples < len(x) else 0.0 for i in range(n)]


def clip(x, limit=1.0):
    return [max(-limit, min(limit, v)) for v in x]


def normalize_peak(x, target=0.85):
    p = max((abs(v) for v in x), default=0.0)
    return [v * target / p for v in x] if p > EPS else list(x)


# ---------------------------------------------------------------- 客观度量
def rms(x):
    return math.sqrt(sum(v * v for v in x) / max(1, len(x)))


def rolling_rms(x, win=256):
    """O(N) 滑动 RMS：维护窗口平方和，用于包络跟踪 / VAD / AGC / 噪声估计。

    out[i] 只依赖 x[:i+1]，因此是因果的，可逐样本在实时链路中使用。
    """
    out = [0.0] * len(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += v * v
        if i >= win:
            acc -= x[i - win] * x[i - win]
        out[i] = math.sqrt(max(acc, 0.0) / min(i + 1, win))
    return out


def smooth(x, attack=0.01, release=0.001):
    """一阶平滑（攻击快、释放慢），AGC 增益与噪声跟踪的常用包络器。"""
    out, v = [], x[0] if x else 0.0
    for s in x:
        a = attack if s > v else release
        v = (1 - a) * v + a * s
        out.append(v)
    return out


def db(x):
    return 20 * math.log10(max(abs(x), EPS))


def energy_db(x):
    return 10 * math.log10(sum(v * v for v in x) / max(1, len(x)) + EPS)


def snr_db(clean, noise):
    """给定时域干净信号与噪声，返回信噪比（dB）。"""
    return 10 * math.log10((sum(v * v for v in clean) + EPS) /
                           (sum(v * v for v in noise) + EPS))


def erle_db(echo, residual):
    """回声返回损耗增强 ERLE：处理前回声能量 / 处理后残余能量。"""
    return 10 * math.log10((sum(v * v for v in echo) + EPS) /
                           (sum(v * v for v in residual) + EPS))


def scale_align(x, ref):
    """把 x 按最小二乘最优标量缩放回去匹配 ref。

    AGC 会整体改变尺度，直接把处理结果与未缩放的 clean 相减会把增益差
    误算成噪声；评测时应先做尺度对齐，或改用尺度不变的 SI-SDR。
    """
    n = min(len(x), len(ref))
    dot = sum(x[i] * ref[i] for i in range(n))
    norm = sum(ref[i] * ref[i] for i in range(n))
    a = dot / (norm + EPS)
    return [v / a for v in x] if abs(a) > 1e-9 else list(x)


def seg_snr_db(clean, noisy, frame=320):
    """分段 SNR：逐帧计算后取平均，避免静音帧主导全局指标。"""
    vals = []
    for s in range(0, min(len(clean), len(noisy)) - frame, frame):
        cs = clean[s:s + frame]
        ns = [noisy[i] - clean[i] for i in range(s, s + frame)]
        ec, en = sum(v * v for v in cs), sum(v * v for v in ns)
        if ec > 1e-6:
            vals.append(max(-10.0, min(35.0, 10 * math.log10((ec + EPS) / (en + EPS)))))
    return sum(vals) / len(vals) if vals else 0.0


def si_sdr_db(est, ref):
    """尺度不变 SDR：先做最小二乘投影，再算目标/残差能量比。"""
    n = min(len(est), len(ref))
    e, r = est[:n], ref[:n]
    dot = sum(a * b for a, b in zip(e, r))
    norm = sum(b * b for b in r)
    alpha = dot / (norm + EPS)
    res = [a - alpha * b for a, b in zip(e, r)]
    return 10 * math.log10((sum((alpha * b) ** 2 for b in r) + EPS) /
                           (sum(v * v for v in res) + EPS))


def lufs_approx(x, sr=SAMPLE_RATE):
    """EBU R128 的简化教学近似：K 加权用单极点高通 + 预滤波近似，再做 400ms 分块门控。

    仅用于演示「响度归一化」的机制，不是合规的 LUFS 测量；工程请用 ffmpeg ebur128 / loudnorm。
    """
    y, prev = [], 0.0
    a = 0.985
    for v in x:
        prev = a * prev + (1 - a) * v
        hp = v - prev
        y.append(hp + 0.35 * v)     # 粗略的高频预加重
    block = int(0.4 * sr)
    blocks = []
    for s in range(0, len(y), block):
        seg = y[s:s + block]
        if seg:
            blocks.append(-0.691 + 10 * math.log10(sum(v * v for v in seg) / len(seg) + EPS))
    if not blocks:
        return -70.0
    # 简化的相对门控：丢掉比块能量中位数低 10 LU 以上的静音块
    ordered = sorted(blocks)
    mid = ordered[len(ordered) // 2]
    gated = [v for v in blocks if v >= mid - 10.0]
    if not gated:
        return -70.0
    return -0.691 + 10 * math.log10(
        sum(10 ** (0.1 * (v + 0.691)) for v in gated) / len(gated))


# ---------------------------------------------------------------- WAV
def write_wav(path, samples, sr=SAMPLE_RATE):
    """写 16-bit 单声道 PCM WAV；先做峰值限制防止溢出。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = array.array("h")
    for v in samples:
        s = int(max(-1.0, min(1.0, v)) * 32767)
        data.append(s)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
    return str(path)


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        raw = w.readframes(w.getnframes())
        sr = w.getframerate()
    n = len(raw) // 2
    values = struct.unpack("<%dh" % n, raw)
    return [v / 32768.0 for v in values], sr


def wav_info(path):
    """返回 (帧数, 采样率, 秒数, 字节数)，供自检器验证 RIFF/WAVE 文件。"""
    with wave.open(str(path), "rb") as w:
        return w.getnframes(), w.getframerate(), w.getnframes() / w.getframerate(), \
            w.getnframes() * w.getnchannels() * w.getsampwidth()

