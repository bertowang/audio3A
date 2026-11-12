#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 00～05 章：卷首共同语言与上卷信号处理基础。"""
from __future__ import annotations

from book_schema import C, eq, table
from chapter_kit import mk_demo, shell, p, ul, ol, note, warn, sec

CH = [

# ==================================================================== 00
C("00", "p0", "part0/00-three-a", "3A 是什么：一条实时语音链路上的三个约束",
  "把「通话里听起来不舒服」拆成三个可建模、可测量、可分别优化的估计问题。",
  hours="2 学时",
  goals=["能画出一条实时语音链路，并标出 AEC / ANS / AGC 各自作用的位置。",
         "能说明为什么三者的顺序不能随意交换。",
         "能写出每个模块的输入、输出与典型指标。",
         "能运行全书第一个实验，听到处理前后的差别并核对数值。"],
  points=["实时语音链路", "AEC 回声消除", "ANS 噪声抑制", "AGC 自动增益控制",
          "三个约束的耦合", "3A 处理顺序", "因果性与算法延迟", "客观与主观评价"],
  sections=[
      ("0.1", "从一次视频会议说起", sec(
          p("你对着笔记本说话，对方的声音从扬声器放出来，又被同一个麦克风收回去——"
            "这就是<strong>声学回声</strong>；空调、键盘、风扇是<strong>加性噪声</strong>；"
            "你离麦克风忽远忽近、有人轻声有人大嗓门，是<strong>电平起伏</strong>。"
            "三类退化同时出现在一段波形里，却在数学上是三种不同的可估计量。"),
          eq("y[n] = d[n] + h * x[n] + v[n]　，g（增益）在采集后端作用"),
          p("其中 <code>x[n]</code> 是远端参考信号、<code>h</code> 是房间回声路径、"
            "<code>d[n]</code> 是近端语音、<code>v[n]</code> 是环境噪声、<code>y[n]</code> 是麦克风信号。"
            "3A 的任务就是：在只知道 <code>x[n]</code> 与 <code>y[n]</code> 的条件下，"
            "把 <code>d[n]</code> 尽量干净、等响地交给编码器。"),
          table(["模块", "要消掉什么", "已知什么", "核心方法", "典型指标"], [
              ["AEC", "h * x（回声）", "远端参考 x", "自适应辨识 ĥ + 残余抑制", "ERLE / 双讲MOS"],
              ["ANS", "v（噪声）", "只有 y", "噪声功率估计 + 谱增益", "segSNR / STOI / DNSMOS"],
              ["AGC", "电平起伏", "输出电平", "包络跟踪 + 平滑增益", "LUFS / 峰值余量"],
          ], ["10%", "20%", "18%", "30%", "22%"]))),
      ("0.2", "为什么是「三」个而不是一个", sec(
          p("三者的<strong>可观测性</strong>不同：AEC 有参考信号，是监督式系统辨识；"
            "ANS 没有参考，只能靠统计假设区分语音与噪声；AGC 不区分内容，只改整体尺度。"
            "把它们做成一个黑箱模型并非不行，但工程上分开有三个硬理由："),
          ul(["<strong>顺序有物理约束</strong>：AGC 若放在 AEC 前面会改变回声路径增益，"
              "使自适应滤波器不断追一个移动的目标；AEC 必须在 AGC 之前、且用未加工的参考信号。",
              "<strong>失效模式可隔离</strong>：双讲漏回声、音乐噪声、增益泵浦分别可定位到具体模块。",
              "<strong>算力与延迟可预算</strong>：每块单独估算 MIPS、内存与算法延迟，便于端侧裁剪。"]),
          note("全书主线", "信号 → 系统 → 估计 → 适应 → 感知 → 数据驱动 → 部署。"
               "上卷把每个模块写成可手推的估计器；下卷把同一批估计器换成可学习的函数，"
               "但链路结构、因果约束与评价指标完全不变。"))),
      ("0.3", "两卷的分工与阅读方式", sec(
          table(["", "上卷 · 传统算法（04–18）", "下卷 · AI 算法（19–31）"], [
              ["先验", "声学模型 + 统计假设 + 最优滤波", "数据分布 + 网络归纳偏置"],
              ["参数", "步长、滤波器长度、时间常数，可解释", "权重由数据训练得到，需专门做可解释性"],
              ["数据", "不需要训练集，逐帧在线自适应", "需要成对的干净/退化语料与增强策略"],
              ["优势", "低算力、低延迟、可证明收敛", "非线性失真、非平稳噪声下上限更高"],
              ["弱点", "非线性回声、突发噪声、强混响", "分布外泛化、算力与黑箱"],
              ["主流做法", "WebRTC AEC3 / SpeexDSP", "RNNoise / DNS Challenge 系列 / 混合系统"],
          ], ["14%", "43%", "43%"]),
          p("今天的工业系统几乎都是<strong>混合式</strong>：经典 AEC 做线性消除，"
            "神经网络做残余回声与噪声抑制，再用传统 AGC 收尾。因此两卷不是替代关系，而是同一条链路的两层。"))),
  ],
  demos=[mk_demo(
      "code/00-three-a.py", "实验 0-1 · 造一条含回声、噪声与电平起伏的链路，逐个打开 3A",
      "合成一整段退化语音，依次施加理想 AEC、谱减 ANS 与 AGC，打印每步指标并生成可试听 WAV。",
      """N = 16000                  # 1 秒 @ 16 kHz
NOISE_AMP = 0.020           # 环境噪声幅度
ECHO_GAIN = 2.00            # 回声路径整体增益
FAR_GAIN = 0.35             # 近端语音电平（模拟说话人忽远忽近）
SUB_FACTOR = 1.20           # 谱减过减因子
FLOOR = 0.12                # 谱增益下限（抑制音乐噪声）""",
      """rng = random.Random(7)
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
print("RMS 原始=%.4f → 输出=%.4f | 目标=%.4f" % (rms(mic), rms(out), target_rms))""",
      [("fig/00-waveform.svg", "麦克风信号、目标语音与 3A 输出波形"),
       ("fig/00-metrics.svg", "逐阶段分段 SNR 变化")],
      [("audio/00-mic.wav", "未处理：可同时听到回声与噪声"),
       ("audio/00-clean.wav", "目标近端语音（参考）"),
       ("audio/00-processed.wav", "依次打开 3A 后的输出")],
      "先听 <code>00-mic.wav</code> 再听 <code>00-processed.wav</code>；"
      "把 <code>ECHO_GAIN</code> 与 <code>NOISE_AMP</code> 调大，看图与指标如何变化。",
      "理想 AEC 能获得很高的 ERLE（本例用真实 <code>h</code>，是上界而非真实算法性能）；"
      "ANS 与 AGC 逐步抬升分段 SNR、把 RMS 拉到目标电平。"
      "<strong>请特别注意：AGC 之后的波形幅度变了，直接比较波形不再等价于比较质量。</strong>",
      "把 <code>FAR_GAIN</code> 改成常数 1.0（无电平起伏），AGC 的作用会明显变小。")],
  commands=[shell("用 ffmpeg 查本机到底有哪些 3A 相关滤镜",
                  """ffmpeg -hide_banner -version | head -3
ffmpeg -hide_banner -filters | grep -E 'arnndn|afftdn|anlmdn|loudnorm|dynaudnorm|speechnorm|ebur128|acompressor|alimiter|silencedetect|astats|volumedetect|aecho|aresample'""",
                  "滤镜是否可用取决于本机 ffmpeg 版本与编译选项；本书不假定任何特定版本，"
                  "所有引入版本请以 https://ffmpeg.org/ffmpeg-filters.html 为准。")],
  highlights=[("webrtc", "3A 的工业级参考实现，先建立整体印象"),
              ("ffmpeg-filters", "离线验证与实验的权威文档"),
              ("wiki-aec", "回声消除问题定义"),
              ("rfc3550", "实时链路里延迟与抖动的来源")],
  analogy="3A 是一条流式处理管道：<code>x[n]</code> 是旁路输入，<code>y[n]</code> 是主数据流，"
          "AEC 是有参考的抵消器、ANS 是统计滤波器、AGC 是输出限幅器。"
          "<strong>任何一环用了未来帧，整条链路就不再是因果系统。</strong>",
  bridge="全书入口。{{ch:01}} 把 <code>h</code> 与房间讲清楚，{{ch:02}} 建立时频工具，"
         "{{ch:03}} 约定「变好了」怎么算；上卷从 {{ch:04}} 开始实现。",
  pitfalls=["把 AGC 放在 AEC 之前，破坏参考信号与回声的线性关系。",
            "用处理后信号与处理前信号直接算波形差，忽略 AGC 的尺度变化。",
            "以为 ERLE 高就等于通话好听（还需看双讲与语音失真）。",
            "把离线处理的结果当成实时可用，忽略因果性与算法延迟。"],
  exercises=["画出 3A 链路框图，标出每个模块的输入、输出与可观测信号。",
             "解释为什么 AEC 需要参考信号而 ANS 不需要。",
             "列举两种「客观指标变好但主观变差」的情形。"],
  further=["{{ch:16}} 级联顺序的工程细节；{{ch:17}} ffmpeg / WebRTC 命令实操；{{home#roadmap}} 两卷路线。"]),

# ==================================================================== 01
C("01", "p0", "part0/01-acoustic-path", "声学链路与信号模型：房间、麦克风与回声路径",
  "把「扬声器放出来的声音又被自己收回去」写成可辨识的线性系统。",
  hours="3 学时",
  goals=["能画出声学回声链路并写出卷积模型。",
         "能解释房间冲激响应的直达声、早期反射与混响尾。",
         "能用互相关估计回声路径的时延并核对真值。",
         "能说明非线性失真、时钟漂移与双讲为何让模型失效。"],
  points=["声学回声链路", "房间冲激响应 RIR", "直达声与早期反射", "混响时间与 T60",
          "线性卷积模型", "时延估计与互相关", "双讲场景", "非线性与时钟漂移"],
  sections=[
      ("1.1", "从扬声器到麦克风是一条 LTI 通道", sec(
          eq("e[n] = (h * x)[n] = Σ_{k=0}^{L−1} h[k] · x[n−k]　，y[n] = d[n] + e[n] + v[n]"),
          p("<code>h</code> 是房间冲激响应：先是一段静默（声波传播 + 缓冲），然后是直达声脉冲，"
            "接着是几次离散的墙面反射，最后是指数衰减的密集混响尾。"
            "AEC 的全部工作，本质上是<strong>在双讲与噪声干扰下在线估计 h 并用它预测 e</strong>。"),
          table(["RIR 区段", "物理来源", "对 AEC 的影响"], [
              ["直达延迟", "扬声器到麦克风距离 + 系统缓冲", "决定滤波器起始位置，估计错则整段抵消失效"],
              ["早期反射", "桌面、墙壁的一次/二次反射", "稀疏强系数，自适应滤波器需覆盖"],
              ["混响尾", "多次散射，能量指数衰减", "尾长决定滤波器阶数（16 kHz 下常取 128–512 ms）"],
              ["非线性", "扬声器削波、外壳振动", "线性模型无法解释，需要残余回声抑制或神经后处理"],
          ], ["18%", "38%", "44%"]))),
      ("1.2", "三个让模型失效的现实", sec(
          ul(["<strong>双讲</strong>：近端与远端同时说话，<code>d[n]</code> 不再是「安静的噪声」，"
              "自适应滤波器会把近端语音当成误差、把 h 往错误方向更新。",
              "<strong>时钟漂移</strong>：播放与采集用不同晶振，采样率有 ppm 级偏差，"
              "等效于 h 缓慢平移；不做缓冲对齐会让 ERLE 周期性塌陷。",
              "<strong>路径突变</strong>：有人移动笔记本、手掌挡住麦克风，h 在几十毫秒内整体改变，"
              "滤波器需要快速重收敛。"]),
          p("工程上因此把问题拆成三层：<strong>时延对齐</strong>（粗对齐，见本实验）、"
            "<strong>线性自适应滤波</strong>（见上卷第二篇）、"
            "<strong>残余抑制</strong>（处理非线性与双讲残差，见第 11 章与下卷）。"))),
  ],
  demos=[mk_demo(
      "code/01-rir.py", "实验 1-1 · 合成房间冲激响应并用互相关找回真实时延",
      "生成含直达声与混响尾的 RIR，卷积出回声，再用归一化互相关估计延迟。",
      """N = 12000
TRUE_DELAY = 24             # 真实直达声延迟（样本）
RIR_LEN = 256               # 冲激响应长度
DECAY = 0.008               # 混响能量衰减时间常数（秒）
CORR_LEN = 2048             # 互相关累加点数
MAX_LAG = 120               # 搜索的最大延迟""",
      """rng = random.Random(7)
far = synthetic_speech(rng, N)
probe = white_noise(rng, N, 0.35)     # 宽带探测信号：自相关接近冲激，便于对齐
h = rir(rng, RIR_LEN, decay=DECAY, direct_delay=TRUE_DELAY)
echo = fft_convolve(far, h)[:N]
near = [0.30 * v for v in synthetic_speech(rng, N)]
mic = [near[i] + echo[i] for i in range(N)]
probe_echo = fft_convolve(probe, h)[:N]
mic_probe = [probe_echo[i] + 0.3 * near[i] for i in range(N)]

# 归一化互相关：用参考信号 x 与麦克风 y 找最强线性相关的滞后
def norm_corr(a, b, lag, k):
    num = sum(a[i] * b[i + lag] for i in range(k))
    da = math.sqrt(sum(a[i] ** 2 for i in range(k)))
    db_ = math.sqrt(sum(b[i + lag] ** 2 for i in range(k)))
    return num / (da * db_ + 1e-12)

lags = list(range(MAX_LAG))
corr = [norm_corr(probe, mic_probe, lag, CORR_LEN) for lag in lags]
best_lag = lags[max(range(len(lags)), key=lambda i: corr[i])]
peak = max(corr)

c = Chart(FIG / "01-rir.svg", "合成房间冲激响应 h[k]", xlabel="抽头 k（16 kHz）", ylabel="幅度")
c.line(range(RIR_LEN), h, BLUE, label="h[k]")
c.vline(TRUE_DELAY, RED, label="真实直达延迟")
print("冲激图:", c.save())
d = Chart(FIG / "01-corr.svg", "参考信号与麦克风信号的归一化互相关",
          xlabel="滞后 lag", ylabel="相关系数")
d.line(lags, corr, GREEN, label="归一化互相关")
d.vline(best_lag, RED, label="峰值")
print("互相关图:", d.save())
write_wav(AUDIO / "01-far.wav", normalize_peak(far))
write_wav(AUDIO / "01-mic.wav", normalize_peak(mic))
print("真实延迟=%d 估计延迟=%d 峰值相关=%.3f | 直达增益=%.3f RIR能量=%.4f" %
      (TRUE_DELAY, best_lag, peak, h[TRUE_DELAY], sum(v * v for v in h)))
print("混响时间常数=%.4f s 理论 T60≈%.3f s（指数衰减到 -60 dB）" %
      (DECAY, 6.9 * DECAY))""",
      [("fig/01-rir.svg", "脉冲、早期反射与指数衰减尾"),
       ("fig/01-corr.svg", "互相关峰值定位回声延迟")],
      [("audio/01-far.wav", "远端参考信号（扬声器播放的内容）"),
       ("audio/01-mic.wav", "麦克风：近端语音 + 回声")],
      "对照估计延迟与 <code>TRUE_DELAY</code>；把 <code>TRUE_DELAY</code> 改成 60 再跑一次。",
      "互相关峰值精确落在真实直达延迟，因为 <code>y</code> 中含 <code>h*x</code>；"
      "这里刻意用<strong>白噪声探测信号</strong>而非语音做对齐——语音有准周期自相关，"
      "会产生旁峰把峰值拉偏。近端语音只贡献不相关背景，使峰值幅度下降但位置稳定。"
      "这正是工程上「先粗对齐、再自适应」的第一步。",
      "把 <code>near</code> 幅度调大到与回声相当（模拟强双讲），峰值会变钝甚至偏移。")],
  commands=[shell("用 ffmpeg 合成一条可听的回声样本（无需写代码）",
                  """ffmpeg -hide_banner -i input.wav -af \\
  "aecho=0.8:0.9:1000|1800:0.25|0.15" echo.wav
ffmpeg -hide_banner -i echo.wav -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'""",
                  "aecho 用「输入增益:输出增益:延迟ms|延迟ms:衰减|衰减」叠加延迟副本；"
                  "该滤镜是否在本机可用请先用 `ffmpeg -filters | grep aecho` 自查。")],
  highlights=[("pyroomacoustics", "用镜像源模型生成更真实的 RIR，替换本书合成例"),
              ("wiki-aec", "回声路径与抵消的经典定义"),
              ("itu-g168", "回声消除器测试信号与 ERLE 规范"),
              ("ffmpeg-aecho", "不用写代码就能造回声测试样本")],
  analogy="RIR 是一个长度为 L 的 FIR 系数数组，AEC 是<strong>在线系统辨识</strong>："
          "输入 x、观测 y、目标 d，求一组 ĥ 使预测误差最小。"
          "时延对齐相当于先给这段数组找到正确的起始下标。",
  bridge="{{ch:00}} 给出链路与三个约束，本章把 <code>h</code> 具体化；"
         "{{ch:02}} 提供观察 <code>h</code> 与信号的时频工具，{{ch:03}} 约定评价指标。",
  pitfalls=["忽略播放与采集缓冲造成的几十毫秒延迟，直接让自适应滤波器硬追。",
            "把混响尾当噪声，滤波器阶数不够导致 ERLE 上不去。",
            "用纯线性模型解释扬声器削波造成的非线性回声。",
            "在双讲时照常更新 h，把滤波器「带跑」。"],
  exercises=["推导 16 kHz 下 128 ms 混响需要多少抽头，并说明算力代价。",
             "解释为什么互相关峰值会被强双讲拉偏。",
             "列举三种会改变 h 的日常动作，并给出检测思路。"],
  further=["{{ch:09}} AEC 总体结构；{{ch:11}} AEC3 的对齐与双讲处理。"]),

# ==================================================================== 02
C("02", "p0", "part0/02-time-frequency", "采样、量化与时频表示：从 PCM 到 STFT",
  "3A 的所有算法都在「一帧频谱」上做决策；先把这块数据结构讲透。",
  hours="3 学时",
  goals=["能说明采样率、位深、帧长与算法延迟的关系。",
         "能手推 radix-2 FFT 的蝶形结构并验证 Parseval 定理。",
         "能解释 STFT 的窗、重叠相加与时频分辨率折中。",
         "能量化位深与量化噪声的信噪比关系。"],
  points=["采样与混叠", "量化位深与量化噪声", "PCM 与 WAV 容器", "DFT 与 radix-2 FFT",
          "Parseval 定理", "STFT 与 Hann 窗", "重叠相加 OLA", "时频分辨率折中"],
  sections=[
      ("2.1", "三段不可逆的信息压缩", sec(
          p("真实声压是连续时间、连续幅度的。进入算法前经过三步："
            "<strong>抗混叠滤波 + 采样</strong>（时间离散化）、<strong>量化</strong>（幅度离散化）、"
            "<strong>分帧</strong>（局部平稳假设）。每一步都丢信息，也各自带一个必须记住的约束。"),
          table(["步骤", "关键参数", "丢掉什么", "3A 里的后果"], [
              ["采样", "16 k / 48 kHz", "高于奈奎斯特频率的成分", "宽带回声需更高采样率才有足够 h 精度"],
              ["量化", "16 / 24 bit", "幅度精度，引入量化噪声", "低电平近端语音被 AGC 放大时噪声一起被放大"],
              ["分帧", "20–32 ms、50% 重叠", "帧内非平稳细节", "帧长 + 前瞻直接决定算法延迟"],
          ], ["12%", "20%", "30%", "38%"]),
          eq("SNR_量化 ≈ 6.02·B + 1.76 dB　（满幅正弦、均匀量化）"))),
      ("2.2", "FFT 只是 DFT 的一个 O(N log N) 实现", sec(
          eq("X[k] = Σ_{n=0}^{N−1} x[n]·e^(−j2πkn/N)　|　Σ|x[n]|² = (1/N)Σ|X[k]|²"),
          p("本书的 <code>tools/dsp.py</code> 手写迭代 radix-2 FFT：位反转置换 + log₂N 层蝶形。"
            "这样做不是重复造轮子，而是让「频域自适应滤波」「谱减」「复数掩码」都能被逐行读懂。"
            "附录 A.6 给出迁移到 <code>numpy.fft</code> / <code>torchaudio</code> 的对照。"))),
      ("2.3", "STFT：把一维流变成二维图", sec(
          eq("X[t,k] = Σ_n x[n + tH]·w[n]·e^(−j2πkn/N)　，H = N/2"),
          p("帧长 N 越大，频率分辨率越好、时间分辨率越差；这就是 3A 里最基础的折中。"
            "Hann 窗抑制频谱泄漏，50% 重叠 + 加权重叠相加（WOLA）保证修改频谱后仍能无失真重建——"
            "<strong>这是所有掩码类算法能成立的前提</strong>，下卷会反复用到。"),
          note("实验提醒", "本书 <code>stft()</code> 在信号前后各补 N/2 个零，"
               "确保首尾样本也被两帧覆盖；否则在频谱被谱减/掩码修改后，边界会因窗平方和过小而被放大。"))),
  ],
  demos=[mk_demo(
      "code/02-time-frequency.py", "实验 2-1 · FFT/Parseval、量化噪声与 STFT 时频谱",
      "手写 FFT 验证能量守恒，测量不同位深的量化 SNR，并画出时频热力图。",
      """N_FFT, HOP = 512, 256
N = 8000
BITS = (4, 8, 12, 16)      # 对比的量化位深""",
      """rng = random.Random(7)
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
      " | 每增 1 bit 约 +6 dB")""",
      [("fig/02-spectrum.svg", "双正弦幅度谱与峰值箱定位"),
       ("fig/02-spectrogram.svg", "合成语音的时频热力图"),
       ("fig/02-quantization.svg", "位深与量化噪声 SNR 的线性关系")],
      [("audio/02-4bit.wav", "4 bit 量化，可明显听到量化噪声"),
       ("audio/02-16bit.wav", "16 bit 量化，接近原始合成语音")],
      "核对 Parseval 相对误差应接近机器精度；试听两个 WAV 比较量化噪声。",
      "Parseval 误差在 1e-15 量级，说明手写 FFT 的归一化正确；峰值箱对应 440 Hz 附近。"
      "量化 SNR 随位深约每 bit 提升 6 dB，与 <code>6.02B+1.76</code> 一致（本例信号非满幅，故有固定偏移）。",
      "把 <code>N_FFT</code> 改成 1024，观察频率分辨率提高而时间分辨率下降。")],
  commands=[shell("用 ffmpeg 检查采样率、重采样与电平统计",
                  """ffmpeg -hide_banner -i input.wav -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'
ffmpeg -hide_banner -i input48k.wav -af aresample=16000 -c:a pcm_s16le out16k.wav
ffmpeg -hide_banner -i out16k.wav -af astats=metadata=1 -f null - 2>&1 | grep -E 'RMS level|Peak level'""",
                  "aresample 负责采样率转换，volumedetect / astats 给出量化前后的电平核对；"
                  "滤镜可用性以本机 `ffmpeg -filters` 为准。")],
  highlights=[("wiki-fft", "radix-2 FFT 的算法依据"),
              ("wiki-stft", "STFT 与重叠相加定义"),
              ("dspguide", "免费在线 DSP 教材，卷积/FFT 章节直观"),
              ("python-docs", "wave 模块是本书 WAV 读写的依据")],
  analogy="STFT 是把一维流按滑动窗口切成二维矩阵；"
          "<code>istft(stft(x)) == x</code> 是一条单元测试。"
          "<strong>下卷所有掩码模型，本质上都是在这个矩阵上做逐元素乘法。</strong>",
  bridge="{{ch:01}} 给出时域的 h，本章给出观察它的频域工具；"
         "{{ch:03}} 用这些工具定义指标，{{ch:12}} 与 {{ch:19}} 将用它实现谱减与神经掩码。",
  pitfalls=["把 FFT 结果当成 dB 谱直接比较，忘记取幅度与对数。",
            "频谱修改后不用 WOLA 归一化，边界出现爆音。",
            "混淆频率箱索引与实际 Hz（需乘 fs/N）。",
            "用长帧追求频率分辨率，忽略实时链路的延迟预算。"],
  exercises=["推导 N=512、fs=16 kHz 时每个频率箱对应多少 Hz。",
             "解释为什么 50% 重叠的 Hann 窗能无失真重建。",
             "把量化位深从 16 降到 8，估算 AGC 放大后噪声的听感变化。"],
  further=["{{ch:06}} 频域自适应滤波；{{ch:12}} 谱减；{{ch:19}} 时频掩码。"]),

# ==================================================================== 03
C("03", "p0", "part0/03-metrics", "怎么算「变好了」：客观指标、尺度与主观听测",
  "没有度量就没有工程；但每个指标都只回答一个问题，且都带自己的陷阱。",
  hours="3 学时",
  goals=["能计算 ERLE、分段 SNR、SI-SDR 与响度近似值。",
         "能说明为什么 AGC 之后必须先做尺度对齐。",
         "能区分有参考指标与无参考指标、 intrusive 与 non-intrusive。",
         "能设计一组覆盖双讲与噪声类型的评测集。"],
  points=["ERLE 与回声残余", "分段 SNR", "SI-SDR 与尺度不变性", "PESQ / POLQA / STOI",
          "DNSMOS 无参考评分", "LUFS 与真峰值", "主观听测 P.835", "评测集设计"],
  sections=[
      ("3.1", "指标族：每个都对应一个具体问法", sec(
          eq("ERLE = 10log₁₀(Σe²[n] / Σr²[n])　|　segSNR = mean_t 10log₁₀(Σd² / Σ(d−d̂)²)"),
          table(["指标", "问的是", "需要干净参考吗", "典型陷阱"], [
              ["ERLE", "回声被消掉多少", "需要回声 e[n]", "双讲时含近端语音，会虚高或虚低"],
              ["segSNR / SI-SDR", "整体失真有多大", "需要 d[n]", "AGC 改尺度后直接相减会误判"],
              ["PESQ / POLQA", "人耳觉得像不像", "需要 d[n]", "对非语音噪声与非线性编解码不准"],
              ["STOI / ESTOI", "可懂度还剩多少", "需要 d[n]", "不反映舒适度与音乐噪声"],
              ["DNSMOS", "没参考时打个分", "不需要", "模型偏好可能奖励过度降噪"],
              ["LUFS / True Peak", "响度与削波余量", "不需要", "响度合规不等于听感舒适"],
          ], ["18%", "26%", "20%", "36%"]),
          p("ITU-T G.168 规定回声消除器的测试信号与 ERLE 口径；"
            "P.862 / P.863 是有参考感知质量，P.835 是带噪声语音的三维主观评分。"
            "<strong>工程上至少要同时报一个失真类、一个可懂度类、一个主观/无参考类指标</strong>。"))),
      ("3.2", "三个最常见的评测错误", sec(
          ul(["<strong>尺度错配</strong>：AGC 后信号整体变大，用原始 clean 相减会把增益差当成噪声；"
              "先做最小二乘尺度对齐，或改用尺度不变的 SI-SDR（本书 <code>scale_align()</code>）。",
              "<strong>数据泄漏</strong>：用测试集挑阈值、调网络、选 checkpoint，"
              "得到的分数只是样本内成绩（下卷 {{ch:30}} 详述）。",
              "<strong>指标单一</strong>：只报 segSNR 会奖励「把一切都压成静音」的策略；"
              "必须同时报语音失真或可懂度。"]),
          note("可复现实验", "每个指标都写下：信号长度、采样率、窗长、是否尺度对齐、"
               "退化类型与强度、随机种子。本书全部脚本固定 <code>random.seed(7)</code>，"
               "打印的数值可被逐行复算。"))),
  ],
  demos=[mk_demo(
      "code/03-metrics.py", "实验 3-1 · 退化强度扫描下的指标族与尺度对齐陷阱",
      "扫描噪声与回声强度，计算 ERLE / segSNR / SI-SDR / LUFS，并演示 AGC 尺度错配。",
      """N = 8000
AMPS = (0.004, 0.012, 0.030, 0.070)   # 噪声幅度扫描
ECHO_GAINS = (0.3, 0.9, 1.8, 3.0)     # 回声强度扫描""",
      """rng = random.Random(7)
clean = synthetic_speech(rng, N)
h = rir(rng, 128, decay=0.006)
far = synthetic_speech(rng, N)
echo_ref = fft_convolve(far, h)[:N]      # 卷积只算一次，避免在循环/推导里重复 O(N log N)
rows, noisy_samples = [], []
for amp in AMPS:
    nz = white_noise(rng, N, amp)
    noisy = [clean[i] + nz[i] for i in range(N)]
    noisy_samples.append(noisy)
    rows.append([snr_db(clean, nz), seg_snr_db(clean, noisy),
                 si_sdr_db(noisy, clean), lufs_approx(noisy)])
erle_rows = []
for g in ECHO_GAINS:
    echo = [g * v for v in echo_ref]
    mic = [clean[i] + echo[i] for i in range(N)]
    # 理想 AEC 上界：减去真实回声，残余只剩近端语音，用回声/残余比衡量
    erle_rows.append(erle_db(echo, clean))

c = Chart(FIG / "03-metrics.svg", "噪声增强时四个指标的变化", xlabel="噪声幅度", ylabel="数值",
          xticks=[(i, "%.3f" % a) for i, a in enumerate(AMPS)])
c.line(range(len(AMPS)), [r[1] for r in rows], BLUE, label="分段 SNR (dB)")
c.line(range(len(AMPS)), [r[2] for r in rows], GREEN, label="SI-SDR (dB)")
c.line(range(len(AMPS)), [r[0] for r in rows], AMBER, label="全局 SNR (dB)")
print("指标图:", c.save())
heatmap(FIG / "03-heatmap.svg", [[round(v, 2) for v in r] for r in rows],
        ["amp=%.3f" % a for a in AMPS], ["SNR", "segSNR", "SI-SDR", "LUFS"],
        title="不同噪声强度下的指标矩阵", vmin=-25, vmax=30, annotate=True)
print("矩阵图:", str(FIG / "03-heatmap.svg"))
write_wav(AUDIO / "03-clean.wav", normalize_peak(clean))
write_wav(AUDIO / "03-noisy.wav", normalize_peak(noisy_samples[2]))
write_wav(AUDIO / "03-echo.wav", normalize_peak(
    [clean[i] + 1.8 * echo_ref[i] for i in range(N)]))

# 尺度错配：把 clean 放大 2.5 倍后再直接算 segSNR
scaled = [2.5 * v for v in clean]
before = seg_snr_db(clean, scaled)
after = seg_snr_db(clean, scale_align(scaled, clean))
print("ERLE(理想AEC): " + " ".join("g=%.1f→%.1fdB" % (g, e)
                                  for g, e in zip(ECHO_GAINS, erle_rows)))
print("噪声扫描 segSNR: " + " ".join("amp=%.3f→%.2f" % (a, r[1]) for a, r in zip(AMPS, rows)))
print("噪声扫描 SI-SDR: " + " ".join("amp=%.3f→%.2f" % (a, r[2]) for a, r in zip(AMPS, rows)))
print("噪声 amp=%.3f 时 segSNR=%.2f SI-SDR=%.2f LUFS≈%.1f" %
      (AMPS[2], rows[2][1], rows[2][2], rows[2][3]))
print("AGC 尺度错配演示：直接相减 segSNR=%.2f dB，尺度对齐后=%.2f dB" % (before, after))""",
      [("fig/03-metrics.svg", "四个指标随噪声强度的变化"),
       ("fig/03-heatmap.svg", "指标矩阵热力图")],
      [("audio/03-clean.wav", "干净参考语音"),
       ("audio/03-noisy.wav", "中等强度加噪语音"),
       ("audio/03-echo.wav", "含强回声的麦克风信号")],
      "对照尺度对齐前后的 segSNR；把 <code>2.5</code> 改成 1.0 观察差值消失。",
      "segSNR 与 SI-SDR 随噪声增强单调下降；把一个纯放大 2.5 倍的干净信号直接相减，"
      "segSNR 会<strong>虚低</strong>，尺度对齐后恢复。<strong>AGC 之后的评测必须先对齐尺度。</strong>",
      "把 <code>AMPS</code> 增加一档 0.15，看 segSNR 的下限截断是否影响结论。")],
  commands=[shell("用 ffmpeg 做客观电平与响度核对",
                  """ffmpeg -hide_banner -i out.wav -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'
ffmpeg -hide_banner -i out.wav -af ebur128=peak=true -f null - 2>&1 | tail -12
ffmpeg -hide_banner -i out.wav -af astats=metadata=1:reset=0 -f null - 2>&1 | grep -E 'RMS|Peak|Number of samples'""",
                  "ebur128 输出 I/S/LRA 与 True Peak；astats 给出 RMS 与峰值统计。"
                  "注意本书 <code>lufs_approx()</code> 只是教学近似，不是合规测量。")],
  highlights=[("itu-g168", "ERLE 与回声消除器测试规范"),
              ("itu-p862", "PESQ 有参考感知质量"),
              ("stoi", "可懂度指标实现"),
              ("dnsmos", "无参考神经 MOS 评分")],
  analogy="指标是监控面板：ERLE 是回声模块的 unit test，segSNR 是信噪比 SLO，"
          "SI-SDR 是尺度不变的回归测试，DNSMOS 是线上无标签监控。"
          "<strong>只看一块面板做决策，迟早被「静音策略」骗过。</strong>",
  bridge="卷首结束。{{ch:04}} 起进入上卷，先补线性系统与自适应滤波两块数学地基，"
         "再在 {{ch:09}}～{{ch:14}} 实现三大引擎。",
  pitfalls=["AGC 后不做尺度对齐就报告 SNR 提升。",
            "只在安静背景、单讲条件下测 ERLE，忽略双讲。",
            "用测试集调完阈值再报告该测试集分数。",
            "把 DNSMOS 高分当成语音保真度高。"],
  exercises=["构造一个「segSNR 很高但完全听不清」的信号，并解释原因。",
             "推导 scale_align 的最小二乘解，说明它与 SI-SDR 投影的关系。",
             "为一款实时通话 App 设计一份至少含 6 个场景的评测集。"],
  further=["{{ch:18}} 上卷综合评测；{{ch:30}} 下卷评测陷阱与数据泄漏。"]),

# ==================================================================== 04
C("04", "p1", "part1/04-lti-convolution", "线性系统、卷积与频域实现",
  "AEC 的每一次「预测回声」，都是一次带长滤波器的实时卷积。",
  hours="2 学时",
  goals=["能写出 LTI 系统的卷积与频域等价形式。",
         "能手算分块 overlap-add 频域卷积并验证数值一致。",
         "能说明滤波器长度、算力与混响尾的关系。",
         "能解释为什么频域实现是实时 AEC 的必然选择。"],
  points=["LTI 与冲激响应", "线性卷积", "循环卷积与补零", "overlap-add",
          "FFT 卷积复杂度", "分块频域滤波", "滤波器阶数", "混响尾与尾长"],
  sections=[
      ("4.1", "同一个运算，两种复杂度", sec(
          eq("y[n] = Σ_{k=0}^{L−1} h[k]x[n−k]　⇔　Y[k] = H[k]·X[k]（补足零后）"),
          table(["实现", "每输出样本代价", "L=512 时相对量级", "适用"], [
              ["朴素时域卷积", "O(L) 乘加", "~512", "短滤波器、教学、离线核对"],
              ["分块频域 OLA", "O(log(L+B))", "~10–20", "实时 AEC、长混响尾"],
              ["逐块 FDAF/MDF", "O(log L) + 自适应更新", "工业主流", "第 06 章详述"],
          ], ["24%", "26%", "24%", "26%"]),
          p("16 kHz 下覆盖 128 ms 混响需要 L≈2048 抽头。时域逐样本做 2048 次乘加约"
            "32 M 次/秒，而分块频域把它压到几 M 次/秒——<strong>这不是优化技巧，是能不能实时跑的分界线</strong>。"))),
      ("4.2", "分块 overlap-add 的正确性条件", sec(
          ul(["每块长度 B，FFT 长度 N ≥ B + L − 1，否则循环卷积会绕回（时域混叠）。",
              "<code>H</code> 预先补零到 N 点并做一次 FFT，之后每块只做一次正/逆变换与逐点乘。",
              "相邻块的尾部重叠部分相加，不能覆盖。",
              "本书 <code>fft_convolve()</code> 就是这一算法的最小实现，"
              "与 <code>convolve()</code> 的差值应停在浮点误差量级。"]))),
  ],
  demos=[mk_demo(
      "code/04-convolution.py", "实验 4-1 · 朴素卷积 vs 分块频域卷积的数值与耗时",
      "在不同滤波器长度下比较两种实现的最大误差与耗时，并观察混响尾能量。",
      """N = 4000
LENS = (64, 128, 256, 512, 1024, 2048)   # 扫描到 2048，加速比才明显
DECAY = 0.006""",
      """rng = random.Random(7)
x = white_noise(rng, N, 0.4)
errors, t_naive, t_fft = [], [], []
for L in LENS:
    h = rir(rng, L, decay=DECAY, direct_delay=min(24, L // 4))
    t0 = time.perf_counter()
    a = convolve(x[:1200], h)
    t1 = time.perf_counter()
    b = fft_convolve(x[:1200], h)
    t2 = time.perf_counter()
    errors.append(max(abs(u - v) for u, v in zip(a, b)))
    t_naive.append(t1 - t0)
    t_fft.append(t2 - t1)

h = rir(rng, 256, decay=DECAY)
wet = fft_convolve(synthetic_speech(rng, N), h)[:N]
energy = [10 * math.log10(sum(v * v for v in h[i:i + 16]) / 16 + 1e-12)
          for i in range(0, len(h) - 16, 16)]
c = Chart(FIG / "04-complexity.svg", "两种卷积实现的耗时对比（毫秒）",
          xlabel="滤波器长度 L", ylabel="耗时 ms",
          xticks=[(i, "L=%d" % L) for i, L in enumerate(LENS)])
c.bars(range(len(LENS)), [1000 * t for t in t_naive], RED, label="朴素 O(L)")
c.bars(range(len(LENS)), [1000 * t for t in t_fft], GREEN, label="分块频域 OLA")
print("复杂度图:", c.save())
e = Chart(FIG / "04-rir-energy.svg", "RIR 分段能量衰减（dB）", xlabel="16 抽头块", ylabel="dB")
e.line(range(len(energy)), energy, BLUE, label="分段能量")
print("能量图:", e.save())
write_wav(AUDIO / "04-dry.wav", normalize_peak(x))
write_wav(AUDIO / "04-wet.wav", normalize_peak(wet))
print("最大数值误差: " + " ".join("L=%d→%.1e" % (L, e) for L, e in zip(LENS, errors)))
print("L=%d 时 朴素=%.1fms 频域=%.1fms 加速=%.1f× | RIR能量衰减 %.1f dB" %
      (LENS[-1], 1000 * t_naive[-1], 1000 * t_fft[-1], t_naive[-1] / max(t_fft[-1], 1e-9),
       energy[0] - energy[-1]))""",
      [("fig/04-complexity.svg", "朴素与频域卷积耗时对比"),
       ("fig/04-rir-energy.svg", "冲激响应分段能量衰减")],
      [("audio/04-dry.wav", "干信号（白噪声探测）"),
       ("audio/04-wet.wav", "经过 RIR 卷积后的湿信号")],
      "核对最大误差应停留在 1e-14 量级；观察 L 增大后两种实现的耗时差距拉开。",
      "两种实现数值一致（浮点误差量级）；朴素卷积耗时随 L 线性增长，"
      "但手写 FFT 的常数开销很大，即使扫到 L=2048，本例频域实现也未必更快。"
      "<strong>算法复杂度优势不等于实测更快：实时 AEC 必须换工业级 FFT 库（见附录 A.6）。</strong>",
      "把 <code>DECAY</code> 调到 0.02（长混响），湿信号尾音明显变长。")],
  highlights=[("dspguide", "卷积与 FFT 的直观讲解"),
              ("scipy-signal", "fftconvolve 的工业实现参照"),
              ("ccrma", "分块卷积与频域滤波的免费教材"),
              ("numpy", "向量化实现的迁移目标")],
  analogy="时域卷积是嵌套循环，频域卷积是「先变换到可逐点乘的域、再变换回来」——"
          "典型的<strong>换域加速</strong>。补零长度 N ≥ B+L−1 就是防止环形缓冲区回绕。",
  bridge="{{ch:03}} 约定指标，本章补上最基础的算子；"
         "{{ch:05}} 让这个滤波器的系数自己学出来，{{ch:06}} 再把它搬进频域。",
  pitfalls=["FFT 长度不足 B+L−1，循环卷积造成时域混叠。",
            "忘记把相邻块的重叠尾相加，直接在块边界拼接。",
            "用短滤波器覆盖长混响，还以为是自适应算法不收敛。",
            "忽略浮点误差量级，把 1e-12 当成实现错误。"],
  exercises=["推导 N ≥ B+L−1 的来源，并说明违反时会发生什么。",
             "估算 48 kHz、256 ms 混响需要的抽头数与每秒乘加量。",
             "把 fft_convolve 的块长 B 改成 64，观察耗时如何变化。"],
  further=["{{ch:06}} 频域自适应滤波 FDAF/MDF；{{ch:10}} NLMS 回声消除实现。"]),

# ==================================================================== 05
C("05", "p1", "part1/05-adaptive-filter", "自适应滤波：LMS、NLMS 与收敛",
  "把「求一组滤波系数」变成逐样本的梯度下降，这是整个上卷的心脏。",
  hours="3 学时",
  goals=["能推导 LMS 与 NLMS 的更新式并说明归一化项的作用。",
         "能实现 NLMS 辨识一段房间冲激响应并画出学习曲线。",
         "能量化步长、正则项与滤波器长度对收敛速度/稳态误差的影响。",
         "能解释双讲时为何必须冻结系数更新。"],
  points=["最速下降与梯度估计", "LMS 更新式", "NLMS 归一化", "步长与稳定性",
          "正则项 δ", "学习曲线与稳态误差", "权重误差范数", "双讲冻结"],
  sections=[
      ("5.1", "一条更新式，四个可调量", sec(
          eq("e[n] = d[n] − wᵀ[n]x[n]　|　LMS: w ← w + μ·e[n]·x[n]"),
          eq("NLMS: w ← w + (μ / (‖x[n]‖² + δ))·e[n]·x[n]　，0 < μ < 2"),
          table(["量", "作用", "调大的后果"], [
              ["μ 步长", "收敛速度", "收敛快但稳态误差大、双讲时更易发散"],
              ["δ 正则", "防止输入能量接近 0 时步长爆炸", "过大则收敛变慢，等效缩小 μ"],
              ["L 阶数", "能覆盖的回声尾长度", "算力线性增长、收敛变慢"],
              ["冻结条件", "双讲/近端语音期间停止更新", "太保守则路径变化后追不上"],
          ], ["18%", "42%", "40%"]),
          p("NLMS 的归一化本质上是<strong>把学习率按输入能量做自适应缩放</strong>："
            "语音电平忽大忽小时，LMS 的等效步长会剧烈波动，NLMS 则保持稳定。"
            "这就是它与 Adam/RMSProp 一类归一化优化器 homologous 的地方。"))),
      ("5.2", "收敛看两条曲线", sec(
          ul(["<strong>学习曲线</strong>：<code>10log₁₀(e²)</code> 随样本数下降，"
              "斜率反映收敛速度，地板高度反映稳态失调（misadjustment）。",
              "<strong>权重误差</strong>：<code>‖w − h‖²</code> 下降，说明辨识的是真实路径而非仅仅拟合当前样本。",
              "双讲时 <code>d[n]</code> 中的近端语音与 <code>x[n]</code> 不相关，"
              "梯度里混入大噪声，系数会被推离 h——工业实现必须做双讲检测（第 07、11 章）。"]))),
  ],
  demos=[mk_demo(
      "code/05-nlms.py", "实验 5-1 · NLMS 辨识房间冲激响应与步长扫描",
      "用 NLMS 在线估计 h，画学习曲线、比较三个步长，并输出消除后的可听残差。",
      """N, L = 6000, 96
MUS = (0.15, 0.50, 1.20)      # 三个步长对照
DELTA = 1e-3                   # 正则项
SMOOTH = 200                   # 学习曲线平滑窗""",
      """rng = random.Random(7)
far = white_noise(rng, N, 0.35)      # 白噪声激励充分，收敛最快
true_h = rir(rng, L, decay=0.004, direct_delay=12)
echo = fft_convolve(far, true_h)[:N]
target = [echo[i] + rng.gauss(0, 0.002) for i in range(N)]

def nlms(mu):
    w, errs, out = [0.0] * L, [], []
    for n in range(L, N):
        xv = [far[n - i] for i in range(L)]
        y = sum(w[i] * xv[i] for i in range(L))
        e = target[n] - y
        power = sum(v * v for v in xv) + DELTA
        for i in range(L):
            w[i] += mu * e * xv[i] / power
        errs.append(e * e)
        out.append(e)
    return w, errs, out

results = {mu: nlms(mu) for mu in MUS}

def smooth_curve(vals, win):
    out, v = [], 0.0
    for i, x in enumerate(vals):
        v = v + (x - v) / min(i + 1, win)
        out.append(10 * math.log10(v + 1e-12))
    return out

c = Chart(FIG / "05-learning.svg", "NLMS 学习曲线：不同步长的残差能量 (dB)",
          xlabel="迭代样本", ylabel="dB")
for mu, color in zip(MUS, (BLUE, GREEN, RED)):
    c.line(range(len(results[mu][1])), smooth_curve(results[mu][1], SMOOTH),
           color, label="μ=%.2f" % mu)
print("学习图:", c.save())
w = Chart(FIG / "05-weights.svg", "μ=0.50 时估计的滤波器系数 vs 真实 RIR",
          xlabel="抽头 k", ylabel="幅度")
w.line(range(L), true_h, "#9aa6b2", label="真实 h[k]")
w.line(range(L), results[0.50][0], RED, label="估计 w[k]")
print("权重图:", w.save())
write_wav(AUDIO / "05-before.wav", normalize_peak(target))
write_wav(AUDIO / "05-error.wav", normalize_peak(results[0.50][2]))
for mu in MUS:
    wt, errs, out = results[mu]
    mse = statistics.fmean(errs[len(errs) // 2:])
    werr = math.sqrt(sum((a - b) ** 2 for a, b in zip(wt, true_h)))
    print("μ=%.2f 稳态MSE=%.6f 权重误差=%.4f 输出/输入能量比=%.4f" %
          (mu, mse, werr, sum(v * v for v in out) / sum(v * v for v in target)))
print("前半段均方误差=%.6f 后半段=%.6f（下降说明收敛）" %
      (statistics.fmean(results[0.50][1][:1000]),
       statistics.fmean(results[0.50][1][-1000:])))""",
      [("fig/05-learning.svg", "三个步长的学习曲线"),
       ("fig/05-weights.svg", "估计系数与真实冲激响应")],
      [("audio/05-before.wav", "含回声的目标信号"),
       ("audio/05-error.wav", "NLMS 输出的残差（回声已被消除）")],
      "对照三个步长的稳态 MSE、权重误差与学习曲线；试听 <code>05-error.wav</code>。",
      "学习曲线先快速下降再进入稳态；权重误差随 μ 单调变大（0.0018→0.0036→0.0078），"
      "而稳态 MSE 都在 1e-5 量级且非单调（受观测噪声地板影响）。"
      "<strong>大步长收敛快、失调大，但稳态误差还叠加了噪声地板，不能只看一个数。</strong>",
      "把 <code>far</code> 换成 <code>synthetic_speech</code>（有色激励），观察收敛明显变慢。")],
  highlights=[("wiki-lms", "LMS/NLMS 更新式与收敛条件"),
              ("ccrma", "自适应滤波的免费在线讲义"),
              ("speexdsp", "经典 AEC 里 NLMS 的工业实现"),
              ("numpy", "把权重更新向量化后的对照")],
  analogy="NLMS 就是<strong>在线随机梯度下降</strong>：<code>x</code> 是特征、"
          "<code>d</code> 是标签、<code>e</code> 是损失梯度、<code>μ/‖x‖²</code> 是自适应学习率。"
          "双讲相当于标签里混入了大量噪声样本，必须暂停训练。",
  bridge="{{ch:04}} 给出固定系数的卷积，本章让系数在线学习；"
         "{{ch:06}} 把同一更新式搬进频域，{{ch:10}} 用它实现完整 AEC。",
  pitfalls=["δ 设为 0，静音段输入能量趋零导致系数爆炸。",
            "μ 取到 2 以上，更新发散。",
            "用语音而非白噪声做激励，误判为算法不收敛。",
            "双讲时继续更新，滤波器被近端语音带跑。"],
  exercises=["推导 LMS 的均方收敛条件 0 < μ < 2/λ_max。",
             "解释为什么 δ 必须与输入功率同量级。",
             "在实验里加入双讲段并观察权重误差如何跳变。"],
  further=["{{ch:06}} 频域自适应；{{ch:07}} 双讲检测；{{ch:10}} AEC 实现。"]),


]
