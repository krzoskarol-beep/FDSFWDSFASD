#!/usr/bin/env bash
# Porównuje Lightpanda i Chromium: ten sam skrypt Puppeteera (scrape.mjs),
# czas na stronę i szczytowa pamięć RSS przeglądarki (Linux, z /proc).
#
#   ./bench.sh [liczba_załadowań] [tryby...]     np. ./bench.sh 50 lightpanda chrome
#
# Bez zmiennej URL uruchamia lokalną stronę demo z ./site (python3 -m http.server).
set -euo pipefail

DIR=$(cd "$(dirname "$0")" && pwd)
N=${1:-50}; shift || true
if [ $# -gt 0 ]; then MODES=("$@"); else MODES=(lightpanda chrome); fi
SITE_PORT=${SITE_PORT:-8811}
LP_PORT=${LP_PORT:-9222}
LP_BIN=${LP_BIN:-$DIR/bin/lightpanda}
export LIGHTPANDA_DISABLE_TELEMETRY=true
export LIGHTPANDA_WS="ws://127.0.0.1:$LP_PORT"

PIDS=()
cleanup() { for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT

# Lightpanda: pobierz nightly, jeśli nie ma binarki.
if [[ " ${MODES[*]} " == *" lightpanda "* && ! -x "$LP_BIN" ]]; then
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)  ASSET=lightpanda-x86_64-linux ;;
    Linux-aarch64) ASSET=lightpanda-aarch64-linux ;;
    Darwin-arm64)  ASSET=lightpanda-aarch64-macos ;;
    Darwin-x86_64) ASSET=lightpanda-x86_64-macos ;;
    *) echo "Brak gotowej binarki dla $(uname -sm); ustaw LP_BIN." >&2; exit 1 ;;
  esac
  echo "Pobieram $ASSET (nightly)…" >&2
  mkdir -p "$(dirname "$LP_BIN")"
  curl -fsSL -o "$LP_BIN" "https://github.com/lightpanda-io/browser/releases/download/nightly/$ASSET"
  chmod +x "$LP_BIN"
fi

wait_port() { for _ in $(seq 50); do (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && return 0; sleep 0.1; done; return 1; }

[ -d "$DIR/node_modules/puppeteer-core" ] || (cd "$DIR" && PUPPETEER_SKIP_DOWNLOAD=1 npm install --silent)

# Lokalna strona demo, chyba że podano własny URL.
if [ -z "${URL:-}" ]; then
  python3 -m http.server "$SITE_PORT" --bind 127.0.0.1 --directory "$DIR/site" >/dev/null 2>&1 &
  PIDS+=($!)
  export URL="http://127.0.0.1:$SITE_PORT/"
  wait_port "$SITE_PORT" || { echo "Strona demo nie wystartowała" >&2; exit 1; }
fi

# Suma VmRSS procesu i wszystkich jego potomków (KB). Z drugim argumentem
# "children" pomija sam proces (dla Chromium: nie liczy procesu node).
# Pamięć współdzielona między procesami Chromium liczy się kilka razy,
# więc dla niego to górne oszacowanie.
tree_rss() {
  local pids=("$1") all=() p kb=0 r
  while [ ${#pids[@]} -gt 0 ]; do
    p=${pids[0]}; pids=("${pids[@]:1}"); all+=("$p")
    for c in $(cat /proc/"$p"/task/*/children 2>/dev/null); do pids+=("$c"); done
  done
  [ "${2:-}" = children ] && all=("${all[@]:1}")
  for p in "${all[@]}"; do
    r=$(awk '/^VmRSS/{print $2}' /proc/"$p"/status 2>/dev/null || true); kb=$((kb + ${r:-0}))
  done
  echo "$kb"
}

for MODE in "${MODES[@]}"; do
  ROOT=""
  if [ "$MODE" = lightpanda ]; then
    "$LP_BIN" serve --host 127.0.0.1 --port "$LP_PORT" --log-level error >/dev/null 2>&1 &
    ROOT=$!; PIDS+=("$ROOT")
    wait_port "$LP_PORT" || { echo "Lightpanda nie wystartowała" >&2; exit 1; }
  fi

  OUT=$(mktemp)
  node "$DIR/scrape.mjs" "$MODE" "$N" >"$OUT" &
  JOB=$!
  peak=0
  while kill -0 "$JOB" 2>/dev/null; do
    if [ -d /proc ]; then
      if [ "$MODE" = lightpanda ]; then r=$(tree_rss "$ROOT"); else r=$(tree_rss "$JOB" children); fi
      [ "$r" -gt "$peak" ] && peak=$r
    fi
    sleep 0.05
  done
  wait "$JOB"
  echo "$(cat "$OUT") peak_rss_mb=$((peak / 1024))"
  rm -f "$OUT"

  if [ -n "$ROOT" ]; then kill "$ROOT" 2>/dev/null || true; wait "$ROOT" 2>/dev/null || true; fi
done
