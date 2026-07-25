#!/usr/bin/env bash
set -euo pipefail

# Update leaderboard.json from DeepSWE Datacurve's live leaderboard.
# Usage: ./update.sh
# Output: overwrites leaderboard.json with transformed data.

URL="https://deepswe.datacurve.ai/artifacts/v1.1/leaderboard-live.json"
OUT="leaderboard.json"

curl -sfL "$URL" | python3 -c "
import json, sys

data = json.load(sys.stdin)
rows = data['rows']

# Transform to the schema expected by index.html
out = []
for r in rows:
    out.append({
        'model': r['model'],
        'effort': r['reasoning_effort'] or 'default',
        'p1': r['pass_at_1'],
        'p4': r['pass_at_4'],
        'cost': r['mean_cost_usd'],
        'dur': r['mean_duration_seconds'],
        'outTok': r['mean_output_tokens'],
        'inTok': r['mean_input_tokens'],
        'steps': r['mean_agent_steps'],
    })

# Sort by model then by effort order (same as JS)
effort_order = {'low': 0, 'medium': 1, 'high': 2, 'xhigh': 3, 'max': 4, 'default': 2}
out.sort(key=lambda r: (r['model'], effort_order.get(r['effort'], 5)))

with open('$OUT', 'w') as f:
    json.dump(out, f, indent=2)

print(f'Wrote {len(out)} configs to $OUT')
print(f'Generated at: {data.get(\"generated_at\", \"unknown\")}')
"
