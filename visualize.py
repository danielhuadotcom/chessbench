import argparse
import html
import json
from collections import defaultdict
from pathlib import Path

from tabulate import tabulate


def load_results(filepath):
    results = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def latest_run_log():
    run_logs = sorted(Path("run_logs").glob("[0-9]*.jsonl"))
    if not run_logs:
        raise FileNotFoundError("No .jsonl files found in run_logs/")
    return run_logs[-1]


def count_moves(result):
    assistant_msgs = sum(1 for m in result["messages"] if m["role"] == "assistant")
    return assistant_msgs - result["illegals"]


def aggregate(runs):
    n = len(runs)
    wins = sum(1 for r in runs if r["success"])
    avg_ill = sum(r["illegals"] for r in runs) / n
    avg_cost = sum(r["cost"] for r in runs) / n
    avg_moves = sum(count_moves(r) for r in runs) / n
    return wins, n, avg_ill, avg_cost, avg_moves


def group_results(results):
    grouped = defaultdict(list)
    for r in results:
        grouped[(r["starting_position_description"], r["modelstring"])].append(r)
    positions = list(dict.fromkeys(r["starting_position_description"] for r in results))
    models = list(dict.fromkeys(r["modelstring"] for r in results))
    return grouped, positions, models


def build_cli_table(grouped, positions, models):
    table = []
    for pos in positions:
        row = [pos]
        for model in models:
            wins, n, avg_ill, avg_cost, avg_moves = aggregate(grouped[(pos, model)])
            pct = f"{wins * 100 // n}% winrate"
            detail = f"Avg: {avg_ill:.1f} illegal, {avg_moves:.0f} moves, ${avg_cost:.4f}"
            row.append(f"{pct} | {detail}")
        table.append(row)
    return table


def format_messages_html(messages):
    lines = []
    for m in messages:
        role = html.escape(m["role"])
        content = ""
        if m["content"]:
            content = html.escape(m["content"]).replace("\n", "<br>")
        lines.append(f"<b>{role}:</b> {content}")
    return "<br>".join(lines)


def build_html(grouped, positions, models, samples, filename):
    header_cells = "<th>Position</th>" + "".join(
        f"<th>{html.escape(m)}</th>" for m in models
    )

    body_rows = []
    for pos in positions:
        cells = [f"<td><b>{html.escape(pos)}</b></td>"]
        for model in models:
            runs = grouped[(pos, model)]
            wins, n, avg_ill, avg_cost, avg_moves = aggregate(runs)
            pct = wins * 100 // n

            sample_details = []
            for i, r in enumerate(runs, 1):
                outcome = "Win" if r["success"] else "Failure"
                summary = f"Sample {i}: {outcome} ({count_moves(r)} moves, {r['illegals']} illegal, ${r['cost']:.4f})"
                sample_details.append(
                    f'<details><summary>{html.escape(summary)}</summary>'
                    f'<div class="messages">{format_messages_html(r["messages"])}</div>'
                    f"</details>"
                )

            cell = (
                f'<div class="cell">'
                f"<div class=\"winrate\">{pct}% winrate</div>"
                f"<div class=\"averages\">Averages: {avg_moves:.1f} total moves, {avg_ill:.1f} illegal moves, ${avg_cost:.4f} cost</div>"
                f'<div class="samples">{"".join(sample_details)}</div>'
                f"</div>"
            )
            cells.append(f"<td>{cell}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Chessbench Results - {html.escape(filename)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f8f8f8; }}
h1 {{ font-size: 1.3rem; }}
table {{ border-collapse: collapse; width: 100%; background: white; }}
th, td {{ border: 1px solid #ccc; padding: 10px 14px; text-align: left; vertical-align: top; }}
th {{ background: #333; color: white; }}
tr:nth-child(even) {{ background: #f4f4f4; }}
.winrate {{ font-size: 1.2rem; font-weight: bold; margin-bottom: 4px; }}
.averages {{ color: #555; margin-bottom: 8px; }}
details {{ margin: 2px 0; }}
summary {{ cursor: pointer; font-size: 0.9rem; }}
.messages {{ margin: 8px 0 8px 12px; padding: 8px; background: #f0f0f0; border-radius: 4px;
             font-family: monospace; font-size: 0.8rem; line-height: 1.5; max-height: 400px; overflow-y: auto; }}
</style>
</head>
<body>
<h1>Chessbench Results ({html.escape(filename)}, {samples} samples/scenario)</h1>
<table>
<thead><tr>{header_cells}</tr></thead>
<tbody>{''.join(body_rows)}</tbody>
</table>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", help="Path to a .jsonl run log")
    args = parser.parse_args()

    filepath = Path(args.file) if args.file else latest_run_log()
    results = load_results(filepath)
    grouped, positions, models = group_results(results)
    samples = len(results) // (len(positions) * len(models)) if positions and models else 0

    cli_table = build_cli_table(grouped, positions, models)
    print(f"Chessbench Results ({filepath.name}, {samples} samples/scenario)\n")
    print(tabulate(cli_table, headers=["Position"] + models, tablefmt="simple_outline"))

    html_path = filepath.with_suffix(".html")
    html_path.write_text(build_html(grouped, positions, models, samples, filepath.name))
    print(f"\nHTML report saved to {html_path}")


if __name__ == "__main__":
    main()
