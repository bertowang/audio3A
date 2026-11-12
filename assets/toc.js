/* 由 tools/build_book.py 生成，请勿手工编辑。
   目录、侧栏、面包屑、上下章导航共用这一份数据。 */
window.BOOK_TOC = {
  "title": "音频 3A 处理：从自适应滤波到神经增强",
  "subtitle": "本科到研究生 · AEC 回声消除 / ANS 噪声抑制 / AGC 增益控制的传统与 AI 两条路线",
  "parts": [
    {
      "id": "p0",
      "title": "卷首 · 3A 问题全景",
      "stage": "卷首 · 共同语言与问题定义",
      "chapters": [
        {
          "id": "00",
          "title": "3A 是什么：一条实时语音链路上的三个约束",
          "path": "part0/00-three-a/index.html",
          "status": "done"
        },
        {
          "id": "01",
          "title": "声学链路与信号模型：房间、麦克风与回声路径",
          "path": "part0/01-acoustic-path/index.html",
          "status": "done"
        },
        {
          "id": "02",
          "title": "采样、量化与时频表示：从 PCM 到 STFT",
          "path": "part0/02-time-frequency/index.html",
          "status": "done"
        },
        {
          "id": "03",
          "title": "怎么算「变好了」：客观指标、尺度与主观听测",
          "path": "part0/03-metrics/index.html",
          "status": "done"
        }
      ]
    },
    {
      "id": "p1",
      "title": "第一篇 · 信号、系统与自适应滤波基础",
      "stage": "上卷 · 传统算法（Model-based）",
      "chapters": [
        {
          "id": "04",
          "title": "线性系统、卷积与频域实现",
          "path": "part1/04-lti-convolution/index.html",
          "status": "done"
        },
        {
          "id": "05",
          "title": "自适应滤波：LMS、NLMS 与收敛",
          "path": "part1/05-adaptive-filter/index.html",
          "status": "done"
        },
        {
          "id": "06",
          "title": "频域自适应滤波：FDAF、分块 MDF 与收敛",
          "path": "part1/06-fdaf/index.html",
          "status": "done"
        },
        {
          "id": "07",
          "title": "双讲检测、时延漂移与路径突变",
          "path": "part1/07-doubletalk/index.html",
          "status": "done"
        },
        {
          "id": "08",
          "title": "VAD 与噪声功率谱估计（MCRA 思路）",
          "path": "part1/08-noise-estimation/index.html",
          "status": "done"
        }
      ]
    },
    {
      "id": "p2",
      "title": "第二篇 · AEC / ANS / AGC 三类经典引擎",
      "stage": "上卷 · 传统算法（Model-based）",
      "chapters": [
        {
          "id": "09",
          "title": "AEC 总体结构：参考信号、线性滤波与残余抑制",
          "path": "part2/09-aec-architecture/index.html",
          "status": "done"
        },
        {
          "id": "10",
          "title": "用 NLMS 实现一个可验证的 AEC",
          "path": "part2/10-nlms-aec/index.html",
          "status": "done"
        },
        {
          "id": "11",
          "title": "残余回声抑制与 WebRTC AEC3 结构",
          "path": "part2/11-residual-echo/index.html",
          "status": "done"
        },
        {
          "id": "12",
          "title": "谱减、过减因子与音乐噪声",
          "path": "part2/12-spectral-subtraction/index.html",
          "status": "done"
        },
        {
          "id": "13",
          "title": "Wiener 滤波、先验 SNR 与 MMSE-STSA",
          "path": "part2/13-wiener-mmse/index.html",
          "status": "done"
        },
        {
          "id": "14",
          "title": "AGC：包络跟踪、攻击释放、限幅与响度",
          "path": "part2/14-agc/index.html",
          "status": "done"
        }
      ]
    },
    {
      "id": "p3",
      "title": "第三篇 · 级联、评测与工程链路",
      "stage": "上卷 · 传统算法（Model-based）",
      "chapters": [
        {
          "id": "15",
          "title": "麦克风阵列与波束形成：从 delay-and-sum 到 MVDR",
          "path": "part3/15-beamforming/index.html",
          "status": "done"
        },
        {
          "id": "16",
          "title": "3A 级联顺序与模块间相互干扰",
          "path": "part3/16-cascade-order/index.html",
          "status": "done"
        },
        {
          "id": "17",
          "title": "ffmpeg / WebRTC / SpeexDSP 工具链实操",
          "path": "part3/17-toolchain/index.html",
          "status": "done"
        },
        {
          "id": "18",
          "title": "上卷综合实验：完整传统 3A 链路与评测",
          "path": "part3/18-classic-eval/index.html",
          "status": "done"
        }
      ]
    },
    {
      "id": "p4",
      "title": "第四篇 · 数据、表示与学习基础",
      "stage": "下卷 · AI 算法（Data-driven）",
      "chapters": [
        {
          "id": "19",
          "title": "时频掩码：IBM / IRM / CRM 与监督学习形式化",
          "path": "part4/19-tf-mask/index.html",
          "status": "done"
        },
        {
          "id": "20",
          "title": "训练数据合成：RIR、噪声、SNR 配比与数据泄漏",
          "path": "part4/20-data-synthesis/index.html",
          "status": "done"
        },
        {
          "id": "21",
          "title": "网络骨架：DNN / CRN / U-Net / TCN / Conformer",
          "path": "part4/21-network-backbones/index.html",
          "status": "done"
        },
        {
          "id": "22",
          "title": "复数域与相位：DCCRN、深度滤波与时域模型",
          "path": "part4/22-complex-phase/index.html",
          "status": "done"
        }
      ]
    },
    {
      "id": "p5",
      "title": "第五篇 · 神经 3A 与联合建模",
      "stage": "下卷 · AI 算法（Data-driven）",
      "chapters": [
        {
          "id": "23",
          "title": "神经噪声抑制：从 RNNoise 到 DNS Challenge",
          "path": "part5/23-neural-ns/index.html",
          "status": "done"
        },
        {
          "id": "24",
          "title": "神经 AEC 与回声/噪声联合抑制",
          "path": "part5/24-neural-aec/index.html",
          "status": "done"
        },
        {
          "id": "25",
          "title": "神经增益控制与感知响度",
          "path": "part5/25-neural-agc/index.html",
          "status": "done"
        },
        {
          "id": "26",
          "title": "联合 3A：多任务、级联与端到端建模",
          "path": "part5/26-joint-3a/index.html",
          "status": "done"
        }
      ]
    },
    {
      "id": "p6",
      "title": "第六篇 · 实时部署、评测与前沿",
      "stage": "下卷 · AI 算法（Data-driven）",
      "chapters": [
        {
          "id": "27",
          "title": "因果性与流式推理：状态缓存、感受野",
          "path": "part6/27-causal-streaming/index.html",
          "status": "done"
        },
        {
          "id": "28",
          "title": "延迟预算与 RTF：实时链路账本",
          "path": "part6/28-latency-budget/index.html",
          "status": "done"
        },
        {
          "id": "29",
          "title": "量化、剪枝与端侧推理",
          "path": "part6/29-quantization/index.html",
          "status": "done"
        },
        {
          "id": "30",
          "title": "泛化、鲁棒性与评测陷阱",
          "path": "part6/30-generalization/index.html",
          "status": "done"
        },
        {
          "id": "31",
          "title": "结课项目：小型掩码估计器与全链路验证",
          "path": "part6/31-capstone/index.html",
          "status": "done"
        }
      ]
    },
    {
      "id": "pa",
      "title": "附录 · 公式、术语、命令与资源总表",
      "stage": "附录 · 速查与资源总表",
      "chapters": [
        {
          "id": "A",
          "title": "附录 A · 公式、术语、命令与资源速查",
          "path": "appendix/index.html",
          "status": "done"
        }
      ]
    }
  ]
};

window.BOOK_FLAT = (function () {
  const out = [];
  (window.BOOK_TOC.parts || []).forEach(function (part) {
    (part.chapters || []).forEach(function (ch) {
      out.push(Object.assign({ partId: part.id, partTitle: part.title }, ch));
    });
  });
  return out;
})();
