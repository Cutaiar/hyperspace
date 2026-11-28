"""Per-agent metrics for a workflow run: time, turns, messages, tool calls,
context at start and at peak, and which tools filled it.

    python3 .claude/workflows/agent_metrics.py <transcript_dir> [--json OUT]

The transcript dir is printed when the workflow launches.
"""
import glob
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def analyse(path):
    meta_p = Path(str(path).replace(".jsonl", ".meta.json"))
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    rows = [json.loads(l) for l in open(path)]
    times = [ts(r["timestamp"]) for r in rows if r.get("timestamp")]
    turns = {}            # message id -> usage (dedupe streamed blocks)
    tool_calls = Counter()
    tool_ids = {}
    result_chars = Counter()
    result_max = defaultdict(int)
    user_msgs = 0
    for r in rows:
        m = r.get("message")
        if r["type"] == "assistant" and isinstance(m, dict):
            if m.get("usage"):
                turns[m.get("id", r["uuid"])] = m["usage"]
            for c in m.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    if c["id"] not in tool_ids:
                        tool_ids[c["id"]] = c["name"]
                        tool_calls[c["name"]] += 1
        elif r["type"] == "user" and isinstance(m, dict):
            user_msgs += 1
            for c in m.get("content") if isinstance(m.get("content"), list) else []:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    n = len(json.dumps(c.get("content")))
                    name = tool_ids.get(c.get("tool_use_id"), "?")
                    result_chars[name] += n
                    result_max[name] = max(result_max[name], n)
    ctx = [u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
           + u.get("cache_read_input_tokens", 0) for u in turns.values()]
    out_tok = sum(u.get("output_tokens", 0) for u in turns.values())
    created = sum(u.get("cache_creation_input_tokens", 0) for u in turns.values())
    read = sum(u.get("cache_read_input_tokens", 0) for u in turns.values())
    return {
        "label": meta.get("description", path.name), "phase": meta.get("workflowPhase"),
        "model": meta.get("model"),
        "seconds": round((max(times) - min(times)).total_seconds()) if times else 0,
        "turns": len(turns), "messages": len(turns) + user_msgs,
        "tool_calls": sum(tool_calls.values()), "tools": dict(tool_calls.most_common()),
        "ctx_first": ctx[0] if ctx else 0, "ctx_peak": max(ctx) if ctx else 0,
        "ctx_growth": (max(ctx) - ctx[0]) if ctx else 0,
        "output_tokens": out_tok, "cache_created": created, "cache_read": read,
        "tool_result_kchars": {k: round(v / 1000, 1) for k, v in result_chars.most_common()},
        "largest_result_kchars": {k: round(v / 1000, 1) for k, v in sorted(result_max.items(), key=lambda x: -x[1])[:3]},
        "start": min(times).isoformat() if times else None,
    }


def main():
    d = Path(sys.argv[1])
    rows = sorted((analyse(Path(p)) for p in glob.glob(str(d / "agent-*.jsonl"))),
                  key=lambda r: r["start"] or "")
    hdr = f"{'agent':34} {'phase':10} {'sec':>5} {'turns':>5} {'msgs':>5} {'tools':>5} {'ctx0 k':>7} {'peak k':>7} {'grow k':>7} {'out k':>6}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['label'][:34]:34} {str(r['phase'])[:10]:10} {r['seconds']:>5} {r['turns']:>5} {r['messages']:>5} "
              f"{r['tool_calls']:>5} {r['ctx_first']/1000:>7.1f} {r['ctx_peak']/1000:>7.1f} {r['ctx_growth']/1000:>7.1f} {r['output_tokens']/1000:>6.1f}")
    tot = lambda k: sum(r[k] for r in rows)  # noqa: E731
    print("-" * len(hdr))
    print(f"{'TOTAL':34} {'':10} {tot('seconds'):>5} {tot('turns'):>5} {tot('messages'):>5} {tot('tool_calls'):>5} "
          f"{'':>7} {'':>7} {'':>7} {tot('output_tokens')/1000:>6.1f}")
    print(f"\ncache created {tot('cache_created')/1e6:.2f}M tok, cache read {tot('cache_read')/1e6:.2f}M tok")
    print("\nwhere context came from (tool result kchars) per agent:")
    for r in rows:
        print(f"  {r['label'][:34]:34} {r['tools']}  results={r['tool_result_kchars']}  largest={r['largest_result_kchars']}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(rows, indent=1))


main()
