"""
DataLogger 모듈
센서 데이터를 CSV 파일로 저장하고 조회하는 기능 제공

주요 기능:
- 센서 데이터 CSV 저장
- 날짜별 자동 파일 분리
- 데이터 조회 및 필터링
- 통계 계산 (평균, 최소, 최대)

작성자: spinoza-lab
날짜: 2026-02-12
"""

import csv
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import threading

# BUG-7: 설치 경로 동적 계산 (하드코딩 제거)
_BASE_DIR = Path(__file__).resolve().parent.parent


class DataLogger:
    """
    센서 데이터 로깅 클래스
    
    CSV 형식으로 센서 데이터를 저장하고 조회
    날짜별로 파일을 자동 분리하여 관리
    """
    
    def __init__(self, log_dir: str = str(_BASE_DIR / 'logs')):
        """
        DataLogger 초기화
        
        Args:
            log_dir: 로그 파일을 저장할 디렉터리 경로
        """
        self.log_dir = log_dir
        self._lock = threading.Lock()
        
        # 로그 디렉터리 생성
        self._ensure_log_directory()
        
        print(f"✅ DataLogger 초기화 완료")
        print(f"   로그 디렉터리: {self.log_dir}")
    
    def _ensure_log_directory(self):
        """로그 디렉터리가 없으면 생성"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            print(f"📁 로그 디렉터리 생성: {self.log_dir}")
    
    def _get_log_filename(self, date: Optional[datetime] = None) -> str:
        """
        날짜에 해당하는 로그 파일명 반환
        
        Args:
            date: 날짜 (None이면 오늘)
        
        Returns:
            로그 파일 경로
        """
        if date is None:
            date = datetime.now()
        
        filename = f"sensors_{date.strftime('%Y-%m-%d')}.csv"
        return os.path.join(self.log_dir, filename)
    
    def _ensure_csv_header(self, filepath: str):
        """
        CSV 파일에 헤더가 없으면 추가
        
        Args:
            filepath: CSV 파일 경로
        """
        # 파일이 없거나 비어있으면 헤더 작성
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'tank1_level',
                    'tank2_level',
                    'ch0_voltage',
                    'ch1_voltage',
                    'ch2_voltage',
                    'ch3_voltage'
                ])
    
    def log_sensor_data(self, 
                       tank1_level: float,
                       tank2_level: float,
                       voltages: List[float],
                       timestamp: Optional[datetime] = None) -> bool:
        """
        센서 데이터를 CSV 파일에 기록
        
        Args:
            tank1_level: 탱크 1 수위 (%)
            tank2_level: 탱크 2 수위 (%)
            voltages: 4채널 전압 리스트 [ch0, ch1, ch2, ch3]
            timestamp: 타임스탬프 (None이면 현재 시간)
        
        Returns:
            성공 여부
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # 날짜별 파일명 생성
            filepath = self._get_log_filename(timestamp)
            
            # 스레드 안전성 보장
            with self._lock:
                # 헤더 확인
                self._ensure_csv_header(filepath)
                
                # 데이터 기록
                with open(filepath, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        f"{tank1_level:.1f}",
                        f"{tank2_level:.1f}",
                        f"{voltages[0]:.3f}",
                        f"{voltages[1]:.3f}",
                        f"{voltages[2]:.3f}",
                        f"{voltages[3]:.3f}"
                    ])
            
            return True
            
        except Exception as e:
            print(f"❌ 데이터 로깅 실패: {e}")
            return False
    
    def get_data(self,
                 start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None,
                 tank_filter: Optional[int] = None,
                 level_min: Optional[float] = None,
                 level_max: Optional[float] = None) -> List[Dict]:
        """
        저장된 데이터 조회
        
        Args:
            start_date: 조회 시작 날짜 (None이면 오늘)
            end_date: 조회 종료 날짜 (None이면 start_date와 동일)
            tank_filter: 특정 탱크만 필터링 (1 또는 2)
            level_min: 최소 수위 필터
            level_max: 최대 수위 필터
        
        Returns:
            데이터 리스트 [{timestamp, tank1_level, tank2_level, ...}, ...]
        """
        if start_date is None:
            start_date = datetime.now()
        
        if end_date is None:
            end_date = start_date
        
        # 날짜 범위의 모든 파일 읽기
        all_data = []
        current_date = start_date
        
        while current_date <= end_date:
            filepath = self._get_log_filename(current_date)
            
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # 필터 적용
                            if self._apply_filters(row, tank_filter, level_min, level_max):
                                all_data.append(row)
                except Exception as e:
                    print(f"⚠️  파일 읽기 실패 ({filepath}): {e}")
            
            current_date += timedelta(days=1)
        
        return all_data
    
    def _apply_filters(self,
                      row: Dict,
                      tank_filter: Optional[int],
                      level_min: Optional[float],
                      level_max: Optional[float]) -> bool:
        """
        데이터 행에 필터 조건 적용
        
        Args:
            row: CSV 행 데이터
            tank_filter: 탱크 번호 (1 또는 2)
            level_min: 최소 수위
            level_max: 최대 수위
        
        Returns:
            필터 통과 여부
        """
        try:
            # 탱크 필터
            if tank_filter is not None:
                tank_key = f"tank{tank_filter}_level"
                level = float(row[tank_key])
                
                # 수위 범위 필터
                if level_min is not None and level < level_min:
                    return False
                if level_max is not None and level > level_max:
                    return False
            
            return True
            
        except (KeyError, ValueError):
            return False
    
    def get_statistics(self,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      tank_num: int = 1) -> Dict:
        """
        기간별 통계 계산
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            tank_num: 탱크 번호 (1 또는 2)
        
        Returns:
            통계 딕셔너리 {count, avg, min, max, first, last}
        """
        data = self.get_data(start_date, end_date)
        
        if not data:
            return {
                'count': 0,
                'avg': 0.0,
                'min': 0.0,
                'max': 0.0,
                'first': None,
                'last': None
            }
        
        tank_key = f"tank{tank_num}_level"
        levels = [float(row[tank_key]) for row in data]
        
        return {
            'count': len(levels),
            'avg': sum(levels) / len(levels),
            'min': min(levels),
            'max': max(levels),
            'first': levels[0],
            'last': levels[-1]
        }
    
    def get_latest_data(self, limit: int = 10) -> List[Dict]:
        """
        최근 데이터 조회
        
        Args:
            limit: 조회할 데이터 개수
        
        Returns:
            최근 데이터 리스트 (최신순)
        """
        # 오늘과 어제 데이터 조회
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        data = self.get_data(start_date=yesterday, end_date=today)
        
        # 최신순 정렬 후 제한
        return data[-limit:] if data else []
    
    def delete_old_logs(self, days_to_keep: int = 30) -> int:
        """
        오래된 로그 파일 삭제
        
        Args:
            days_to_keep: 보관할 일수
        
        Returns:
            삭제된 파일 개수
        """
        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            for filename in os.listdir(self.log_dir):
                if filename.startswith("sensors_") and filename.endswith(".csv"):
                    # 파일명에서 날짜 추출
                    date_str = filename.replace("sensors_", "").replace(".csv", "")
                    try:
                        file_date = datetime.strptime(date_str, "%Y-%m-%d")
                        
                        # 오래된 파일 삭제
                        if file_date < cutoff_date:
                            filepath = os.path.join(self.log_dir, filename)
                            os.remove(filepath)
                            deleted_count += 1
                            print(f"🗑️  삭제됨: {filename}")
                    
                    except ValueError:
                        continue
        
        except Exception as e:
            print(f"❌ 로그 정리 실패: {e}")
        
        return deleted_count
    
    def get_log_files(self) -> List[Tuple[str, int]]:
        """
        로그 파일 목록 및 크기 조회
        
        Returns:
            [(파일명, 크기(bytes)), ...] 리스트
        """
        files = []
        
        try:
            for filename in sorted(os.listdir(self.log_dir)):
                if filename.startswith("sensors_") and filename.endswith(".csv"):
                    filepath = os.path.join(self.log_dir, filename)
                    size = os.path.getsize(filepath)
                    files.append((filename, size))
        
        except Exception as e:
            print(f"❌ 파일 목록 조회 실패: {e}")
        
        return files


# ============================================================
# 테스트 코드
# ============================================================

def test_data_logger():
    """DataLogger 테스트"""
    
    print("=" * 60)
    print("🧪 DataLogger 테스트")
    print("=" * 60)
    print()
    
    # 테스트용 로그 디렉터리
    import tempfile
    test_dir = tempfile.mkdtemp()
    
    print("=" * 60)
    print("📊 DataLogger 초기화")
    print("=" * 60)
    logger = DataLogger(log_dir=test_dir)
    print()
    
    # [테스트 1] 데이터 로깅
    print("[테스트 1] 센서 데이터 로깅")
    print("-" * 60)
    
    # 샘플 데이터 10개 기록
    from datetime import datetime, timedelta
    base_time = datetime.now()
    
    for i in range(10):
        timestamp = base_time + timedelta(minutes=i)
        tank1 = 80.0 + i * 0.5
        tank2 = 75.0 + i * 0.3
        voltages = [2.0 + i * 0.01, 1.9 + i * 0.01, 0.6, 0.6]
        
        success = logger.log_sensor_data(
            tank1_level=tank1,
            tank2_level=tank2,
            voltages=voltages,
            timestamp=timestamp
        )
        
        if i == 0 or i == 9:
            print(f"✅ 데이터 {i+1}/10 기록: 탱크1={tank1:.1f}%, 탱크2={tank2:.1f}%")
    
    print(f"✅ 총 10개 데이터 기록 완료")
    print()
    
    # [테스트 2] 데이터 조회
    print("[테스트 2] 전체 데이터 조회")
    print("-" * 60)
    
    all_data = logger.get_data()
    print(f"✅ 조회된 데이터 개수: {len(all_data)}")
    
    if all_data:
        print(f"   첫 번째: {all_data[0]['timestamp']} - 탱크1={all_data[0]['tank1_level']}%")
        print(f"   마지막: {all_data[-1]['timestamp']} - 탱크1={all_data[-1]['tank1_level']}%")
    print()
    
    # [테스트 3] 필터링 조회
    print("[테스트 3] 필터링 조회 (탱크1 수위 >= 83%)")
    print("-" * 60)
    
    filtered_data = logger.get_data(tank_filter=1, level_min=83.0)
    print(f"✅ 조회된 데이터 개수: {len(filtered_data)}")
    
    for row in filtered_data[:3]:
        print(f"   {row['timestamp']}: 탱크1={row['tank1_level']}%")
    print()
    
    # [테스트 4] 통계 계산
    print("[테스트 4] 통계 계산 (탱크1)")
    print("-" * 60)
    
    stats = logger.get_statistics(tank_num=1)
    print(f"✅ 데이터 개수: {stats['count']}")
    print(f"   평균: {stats['avg']:.1f}%")
    print(f"   최소: {stats['min']:.1f}%")
    print(f"   최대: {stats['max']:.1f}%")
    print(f"   첫 값: {stats['first']:.1f}%")
    print(f"   마지막 값: {stats['last']:.1f}%")
    print()
    
    # [테스트 5] 최근 데이터 조회
    print("[테스트 5] 최근 5개 데이터")
    print("-" * 60)
    
    latest = logger.get_latest_data(limit=5)
    print(f"✅ 조회된 데이터: {len(latest)}개")
    
    for row in latest:
        print(f"   {row['timestamp']}: 탱크1={row['tank1_level']}%, 탱크2={row['tank2_level']}%")
    print()
    
    # [테스트 6] 로그 파일 목록
    print("[테스트 6] 로그 파일 목록")
    print("-" * 60)
    
    files = logger.get_log_files()
    print(f"✅ 로그 파일 개수: {len(files)}")
    
    for filename, size in files:
        print(f"   {filename}: {size} bytes")
    print()
    
    # 테스트 디렉터리 정리
    import shutil
    shutil.rmtree(test_dir)
    
    print("=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_data_logger()
