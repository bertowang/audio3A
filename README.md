# 音频 3A 处理：从自适应滤波到神经增强

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](#快速开始)
[![Pages](https://img.shields.io/badge/pages-34-blue)](#内容结构)
[![License](https://img.shields.io/badge/license-not%20specified-lightgrey)](#许可证)

面向**爱好音频处理的计算机专业学生**的一本「音频 3A 处理」教材，覆盖本科到研究生层次。
全书把 AEC（声学回声消除）、ANS/NS（噪声抑制）、AGC（自动增益控制）还原成可推导、
可运行、可测量的估计问题，并严格按**上卷传统算法 / 下卷 AI 算法**两条路线组织。

> 打开 `index.html` 即可阅读，无需构建、无需联网、无需安装任何第三方包；
> `file://` 双击可用。每章都配可运行的 Python 实验、自绘 SVG 图与可试听的合成 WAV。

## 一眼看懂

- **统一信号模型**：`y[n] = d[n] + h * x[n] + v[n]`。AEC 有远端参考 `x`，做在线系统辨识；
  ANS 没有参考，做统计估计；AGC 不区分内容，只改整体尺度。
- **一条链路贯穿两卷**：`时延对齐 → 线性 AEC → 残余抑制 → ANS → AGC → 限幅`。
  上卷用物理假设手工推导每个增益，下卷把同一批增益换成可学习函数；
  **接口、因果约束与评价指标完全不变**。
- **上下卷分工**：上卷 04～18（LTI、FFT/STFT、LMS/NLMS、FDAF、谱减、Wiener、AGC、
  波束形成、级联与评测）；下卷 19～31（时频掩码、数据合成、网络骨架、复数域、
  神经 3A、因果流式、延迟预算、量化、泛化与结课项目）。
- **零依赖可复现**：32 个实验脚本只用 Python 3 标准库 + 仓库内 `tools/dsp.py` /
  `tools/chart.py`；所有语音、噪声与房间冲激响应均由代码合成，`random.seed(7)`，
  统一 16 kHz；运行后写出 65 张 SVG 图与 78 段 WAV。
- **不写死软件版本**：ffmpeg / WebRTC 命令一律作为「可选真机实验」，
  要求先用本机 `ffmpeg -filters` / `ffmpeg -version` 自查，并以官方文档为准。

## 快速开始

```bash
# 1. 直接读
open index.html                        # macOS；其它系统用浏览器打开即可

# 2. 跑某一个实验（无需 pip install）
python3 part0/00-three-a/code/00-three-a.py

# 3. 批量跑完全书实验，重新生成所有 SVG 与 WAV
./tools/run_python.sh

# 4. 全书自检（加 --run 把实跑纳入检查）
python3 tools/check_book.py --run
```

首个实验会打印类似结论：

```
波形图: .../part0/00-three-a/fig/00-waveform.svg
指标图: .../part0/00-three-a/fig/00-metrics.svg
WAV: 16000 帧 / 16000 Hz / 1.00 s / 32000 字节
ERLE(理想AEC)=24.11 dB | segSNR 原始=-2.21 → AEC后=-0.32 → ANS后=5.82 → 3A输出=5.82 dB
RMS 原始=0.3452 → 输出=0.1600 | 目标=0.1600
```

同时在 `part0/00-three-a/fig/` 生成波形图与指标图，在 `part0/00-three-a/audio/`
生成「未处理 / 目标 / 处理后」三段可试听样本。**所有声音都是代码合成的教学信号，不是真实录音。**

## 内容结构

| 卷 | 章 | 主题 |
| --- | --- | --- |
| 卷首 · 共同语言 | 00–03 | 3A 问题全景、声学路径与 RIR、采样量化与 STFT、指标族与尺度对齐 |
| 上卷 · 传统算法 | 04–08 | LTI 与卷积、LMS/NLMS、FDAF/MDF、双讲与时延漂移、VAD 与噪声估计 |
| 上卷 · 传统算法 | 09–14 | AEC 结构与实现、残余回声抑制、谱减、Wiener/MMSE、AGC |
| 上卷 · 传统算法 | 15–18 | 波束形成、级联顺序、ffmpeg/WebRTC 工具链、上卷综合评测 |
| 下卷 · AI 算法 | 19–22 | 时频掩码、训练数据合成、网络骨架、复数域与相位 |
| 下卷 · AI 算法 | 23–26 | 神经降噪、神经 AEC、神经增益控制、联合 3A |
| 下卷 · AI 算法 | 27–31 | 因果流式、延迟预算与 RTF、量化部署、泛化与评测陷阱、结课项目 |
| 附录 | A | 公式 / 术语 / 命令速查、实验索引、手写实现与工业库对照、链接总表 |

每章固定栏目：**本章位置 → 给程序员的翻译 → 学习目标 → 知识点地图（逐条挂链接）
→ 原理小节 → Python 实验（代码 + 图 + 试听）→ 可选命令片段 → 参考资料
→ 常见误区 → 习题与思考 → 扩展学习**。

## 仓库结构

```
audio3A/
├── index.html                 全书总目录（生成器产出）
├── assets/
│   ├── style.css              统一样式（含 .audio-grid / .volume-banner / pre.cmd）
│   ├── app.js                 侧栏、主题、复制、上下章导航
│   └── toc.js                 由生成器产出的目录数据（侧栏唯一数据源）
├── part0/00-three-a/
│   ├── index.html             章节页
│   ├── code/00-three-a.py     可直接运行的零依赖实验
│   ├── fig/*.svg              实验生成的矢量图
│   └── audio/*.wav            实验生成的 16 kHz 试听样本
├── part1/ … part6/            其余 32 章，结构相同
├── appendix/index.html        附录 A
└── tools/
    ├── book_schema.py         分卷分部、章节数据接口、全局约定
    ├── chapter_kit.py         HTML 片段助手 + 统一实验样板
    ├── book_resources.py      外部参考资料唯一数据源（69 条）
    ├── chapters_*.py          分文件的章节正文与实验定义
    ├── book_data.py           章节汇总入口 + 数据层校验
    ├── dsp.py                 纯标准库 DSP 原语（FFT/STFT/RIR/度量/WAV）
    ├── chart.py               纯标准库 SVG 绘图
    ├── build_book.py          生成全部 HTML 与 assets/toc.js
    ├── extract_code.py        从 HTML 同步 code/*.py
    ├── run_python.sh          批量运行实验
    └── check_book.py          全书静态自检
```

## 工具链

单一数据源在 `tools/chapters_*.py`，改完数据后按固定顺序重建：

```bash
python3 tools/book_data.py                 # 数据层自检（章节字段、资源 key、示例代码契约）
python3 tools/build_book.py --force        # 生成 index.html、33 章页面、assets/toc.js
python3 tools/extract_code.py             # 从页面代码块同步 code/*.py
./tools/run_python.sh                     # 实跑全部实验，生成 fig/*.svg 与 audio/*.wav
python3 tools/check_book.py --run         # 全书自检：结构 / 内链 / 代码 / SVG / WAV / 实跑
```

`tools/extract_code.py --check` 只比对不落盘；`--clean` 会删除页面里已不存在的孤立脚本。
`tools/check_book.py --urls` 可联网探测外部链接（默认不做，避免网络波动干扰本地自检）。

## 质量保障

- **数据层**：`book_data.problems()` 校验章节 id/目录唯一性、分部归属、必填字段、
  参考资源 key、命令片段、示例脚本零依赖契约（禁止 numpy/scipy/torch/matplotlib 等）、
  图/WAV 路径与脚本内生成语句是否一致、脚本能否编译。
- **页面层**：`check_book.py` 校验 `toc.js` 与章节顺序一致、页面必备栏目与页脚、
  HTML 标签平衡、无残留占位符、内链与页内锚点可解析。
- **产物层**：SVG 必须能被 XML 解析；WAV 必须是 16 kHz / 16-bit / 单声道；
  代码块与 `code/*.py` 逐字一致；所有声明的图与试听样本都存在。
- **运行层**：`--run` 实跑全部 32 个脚本，任一异常即报错退出。

## 约定与边界

- **零第三方依赖**：教材要展示算法本身与「图、声音是怎么生成的」。下卷涉及真实训练时，
  各章给出 PyTorch / ONNX Runtime / 开源工程的进阶入口，实验本身仍保持零依赖。
- **合成信号**：全部语音、噪声、RIR 由代码生成，用于说明机制与量级；
  `tools/dsp.py` 的 `lufs_approx()`、手写 FFT、小型掩码估计器都是教学实现，
  **不能直接用于生产环境，也不是任何厂商产品的性能数据**。
- **版本口径**：ffmpeg 各滤镜（`afftdn` / `arnndn` / `anlmdn` / `loudnorm` /
  `dynaudnorm` / `speechnorm` / `ebur128` / `astats` / `aecho` 等）是否可用取决于本机
  版本与编译选项；书中命令均为「先自查、再查官方文档」的形式，不写死版本。
  权威入口见 https://ffmpeg.org/ffmpeg-filters.html 与附录 A.7。
- **不从属**：本书与 WebRTC、FFmpeg、SpeexDSP、RNNoise、Microsoft DNS/AEC Challenge
  等项目无从属关系，也不构成产品推荐；参考资料与工具的版权归各自维护者所有。

## 同系列教材

- `analogCircuits` — 模拟电路（LTspice 网表 + HTML 教材）
- `imageProcessing` — 图像处理（GNU Octave 脚本，上/下卷）
- `touZi` — 投资理财（纯标准库 Python + SVG 图）

四本共用同一套静态 HTML 教材框架：结构化章节数据 → 生成器 → 页面 / 目录 /
可运行示例 → 自检器闭环。

## 作者与 AI 使用说明

- **作者**：汪亮（bertonwang） · [47608843@qq.com](mailto:47608843@qq.com)
- **AI 使用说明**：本教材的知识框架、正文、Python 实验脚本与开源工程清单在 AI 辅助下
  整理生成，并经人工校订、实际运行与静态自检；公式、数值与运行结果请以 Python 3
  实际输出及权威教材、官方文档为准。发现错漏欢迎通过上方邮箱勘误。

## 许可证

本仓库目前**未附带 `LICENSE` 文件**，尚未声明开源许可证。个人学习与课堂教学可直接
阅读、使用页面内容；转载、二次分发或商业使用前请先联系作者。外部参考资料、
开源工程与工具的版权与许可证归各自维护者所有。
