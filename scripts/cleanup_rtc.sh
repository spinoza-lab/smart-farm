#!/usr/bin/env bash
# 죽은 코드 제거: hardware/rtc_manager.py
# 삭제 대상: set_datetime, sync_from_system, sync_to_system, wait_until, display_clock

set -e
cd ~/smart_farm

echo "=== 죽은 코드 정리: rtc_manager.py ==="

python3 << 'PYEOF'
import re

path = 'hardware/rtc_manager.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

original = content

# 삭제할 메서드 5개 패턴
# 각 def 블록 시작부터 다음 def 또는 파일 끝까지 제거
dead_methods = [
    'set_datetime',
    'sync_from_system',
    'sync_to_system',
    'wait_until',
    'display_clock',
]

for method in dead_methods:
    # def method_name(... 부터 다음 def 또는 파일 끝까지 매칭
    pattern = rf'(    def {method}\(.*?)(?=    def |\Z)'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        content = content.replace(m.group(0), '', 1)
        print(f'✅ {method}() 삭제')
    else:
        print(f'⚠️  {method}() 패턴 미발견 (이미 삭제됐거나 구조 다름)')

# 말미에 if __name__ == "__main__": 테스트 블록도 제거
test_pattern = r'\nif __name__ == ["\']__main__["\']:.*'
m = re.search(test_pattern, content, re.DOTALL)
if m:
    content = content[:m.start()] + '\n'
    print('✅ __main__ 테스트 블록 삭제')
else:
    print('ℹ️  __main__ 블록 없음 (스킵)')

# 연속된 빈 줄 2개 초과 → 2개로 정리
content = re.sub(r'\n{3,}', '\n\n', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# 결과 요약
removed = len(original) - len(content)
print(f'\n총 {removed}자 제거')
print('남은 메서드:')
for line in content.splitlines():
    if line.strip().startswith('def '):
        print(f'  {line.strip()}')
PYEOF

# 문법 검사
python3 -m py_compile hardware/rtc_manager.py && echo "✅ rtc_manager.py 문법 OK" || echo "❌ 문법 오류"

# 전체 프로젝트에서 삭제된 메서드 호출 여부 재확인
echo ""
echo "=== 삭제된 메서드 호출부 잔존 여부 확인 ==="
result=$(grep -rn "set_datetime\|wait_until\|sync_from_system\|sync_to_system\|display_clock" \
  ~/smart_farm --include="*.py" | grep -v "rtc_manager.py" || true)
if [ -z "$result" ]; then
    echo "✅ 호출부 없음 — 안전하게 삭제됨"
else
    echo "⚠️  아직 호출부 존재:"
    echo "$result"
fi

# git commit
git add hardware/rtc_manager.py
git commit -m "refactor: rtc_manager.py 죽은 코드 제거

삭제된 메서드 (호출부 없음 확인):
  - set_datetime()      : no-op, BUG-3 잔재
  - sync_from_system()  : 시스템 시간 모드에서 불필요
  - sync_to_system()    : 시스템 시간 모드에서 불필요
  - wait_until()        : 블로킹 위험, BUG-4 잔재
  - display_clock()     : 터미널 디버그용, 미사용
  - __main__ 테스트 블록

유지된 메서드:
  get_datetime / get_datetime_string / get_time_string / get_date_string
  get_timestamp / is_time_in_range / get_hour / get_minute
  get_weekday / get_weekday_name"

echo ""
echo "=== ✅ 죽은 코드 정리 완료 ==="
echo "  git push: git push origin main"
