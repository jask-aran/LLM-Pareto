# LLM-Pareto

Small tools for comparing model capability, task cost, token use, and response-time trade-offs.

## Model data

`artificial_analysis_v2.py` requires Python 3 and uses only the standard library. Run it with `uv run`:

One model:

```bash
uv run artificial_analysis_v2.py gpt-5-6-sol
```

Multiple models:

```bash
uv run artificial_analysis_v2.py \
  gpt-5-6-terra-low,gpt-5-6-sol-high,gpt-5-6-sol-xhigh
```

Slugs can be comma-separated, space-separated, or both. A single slug returns `data.model`; multiple slugs return `data.models` in requested order. Duplicate slugs are removed.

Every invocation includes:

- `schema_version`
- `collected_at`: current system time in UTC
- `requested_count` and `returned_count`
- `sources.general` and `sources.coding`
- `evaluation_reference_model` and `evaluation_fields`

The same `collected_at` value is also placed on every model record for future row-oriented storage.

### Evaluation schema

`EVALUATION_REFERENCE_MODEL` near the top of the script defines the archived evaluation set. It defaults to `gpt-5-6-sol` and can be overridden with `--evaluation-reference-model MODEL_SLUG`. The selected reference model's non-null evaluations define a consistent schema; requested models return `null` where they have no reported result.

Evaluation keys include GDPval-AA, normalized GDPval-AA, tau2, tau-bench Banking, Terminal-Bench Hard, Terminal-Bench v2.1, SciCode, Humanity's Last Exam, GPQA Diamond, CritPt, AA-Omniscience, AA Long Context Reasoning, IFBench, APEX Agents, ITBench SRE, MMMU-Pro, LiveCodeBench, and AIME 2025.

The pre-v2 scripts are retained under `legacy/` for compatibility:

```bash
uv run legacy/artificial_analysis_single_model.py gpt-5-6-sol
uv run legacy/artificial_analysis_models.py gpt-5-6-sol,gpt-5-6-terra-low
```

### Identity and metadata

- slug, name, short name, creator and release date
- reasoning, open-weights and deprecation status
- replacement model, host-model count and performance-data source
- knowledge cutoff, parameter count, active parameters and size class
- context window and supported input/output modalities
- licence, commercial-use status, open-source category and weights source
- input, output, cache-hit, cache-write, blended-token and image prices
- cache-hit discount

### Intelligence Index

- Intelligence Index score and estimated-score status
- individual evaluation scores and nested benchmark detail
- cost per task with aggregate input, answer, reasoning, cache-write and cache-hit components
- each evaluation's weighted contribution to cost per task
- total index-run cost with token-category components
- input tokens per task
- total, answer and reasoning output tokens per task
- canonical input/output/answer/reasoning token totals for the complete index run
- time per task

### Response performance

- median output speed and its p05, p25, median, p75 and p95 distribution
- time to first token and its percentile distribution
- time to first answer token with input and reasoning components
- end-to-end response time with input, reasoning and answer components
- performance by prompt type, including the available medium, long, 100K-context and parallel measurements
- available performance time-series data

### Coding Index

- Coding Index score, weighted index and component subscores where available
- cost per task with aggregate input, answer, reasoning, cache-write and cache-hit components
- total Coding Index run cost with token-category components
- time per task
- total, answer and reasoning output tokens per task

### Source records

`source_record.general` and `source_record.coding` retain the canonical records used to produce the normalized fields. This preserves newly introduced or currently unnormalized parameters in historical outputs.

The command fails rather than returning a partial result when required records are unavailable for any requested model.

## Efficiency explorer

`index.html` is a standalone interactive comparison of capability against cost, duration, token use, and a blended resource index.
