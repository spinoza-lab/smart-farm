🔌 릴레이 하드웨어 구성 (상세)
시스템 개요
펌프: 1개 (모든 구역 공용)
구역(Zone): 12개 독립 밸브
릴레이 보드: 6채널 × 4개 = 24채널 (17개 사용, 7개 예비)
MCP23017: 2개 (0x20, 0x21) - 총 32핀 중 18핀 사용
릴레이 할당표
보드 #1: 필수 제어 (6채널)
릴레이	MCP	핀	명칭	제어 대상	평상시
1-1	0x20	PA0	관수펌프	SSR → 관수펌프	OFF
1-2	0x20	PA1	양액차단	지하수 → 양액탱크	ON
1-3	0x20	PA2	물차단	지하수 → 물탱크	ON
1-4	0x20	PA3	핸드건	지하수 → 핸드건	OFF
1-5	0x20	PA4	체크밸브	물탱크 → 펌프	ON
1-6	0x20	PA5	예비	교반기 등	OFF
보드 #2: Zone 1~6 (6채널)
릴레이	MCP	핀	Zone	평상시
2-1	0x20	PA6	Zone 1	OFF
2-2	0x20	PA7	Zone 2	OFF
2-3	0x20	PB0	Zone 3	OFF
2-4	0x20	PB1	Zone 4	OFF
2-5	0x20	PB2	Zone 5	OFF
2-6	0x20	PB3	Zone 6	OFF
보드 #3: Zone 7~12 (6채널)
릴레이	MCP	핀	Zone	평상시
3-1	0x20	PB4	Zone 7	OFF
3-2	0x20	PB5	Zone 8	OFF
3-3	0x20	PB6	Zone 9	OFF
3-4	0x20	PB7	Zone 10	OFF
3-5	0x21	PA0	Zone 11	OFF
3-6	0x21	PA1	Zone 12	OFF
보드 #4: 예비 (6채널)
릴레이	MCP	핀	예정 용도	평상시
4-1	0x21	PA2	물탱크 드레인	OFF
4-2	0x21	PA3	양액탱크 드레인	OFF
4-3	0x21	PA4	Zone 13 확장	OFF
4-4	0x21	PA5	Zone 14 확장	OFF
4-5	0x21	PA6	예비	OFF
4-6	0x21	PA7	예비	OFF
물 흐름도
지하수 공급
├─→ [양액차단밸브 ON] → 양액탱크 (자동 충수)
├─→ [물차단밸브 ON] → 물탱크 (자동 충수)
│                        ↓
│                     [체크밸브 ON]
│                        ↓
│                     [관수펌프]
│                        ↓
│                   [Zone 1~12 선택]
│                        ↓
│                    해당 구역 관수
│
└─→ [핸드건밸브] → 핸드건 (수동 사용)
제어 로직
일반 관수 (Zone 3 예시)
1. 사전 조건 확인
   - check_valve = ON (항상 켜짐)
   - water_block = ON (항상 켜짐)
   - 물탱크 수위 ≥ 20%

2. 관수 시작
   - pump = ON
   - zone_3 = ON

3. 관수 진행 (설정 시간)

4. 관수 종료
   - zone_3 = OFF
   - pump = OFF
핸드건 모드
1. 안전 조치
   - pump = OFF
   - all_zones = OFF

2. 핸드건 활성화
   - hand_gun = ON
   - 사용자가 핸드건 직접 사용

3. 핸드건 종료
   - hand_gun = OFF
릴레이 사용 현황
카테고리	사용	예비	합계
필수 제어	5개	1개	6개
Zone 1~12	12개	-	12개
예비 (보드#4)	-	6개	6개
총계	17개	7개	24개
Python 릴레이 매핑
CopyRELAY_MAP = {
    # 필수 제어
    'pump': (0x20, 0),           # PA0
    'nutrient_block': (0x20, 1), # PA1
    'water_block': (0x20, 2),    # PA2
    'hand_gun': (0x20, 3),       # PA3
    'check_valve': (0x20, 4),    # PA4
    'spare_1': (0x20, 5),        # PA5
    
    # Zone 1~12
    'zone_1': (0x20, 6),         # PA6
    'zone_2': (0x20, 7),         # PA7
    'zone_3': (0x20, 8),         # PB0
    'zone_4': (0x20, 9),         # PB1
    'zone_5': (0x20, 10),        # PB2
    'zone_6': (0x20, 11),        # PB3
    'zone_7': (0x20, 12),        # PB4
    'zone_8': (0x20, 13),        # PB5
    'zone_9': (0x20, 14),        # PB6
    'zone_10': (0x20, 15),       # PB7
    'zone_11': (0x21, 0),        # PA0
    'zone_12': (0x21, 1),        # PA1
    
    # 예비
    'drain_water': (0x21, 2),    # PA2
    'drain_nutrient': (0x21, 3), # PA3
    'spare_zone_13': (0x21, 4),  # PA4
    'spare_zone_14': (0x21, 5),  # PA5
    'spare_2': (0x21, 6),        # PA6
    'spare_3': (0x21, 7),        # PA7
}

ZONE_MAP = {i: f'zone_{i}' for i in range(1, 13)}
MAX_ZONES = 12