#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
SKILL_DIR="${SCRIPT_DIR:h}"
ROOT="${ROOT:-$PWD}"
LOG_DIR="${LOG_DIR:-$ROOT/run_logs}"

WORKFLOW="${WORKFLOW:-outstanding-equity-awards}"
BATCH_DIR="${BATCH_DIR:-}"
WAVE_MANIFEST="${WAVE_MANIFEST:-${BATCH_DIR:+$BATCH_DIR/wave_manifest.csv}}"
PARALLELISM="${PARALLELISM:-20}"
MODEL="${MODEL:-gpt-5.4}"
REASONING_EFFORT="${REASONING_EFFORT:-medium}"
START_WAVE="${START_WAVE:-1}"
END_WAVE="${END_WAVE:-}"
CODEX_BIN="${CODEX_BIN:-$(command -v codex || true)}"

case "$WORKFLOW" in
  outstanding-equity-awards)
    PROMPT_FILE="${PROMPT_FILE:-$SKILL_DIR/references/outstanding-equity-awards/Outstanding-Equity-Awards-Chunk-Thread-Prompt-V1.txt}"
    OUTPUT_SUFFIX_A="_outstanding_equity_awards.csv"
    OUTPUT_SUFFIX_B="_report.csv"
    ;;
  summary-compensation-table)
    PROMPT_FILE="${PROMPT_FILE:-$SKILL_DIR/references/summary-compensation-table/Summary-Compensation-Table-Chunk-Thread-Prompt-V3.txt}"
    OUTPUT_SUFFIX_A="_compensation_table_master.csv"
    OUTPUT_SUFFIX_B="_report.csv"
    ;;
  beneficial-ownership)
    PROMPT_FILE="${PROMPT_FILE:-$SKILL_DIR/references/beneficial-ownership/Beneficial-Ownership-Chunk-Thread-Prompt-V1.txt}"
    OUTPUT_SUFFIX_A="_beneficial_ownership.csv"
    OUTPUT_SUFFIX_B="_report.csv"
    ;;
  *)
    echo "Unsupported WORKFLOW: $WORKFLOW" >&2
    exit 1
    ;;
esac

render_progress_line() {
  local progress_dir="$1"
  local total_chunks="$2"
  python3 - "$progress_dir" "$total_chunks" <<'PY'
import sys
from pathlib import Path

progress_dir = Path(sys.argv[1])
total_chunks = int(sys.argv[2])
counts = {"running": 0, "done": 0, "skipped": 0, "failed": 0}
for path in progress_dir.glob("*.status"):
    state = path.read_text().strip()
    if state in counts:
        counts[state] += 1
finished = counts["done"] + counts["skipped"] + counts["failed"]
pending = max(total_chunks - finished - counts["running"], 0)
print(
    f"Progress {finished}/{total_chunks} "
    f"(running={counts['running']}, done={counts['done']}, "
    f"skipped={counts['skipped']}, failed={counts['failed']}, pending={pending})",
    end="",
)
PY
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Run DEF 14A table extraction chunk workers using a prebuilt wave manifest.

Required:
  BATCH_DIR=/abs/path/to/batch

Common overrides:
  WORKFLOW=outstanding-equity-awards
  WORKFLOW=summary-compensation-table
  WORKFLOW=beneficial-ownership
  PARALLELISM=20
  MODEL=gpt-5.4
  REASONING_EFFORT=medium
  START_WAVE=1
  END_WAVE=1

The selected workflow controls the bundled chunk prompt and expected output files.
EOF
  exit 0
fi

if [[ -z "$BATCH_DIR" ]]; then
  echo "Set BATCH_DIR to a batch folder created by create_def14a_batch.py" >&2
  exit 1
fi

if [[ ! -f "$WAVE_MANIFEST" ]]; then
  echo "Wave manifest not found: $WAVE_MANIFEST" >&2
  exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

if [[ -z "$CODEX_BIN" || ! -x "$CODEX_BIN" ]]; then
  echo "Codex binary not found or not executable: $CODEX_BIN" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"

wave_lines=("${(@f)$(python3 - "$WAVE_MANIFEST" "$START_WAVE" "$END_WAVE" <<'PY'
import csv
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
start_wave = int(sys.argv[2])
end_wave = int(sys.argv[3]) if sys.argv[3] else None
with manifest_path.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
selected = []
for row in rows:
    wave_num = int(row["Wave Number"])
    if wave_num < start_wave:
        continue
    if end_wave is not None and wave_num > end_wave:
        continue
    selected.append("\t".join([
        row["Wave Number"],
        row["Wave File"],
        row["Chunks In Wave"],
        row["Total Filings In Wave"],
        row["Wave Path"],
    ]))
print("\n".join(selected))
PY
)}")

if (( ${#wave_lines[@]} == 0 )); then
  echo "No waves selected from $WAVE_MANIFEST" >&2
  exit 1
fi

echo "Workflow: $WORKFLOW"
echo "Batch dir: $BATCH_DIR"
echo "Wave manifest: $WAVE_MANIFEST"
echo "Prompt file: $PROMPT_FILE"
echo "Log dir: $LOG_DIR"
echo "Parallelism: $PARALLELISM"
echo "Model: $MODEL"
echo "Reasoning effort: $REASONING_EFFORT"

for wave_line in "${wave_lines[@]}"; do
  IFS=$'\t' read -r wave_num wave_file chunks_in_wave total_filings wave_path <<< "$wave_line"
  echo ""
  echo "Wave $wave_num: $chunks_in_wave chunk(s), $total_filings filing(s)"
  echo "Wave file: $wave_file"
  read "reply?Run this wave? [y/N]: "
  if [[ ! "$reply" =~ ^[Yy]$ ]]; then
    echo "Stopped before running wave $wave_num."
    exit 0
  fi

  chunk_paths=("${(@f)$(python3 - "$wave_path" <<'PY'
import csv
import sys
from pathlib import Path

wave_path = Path(sys.argv[1])
with wave_path.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
for row in rows:
    print(row["Chunk Path"])
PY
)}")

  total_chunks_in_wave=${#chunk_paths[@]}
  progress_dir="$(mktemp -d "${TMPDIR:-/tmp}/def14a-wave-${wave_num}-XXXXXX")"

  printf '%s\0' "${chunk_paths[@]}" | \
    xargs -0 -n 1 -P "$PARALLELISM" -I {} bash -lc '
      chunk="$1"
      root="$2"
      prompt_file="$3"
      codex_bin="$4"
      model="$5"
      reasoning_effort="$6"
      progress_dir="$7"
      output_suffix_a="$8"
      output_suffix_b="$9"

      base="$(basename "$chunk" .csv)"
      outdir="$(dirname "$chunk")"
      output_a="${outdir}/${base}${output_suffix_a}"
      output_b="${outdir}/${base}${output_suffix_b}"
      final_log="${root}/run_logs/${base}.final.txt"
      event_log="${root}/run_logs/${base}.jsonl"
      status_file="${progress_dir}/${base}.status"

      if [ -f "$output_a" ] && [ -f "$output_b" ]; then
        printf "skipped\n" > "$status_file"
        exit 0
      fi

      printf "running\n" > "$status_file"
      prompt="$(<"$prompt_file")"
      prompt="${prompt//\[CHUNK_FILENAME\]/$chunk}"

      cmd=("$codex_bin" exec --skip-git-repo-check -s danger-full-access -C "$root" -o "$final_log")
      if [ -n "$model" ]; then
        cmd+=(-m "$model")
      fi
      if [ -n "$reasoning_effort" ]; then
        cmd+=(-c "model_reasoning_effort=\"$reasoning_effort\"")
      fi
      cmd+=("$prompt")

      if "${cmd[@]}" > "$event_log" 2>&1; then
        if [ -f "$output_a" ] && [ -f "$output_b" ]; then
          printf "done\n" > "$status_file"
        else
          printf "failed\n" > "$status_file"
          printf "\n[runner] codex exited successfully but expected chunk outputs were not created.\n" >> "$event_log"
          exit 1
        fi
      else
        printf "failed\n" > "$status_file"
        exit 1
      fi
    ' _ {} "$ROOT" "$PROMPT_FILE" "$CODEX_BIN" "$MODEL" "$REASONING_EFFORT" "$progress_dir" "$OUTPUT_SUFFIX_A" "$OUTPUT_SUFFIX_B" &
  wave_job_pid=$!

  while kill -0 "$wave_job_pid" 2>/dev/null; do
    progress_line="$(render_progress_line "$progress_dir" "$total_chunks_in_wave")"
    printf '\rWave %s %s' "$wave_num" "$progress_line"
    sleep 2
  done

  if wait "$wave_job_pid"; then
    wave_rc=0
  else
    wave_rc=$?
  fi
  progress_line="$(render_progress_line "$progress_dir" "$total_chunks_in_wave")"
  printf '\rWave %s %s\n' "$wave_num" "$progress_line"
  rm -rf "$progress_dir"

  if (( wave_rc != 0 )); then
    echo "Wave $wave_num failed. Check run_logs/ for chunk logs." >&2
    exit "$wave_rc"
  fi
  echo "Wave $wave_num finished."
done

echo "All selected waves completed."
