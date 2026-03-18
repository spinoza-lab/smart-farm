"""
app_patch_stage11.py
Stage 11: app.py → init_monitoring_system() 에 DBManager 초기화 삽입

패치 내용:
  1. 'from database.db_manager import DBManager' import 추가
  2. init_monitoring_system() 첫 줄에 DBManager 초기화 코드 삽입
  3. DataLogger 생성 시 db_manager 파라미터 전달
  4. EnvironmentMonitor 생성 시 db_manager 파라미터 전달

사용법:
  cd ~/smart_farm
  python3 scripts/app_patch_stage11.py
"""
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / 'web' / 'app.py'


def patch():
    text = TARGET.read_text(encoding='utf-8')

    changed = False

    # ── 1. DBManager import 추가 ──────────────────────────────────────────────
    IMPORT_MARKER  = 'from monitoring.data_logger import DataLogger'
    IMPORT_INSERT  = 'from database.db_manager import DBManager\n'
    if 'from database.db_manager import DBManager' not in text:
        text = text.replace(IMPORT_MARKER, IMPORT_INSERT + IMPORT_MARKER)
        changed = True
        print("  ✅ DBManager import 추가")
    else:
        print("  ✅ DBManager import 이미 존재")

    # ── 2. DBManager 초기화 코드 삽입 ─────────────────────────────────────────
    # 'def init_monitoring_system():' 바로 다음 줄 try: 안에 삽입
    DB_INIT = """\
        # Stage 11: SQLite DBManager 초기화
        try:
            g.db_manager = DBManager()
            print("✅ DBManager 초기화 완료")
        except Exception as _e:
            print(f"⚠️  DBManager 초기화 실패: {_e}")
            g.db_manager = None
"""
    INIT_MARKER = "        g.data_logger = DataLogger(log_dir=str(_BASE_DIR / 'logs'))"
    if 'Stage 11: SQLite DBManager 초기화' not in text:
        if INIT_MARKER in text:
            text = text.replace(INIT_MARKER,
                                DB_INIT + "        " + INIT_MARKER.lstrip())
            changed = True
            print("  ✅ DBManager 초기화 코드 삽입")
        else:
            print("  ⚠️  DataLogger 초기화 위치를 찾지 못했습니다 – 수동 삽입 필요")
    else:
        print("  ✅ DBManager 초기화 코드 이미 존재")

    # ── 3. DataLogger 생성 시 db_manager 전달 ─────────────────────────────────
    OLD_DL = "g.data_logger = DataLogger(log_dir=str(_BASE_DIR / 'logs'))"
    NEW_DL = "g.data_logger = DataLogger(log_dir=str(_BASE_DIR / 'logs'), db_manager=g.db_manager)"
    if OLD_DL in text:
        text = text.replace(OLD_DL, NEW_DL)
        changed = True
        print("  ✅ DataLogger db_manager 파라미터 추가")
    elif NEW_DL in text:
        print("  ✅ DataLogger db_manager 파라미터 이미 존재")
    else:
        print("  ⚠️  DataLogger 생성 라인을 찾지 못했습니다")

    # ── 4. EnvironmentMonitor 생성 시 db_manager 전달 ─────────────────────────
    OLD_EM = """            g.environment_monitor = EnvironmentMonitor(
                air_sensor_manager=g.air_sensor_manager,
                weather_station_reader=g.weather_station
            )"""
    NEW_EM = """            g.environment_monitor = EnvironmentMonitor(
                air_sensor_manager=g.air_sensor_manager,
                weather_station_reader=g.weather_station,
                db_manager=g.db_manager
            )"""
    if 'db_manager=g.db_manager' not in text and OLD_EM in text:
        text = text.replace(OLD_EM, NEW_EM)
        changed = True
        print("  ✅ EnvironmentMonitor db_manager 파라미터 추가")
    else:
        print("  ✅ EnvironmentMonitor db_manager 파라미터 이미 존재 또는 패턴 불일치")

    if changed:
        # 백업 저장
        backup = str(TARGET) + '.bak_stage11'
        Path(backup).write_text(TARGET.read_text(encoding='utf-8'), encoding='utf-8')
        TARGET.write_text(text, encoding='utf-8')
        print(f"\n✅ app.py 패치 완료  (백업: {backup})")
    else:
        print("\n✅ 변경사항 없음 – 이미 최신 상태")


if __name__ == '__main__':
    patch()
