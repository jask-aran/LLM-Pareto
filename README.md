# LLM-Pareto

Small tools for comparing model capability, task cost, token use, and response-time trade-offs.

## Model data scripts

The scripts require Python 3 and use only the standard library.

Single model:

```bash
python artificial_analysis_single_model.py gpt-5-6-terra-low
```

Multiple models from two shared page requests:

```bash
python artificial_analysis_models.py \
  gpt-5-6-terra-low,gpt-5-6-sol-high,gpt-5-6-sol-xhigh
```

`EVALUATION_REFERENCE_MODEL` near the top of each script controls which model defines the archived evaluation set. It defaults to `gpt-5-6-sol`. The multi-model command also accepts `--evaluation-reference-model MODEL_SLUG`.

### Identity and metadata

- `slug`, `name`, `short_name`
- `model_metadata.release_date`
- `model_metadata.creator`
- `model_metadata.is_reasoning`, `is_open_weights`, and `deprecated`
- `model_metadata.context_window_tokens`
- input, output, cache-hit, and cache-write prices per million tokens

### Intelligence Index

- `intelligence_index`
- `cost_per_task`
- `cost_per_task_breakdown`: aggregate input, answer output, reasoning output, cache write, and cache hit
- `intelligence_index_total_cost_breakdown`: total index-run cost with input and output components
- `input_tokens_per_task`
- `output_tokens_per_task`, `reasoning_tokens_per_task`
- `output_tokens_per_task_breakdown`: total, answer, and reasoning output tokens
- `time_per_task`
- `output_speed_tokens_per_second`
- `time_to_first_token` and its percentile distribution
- `time_to_first_answer_token` and its input/reasoning breakdown
- `end_to_end_response_time` and its input/reasoning/answer breakdown

### Intelligence evaluations

`intelligence_evaluations` uses the evaluation set reported for the configured reference model. Values remain `null` when a requested model has no reported result.

The supported evaluation keys include:

- GDPval-AA and its normalized score
- tau2 and tau-bench Banking
- Terminal-Bench Hard and Terminal-Bench v2.1
- SciCode
- Humanity's Last Exam
- GPQA Diamond
- CritPt
- AA-Omniscience
- AA Long Context Reasoning
- IFBench
- APEX Agents
- ITBench SRE
- MMMU-Pro
- LiveCodeBench
- AIME 2025

The active subset is returned as `evaluation_fields`, together with `evaluation_reference_model`.

### Coding Index

- `coding_index`
- `coding_cost_per_task`
- `coding_cost_per_task_breakdown`: aggregate input, answer output, reasoning output, cache write, and cache hit
- `coding_index_total_cost_breakdown`: total Coding Index run cost with input and output components
- `coding_time_per_task`
- `coding_output_tokens_per_task`: total, answer, and reasoning output tokens

### Multi-model response metadata

- `requested_count`, `returned_count`
- `sources.general`, `sources.coding`
- `evaluation_reference_model`, `evaluation_fields`

The multi-model command preserves requested order, removes duplicate slugs, and fails if either dataset lacks the fields required for any requested model.

## Efficiency explorer

`index.html` is a standalone interactive comparison of capability against cost, duration, token use, and a blended resource index.
