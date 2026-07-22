# LLM-Pareto

Tools for comparing model capability, task cost, token use, response time, and coding-agent configurations.

## Running the CLI with uv

`artificial_analysis_v2.py` uses only the Python standard library. There are no packages to install.

Run it directly through `uv`:

```bash
uv run artificial_analysis_v2.py --help
```

Optionally select a Python version:

```bash
uv run --python 3.12 artificial_analysis_v2.py --help
```

The pre-v2 commands remain under `legacy/`:

```bash
uv run legacy/artificial_analysis_single_model.py gpt-5-6-sol
uv run legacy/artificial_analysis_models.py gpt-5-6-sol,gpt-5-6-terra-low
```

## CLI modes

The command has three mutually exclusive modes:

1. model details from one or more positional slugs;
2. the model catalogue through `--list-models`;
3. Coding Agent Index configurations through `--coding-agents` or `--coding-agent`.

Every successful response contains `schema_version`, `status`, and a UTC `collected_at` system timestamp. Each detailed model or coding-agent record uses the same timestamp as its containing response.

### Model details

One model returns `data.model`:

```bash
uv run artificial_analysis_v2.py gpt-5-6-sol
```

Multiple comma-separated or space-separated slugs return `data.models` in requested order:

```bash
uv run artificial_analysis_v2.py \
  gpt-5-6-terra-low,gpt-5-6-sol-high gpt-5-6-sol-xhigh
```

Duplicate slugs are removed. The request fails rather than returning a partial collection when a required record is unavailable for any requested model.

#### Default model output

The default is a compact comparison record close to the original cost-per-task output:

- `collected_at`, `slug`, `name`, `short_name`
- `intelligence_index`
- `cost_per_task` and `cost_per_task_breakdown`
- input, answer-output and reasoning-output tokens per task
- `time_per_task`
- `output_speed_tokens_per_second`
- `end_to_end_response_time`
- `time_to_first_answer_token`
- `coding_index`
- `coding_cost_per_task` and `coding_cost_per_task_breakdown`
- `coding_time_per_task`
- `model_metadata.release_date`

The response metadata also includes requested and returned counts, source URLs, the evaluation reference model, the active evaluation field set, and the selected output fields.

#### Verbose model output

`--verbose` returns every normalized field plus the canonical source records:

```bash
uv run artificial_analysis_v2.py gpt-5-6-sol --verbose
```

This adds:

- complete Intelligence and Coding Index cost totals and breakdowns;
- evaluation scores and each evaluation's weighted cost contribution;
- canonical token totals and answer/reasoning token splits;
- output-speed and first-token percentile distributions;
- first-answer and end-to-end timing components;
- performance by prompt type and available time-series data;
- nested benchmark details and result-status fields;
- release, lineage, modality, context, licensing and pricing metadata;
- `source_record.general` and `source_record.coding`.

### Model catalogue

The catalogue discovers dated candidates without requesting each model separately:

```bash
uv run artificial_analysis_v2.py --list-models
```

#### Default catalogue output

The default catalogue is deliberately minimal:

- `slug`
- `short_name`
- `release_date`

It excludes deprecated models by default and sorts newest releases first.

Filter by data availability:

```bash
uv run artificial_analysis_v2.py --list-models --eligibility full
```

Eligibility modes are:

- `all`: every canonical dated model allowed by the deprecation filter;
- `active`: non-deprecated models, the default;
- `general`: models with complete general cost data;
- `coding`: models with complete Coding Index cost data;
- `full`: models with complete general and Coding Index cost data.

Filter by release date or include historical models:

```bash
uv run artificial_analysis_v2.py --list-models --since 2026-07-01
uv run artificial_analysis_v2.py --list-models --include-deprecated
```

#### Verbose catalogue output

```bash
uv run artificial_analysis_v2.py --list-models --verbose
```

Verbose catalogue entries add full identity, creator, reasoning/open-weight/deprecation status, general and coding availability flags, and the canonical general and coding records.

Typed canonical-record rules keep chart-specific representations out of the catalogue. Conflicting equally complete canonical records fail instead of being selected silently.

### Coding Agent Index

Coding-agent results are harness-model configurations rather than ordinary model slugs. Their stable primary identity is the configuration `id`; harness and host model are separate dimensions.

Return all configurations:

```bash
uv run artificial_analysis_v2.py --coding-agents
```

`--list-coding-agents` is an alias for the same command.

Select one or more configurations by stable ID or exact display label:

```bash
uv run artificial_analysis_v2.py \
  --coding-agent 6eb6667a6c986c2afc40c779a1666e5a
```

Repeat `--coding-agent` to select several configurations.

#### Default coding-agent output

- `id`, `display_label`, `agent_name`, `host_model_slug`
- aggregate Coding Agent Index score
- DeepSWE, Terminal-Bench v2 and SWE-Atlas-QnA component scores and token means
- cost per task
- active agent wall time per task
- output and total tokens per task

#### Verbose coding-agent output

```bash
uv run artificial_analysis_v2.py --coding-agents --verbose
```

Verbose records additionally contain provider and display metadata, variant relationship, component/evaluation counts, steps, input/cache/output token fields, cache-hit rate, total evaluation cost, cost/token percentiles, harness versions per benchmark, and the canonical source record.

## Selecting output fields

`--fields` accepts comma-separated dotted paths, repeated flags, named groups, or a mixture:

```bash
uv run artificial_analysis_v2.py gpt-5-6-sol \
  --fields slug,name,intelligence_index,cost_per_task,coding_index
```

```bash
uv run artificial_analysis_v2.py gpt-5-6-sol \
  --fields identity,cost,timing,evaluations
```

```bash
uv run artificial_analysis_v2.py --coding-agents \
  --fields id,display_label,index_score,percentiles
```

Named model groups are:

- `identity`
- `summary`
- `cost`
- `tokens`
- `timing`
- `evaluations`
- `coding`
- `metadata`
- `performance`
- `source`

Unknown paths fail explicitly. `--fields` and `--verbose` are mutually exclusive.

## Flags

| Flag | Use |
|---|---|
| positional `slugs` | Select one or more model slugs. |
| `--list-models` | Return the dated model catalogue. |
| `--eligibility all\|active\|general\|coding\|full` | Filter catalogue candidates by available data. |
| `--include-deprecated` | Allow deprecated models in catalogue results. |
| `--since YYYY-MM-DD` | Include catalogue entries released on or after the date. |
| `--coding-agents`, `--list-coding-agents` | Return all Coding Agent Index configurations. |
| `--coding-agent VALUE` | Select a configuration by ID or exact display label; repeatable. |
| `--evaluation-reference-model SLUG` | Change the model whose non-null evaluations define the detailed-model evaluation schema. Defaults to `gpt-5-6-sol`. |
| `--fields PATHS` | Return explicit dotted fields or named groups; repeatable. |
| `--verbose` | Return all normalized and canonical fields. |
| `--compact` | Emit JSON without indentation. |
| `--timeout SECONDS` | Set the HTTP timeout; defaults to 30 seconds. |
| `-h`, `--help` | Show CLI help. |

## Planned SQLite archive

Keep persistence separate from collection. A future `archive.py` should import functions from `artificial_analysis_v2.py`, run a small fixed set of collection jobs, and write append-only snapshots with the standard-library `sqlite3` module. It should not invoke the CLI as a subprocess.

The collection jobs can remain ordinary Python configuration, for example:

- active model catalogue;
- verbose details for newly eligible or changed model slugs, batched in small groups;
- verbose Coding Agent Index collection.

The CLI's compact defaults are presentation choices. The archiver should always request verbose records so historical data is not discarded.

A minimal database needs only two tables:

- `collection_runs`: run ID, timestamp, entity type, schema version and job configuration;
- `snapshots`: run ID, entity type, stable entity ID, release date, canonical JSON payload and payload hash.

Use model slug as the model entity ID and coding-agent configuration ID as the coding-agent entity ID. Write one transaction per collection run, index snapshots by entity type/ID and collection time, and use a SHA-256 payload hash to detect unchanged records. More normalized tables can be added only when an actual query requires them.

## Efficiency explorer

`index.html` is a standalone interactive comparison of capability against cost, duration, token use, and a blended resource index.
