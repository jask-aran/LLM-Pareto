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

### Output selection

The default output is a compact comparison record close to the original cost-per-task format. It includes model identity, Intelligence and Coding Index scores, their cost breakdowns, token use, time per task, response speed, end-to-end time, time to first answer token, and release date.

Select particular dotted fields:

```bash
uv run artificial_analysis_v2.py gpt-5-6-sol \
  --fields slug,name,intelligence_index,cost_per_task,coding_index
```

Named groups can be combined with field paths:

```bash
uv run artificial_analysis_v2.py gpt-5-6-sol \
  --fields identity,cost,timing,evaluations
```

Available groups are `identity`, `summary`, `cost`, `tokens`, `timing`, `evaluations`, `coding`, `metadata`, `performance`, and `source`.

Return the complete normalized and canonical records:

```bash
uv run artificial_analysis_v2.py gpt-5-6-sol --verbose
```

`--fields` and `--verbose` are mutually exclusive. Unknown field paths fail explicitly.

### Model catalogue

Return dated model candidates without requesting each model separately:

```bash
uv run artificial_analysis_v2.py --list-models
uv run artificial_analysis_v2.py --list-models --eligibility full
uv run artificial_analysis_v2.py --list-models --since 2026-07-01
uv run artificial_analysis_v2.py --list-models --include-deprecated
```

Eligibility modes are `all`, `active`, `general`, `coding`, and `full`. Catalogue records include release date and flags for Intelligence Index, general cost, Coding Index, and coding cost availability. Typed canonical-record rules keep chart-specific representations out of the catalogue; conflicting equally complete canonical records fail rather than being selected silently.

### Coding Agent Index

Coding-agent results are represented as harness-model configurations with a stable configuration `id`, rather than as model slugs.

Return all configurations:

```bash
uv run artificial_analysis_v2.py --coding-agents
```

Select a configuration by stable ID or exact display label:

```bash
uv run artificial_analysis_v2.py \
  --coding-agent 6eb6667a6c986c2afc40c779a1666e5a
```

Each default record includes harness, provider, host model, composite score, component benchmark scores, cost, active wall time, steps, token usage and cache-hit rate. `--fields` and `--verbose` apply to coding-agent records as well. Verbose records additionally retain distributions, harness versions, display metadata, total cost and the canonical source record.

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
