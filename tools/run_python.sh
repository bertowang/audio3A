#!/usr/bin/env bash
# 批量运行全书 Python 实验，生成 fig/*.svg 与 audio/*.wav。
# 用法:
#   ./tools/run_python.sh                      # 运行全部
#   ./tools/run_python.sh part1/05-adaptive-filter/code/05-nlms.py part2/12-*/code/*.py
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

SCRIPTS=()
if [ "$#" -eq 0 ]; then
  while IFS= read -r f; do
    SCRIPTS+=("$f")
  done < <(find part0 part1 part2 part3 part4 part5 part6 appendix \
    -path '*/code/*.py' -type f 2>/dev/null | sort)
else
  SCRIPTS=("$@")
fi

if [ "${#SCRIPTS[@]}" -eq 0 ]; then
  echo "没有找到任何 code/*.py 脚本" >&2
  exit 1
fi

ok=0
fail=0
for f in "${SCRIPTS[@]}"; do
  if [ ! -f "$f" ]; then
    echo "FAIL  $f (文件不存在)"
    fail=$((fail + 1))
    continue
  fi
  if out="$(python3 "$f" 2>&1)"; then
    last="$(printf '%s\n' "$out" | grep -v '\.svg' | tail -n 1)"
    printf 'OK    %-60s %s\n' "$f" "$last"
    ok=$((ok + 1))
  else
    printf 'FAIL  %s\n' "$f"
    printf '%s\n' "$out" | tail -n 12
    fail=$((fail + 1))
  fi
done

echo "---- 运行完成：成功 ${ok}，失败 ${fail} ----"
[ "$fail" -eq 0 ]
