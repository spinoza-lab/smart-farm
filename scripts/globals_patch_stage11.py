"""
globals_patch_stage11.py
Stage 11: globals.py 에 db_manager 전역 변수 추가 패치

사용법 (raspberry pi에서):
  cd ~/smart_farm
  python3 scripts/globals_patch_stage11.py
"""
import re
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / 'web' / 'globals.py'

INSERT_AFTER = "environment_state = {"

DB_SNIPPET = """
# ══════════════════════════════════════════════════════════════════════
# Stage 11: SQLite DBManager 전역 변수
# ══════════════════════════════════════════════════════════════════════
db_manager = None  # database.db_manager.DBManager 인스턴스
"""

def patch():
    text = TARGET.read_text(encoding='utf-8')
    if 'db_manager' in text:
        print("✅ 이미 패치됨 (db_manager 존재) → 건너뜀")
        return
    # environment_state 블록 끝 ('}\n') 뒤에 삽입
    idx = text.find('environment_state = {')
    if idx == -1:
        print("❌ 삽입 위치(environment_state) 를 찾지 못했습니다")
        return
    # 블록 끝 위치 찾기
    brace_start = text.index('{', idx)
    depth = 0
    pos = brace_start
    while pos < len(text):
        if text[pos] == '{': depth += 1
        elif text[pos] == '}': depth -= 1
        if depth == 0:
            break
        pos += 1
    insert_pos = pos + 1  # '}' 다음
    new_text = text[:insert_pos] + '\n' + DB_SNIPPET + text[insert_pos:]
    TARGET.write_text(new_text, encoding='utf-8')
    print(f"✅ globals.py 패치 완료 (db_manager 전역 변수 추가, 위치: {insert_pos})")

if __name__ == '__main__':
    patch()
