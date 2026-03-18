#!/usr/bin/env bash
# 버전 체계 변경: vX.Y → v0.X.Y (개발단계 명시)
# 변경 파일: docs/STATUS.md, docs/CHANGELOG.md, docs/FEATURES.md, README.md, web/app.py

set -e
cd ~/smart_farm

echo "=== 버전 체계 변경 시작: vX.Y → v0.X.Y ==="

python3 << 'PYEOF'
import re, os

# ── 변경 규칙 ──────────────────────────────────────────────
# v4.1 → v0.4.1
# v4.0 → v0.4.0
# v3.8 → v0.3.8  ...  v3.0 → v0.3.0
# v2.0 → v0.2.0
# 단, 이미 v0. 으로 시작하는 것은 스킵
# ──────────────────────────────────────────────────────────

def convert_versions(text):
    # v2.x ~ v4.x 형태를 v0.2.x ~ v0.4.x 로 변환
    # 단 v0. 으로 시작하는 건 건드리지 않음
    return re.sub(
        r'\bv([2-4])\.(\d+(?:\.\d+)?)\b',
        lambda m: f'v0.{m.group(1)}.{m.group(2)}',
        text
    )

files = [
    'docs/STATUS.md',
    'docs/CHANGELOG.md',
    'docs/FEATURES.md',
    'README.md',
    'web/app.py',
]

for path in files:
    if not os.path.exists(path):
        print(f'⚠️  {path} 없음 - 스킵')
        continue
    with open(path, 'r', encoding='utf-8') as f:
        original = f.read()
    converted = convert_versions(original)
    if original == converted:
        print(f'ℹ️  {path} - 변경 없음')
    else:
        # 변경된 버전 목록 출력
        old_vers = set(re.findall(r'\bv[2-4]\.\d+(?:\.\d+)?\b', original))
        new_vers = set(re.findall(r'\bv0\.[2-4]\.\d+(?:\.\d+)?\b', converted))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(converted)
        print(f'✅ {path}')
        print(f'   변경: {sorted(old_vers)} → {sorted(new_vers)}')

print()
print('=== 변환 완료 ===')
PYEOF

# 문법 검사 (app.py)
python3 -m py_compile web/app.py && echo "✅ app.py 문법 OK" || echo "❌ app.py 문법 오류"

# git commit
git add docs/STATUS.md docs/CHANGELOG.md docs/FEATURES.md README.md web/app.py
git commit -m "chore: 버전 체계 변경 vX.Y → v0.X.Y (개발단계 명시)

모든 버전 번호에 0. 접두사 추가:
  v2.0  → v0.2.0
  v3.0  → v0.3.0
  ...
  v4.0  → v0.4.0
  v4.1  → v0.4.1  (현재)

정식 서비스 출시 시 v1.0.0 으로 시작 예정"

echo ""
echo "=== ✅ 버전 체계 변경 완료 ==="
echo "  현재 버전: v0.4.1"
echo "  git push: git push origin main"
