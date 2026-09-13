# NVFP4, FP8, and BF16 on one RTX PRO 5000 Blackwell

## Bottom line

**Your memory hunch is right: smaller weights can leave more room for agent histories, reduce cache pressure, and keep more requests running. The speed advantage and quality cost depend on the checkpoint, kernel, and workload.** The evidence does not establish NVFP4 as the universal winner on your 72 GB GPU.

- **BF16 creates the sharpest memory constraint.** Idealized 27B weights consume 50.29 GiB in BF16, 25.15 GiB in FP8, or 14.14 GiB in NVFP4 including block scales. Real checkpoints mix precisions and need additional memory. The NVIDIA Muse checkpoint you actually run averages **6.6 bits per parameter**, substantially above the homogeneous NVFP4 estimate. [10][11]
- **NVFP4 versus FP8 can be a modest capacity improvement after both fit.** One explicit 27B example below leaves 31.38 GiB for cache with FP8 weights and 42.38 GiB with NVFP4: **35% more cache**, with unchanged KV precision. It does not double session capacity. This is a calculation, not a measurement of your model.
- **Four to eight moderate-length agents may already fit comfortably with FP8.** For Qwen3.8-27B, eight independent 16K histories require about **4 GiB of FP8 full-attention KV**, before recurrent state, allocator overhead, and generation growth. At 64K, that component becomes **16 GiB**. Longer histories make the extra weight savings more valuable. [8]
- **Your running Muse NVFP4 route uses a weight-only Marlin path for its NVFP4 layers.** The observed activation/query dtype is BF16 and KV storage is FP8. A B200 NVFP4 matrix-compute speedup cannot be assigned to this route. The live server demonstrates that this combination loads and allocates cache; it does not demonstrate a win over FP8 or BF16.
- **Independent workstation measurements contradict a blanket “2× faster than FP8” claim.** Across four models on an RTX PRO 6000 Blackwell, published warmed single-stream NVFP4 decode estimates range from **10.1% slower to 13.9% faster than FP8**. This is closer hardware evidence, still short of a prediction for your RTX PRO 5000. [12]
- **Useful work per minute should decide.** Select the configuration that completes your coding and tool-use tasks correctly while meeting your latency limits. An aggregate tokens/s win can coexist with slower individual agents, more retries, or worse tail latency.

**No local BF16/FP8/NVFP4 head-to-head was run.** This research inspected configuration, existing startup logs, and idle GPU state; fetched public sources; and calculated memory examples. It did not download weights, submit inference benchmarks, change serving configuration, or restart services.

### How to read the evidence

| Label | Meaning | What it cannot establish |
|---|---|---|
| **Local observation** | Existing configuration, container arguments, startup logs, or an idle hardware snapshot | A speedup, quality retention, or sustainable concurrency limit |
| **Calculation** | Arithmetic from explicit architecture and memory assumptions | Actual allocation after kernels, graphs, padding, and draft models |
| **Independent measurement** | Results published by researchers outside the hardware/checkpoint vendor | Automatic reproducibility or applicability to a different model/GPU |
| **Vendor measurement** | Results published by NVIDIA or the checkpoint/serving supplier | An independently replicated local outcome |
| **Hypothesis / recommendation** | A reasoned expectation or a proposed decision rule | A result already measured |

The report separates explanation from the proposed experiment protocol. The source list identifies the primary documents behind each numbered citation.

## 1. What is actually running

The workstation specification is one RTX PRO 5000 Blackwell 72 GB, 64 GB host RAM, and a Ryzen 5700G. The repository records that specification in [AGENTS.md](../AGENTS.md). Read-only runtime inspection confirmed the following:

| Local observation | Observed value | Interpretation |
|---|---|---|
| GPU memory reported by `nvidia-smi` | 73,415 MiB = **71.694 GiB** | Use this reported capacity for allocation calculations |
| GPU memory used at an idle snapshot | 57,300 MiB | Includes allocated cache and other device allocations; it is not weight size or active-history size |
| Driver / running engine | 595.71.05 / vLLM 0.28.0 | Engine and kernel version matter to any comparison |
| Sole live model container | `vllm-muse-glimmer-nvidia` | Multiple agent clients can share this one loaded model |
| Target checkpoint | `nvidia/Muse-Glimmer-30B-NVFP4` | A mixed-precision checkpoint, described below |
| Memory utilization setting | `0.80` | An executor budget of approximately **57.36 GiB**, not a KV-only budget |
| Maximum model length / sequence cap | 262,144 with YaRN / 32 | Configuration limits, not proof of usable long-context quality or 32 fast agents |
| Speculative decoding | DFlash, 15 speculative tokens | An additional performance and memory variable |
| Logged model-loading allocation | **28.39 GiB** | Covers the target-plus-draft loading interval; do not label this pure target-weight memory |
| Logged available KV memory | **24.57 GiB** | Cache pool after the engine's memory accounting |
| Logged GPU KV capacity | **2,679,084 tokens** | Engine/architecture-specific capacity estimate |
| Logged maximum concurrency | **10.22× at 262,144 tokens** | Allocator estimate, not a measured service-level guarantee |
| Attention dtype / decode backend | BF16 queries, `float8_e4m3fn` KV, XQA decode, SM120 | FP8 KV is independent of the weight format |
| NVFP4 matrix path | Marlin, weight-only | The checkpoint label alone does not specify the arithmetic path |

These observations come from read-only `nvidia-smi`, container inspection, and existing startup logs gathered for this research. The reproducible configuration references are [config.yaml](../services/llama-swap-vllm/config.yaml) and [docker-compose.yml](../services/llama-swap-vllm/docker-compose.yml). Configuration declarations and live observations are intentionally separate: the other declared routes were not launched for this report.

The declared alternatives already contain confounders. The Ornith 35B-A3B route pins BF16 KV. The Qwen3.8 NVFP4 and FP8 routes both use FP8 KV and DFlash2 with seven speculative tokens, but differ in template, batch budget, kernel-disable choices, and thinking metadata. Comparing those routes as written would compare deployment bundles rather than weight precision alone.

### Why nearly full VRAM can be healthy

vLLM reserves a cache pool at startup. With automatic sizing, its budget must cover weights, activations, runtime allocations, and graph memory before cache. A smaller checkpoint can produce a larger cache pool while `nvidia-smi` still shows almost the same total allocation. The relevant measurements are **usable cache blocks/tokens, occupied cache blocks, queueing, and preemption**, rather than free VRAM alone. The explicit `kv_cache_memory_bytes` setting overrides utilization-based sizing. [1][2][7]

The startup concurrency estimate answers a capacity question under the allocator's model. It says nothing about how long ten large prefills take, how quickly ten agents decode, or whether answers remain reliable at the configured extended context.

## 2. Precision has three separate meanings

A serving configuration has at least three precision choices:

1. **Weights:** the stored model parameters. Compressing these creates VRAM headroom and reduces the bytes kernels may need to read.
2. **Activations and arithmetic:** the temporary values and matrix operations used while evaluating tokens. `W4A16` means four-bit weights with sixteen-bit activations; `W4A4` also quantizes activations.
3. **KV cache:** stored attention keys and values for prior tokens. FP8 weights do not imply FP8 KV, and NVFP4 weights do not imply NVFP4 KV. vLLM exposes separate cache controls, including separate recurrent-state dtypes for hybrid models. [1]

| Weight format | Nominal storage per quantized value | Main tradeoff |
|---|---:|---|
| BF16 | 2 bytes | Largest weight footprint; useful reference for additional quantization error |
| FP8 | 1 byte, plus recipe-specific scales | Intermediate weight compression; the exact activation/scaling recipe still matters |
| NVFP4 | 0.5 byte + 1 FP8 scale per 16 values = **0.5625 byte**, plus tensor scales | Smallest of these homogeneous representations; greater dependence on quantization recipe and execution kernels |

NVFP4 stores E2M1 four-bit values with a shared E4M3 FP8 scale for each 16-value block and a second FP32 tensor scale. Its block-scaled representation costs approximately **4.5 bits/value**, giving about **3.56×** compression versus BF16 and **1.78×** versus FP8 before other overhead. These are storage ratios, not throughput ratios. NVFP4 differs from MXFP4, AWQ/INT4, and GGUF quantizations; a result for one should not be relabeled as a result for another. [11]

### Your NVIDIA Muse checkpoint is deliberately mixed

NVIDIA's Muse card describes an AutoQuantize search across three choices: W4A16 NVFP4, FP8 weights/activations, and BF16 fallback for sensitive modules. The vision encoder and unmatched modules remain BF16. A 5.5-bit constraint applies to the selected search layers; the **whole checkpoint averages 6.6 bits/parameter**. NVIDIA reports approximately **60 GB → 24.7 GB on disk**, or about 2.4× compression. [10]

That recipe explains why a generic “30B at four bits is about 15 GB” estimate misrepresents this deployment. Disk bytes, loaded target tensors, target-plus-draft allocation, and total VRAM are four different measurements. Changing a BF16 serving dtype flag also cannot restore information already removed from quantized weights; a BF16 reference must use the corresponding source checkpoint.

## 3. How much memory does quantization actually buy?

### Weight-only arithmetic

**Calculation:** the following table uses exactly 27, 30, or 35 billion parameters and homogeneous storage. It includes NVFP4 block scales but excludes FP8 scales, NVFP4 tensor-scale overhead, unquantized modules, padding, vision-specific differences, and every runtime allocation. GiB means bytes divided by 2³⁰.

| Nominal parameter count | BF16 weights | FP8 weights | NVFP4 weights + block scales | FP8 → NVFP4 saving |
|---|---:|---:|---:|---:|
| 27B | 50.29 GiB | 25.15 GiB | 14.14 GiB | 11.00 GiB |
| 30B | 55.88 GiB | 27.94 GiB | 15.72 GiB | 12.22 GiB |
| 35B | 65.19 GiB | 32.60 GiB | 18.34 GiB | 14.26 GiB |

These are sizing examples, **not predicted loaded sizes for Muse, Qwen, or Ornith**. For MoE, total resident parameters determine weight storage unless experts are offloaded. A “35B-A3B” label does not make its weights occupy the space of a dense 3B model.

### The cache gain is a subtraction, not a precision ratio

An explanatory memory model is:

\[
K = uV - W - H
\]

where \(K\) is usable cache budget, \(V\) is reported VRAM, \(u\) is the executor fraction, \(W\) is resident weight memory, and \(H\) is other memory: activations, workspace, CUDA graphs, draft models, and runtime overhead. Real vLLM allocation adds architecture-specific accounting and block rounding. [1][2][6]

**Illustrative calculation, not a local measurement:** take your observed 71.694 GiB GPU, a common 0.90 executor fraction, the homogeneous 27B weight sizes above, and an explicitly assumed **8 GiB** of other memory. The executor budget becomes 64.52 GiB.

| Format | Executor budget | Assumed other memory | Remaining cache |
|---|---:|---:|---:|
| BF16 | 64.52 GiB | 8.00 GiB | **6.23 GiB** |
| FP8 | 64.52 GiB | 8.00 GiB | **31.38 GiB** |
| NVFP4 | 64.52 GiB | 8.00 GiB | **42.38 GiB** |

NVFP4 adds approximately 11 GiB of cache over FP8 in this example, a **35.1%** increase. The first step from BF16 to FP8 is much larger because BF16 leaves little room after weights. The assumed 8 GiB overhead is neither measured nor guaranteed equal across formats; kernel workspaces and graph allocations can change it.

A homogeneous 35B BF16 model already exceeds the 0.90 budget before runtime overhead. Increasing the fraction or using CPU offload would create a different experiment. Offload also introduces host-to-device traffic on the critical path, so this report does not treat your 64 GB host RAM as equivalent to extra VRAM. [1]

### Context memory depends on architecture

For ordinary full-attention layers, the attention KV payload is:

\[
M_{KV}=T \times L_{full} \times 2 \times H_{KV} \times D_{head} \times b
\]

Here \(T\) is cached tokens, \(L_{full}\) is full-attention layers, \(H_{KV}\) is KV heads, \(D_{head}\) is head dimension, and \(b\) is bytes per cached element. The factor two represents keys and values.

Qwen3.8-27B has 64 layers in 16 groups of three Gated DeltaNet blocks and one gated full-attention block. The full-attention blocks have four KV heads of dimension 256. Consequently, the **full-attention component alone** costs **64 KiB/token in BF16** or **32 KiB/token in FP8**. Applying the full-attention formula to all 64 layers would overcount that component by four. [8]

**Calculation:** independent histories, no shared prefixes; token counts include whatever prompt and generated history remains cached.

| Cached tokens per session | BF16 KV, one session | FP8 KV, one session | FP8 KV, four sessions | FP8 KV, eight sessions |
|---|---:|---:|---:|---:|
| 2,048 | 0.125 GiB | 0.0625 GiB | 0.25 GiB | 0.50 GiB |
| 16,384 | 1.00 GiB | 0.50 GiB | 2.00 GiB | 4.00 GiB |
| 65,536 | 4.00 GiB | 2.00 GiB | 8.00 GiB | 16.00 GiB |
| 262,144 | 16.00 GiB | 8.00 GiB | 32.00 GiB | 64.00 GiB |

Add recurrent states, cache-group padding, block rounding, speculative state, and generation growth before using this table to admit requests. Hybrid caches can have different state sizes and page alignment requirements; vLLM's hybrid-cache design explicitly describes padding overhead. These numbers do not describe Muse's cache layout. Use Muse's own allocator output rather than transplanting Qwen's per-token constant. [6]

This yields a bounded recommendation: **FP8 deserves a baseline trial for four to eight Qwen agents with roughly 16K histories.** Their full-attention KV payload is small relative to the illustrative FP8 cache budget. NVFP4 becomes more compelling as histories grow, more agents run simultaneously, or another model must remain resident. Actual admission and latency still need measurement.

### Why extra cache can improve throughput, and why it can fail to help

- **When cache is full:** additional space can avoid preemption and recomputation, keep more independent histories resident, and admit a larger batch. vLLM documents the latency cost of recomputing preempted requests. [2]
- **When compute or memory bandwidth is already saturated:** more resident requests can increase each agent's wait without adding useful work per second. More memory creates an opportunity for batching; it does not create proportionally more GPU execution capacity.
- **When agents share exact prefixes:** prefix caching can reuse the processed system prompt, code context, or conversation history. That reduces repeated prefill work. Cache hits require matching prefixes, not merely similar documents. [5]
- **When an agent is using a tool:** an open agent session need not have an inference request running. Eight open sessions, eight outstanding requests, and eight sequences in a GPU execution batch are different quantities. Retained prefix blocks can also be evicted under pressure. [3][6]
- **When multiple model servers are resident:** each has its own weights, runtime overhead, and cache budget. Multiple clients of one model normally share the loaded weights. Treat co-resident models as a separate capacity question.

Dense/MoE and full-attention/hybrid are separate axes. MoE changes which experts execute for each token; hybrid attention changes how historical state is represented. Neither the parameter count nor the quantization label captures both.

## 4. What measured speed evidence actually shows

### Closest three-way comparison: one SM120 workstation

Stefano Schotten's June 2026 independent study compares released BF16, FP8, and NVFP4 checkpoints on an **RTX PRO 6000 Blackwell Max-Q 96 GB**, using **vLLM 0.22.1, CUDA 13.2, and driver 595.71.05**. The throughput runner permits one sequence, with a 65,536-token maximum context. Table 5 reports the following at a **128-token prompt**. [12]

| Model | BF16 decode estimate | FP8 decode estimate | NVFP4 decode estimate | NVFP4 versus FP8 |
|---|---:|---:|---:|---:|
| Qwen3.6-27B, dense | 26.7 tokens/s | 48.8 tokens/s | 55.6 tokens/s | **+13.9%** |
| Gemma-4-31B-it, dense | 22.3 tokens/s | 42.0 tokens/s | 40.8 tokens/s | **−2.9%** |
| Qwen3.6-35B-A3B, MoE | 168.6 tokens/s | 221.4 tokens/s | 226.3 tokens/s | **+2.2%** |
| Gemma-4-26B-A4B-it, MoE | 151.7 tokens/s | 200.1 tokens/s | 179.8 tokens/s | **−10.1%** |

These are **warmed single-stream two-point estimates**, not streaming measurements or concurrent-serving throughput. The runner calculates `256 / (median time for 257 outputs − median time for 1 output)`, with three repeats. It warms the same token IDs, then reuses them without disabling or resetting prefix caching. Consequently, its reported “TTFT” values do not establish cold-prefill latency. This report does not adopt the article's claim that sub-0.1-second Gemma 16K results prove an architectural prefill advantage. [12]

The checkpoint matrix also varies recipe and KV precision. Qwen-dense FP8 uses block-128 quantization; its NVFP4 export comes from Unsloth. Gemma's mixed recipes protect different modules. The Qwen MoE NVFP4 arm dequantizes `lm_head` to BF16 to work around an engine limitation. This is useful **deployment-recipe evidence**, with no claim that bit width is the only changed variable. [12]

The actual disk-size differences reinforce the memory caution: this study reports Qwen3.6-27B FP8 at **30.9 GB** and NVFP4 at **26.4 GB**, while Gemma-4-31B FP8/NVFP4 are **33.3/32.7 GB**. Those are checkpoint disk footprints, not measured cache budgets. A homogeneous four-bit estimate would miss how much higher-precision material these exports retain. [12]

### Independent consumer-Blackwell results

A January 2026 independent preprint by Knoop and Holtmann measured consumer Blackwell GPUs using **vLLM 0.12, CUDA 12.9, and AIPerf 0.3.0**. Its RAG workload used synthetic inputs, up to 512 output tokens, and capped concurrency. The engine used an 8,192-token batch budget. These are published measurements, not results reproduced for this report. [9]

| Model / GPU / workload | Format | Aggregate output tokens/s | TTFT | Comparison |
|---|---|---:|---:|---|
| Qwen3-8B / one RTX 5090 / 8K input / concurrency 8 | BF16 | 260 | 1,538 ms | Reference |
| Same | AWQ W4A16 | 314 | 1,030 ms | 1.21× BF16 throughput |
| Same | NVFP4 | 411 | 450 ms | **1.58× BF16**, 1.31× AWQ throughput |
| Gemma3-27B / one RTX 5090 / 8K input / concurrency 4 | W4A16 | 111.6 | 6,817 ms | Reference |
| Same | NVFP4 | 98.5 | 5,722 ms | **11.7% less throughput**, despite lower TTFT |

The Qwen rows come from Table 7; the Gemma rows come from Table 15. The paper does **not** include an FP8-weight arm in the Qwen comparison. Its published YAML gives both Qwen arms the same 9,216-token maximum length, 0.90 utilization fraction, 8,192-token batch budget, 500 requests, five warmups, and disabled thinking. Neither arm pins KV dtype. The currently fetched NVIDIA checkpoint metadata specifies FP8 KV quantization, but that does not prove how the historical run resolved its cache. The paper itself describes 16-bit KV in most configurations and FP8 where needed. **Treat 1.58× as a deployment comparison, not an isolated weight-precision effect.** [9][13][14]

The counterexample matters: lower TTFT and higher throughput are separate outcomes. Even on consumer Blackwell, the same nominal NVFP4 choice can improve one and worsen the other. The report also omits a tempting Gemma3-12B ratio because its table compares concurrency four against concurrency eight.

**No numeric RTX PRO 5000 speed forecast follows from these rows.** Your GPU, newer engine, larger models, hybrid state, speculative decoding, and actual Marlin path differ. A peak FP4 FLOPS ratio or a B200/GB200 rack-level number would be even less transferable.

## 5. How much intelligence is lost?

No single “percentage of intelligence lost” describes quantization. The measurable quantities are changes in named task scores, error rates, and successful agent outcomes under a fixed evaluation setup. A one-percentage-point drop on a science benchmark does not imply the same drop in tool-call accuracy or long-context code repair.

### Most relevant vendor evidence: the exact NVIDIA Muse checkpoint

NVIDIA evaluates its mixed NVFP4/FP8/BF16 checkpoint against the BF16 source using **B200 hardware and vLLM 0.28.0**. The documented serving setup uses **unquantized KV (`auto`) and 131,072 maximum context**, with high reasoning, temperature 1.0, top-p 0.95, and top-k 64. [10]

| Benchmark | BF16 source | Mixed NVIDIA NVFP4 checkpoint | Quantized minus BF16 |
|---|---:|---:|---:|
| Terminal-Bench 2.1 pass@1 | 45.22 ± 0.92 | 47.05 ± 1.42 | +1.83 percentage points |
| GPQA Diamond pass@1 | 83.81 ± 0.33 | 83.02 ± 0.40 | −0.79 points |
| MMMU-Pro | 74.22 | 73.58 | −0.64 points |
| SciCode subtask accuracy | 47.63 | 49.70 | +2.07 points |
| IFBench strict pass@1 | 76.58 ± 0.53 | 78.74 ± 0.52 | +2.16 points |
| AA-LCR mean reward | 76.25 | 75.56 | −0.69 points |

Terminal-Bench used eight repeats, GPQA sixteen, and IFBench five. The `±` values are **standard errors across repeats**, not universal uncertainty bounds for model capability. NVIDIA explicitly warns that higher quantized scores can reflect sampling and evaluation noise. The recipe calibrated on 512 sequences of 2,048 tokens and retained BF16 modules when lower precision was too costly. [10]

This supports the claim that **this carefully mixed checkpoint preserved much of the measured BF16 task performance**. It does not establish the same outcome for a more aggressively quantized Muse export. It also leaves three local changes outside the matched evaluation: FP8 KV, DFlash, and YaRN extension to 262K. A 2,048-token calibration length is not itself evidence of failure at long context, but long-context retention must be evaluated rather than inferred from the bit width.

### Independent three-way quality comparison on SM120

The workstation study above also provides raw quality results for **Qwen3.6-27B**, comparing its BF16 source, official Qwen FP8 export, and Unsloth NVFP4 export. It uses EleutherAI's evaluation harness, native chat/thinking behavior, greedy decoding, seed 1234, 16,384 maximum context, and 4,096 maximum generated tokens. [12]

| Task | BF16 | FP8 | NVFP4 | NVFP4 minus BF16 |
|---|---:|---:|---:|---:|
| MMLU-Pro generative exact match, 700 questions | 84.43 ± 1.34 | 84.00 ± 1.36 | 82.00 ± 1.41 | **−2.43 points** |
| GSM8K strict exact match, 600 questions | 97.17 | 98.17 | 96.67 | −0.50 points |
| HumanEval instruct pass@1, 164 problems | 96.34 | 97.56 | 95.73 | −0.61 points |

The MMLU `±` values are harness sampling standard errors, unlike Muse's standard errors across benchmark repeats. MMLU uses 50 questions per subject. The author reports up to 1.7 points of MMLU drift in a second identical-protocol run across the full model matrix. Its **2.0-point NVFP4-versus-FP8 MMLU difference is a point estimate**, not a demonstrated universal or statistically significant quality tax. The study varies quantization recipes and permits KV differences across its matrix; it also omits GPQA and multi-turn tool evaluation. [12]

The older consumer-GPU preprint reports larger BF16-to-NVFP4 MMLU losses: **77.29 → 75.09** for Qwen3-8B and **62.02 → 57.95** for Gemma3-12B. Its stated 500-example setup and narrow reported confidence intervals lack enough detail here to reconcile their aggregation. The point values support task/recipe variability; its intervals are not used as statistical proof. [9]

### Calibration and recovery change the result

**PTQ** calibrates a trained model for quantization. **QAT** fine-tunes while modeling quantization error. **QAD** trains a quantized student against a high-precision teacher's output distribution. These identify different recipes; a suffix alone does not guarantee better quality. [15][17]

NVIDIA's QAD research demonstrates both recovery and failure modes on reasoning tasks: [15]

| Model / AIME 2025 | BF16 | NVFP4 PTQ | NVFP4 QAT | NVFP4 QAD |
|---|---:|---:|---:|---:|
| Llama Nemotron Super V1 49B | 46.0 | 32.3 | 41.5 | 45.6 |
| AceReason Nemotron 1.1 7B | 63.5 | 58.7 | 46.1 | 62.0 |

These are **vendor research results**, using temperature 0.6, top-p 0.95, and 48 samples per AIME problem. QAD adds approximately 0.3B training tokens for Llama Super and 0.8B for AceReason. The study selects the best average evaluation result among ten low-validation-loss checkpoints. The results concern selected recovery recipes, not NVFP4 storage alone. The AceReason row shows that one QAT recipe can degrade reasoning more than PTQ. [15]

For coding and tools, Baseten's external inference-vendor study reports Qwen3-8B BF16 → NVIDIA NVFP4 PTQ at **82.3 → 73.2 on HumanEval+ (−9.1 points)** and **67.8 → 65.5 on BFCLv3 macro-average (−2.3 points)**. It uses B200, vLLM plus EvalScope, temperature zero, thinking disabled, and seed 42. HumanEval+ contains 164 problems; BFCL combines more than 13 subsets. No error bars are reported. These task-specific losses should not be projected onto Muse's different mixed recipe. [16]

**Quality loss depends on the model, task, activation precision, protected modules, and calibration or recovery method.** Mixed precision can preserve sensitive layers at the cost of additional memory. FP8 is a useful intermediate reference, but its local advantage in accuracy or speed remains unmeasured.

For agents, evaluate invalid tool arguments, incorrect tool selection, ignored constraints, broken patches, repeated attempts, and final task success. A configuration that produces tokens faster but needs more attempts can finish fewer correct tasks per minute.

## 6. Proposed experiment: how to compare the formats fairly

**Protocol only. Nothing in this section was executed.** The proposed settings below are experimental controls, not deployment recommendations. CLI names and semantics were checked against the official vLLM 0.28.0 documentation and Context7. No untested executable benchmark script is provided. [1][3][4]

### 6.1 Fix the comparison contract

For each model family, compare the BF16 source, its FP8 export, and its NVFP4 export. Pin checkpoint revisions, tokenizer, chat template, quantization recipe, and calibration provenance. Comparing Muse against Qwen measures a model-selection tradeoff; it cannot isolate precision.

Hold these variables constant within a comparison:

| Control | Required treatment |
|---|---|
| Hardware/software | Same GPU, driver, vLLM image digest, dependencies, power policy, and host resource allocation |
| Other GPU consumers | None during the isolated comparison; test intentional co-residency separately |
| Weight offload | Disabled for all arms; a format that cannot fit receives **infeasible**, not an offloaded substitute |
| KV and recurrent-state precision | Same explicit KV dtype and scales policy; same recurrent-state dtype/mode |
| Speculation | Off in the first comparison; then repeat with the same compatible draft checkpoint and parameters |
| Serving controls | Same maximum model length, sequence cap, batched-token budget, chunked-prefill policy, and graph policy |
| Prompt behavior | Same rendered prompts, tool schema, reasoning mode/effort, retained thinking policy, sampling parameters, and output budget |
| Backend | Record the actual attention, dense GEMM, and MoE kernels; do not infer them from the checkpoint name |
| Prefix cache | Separate cold unique-prefix trials from controlled warm-prefix/multi-turn trials |

Each precision can require a different compatible matrix kernel. That is a legitimate part of the end-to-end precision package. Record it rather than forcing an incompatible backend or attributing every difference to bit width. After the controlled comparison, a separately labeled best-supported configuration per format can answer which deployment bundle works best.

### 6.2 Run both memory comparisons

| Comparison | Memory control | Question answered |
|---|---|---|
| **Equal total-memory budget** | Same executor fraction of the same observed GPU capacity; let each format obtain its own measured cache pool | Does weight compression improve the capacity and goodput available from this one GPU? |
| **Equal KV budget** | Same explicit `--kv-cache-memory-bytes`, fitting the largest arm; same cache/state dtypes and allocator layout | Does a speed advantage remain after removing extra cache capacity as the explanation? |

`--kv-cache-memory-bytes` overrides `--gpu-memory-utilization`; setting both does not enforce two independent limits. In the equal-KV trial, separately confirm that weights, cache, graphs, and peak working memory fit within the intended total ceiling. For hybrid models, also record actual cache groups, blocks, and usable token capacity. Equal nominal bytes alone can hide padding differences. [1][6]

If BF16 cannot fit the common workload without offload, report that capacity result. Do not shorten only its prompts and publish the resulting timing as an equivalent head-to-head.

### 6.3 Workload matrix

Here K means 1,024 tokens. Token lengths are measured **after** applying the common chat template and tool definitions.

| Input tokens | Outstanding-request concurrency | Output tokens for controlled timing | Purpose |
|---:|---|---|---|
| 2,048 | 1, 2, 4, 8, 16 where feasible | 256, then 1,024 | Short agent turns; single-user latency and batch scaling |
| 16,384 | 1, 2, 4, 8, 16 where feasible | 256, then 1,024 | Working coding sessions with accumulated context |
| 65,536 | 1, 2, 4, 8, 16 where feasible | 256, then 1,024 | Long histories; attention cost, cache pressure, and queueing |

Reserve enough context for the output rather than equating input length with the total sequence limit. Mark infeasible combinations and their cause: startup failure, insufficient cache, preemption, timeout, or unsupported kernel. Do not silently drop failed requests.

Use two complementary prompt sets:

- **Controlled lengths:** fixed-length input/output workloads isolate serving costs. Forcing output length with `--ignore-eos` belongs here only. Save actual token counts because truncation or prompt rendering can defeat intended lengths.
- **Real agent traces:** identical coding, tool-use, and long-context tasks with natural completion lengths. Synthetic tokens cannot establish quality and may poorly represent MoE routing or speculative acceptance. Preserve the same shared-prefix structure and tool pauses across formats.

Measure an isolated model endpoint first. Then replay the same traces through the normal proxy and agent harness to include parsing, network, client, and tool overhead. Keep cold model loading and model swapping in a separate result from warm steady-state inference.

### 6.4 Separate closed-loop capacity from open-loop latency

For the concurrency sweep, `--request-rate inf` with `--max-concurrency` set to 1/2/4/8/16 keeps up to that many requests outstanding. This measures bounded-concurrency capacity. It does not model a fixed number of human users with arbitrary pauses. [3][4]

Then test fixed arrival rates approaching and exceeding the useful service limit. Use the **same offered arrival schedule** for every format. With a finite `--request-rate`, a low `--max-concurrency` can throttle dispatch and reduce the actual arrival rate. Report both offered and dispatched rates, and include waiting before client dispatch in application latency. A server can appear responsive if the load generator hides the queue. [3]

Keep a mixed trial in which one 64K prefill arrives while short requests are decoding. This exposes interference that isolated uniform-length rows miss. vLLM's chunked-prefill settings trade TTFT against inter-token latency; tuning only one format would confound the comparison. [2]

### 6.5 Measure the quantities the user experiences

| Metric | Definition / reporting rule | Why it matters |
|---|---|---|
| **TTFT** | Client send to first streamed output; report P50 and P95 | Time before an agent starts receiving a response; includes server waiting and prefill |
| **TPOT** | Per request: `(end-to-end latency − TTFT) / (output tokens − 1)`; report P50/P95 for requests with at least two output tokens | Average decode pace after first output |
| **ITL** | Gaps between streamed outputs, pooled as documented by the harness | Stalls and burstiness; keep separate from TPOT |
| **End-to-end request latency** | Client send to final output; P50/P95, plus application queue delay separately | Time until the agent can take its next step |
| **Aggregate output tokens/s** | All generated output tokens divided by measured wall time | Total serving capacity; never label it per-agent speed |
| **Completed requests/min** | `60 × successful completed requests / elapsed seconds` | Includes the effect of output length; report errors and unfinished requests alongside it |
| **Latency goodput** | Requests satisfying all predeclared TTFT/TPOT/end-to-end limits per second or minute | Capacity at an acceptable experience rather than at any latency |
| **Correct completed agent tasks/min** | Tasks passing the fixed functional rubric within the latency/deadline policy per wall-clock minute | The final decision metric; includes retries, tool calls, and failed attempts |

The TTFT, ITL, and TPOT definitions above match the vLLM benchmark client. With speculative decoding, one streamed chunk can contain multiple accepted tokens. ITL measures chunk gaps; TPOT amortizes time across tokens. Comparing their numeric values as though they were identical can manufacture a speed claim. [4]

`vllm bench serve --goodput` applies latency thresholds, **not correctness grading**. Define those thresholds before examining winners, and state them per workload class if long prefills legitimately have a different budget. Report the correctness-qualified task metric separately. HTTP 200 and a generated answer do not establish task success. [3]

For a fixed output length \(N\), end-to-end time decomposes as approximately `TTFT + (N − 1) × TPOT`. This explains why a prefill improvement matters more for short answers, while long reasoning traces expose decode speed. Aggregate throughput divided by configured concurrency is only a rough estimate of per-request pace when all requests remain active; use the measured request distributions instead.

### 6.6 Repetitions, telemetry, and quality checks

**Proposed sampling plan:** warm every tested shape and exclude compilation, graph capture, and warmup requests. Use at least five measured runs per feasible cell with at least 100 submitted requests per run. Preserve failures in the denominator. Use the same prompt sets and seed schedule in every arm, rotate format order, and reset or deliberately reproduce cache state between runs.

Five hundred submitted requests provide a starting sample for P95, not a guarantee of precise tails. Report each run and paired bootstrap confidence intervals over independent runs/tasks. Extend runs when intervals are too wide to distinguish a practically useful change. Avoid declaring a winner from a best-of-five run or averaging percentiles without retaining the underlying samples.

Capture:

- Startup target/draft allocation, graph allocation, cache bytes, cache groups, blocks, and token capacity.
- Peak VRAM, GPU clocks/power/temperature, CPU saturation, and available host RAM.
- Running and waiting requests, queue time, cache occupancy, prefix hit rate, and preemption/recomputation. vLLM documents these observability categories; retain the actual exported metric names with the run artifact. [7]
- Speculative acceptance and accepted draft length in the production-settings phase.
- Prompt/output token counts, reasoning-token counts, finish reason, errors, and response bodies.

Use fixed, task-level quality checks: executable coding tasks; correct tool choice and arguments; instruction following; retrieval from early, middle, and late positions in long histories; and multi-turn completion. Score final outcomes with the same harness and independent rubric. Compare paired tasks across formats and repeat stochastic tasks with the same seed schedule. Preserve regressions by category instead of hiding a tool-use failure behind an average score.

A useful future result row would contain:

| Identity / conditions | Memory | User latency | Capacity | Correctness |
|---|---|---|---|---|
| Model revision, weight/activation/KV dtypes, kernels, draft, input/output lengths, concurrency, offered rate | Loaded allocations, usable KV tokens, peak VRAM, preemptions | TTFT P50/P95, TPOT P50/P95, end-to-end P50/P95 | Output tokens/s, completed requests/min, latency goodput | Task pass rate, correct tasks/min, retries, tool/format failures |

### 6.7 Verified CLI controls, without an executable recipe

The official vLLM 0.28.0 reference documents the following relevant controls. These are syntax references for an authorized future experiment, not commands run during this research. [1][3]

| Purpose | Documented control |
|---|---|
| Online benchmark | `vllm bench serve` |
| Fixed concurrency / offered load | `--max-concurrency`, `--request-rate`, `--burstiness` |
| Controlled synthetic lengths | `--dataset-name random`, `--random-input-len`, `--random-output-len` |
| Fixed output timing only | `--ignore-eos` |
| Repetition / warmup | `--num-prompts`, `--num-warmups`, `--seed` |
| Latency percentiles | `--percentile-metrics ttft,tpot,itl,e2el`, `--metric-percentiles 50,95` |
| Latency goodput | `--goodput` followed by space-separated `ttft:milliseconds`, `tpot:milliseconds`, and/or `e2el:milliseconds` pairs |
| Per-request records | `--save-result`, `--save-detailed`, `--metadata` |
| Total executor / explicit cache budget | `--gpu-memory-utilization`, `--kv-cache-memory-bytes` |

## 7. Recommendation for this single GPU

**Keep the existing Muse deployment as a working reference until a controlled comparison justifies changing it.** Its measured allocation and NVIDIA's matched quality results make it a credible candidate. Neither establishes that it is the fastest candidate or that your FP8-KV/extended-context settings preserve every quality result.

For choosing the next comparison:

| Priority | Recommended comparison | Decision rule |
|---|---|---|
| Four to eight agents with moderate histories | FP8 versus the exact NVFP4 recipe, same FP8 KV | Prefer the format with better correct-task goodput and acceptable P95; unused extra cache alone is not a win |
| Long histories, many simultaneously active agents, or co-resident models | Equal-total-budget NVFP4 versus FP8 | Prefer compression when it materially reduces admission failures, preemption, or latency without unacceptable task regressions |
| Highest fidelity for one or a few shorter sessions | BF16 where the full workload fits without offload | Use it as the reference; quantify whether the additional memory buys better task outcomes |
| Apparent NVFP4 speed anomaly | Inspect actual kernel and activation precision before comparing numbers | Distinguish weight-only compression, native low-precision arithmetic, and backend differences |

The remaining unknowns are concrete: matched FP8/NVFP4/BF16 latency and goodput on your GPU; quality under the exact local KV and speculation settings; useful long-context behavior; and the concurrency point where extra cache ceases to help. No same-harness NVIDIA-versus-Inferact Muse comparison or matched exact-recipe quality comparison for Ornith 35B-A3B and Qwen3.8-27B was established in the fetched evidence. Qwen3.6 results are adjacent evidence, not Qwen3.8 validation. The proposed experiment answers these questions without borrowing another GPU's headline ratio.

## Sources

All external sources below were fetched for this research. Model cards and rolling web pages can change; pin their revisions when turning this report into an experiment.

1. **vLLM 0.28.0 engine arguments:** [memory budgets, cache dtypes, offload, and scheduler controls](https://docs.vllm.ai/en/v0.28.0/configuration/engine_args/).
2. **vLLM 0.28.0 optimization guide:** [preemption, chunked prefill, and CPU resources](https://docs.vllm.ai/en/v0.28.0/configuration/optimization/).
3. **vLLM 0.28.0 online benchmark reference:** [`vllm bench serve` controls and latency-goodput thresholds](https://docs.vllm.ai/en/v0.28.0/cli/bench/serve/).
4. **vLLM 0.28.0 benchmarking guide:** [client timing definitions, speculative streaming, and load patterns](https://docs.vllm.ai/en/v0.28.0/benchmarking/cli/).
5. **vLLM 0.28.0 automatic prefix caching:** [reuse behavior and prefill-only benefit](https://docs.vllm.ai/en/v0.28.0/features/automatic_prefix_caching/).
6. **vLLM hybrid-cache design:** [layer-specific state allocation, cache groups, and padding](https://docs.vllm.ai/en/v0.28.0/design/hybrid_kv_cache_manager/). The document identifies its underlying design commit and warns that implementation details can change.
7. **vLLM 0.28.0 metrics design:** [running/waiting requests, cache occupancy, prefix hits, and request timing](https://docs.vllm.ai/en/v0.28.0/design/metrics/).
8. **Qwen model card:** [Qwen3.8-27B architecture and context configuration](https://huggingface.co/Qwen/Qwen3.8-27B).
9. **Independent preprint:** Knoop and Holtmann, *Private LLM Inference on Consumer Blackwell GPUs: A Practical Guide for Cost-Effective Local Deployment in SMEs*, January 14, 2026. [Methods and Tables 1, 7, and 15](https://arxiv.org/html/2601.09527v1). Not independently rerun or fully artifact-audited here.
10. **NVIDIA checkpoint card:** [Muse-Glimmer-30B-NVFP4 recipe, size, evaluation setup, and matched quality results](https://huggingface.co/nvidia/Muse-Glimmer-30B-NVFP4). Vendor evidence.
11. **NVIDIA format explanation:** [Introducing NVFP4 for Efficient and Accurate Low-Precision Inference](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/). Used for representation and scale overhead, not as a workstation speed forecast.
12. **Independent SM120 workstation study:** Schotten, [NVFP4: What 4-Bit Really Costs on Blackwell](https://ure.us/articles/benchmarking-nvfp4-blackwell/), June 8, 2026. Fetched supporting [model matrix](https://github.com/sch0tten/nvfp4-benchmark/blob/main/configs/models.yaml), [throughput runner](https://github.com/sch0tten/nvfp4-benchmark/blob/main/scripts/run_throughput.py), [quality runner](https://github.com/sch0tten/nvfp4-benchmark/blob/main/scripts/run_quality.py), and Qwen3.6-27B [BF16](https://github.com/sch0tten/nvfp4-benchmark/blob/main/results/quality/qwen3_6_27b__bf16.json), [FP8](https://github.com/sch0tten/nvfp4-benchmark/blob/main/results/quality/qwen3_6_27b__fp8.json), and [NVFP4](https://github.com/sch0tten/nvfp4-benchmark/blob/main/results/quality/qwen3_6_27b__nvfp4.json) result files. The repeated-prefix throughput limitation and recipe differences constrain its conclusions.
13. **Consumer-preprint experiment configuration:** [Single RTX 5090 YAML](https://github.com/hholtmann/llm-consumer-gpu-benchmark/blob/main/research_results/results_config/rtx5090_1x.yaml), fetched to inspect shared controls and unpinned KV dtype.
14. **Current Qwen3-8B NVFP4 metadata:** [`hf_quant_config.json`](https://huggingface.co/nvidia/Qwen3-8B-NVFP4/raw/main/hf_quant_config.json). Current metadata cannot establish historical runtime resolution.
15. **NVIDIA recovery research:** [Quantization-Aware Distillation for NVFP4 Inference Accuracy Recovery](https://arxiv.org/html/2601.20088v3), Tables 2–3 and evaluation methods. Vendor research, including checkpoint selection.
16. **Baseten evaluation:** [Qwen3 NVFP4 Quantization Benchmark](https://github.com/basetenlabs/qwen3-nvfp4-benchmark/blob/main/README.md). External inference-vendor measurement; code/tool scores use its stated protocol.
17. **NVIDIA ModelOpt documentation:** [Basic quantization concepts](https://nvidia.github.io/Model-Optimizer/guides/_basic_quantization.html), recipe components, calibration, and quantization-aware training.
