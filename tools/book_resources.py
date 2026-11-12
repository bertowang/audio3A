#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外部参考资料唯一数据源：标准 / ffmpeg 滤镜 / 开源工程 / 数据集 / 教材 / 百科。

条目格式: key -> (名称, URL, 说明, 分类)
版本相关说明：ffmpeg 各音频滤镜的引入版本请以官方文档与本机
`ffmpeg -filters` / `ffmpeg -version` 为准；本书只给可自查的入口与命令。
"""
from __future__ import annotations

import html as html_mod
import urllib.parse

R = {
    # ---- 标准与规范 ----
    "itu-p862": ("ITU-T P.862 PESQ", "https://www.itu.int/rec/T-REC-P.862/en",
                 "感知语音质量评估，传统 3A 最常用的客观分（窄带/宽带）", "标准"),
    "itu-p863": ("ITU-T P.863 POLQA", "https://www.itu.int/rec/T-REC-P.863/en",
                 "PESQ 后继标准，支持超宽带与更多失真类型", "标准"),
    "itu-bs1770": ("ITU-R BS.1770", "https://www.itu.int/rec/R-REC-BS.1770/en",
                   "响度与真峰值测量算法，LUFS/LKFS 的规范来源", "标准"),
    "ebu-r128": ("EBU R128", "https://tech.ebu.org/docs/r/r128",
                 "广播响度归一化规范，-23 LUFS 目标与 True Peak 上限", "标准"),
    "itu-g168": ("ITU-T G.168", "https://www.itu.int/rec/T-REC-G.168/en",
                 "网络回声消除器的测试标准，规定 ERLE 与双讲测试信号", "标准"),
    "itu-p56": ("ITU-T P.56", "https://www.itu.int/rec/T-REC-P.56/en",
                "语音电平测量方法，主动语音电平与 AGC 标定相关", "标准"),
    "itu-p835": ("ITU-T P.835", "https://www.itu.int/rec/T-REC-P.835/en",
                 "带噪声语音的主观评分方法（语音/噪声/总体三维）", "标准"),
    "rfc3550": ("RFC 3550 RTP", "https://www.rfc-editor.org/rfc/rfc3550",
                "实时音视频传输的时间戳、抖动与序列号基础", "标准"),

    # ---- ffmpeg 文档与滤镜 ----
    "ffmpeg": ("FFmpeg 官方文档", "https://ffmpeg.org/documentation.html",
               "文档总入口；用 `ffmpeg -filters` 查本机实际支持的滤镜", "工具"),
    "ffmpeg-filters": ("FFmpeg Filters 文档", "https://ffmpeg.org/ffmpeg-filters.html",
                       "全部音频滤镜的权威说明页，每个滤镜有独立锚点", "工具"),
    "ffmpeg-arnndn": ("ffmpeg arnndn", "https://ffmpeg.org/ffmpeg-filters.html#arnndn",
                      "RNN 降噪滤镜，加载 RNNoise 训练出的模型文件（需自备 .rnnn）", "工具"),
    "ffmpeg-afftdn": ("ffmpeg afftdn", "https://ffmpeg.org/ffmpeg-filters.html#afftdn",
                      "基于 FFT 的自适应降噪，含噪声指纹与自适应白噪声参数", "工具"),
    "ffmpeg-anlmdn": ("ffmpeg anlmdn", "https://ffmpeg.org/ffmpeg-filters.html#anlmdn",
                      "非局部均值降噪滤镜，适合平稳噪声", "工具"),
    "ffmpeg-loudnorm": ("ffmpeg loudnorm", "https://ffmpeg.org/ffmpeg-filters.html#loudnorm",
                        "EBU R128 响度归一化，支持单/双 pass 与 True Peak 限制", "工具"),
    "ffmpeg-dynaudnorm": ("ffmpeg dynaudnorm", "https://ffmpeg.org/ffmpeg-filters.html#dynaudnorm",
                          "动态音频归一化，按局部窗口调整增益，类似软件 AGC", "工具"),
    "ffmpeg-speechnorm": ("ffmpeg speechnorm", "https://ffmpeg.org/ffmpeg-filters.html#speechnorm",
                          "面向语音的归一化滤镜，含高通与压缩", "工具"),
    "ffmpeg-ebur128": ("ffmpeg ebur128", "https://ffmpeg.org/ffmpeg-filters.html#ebur128",
                       "EBU R128 响度测量滤镜，输出短期/积分/真峰值", "工具"),
    "ffmpeg-volumedetect": ("ffmpeg volumedetect", "https://ffmpeg.org/ffmpeg-filters.html#volumedetect",
                            "测量 mean_volume / max_volume，用于 AGC 前后的电平核对", "工具"),
    "ffmpeg-astats": ("ffmpeg astats", "https://ffmpeg.org/ffmpeg-filters.html#astats",
                      "逐通道统计 RMS、峰值、动态范围、削波计数", "工具"),
    "ffmpeg-silencedetect": ("ffmpeg silencedetect", "https://ffmpeg.org/ffmpeg-filters.html#silencedetect",
                             "静音段检测，可用于粗粒度 VAD 与数据集切分", "工具"),
    "ffmpeg-acompressor": ("ffmpeg acompressor", "https://ffmpeg.org/ffmpeg-filters.html#acompressor",
                           "动态范围压缩器，AGC 的阈值/比率/启动释放实现参照", "工具"),
    "ffmpeg-alimiter": ("ffmpeg alimiter", "https://ffmpeg.org/ffmpeg-filters.html#alimiter",
                        "前瞻限幅器，防止 AGC 之后削波", "工具"),
    "ffmpeg-aecho": ("ffmpeg aecho", "https://ffmpeg.org/ffmpeg-filters.html#aecho",
                     "给音频叠加延时衰减副本，可用来合成回声测试样本", "工具"),
    "ffmpeg-aresample": ("ffmpeg aresample", "https://ffmpeg.org/ffmpeg-filters.html#aresample",
                         "重采样与抖动补偿，AEC 参考/采集时钟不一致时的预处理", "工具"),
    "ffmpeg-afreqshift": ("FFmpeg 滤波命令示例", "https://ffmpeg.org/ffmpeg.html",
                          "命令行总文档，包含 -af 滤镜链、滤镜图与参数写法", "工具"),

    # ---- 工业实现与开源库 ----
    "webrtc": ("WebRTC 官网", "https://webrtc.org/",
               "实时通信标准与参考实现，3A 是浏览器通话的默认链路", "工程"),
    "webrtc-src": ("WebRTC 源码（audio_processing）",
                   "https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/",
                   "AEC3 / NS / AGC2 的工业级参考实现目录", "工程"),
    "webrtc-aec3": ("WebRTC AEC3 模块",
                    "https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/aec3/",
                    "分块频域自适应滤波 + 残余回声估计的现代 AEC 结构", "工程"),
    "speex": ("Speex / SpeexDSP", "https://www.speex.org/",
              "经典开源语音编解码与预处理库，含 AEC 与降噪", "工程"),
    "speexdsp": ("speexdsp 源码", "https://gitlab.xiph.org/xiph/speexdsp",
                 "speex_echo_cancellation / speex_preprocess_ctl 的参考实现", "工程"),
    "rnnoise": ("RNNoise", "https://github.com/xiph/rnnoise",
                "Valin 的混合 DSP/深度学习实时降噪，ffmpeg arnndn 的模型来源", "工程"),
    "rnnoise-paper": ("RNNoise 论文（arXiv 1709.08243）", "https://arxiv.org/abs/1709.08243",
                      "A Hybrid DSP/Deep Learning Approach to Real-Time Full-Band Speech Enhancement", "论文"),
    "deepfilternet": ("DeepFilterNet", "https://github.com/Rikorose/DeepFilterNet",
                      "低算力实时语音增强，复数滤波 + 深度掩码", "工程"),
    "clearervoice": ("ClearerVoice-Studio", "https://github.com/modelscope/ClearerVoice-Studio",
                     "语音增强/分离/超分的开源训练与推理框架", "工程"),
    "speechbrain": ("SpeechBrain", "https://github.com/speechbrain/speechbrain",
                    "基于 PyTorch 的语音工具箱，含 SE / 分离 / 识别配方", "工程"),
    "asteroid": ("Asteroid", "https://github.com/asteroid-team/asteroid",
                 "语音分离与增强的研究框架，含 SI-SNR 等损失实现", "工程"),
    "torchaudio": ("torchaudio", "https://docs.pytorch.org/audio/stable/index.html",
                   "音频 I/O、STFT/ISTFT、波形与谱特征的标准实现", "工程"),
    "librosa": ("librosa", "https://librosa.org/",
                "音频特征提取与 STFT/ISTFT 的 Python 工业实现", "工程"),
    "pyroomacoustics": ("pyroomacoustics", "https://github.com/LCAV/pyroomacoustics",
                        "房间声学模拟、RIR 生成与波束形成实验工具", "工程"),
    "numpy": ("NumPy 文档", "https://numpy.org/doc/stable/",
              "向量化 DSP 的事实标准；本书手写实现可逐步替换为 ndarray", "工程"),
    "scipy-signal": ("SciPy signal", "https://docs.scipy.org/doc/scipy/reference/signal.html",
                     "lfilter / fftconvolve / stft / firwin 等工业级 DSP 原语", "工程"),
    "onnxruntime": ("ONNX Runtime", "https://onnxruntime.ai/",
                    "端侧推理运行时，神经 3A 部署常用目标", "工程"),

    # ---- 数据集与挑战赛 ----
    "dns-challenge": ("Microsoft DNS Challenge", "https://github.com/microsoft/DNS-Challenge",
                      "深度噪声抑制挑战赛，含大规模合成数据脚本与基线", "数据集"),
    "aec-challenge": ("Microsoft AEC Challenge", "https://github.com/microsoft/AEC-Challenge",
                      "声学回声消除挑战赛，含真实双讲与非线性失真录音", "数据集"),
    "dnsmos": ("DNSMOS", "https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS",
               "无需参考信号的神经语音质量评分模型（P.835 三维）", "数据集"),
    "librispeech": ("LibriSpeech", "https://www.openslr.org/12",
                    "常用的干净语音语料，用于合成带噪/带回声训练对", "数据集"),
    "musan": ("MUSAN", "https://www.openslr.org/17",
              "音乐/语音/噪声语料，常作为 3A 数据增强的噪声源", "数据集"),
    "demand": ("DEMAND 噪声库", "https://zenodo.org/records/1227121",
               "多环境真实噪声录音，用于噪声泛化测试", "数据集"),
    "pesq-python": ("PESQ 开源实现检索", "https://github.com/ludlows/PESQ",
                    "社区 PESQ 实现之一；商业使用请确认 ITU 授权", "数据集"),
    "stoi": ("STOI / ESTOI", "https://github.com/mpariente/pystoi",
             "语音可懂度客观指标，与增强模型的相关性常优于 SNR", "数据集"),

    # ---- 教材与课程 ----
    "dspguide": ("The Scientist and Engineer's Guide to DSP",
                 "https://www.dspguide.com/",
                 "免费在线 DSP 教材，卷积/FFT/滤波器章节讲解直观", "教材"),
    "ccrma": ("Stanford CCRMA · Julius O. Smith", "https://ccrma.stanford.edu/~jos/",
              "数字信号处理与音频 DSP 的免费在线书系", "教材"),
    "mit-ocw": ("MIT OpenCourseWare · Signals and Systems",
                "https://ocw.mit.edu/search/?q=signals%20and%20systems",
                "信号与系统、离散时间处理的公开课检索入口", "教材"),
    "dsprelated": ("DSPRelated", "https://www.dsprelated.com/",
                   "自适应滤波、AGC 与实时实现的工程文章与博客", "教材"),
    "mdn-webaudio": ("MDN Web Audio API", "https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API",
                     "浏览器里观察 AudioWorklet / 延迟 / 采样率的权威文档", "教材"),
    "mdn-svg": ("MDN SVG 文档", "https://developer.mozilla.org/en-US/docs/Web/SVG",
                "本书自绘波形与频谱图的矢量格式参考", "教材"),
    "python-docs": ("Python 标准库文档", "https://docs.python.org/3/library/index.html",
                    "wave / array / struct / math / random 等标准模块说明", "教材"),

    # ---- 百科与检索入口 ----
    "wiki-aec": ("Echo cancellation", "https://en.wikipedia.org/wiki/Echo_cancellation",
                 "回声消除的问题定义、自适应滤波与双讲概述", "百科"),
    "wiki-lms": ("Least mean squares filter", "https://en.wikipedia.org/wiki/Least_mean_squares_filter",
                 "LMS / NLMS 的更新式与收敛条件", "百科"),
    "wiki-wiener": ("Wiener filter", "https://en.wikipedia.org/wiki/Wiener_filter",
                    "最小均方误差意义下的最优线性滤波", "百科"),
    "wiki-stft": ("Short-time Fourier transform", "https://en.wikipedia.org/wiki/Short-time_Fourier_transform",
                  "STFT、窗函数、重叠相加与谱图", "百科"),
    "wiki-agc": ("Automatic gain control", "https://en.wikipedia.org/wiki/Automatic_gain_control",
                 "AGC 的环路结构与时间常数", "百科"),
    "wiki-vad": ("Voice activity detection", "https://en.wikipedia.org/wiki/Voice_activity_detection",
                 "VAD 的能量/统计/学习方法概览", "百科"),
    "wiki-spectral-sub": ("Spectral subtraction", "https://en.wikipedia.org/wiki/Spectral_subtraction",
                          "谱减法与音乐噪声的成因", "百科"),
    "wiki-beamforming": ("Beamforming", "https://en.wikipedia.org/wiki/Beamforming",
                         "阵列信号处理与 delay-and-sum / MVDR", "百科"),
    "wiki-loudness": ("LUFS / Loudness", "https://en.wikipedia.org/wiki/LUFS",
                      "响度单位与 K 加权、真峰值", "百科"),
    "wiki-fft": ("Cooley–Tukey FFT", "https://en.wikipedia.org/wiki/Cooley%E2%80%93Tukey_FFT_algorithm",
                 "本书手写 radix-2 FFT 的算法依据", "百科"),
    "wiki-mask": ("Ideal ratio mask / T-F masking", "https://en.wikipedia.org/wiki/Time%E2%80%93frequency_analysis",
                  "时频掩码学习范式的背景", "百科"),
    "wiki-quantization": ("Quantization (signal processing)", "https://en.wikipedia.org/wiki/Quantization_(signal_processing)",
                          "模型 int8 量化与定点 DSP 的共同基础", "百科"),
}

TOPIC_RULES = [
    ("回声", ["wiki-aec", "webrtc-aec3"]), ("AEC", ["wiki-aec", "itu-g168"]),
    ("双讲", ["itu-g168", "aec-challenge"]), ("自适应", ["wiki-lms", "dsprelated"]),
    ("NLMS", ["wiki-lms", "speexdsp"]), ("LMS", ["wiki-lms", "ccrma"]),
    ("收敛", ["wiki-lms", "numpy"]), ("频域", ["wiki-fft", "scipy-signal"]),
    ("FFT", ["wiki-fft", "python-docs"]), ("STFT", ["wiki-stft", "librosa"]),
    ("时频", ["wiki-stft", "torchaudio"]), ("窗", ["wiki-stft", "dspguide"]),
    ("谱减", ["wiki-spectral-sub", "ffmpeg-afftdn"]),
    ("维纳", ["wiki-wiener", "rnnoise-paper"]),
    ("MMSE", ["wiki-wiener", "rnnoise-paper"]),
    ("噪声", ["ffmpeg-afftdn", "dns-challenge"]),
    ("降噪", ["ffmpeg-arnndn", "rnnoise"]),
    ("增益", ["wiki-agc", "ffmpeg-dynaudnorm"]),
    ("AGC", ["wiki-agc", "ffmpeg-speechnorm"]),
    ("响度", ["ebu-r128", "ffmpeg-loudnorm"]),
    ("限幅", ["ffmpeg-alimiter", "ffmpeg-acompressor"]),
    ("VAD", ["wiki-vad", "ffmpeg-silencedetect"]),
    ("波束", ["wiki-beamforming", "pyroomacoustics"]),
    ("阵列", ["wiki-beamforming", "pyroomacoustics"]),
    ("房间", ["pyroomacoustics", "dspguide"]),
    ("冲激响应", ["pyroomacoustics", "scipy-signal"]),
    ("卷积", ["dspguide", "scipy-signal"]),
    ("采样", ["python-docs", "wiki-stft"]),
    ("指标", ["itu-p862", "stoi"]), ("评价", ["itu-p862", "dnsmos"]),
    ("PESQ", ["itu-p862", "itu-p863"]), ("主观", ["itu-p835", "dnsmos"]),
    ("ffmpeg", ["ffmpeg-filters", "ffmpeg"]),
    ("命令", ["ffmpeg", "ffmpeg-filters"]),
    ("WebRTC", ["webrtc-src", "webrtc-aec3"]),
    ("工具", ["ffmpeg-filters", "webrtc"]),
    ("掩码", ["wiki-mask", "dns-challenge"]),
    ("数据", ["dns-challenge", "librispeech"]),
    ("数据增强", ["musan", "demand"]),
    ("网络", ["speechbrain", "torchaudio"]),
    ("骨架", ["speechbrain", "asteroid"]),
    ("损失", ["asteroid", "speechbrain"]),
    ("训练", ["dns-challenge", "speechbrain"]),
    ("复数", ["deepfilternet", "torchaudio"]),
    ("相位", ["deepfilternet", "wiki-mask"]),
    ("时域", ["asteroid", "torchaudio"]),
    ("序列", ["torchaudio", "onnxruntime"]),
    ("延迟", ["rfc3550", "mdn-webaudio"]),
    ("实时", ["rfc3550", "webrtc"]),
    ("因果", ["rfc3550", "onnxruntime"]),
    ("量化", ["onnxruntime", "wiki-quantization"]),
    ("部署", ["onnxruntime", "rnnoise"]),
    ("泛化", ["dnsmos", "demand"]),
    ("鲁棒", ["aec-challenge", "demand"]),
    ("过拟合", ["dnsmos", "aec-challenge"]),
]

DEFAULT_KEYS = ["ffmpeg-filters", "webrtc-src", "dspguide"]

CHAPTER_RESOURCES = {
    "00": (["wiki-aec", "webrtc", "rfc3550", "wiki-agc", "ffmpeg"], "audio 3A pipeline AEC ANS AGC overview"),
    "01": (["pyroomacoustics", "wiki-aec", "itu-g168", "wiki-lms"], "room impulse response acoustic echo path model"),
    "02": (["wiki-stft", "wiki-fft", "dspguide", "python-docs", "librosa"], "sampling quantization STFT overlap-add"),
    "03": (["itu-p862", "itu-p863", "stoi", "dnsmos", "itu-p835", "itu-g168"], "ERLE PESQ STOI DNSMOS speech quality metrics"),
    "04": (["dspguide", "pyroomacoustics", "scipy-signal", "wiki-fft"], "linear time invariant system convolution RIR"),
    "05": (["wiki-lms", "dsprelated", "ccrma", "numpy"], "LMS NLMS adaptive filter convergence step size"),
    "06": (["ccrma", "scipy-signal", "webrtc-aec3", "numpy"], "frequency domain adaptive filter FDAF partitioned block"),
    "07": (["itu-g168", "aec-challenge", "webrtc-aec3", "wiki-aec"], "double talk detection nonlinear echo delay drift"),
    "08": (["wiki-vad", "wiki-wiener", "ffmpeg-silencedetect", "dsprelated"], "voice activity detection noise power estimation MCRA"),
    "09": (["wiki-aec", "webrtc-aec3", "speex", "itu-g168"], "acoustic echo canceller reference signal residual echo suppressor"),
    "10": (["wiki-lms", "speexdsp", "webrtc-aec3", "numpy"], "NLMS echo cancellation ERLE implementation"),
    "11": (["webrtc-aec3", "aec-challenge", "itu-g168", "rnnoise-paper"], "AEC3 double talk nonlinear post filter"),
    "12": (["wiki-spectral-sub", "ffmpeg-afftdn", "wiki-wiener", "rnnoise-paper"], "spectral subtraction musical noise denoising"),
    "13": (["wiki-wiener", "rnnoise-paper", "ffmpeg-anlmdn", "dsprelated"], "MMSE STSA OM-LSA a priori SNR MCRA"),
    "14": (["wiki-agc", "ffmpeg-loudnorm", "ebu-r128", "ffmpeg-alimiter", "itu-bs1770"], "automatic gain control EBU R128 limiter"),
    "15": (["wiki-beamforming", "pyroomacoustics", "ccrma", "speechbrain"], "microphone array delay and sum MVDR beamformer"),
    "16": (["webrtc-src", "ffmpeg-afreqshift", "wiki-aec", "rfc3550"], "3A cascade order AEC before AGC artifacts"),
    "17": (["ffmpeg-filters", "ffmpeg-arnndn", "webrtc-src", "speexdsp"], "ffmpeg audio filters WebRTC audio processing CLI"),
    "18": (["itu-p862", "ffmpeg-ebur128", "webrtc", "dns-challenge"], "build classic 3A chain evaluation ERLE PESQ"),
    "19": (["wiki-mask", "dns-challenge", "rnnoise-paper", "speechbrain"], "supervised speech enhancement T-F mask IRM CRM"),
    "20": (["dns-challenge", "librispeech", "musan", "librosa", "asteroid"], "training data synthesis RIR noise augmentation SI-SNR loss"),
    "21": (["speechbrain", "asteroid", "torchaudio", "clearervoice"], "DNN CRN U-Net TCN speech enhancement architecture"),
    "22": (["deepfilternet", "torchaudio", "wiki-mask", "asteroid"], "complex spectral mapping DCCRN Conv-TasNet phase"),
    "23": (["dns-challenge", "dnsmos", "rnnoise", "wiki-spectral-sub"], "neural noise suppression DNS Challenge DNSMOS"),
    "24": (["aec-challenge", "clearervoice", "webrtc-aec3", "speechbrain"], "deep acoustic echo cancellation joint AEC NS"),
    "25": (["ffmpeg-loudnorm", "ebu-r128", "itu-bs1770", "dnsmos"], "neural gain control loudness normalization learned"),
    "26": (["speechbrain", "clearervoice", "asteroid", "dns-challenge"], "joint 3A multi task speech enhancement"),
    "27": (["torchaudio", "onnxruntime", "rnnoise", "rfc3550"], "causal TCN Conformer low latency streaming state cache"),
    "28": (["rfc3550", "mdn-webaudio", "onnxruntime", "webrtc"], "algorithmic latency budget real time factor jitter buffer"),
    "29": (["wiki-quantization", "onnxruntime", "rnnoise", "deepfilternet"], "model quantization int8 inference edge DSP"),
    "30": (["dnsmos", "aec-challenge", "demand", "dns-challenge"], "generalization robustness data leakage DNSMOS evaluation"),
    "31": (["speechbrain", "dns-challenge", "ffmpeg-filters", "python-docs"], "train small mask estimator end to end 3A project"),
    "A": (["dspguide", "ffmpeg-filters", "webrtc-src", "python-docs"], "audio DSP formula cheat sheet commands glossary"),
}

REPOS = [
    ("WebRTC audio_processing", "https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/",
     "工业级 3A 参考实现：AEC3 / NS / AGC2，读源码理解分块频域与双讲逻辑", "传统 · C++"),
    ("speexdsp", "https://gitlab.xiph.org/xiph/speexdsp",
     "最易读的经典 AEC / 预处理实现，适合对照本书 NLMS 代码", "传统 · C"),
    ("RNNoise", "https://github.com/xiph/rnnoise",
     "混合 DSP + GRU 的实时降噪，ffmpeg arnndn 的模型来源", "AI · C"),
    ("Microsoft DNS-Challenge", "https://github.com/microsoft/DNS-Challenge",
     "大规模语音/噪声合成脚本、基线模型与评测协议", "数据集 · 基线"),
    ("Microsoft AEC-Challenge", "https://github.com/microsoft/AEC-Challenge",
     "真实双讲、非线性失真与远端单讲录音，AEC 必测", "数据集 · 基线"),
    ("DeepFilterNet", "https://github.com/Rikorose/DeepFilterNet",
     "低算力实时增强，复数域深度滤波思路", "AI · 实时"),
    ("ClearerVoice-Studio", "https://github.com/modelscope/ClearerVoice-Studio",
     "增强/分离/超分一体化训练与推理框架，含 FRCRN、MossFormer", "AI · 框架"),
    ("SpeechBrain", "https://github.com/speechbrain/speechbrain",
     "语音任务配方齐全，适合复现 SE / 掩码 / 损失函数", "AI · 框架"),
    ("Asteroid", "https://github.com/asteroid-team/asteroid",
     "语音分离与 SI-SNR 损失的研究型框架", "AI · 框架"),
    ("pyroomacoustics", "https://github.com/LCAV/pyroomacoustics",
     "房间声学模拟、RIR 生成与波束形成，构造可复现训练集", "仿真 · Python"),
    ("torchaudio", "https://docs.pytorch.org/audio/stable/index.html",
     "STFT/ISTFT、波形 I/O 与流式推理的工业实现", "AI · Python"),
    ("ONNX Runtime", "https://onnxruntime.ai/",
     "端侧推理目标，配合量化把神经 3A 放进 RTC 预算", "部署"),
    ("FFmpeg", "https://ffmpeg.org/ffmpeg-filters.html",
     "afftdn / arnndn / loudnorm / dynaudnorm 等滤镜的离线验证工具", "工具"),
    ("DNSMOS", "https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS",
     "无参考神经 MOS，用于没有干净参考时的快速评估", "评测"),
    ("pystoi", "https://github.com/mpariente/pystoi",
     "STOI / ESTOI 可懂度指标实现", "评测"),
    ("pyroomacoustics RIR 教程", "https://pyroomacoustics.readthedocs.io/",
     "镜像源模型与波束形成的完整文档", "仿真 · 文档"),
]

def anchor(key, label=None):
    item = R.get(key)
    if not item:
        return ""
    name, url, _desc, _cat = item
    return ('<a href="' + url + '" target="_blank" rel="noopener noreferrer">' +
            html_mod.escape(label or name) + " ↗</a>")


def links_for_point(chapter_id, point, max_links=2):
    """按知识点关键词匹配参考链接；不足时用本章默认资源补齐。"""
    keys = []
    for word, refs in TOPIC_RULES:
        if word.lower() in point.lower():
            for k in refs:
                if k not in keys:
                    keys.append(k)
    chapter_keys = CHAPTER_RESOURCES.get(chapter_id, (DEFAULT_KEYS, ""))[0]
    for k in chapter_keys:
        if k not in keys:
            keys.append(k)
        if len(keys) >= max_links:
            break
    return " · ".join(anchor(k) for k in keys[:max_links] if k in R)


def resource_card(key, why=""):
    item = R.get(key)
    if not item:
        return ""
    name, url, desc, cat = item
    return ('<div class="repo-card"><h3>' + anchor(key, name) + "</h3>"
            '<span class="tag">' + html_mod.escape(cat) + "</span><p>" +
            html_mod.escape(desc) + "</p>" +
            (('<p style="margin:0;color:var(--ink-faint)">推荐理由：' + html_mod.escape(why) + "</p>")
             if why else "") + "</div>")


def repo_card(name, url, desc, tag):
    return ('<div class="repo-card"><h3><a href="' + url +
            '" target="_blank" rel="noopener noreferrer">' +
            html_mod.escape(name) + " ↗</a></h3>"
            '<span class="tag">' + html_mod.escape(tag) + "</span><p>" +
            html_mod.escape(desc) + "</p></div>")


def search_url(query, site="scholar"):
    q = urllib.parse.quote(query)
    if site == "arxiv":
        return "https://arxiv.org/search/?query=" + q + "&searchtype=all"
    if site == "github":
        return "https://github.com/search?q=" + q + "&type=repositories"
    if site == "ffmpeg":
        return "https://ffmpeg.org/ffmpeg-filters.html#" + urllib.parse.quote(query)
    return "https://scholar.google.com/scholar?q=" + q


def chapter_links_html(chapter_id, root="../../"):
    keys, query = CHAPTER_RESOURCES.get(chapter_id, (DEFAULT_KEYS, "audio 3A"))
    out = ['<div class="repo-grid">']
    for k in keys:
        if k in R:
            out.append(resource_card(k))
    out.append("</div>")
    out.append('<h3>继续检索</h3><ul>')
    for label, site in (("Google Scholar", "scholar"), ("arXiv", "arxiv"), ("GitHub", "github")):
        out.append("<li>" + label + "：<a href='" + search_url(query, site) +
                   "' target='_blank' rel='noopener noreferrer'>" +
                   html_mod.escape(query) + " ↗</a></li>")
    out.append("</ul>")
    out.append('<p class="code-hint">全书链接总表见 ' +
               anchor("ffmpeg-filters", "FFmpeg Filters 文档") +
               ' 与 <a href="' + root + 'appendix/index.html#sA-7">附录 A.7</a>；'
               '滤镜是否可用请以本机 <code>ffmpeg -filters</code> 为准。</p>')
    return "\n".join(out)


def all_resources_html():
    """附录 A.7：按分类列出全部外部资源。"""
    groups = {}
    for key, (name, url, desc, cat) in R.items():
        groups.setdefault(cat, []).append((key, name, url, desc))
    out = ['<p>下表为全书引用的全部外部资源（共 ' + str(len(R)) +
           ' 条），按类型分组。所有链接指向官方文档、标准、源码仓库或免费教材；'
           '书中提及的滤镜能力请以本机 <code>ffmpeg -filters</code> 与官方 Filters 文档为准。</p>']
    for cat in ("标准", "工具", "工程", "数据集", "教材", "百科", "论文"):
        if cat not in groups:
            continue
        out.append("<h3>" + cat + "（" + str(len(groups[cat])) + "）</h3>")
        out.append('<table><thead><tr><th style="width:26%">名称</th>'
                   '<th style="width:38%">链接 / 命令入口</th><th>说明</th></tr></thead><tbody>')
        for key, name, url, desc in groups[cat]:
            out.append("<tr><td>" + anchor(key, name) + "</td><td><code>" +
                       html_mod.escape(url) + "</code></td><td>" +
                       html_mod.escape(desc) + "</td></tr>")
        out.append("</tbody></table>")
    out.append("<h3>开源工程速查</h3><div class=\"repo-grid\">")
    out.extend(repo_card(*r) for r in REPOS)
    out.append("</div>")
    return "\n".join(out)
