#!/usr/bin/env python3
"""
CWT-Soil-THC-S 센서 Modbus 슬레이브 주소 설정 도구
------------------------------------------------------
사용법:
  python3 set_sensor_address.py            # 대화형 모드
  python3 set_sensor_address.py --scan     # 버스 전체 주소 스캔
  python3 set_sensor_address.py --set 1 3  # 주소 1 → 3 으로 변경

배선:
  센서 갈색(+)  → DC 12V (또는 5~30V)
  센서 검정(-)  → GND
  센서 노랑(A)  → RS485 A
  센서 파랑(B)  → RS485 B
  
주의: 반드시 센서 1개씩만 연결하고 주소 변경!
"""

import sys
import time
import argparse
import struct

# ── 설정 ────────────────────────────────────────────────
PORT      = '/dev/ttyAMA0'
BAUDRATE  = 4800          # 매뉴얼 기본값
DE_RE_PIN = 18            # GPIO 핀 (BCM)
TIMEOUT   = 1.5           # 응답 대기 (초)
# ────────────────────────────────────────────────────────

try:
    import serial
except ImportError:
    print("❌ pyserial 미설치: pip install pyserial")
    sys.exit(1)

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO 없음 — DE/RE 핀 제어 비활성화 (USB-RS485 어댑터는 자동 제어)")


# ── CRC16 ────────────────────────────────────────────────
def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return bytes([crc & 0xFF, crc >> 8])


def build_pdu(addr: int, func: int, *words: int) -> bytes:
    """Modbus RTU 프레임 생성"""
    body = bytes([addr, func]) + b''.join(w.to_bytes(2, 'big') for w in words)
    return body + crc16(body)


def verify_crc(frame: bytes) -> bool:
    if len(frame) < 4:
        return False
    return crc16(frame[:-2]) == frame[-2:]


# ── RS485 송수신 ─────────────────────────────────────────
class RS485:
    def __init__(self, port, baudrate, de_re_pin=None, timeout=1.5):
        self.de_re_pin = de_re_pin
        self.ser = serial.Serial(
            port, baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )
        if de_re_pin and GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(de_re_pin, GPIO.OUT)
            GPIO.output(de_re_pin, GPIO.LOW)   # 초기: 수신 모드
        time.sleep(0.3)

    def send_recv(self, frame: bytes, expect_len: int = 8) -> bytes:
        """송신 후 수신"""
        self.ser.reset_input_buffer()

        # DE/RE → HIGH (송신)
        if self.de_re_pin and GPIO_AVAILABLE:
            GPIO.output(self.de_re_pin, GPIO.HIGH)
        time.sleep(0.01)

        self.ser.write(frame)
        self.ser.flush()

        # 송신 완료 대기 (바이트수 × 비트/바이트 ÷ 보드레이트)
        tx_time = len(frame) * 10 / BAUDRATE
        time.sleep(tx_time + 0.02)

        # DE/RE → LOW (수신)
        if self.de_re_pin and GPIO_AVAILABLE:
            GPIO.output(self.de_re_pin, GPIO.LOW)

        # 응답 수신
        deadline = time.time() + self.ser.timeout
        buf = b''
        while time.time() < deadline:
            chunk = self.ser.read(expect_len - len(buf))
            buf += chunk
            if len(buf) >= expect_len:
                break
            if chunk:
                deadline = time.time() + 0.05  # 데이터 들어오면 조금 더 대기
        return buf

    def close(self):
        self.ser.close()
        if self.de_re_pin and GPIO_AVAILABLE:
            GPIO.cleanup()


# ── Modbus 명령 ───────────────────────────────────────────
def read_register(bus: RS485, addr: int, reg: int, count: int = 1):
    """FC03 — 레지스터 읽기. 성공 시 값 리스트 반환, 실패 시 None"""
    frame = build_pdu(addr, 0x03, reg, count)
    # 응답: addr(1) + fc(1) + byte_count(1) + data(count*2) + crc(2)
    resp = bus.send_recv(frame, expect_len=3 + count * 2 + 2)

    if len(resp) < 5:
        return None
    if resp[0] != addr or resp[1] != 0x03:
        return None
    if not verify_crc(resp):
        return None

    n = resp[2]
    values = [int.from_bytes(resp[3 + i*2: 5 + i*2], 'big')
              for i in range(n // 2)]
    return values


def write_register(bus: RS485, addr: int, reg: int, value: int) -> bool:
    """FC06 — 단일 레지스터 쓰기. 성공 시 True"""
    frame = build_pdu(addr, 0x06, reg, value)
    # 응답: 요청과 동일한 8바이트 에코
    resp = bus.send_recv(frame, expect_len=8)

    if len(resp) < 8:
        return False
    if resp[0] != addr or resp[1] != 0x06:
        return False
    if not verify_crc(resp):
        return False
    return True


# ── 기능 함수 ─────────────────────────────────────────────
def ping_sensor(bus: RS485, addr: int) -> dict | None:
    """센서 응답 확인 + 수분/온도/EC 읽기"""
    vals = read_register(bus, addr, 0x0000, 3)
    if vals is None or len(vals) < 3:
        return None

    moisture = vals[0] / 10.0
    raw_temp = vals[1]
    if raw_temp > 32767:
        raw_temp -= 65536
    temperature = raw_temp / 10.0
    ec = vals[2]

    return {'moisture': moisture, 'temperature': temperature, 'ec': ec}


def change_address(bus: RS485, current: int, new_addr: int) -> bool:
    """슬레이브 주소 변경 (레지스터 0x07D0)"""
    return write_register(bus, current, 0x07D0, new_addr)


def scan_bus(bus: RS485, start: int = 1, end: int = 247) -> list[int]:
    """버스 전체 스캔 — 응답하는 주소 목록 반환"""
    found = []
    print(f"\n🔍 주소 {start}~{end} 스캔 중...")
    for addr in range(start, end + 1):
        sys.stdout.write(f'\r   검사 중: {addr:3d} / {end}  ')
        sys.stdout.flush()
        vals = read_register(bus, addr, 0x0000, 1)
        if vals is not None:
            found.append(addr)
            sys.stdout.write(f'\r   ✅ 주소 {addr:3d} 응답!\n')
    print(f'\r   스캔 완료. {" " * 30}')
    return found


# ── 대화형 모드 ───────────────────────────────────────────
ZONE_PLAN = {z: z for z in range(1, 13)}   # 구역번호 = 주소 (기본 계획)

def interactive_mode(bus: RS485):
    print()
    print("┌─────────────────────────────────────────┐")
    print("│  CWT-Soil-THC-S  주소 설정 도구  v1.0   │")
    print("│  센서를 1개씩 연결하고 진행하세요        │")
    print("└─────────────────────────────────────────┘")
    print()
    print("  설정 계획 (구역 번호 = Modbus 주소):")
    print("  ┌──────────┬──────────┬──────────┬──────────┐")
    print("  │ 구역  1→1 │ 구역  2→2 │ 구역  3→3 │ 구역  4→4 │")
    print("  │ 구역  5→5 │ 구역  6→6 │ 구역  7→7 │ 구역  8→8 │")
    print("  │ 구역  9→9 │ 구역 10→10│ 구역 11→11│ 구역 12→12│")
    print("  └──────────┴──────────┴──────────┴──────────┘")
    print()
    print("  명령어:")
    print("    s <주소>       — 주소 스캔 / 센서 응답 확인")
    print("    set <현재> <새> — 주소 변경")
    print("    scan           — 버스 전체 스캔 (1~30)")
    print("    q              — 종료")
    print()

    while True:
        try:
            cmd = input("▶ 명령 입력: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if not cmd:
            continue

        parts = cmd.split()

        # ── 종료 ──
        if parts[0] in ('q', 'quit', 'exit'):
            break

        # ── 전체 스캔 ──
        elif parts[0] == 'scan':
            end = int(parts[1]) if len(parts) > 1 else 30
            found = scan_bus(bus, 1, end)
            if found:
                print(f"\n  발견된 주소: {found}")
                for a in found:
                    data = ping_sensor(bus, a)
                    if data:
                        print(f"    주소 {a:3d}: 수분={data['moisture']}%  "
                              f"온도={data['temperature']}°C  EC={data['ec']}μS/cm")
            else:
                print("  ⚠️  응답하는 센서 없음")

        # ── 단일 핑 ──
        elif parts[0] == 's' and len(parts) == 2:
            addr = int(parts[1])
            print(f"\n  주소 {addr} 센서 확인 중...")
            data = ping_sensor(bus, addr)
            if data:
                print(f"  ✅ 응답 확인!")
                print(f"     수분:  {data['moisture']} %RH")
                print(f"     온도:  {data['temperature']} °C")
                print(f"     EC:    {data['ec']} μS/cm")
            else:
                print(f"  ❌ 응답 없음 (주소 {addr}, 연결/전원 확인)")

        # ── 주소 변경 ──
        elif parts[0] == 'set' and len(parts) == 3:
            cur, new = int(parts[1]), int(parts[2])
            if not (1 <= new <= 247):
                print("  ⚠️  주소는 1~247 범위로 입력하세요")
                continue

            print(f"\n  현재 주소 {cur} → 새 주소 {new} 변경 중...")
            # 먼저 현재 주소 응답 확인
            data = ping_sensor(bus, cur)
            if data is None:
                print(f"  ❌ 주소 {cur} 에서 응답 없음 — 연결/주소 재확인")
                continue

            print(f"  ✅ 현재 센서 데이터: 수분={data['moisture']}%  "
                  f"온도={data['temperature']}°C  EC={data['ec']}μS/cm")

            ok = change_address(bus, cur, new)
            if ok:
                print(f"  ✅ 주소 변경 명령 전송 성공!")
                time.sleep(0.5)
                # 변경 후 새 주소로 응답 확인
                data2 = ping_sensor(bus, new)
                if data2:
                    print(f"  ✅ 새 주소 {new} 응답 확인 — 변경 완료!")
                    print(f"     다음 센서를 연결하고 'set 1 <구역번호>' 를 입력하세요")
                else:
                    print(f"  ⚠️  새 주소 {new} 에서 즉시 응답 없음")
                    print(f"     (일부 센서는 재전원 후 적용됩니다)")
                    print(f"     센서 전원을 껐다 켠 뒤 's {new}' 로 확인하세요")
            else:
                print(f"  ❌ 주소 변경 실패 — 응답 없음 또는 CRC 오류")

        else:
            print("  명령 형식: s <주소> | set <현재> <새> | scan | q")

    print("\n종료합니다.")


# ── CLI 모드 ──────────────────────────────────────────────
def cli_set(bus: RS485, current: int, new_addr: int):
    print(f"\n주소 {current} → {new_addr} 변경 시도...")
    data = ping_sensor(bus, current)
    if data is None:
        print(f"❌ 주소 {current} 응답 없음")
        sys.exit(1)
    print(f"✅ 현재 센서: 수분={data['moisture']}% 온도={data['temperature']}°C EC={data['ec']}")
    if change_address(bus, current, new_addr):
        print(f"✅ 주소 변경 성공: {current} → {new_addr}")
    else:
        print(f"❌ 주소 변경 실패")
        sys.exit(1)


def cli_scan(bus: RS485):
    found = scan_bus(bus, 1, 30)
    if found:
        print(f"\n발견된 센서 주소: {found}")
        for a in found:
            data = ping_sensor(bus, a)
            if data:
                print(f"  주소 {a:2d}: 수분={data['moisture']}%  "
                      f"온도={data['temperature']}°C  EC={data['ec']}μS/cm")
    else:
        print("응답하는 센서 없음")


# ── 진입점 ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='CWT-Soil-THC-S Modbus 주소 설정 도구'
    )
    parser.add_argument('--port',    default=PORT,      help=f'시리얼 포트 (기본: {PORT})')
    parser.add_argument('--baud',    default=BAUDRATE,  type=int, help=f'보드레이트 (기본: {BAUDRATE})')
    parser.add_argument('--de-re',   default=DE_RE_PIN, type=int, help=f'DE/RE GPIO 핀 (기본: {DE_RE_PIN})')
    parser.add_argument('--scan',    action='store_true',          help='버스 전체 스캔 (1~30)')
    parser.add_argument('--set',     nargs=2, type=int, metavar=('현재주소', '새주소'),
                        help='주소 변경 (예: --set 1 3)')
    args = parser.parse_args()

    print(f"\n포트: {args.port}  보드레이트: {args.baud}  DE/RE: GPIO{args.de_re}")

    try:
        bus = RS485(args.port, args.baud, de_re_pin=args.de_re, timeout=TIMEOUT)
    except serial.SerialException as e:
        print(f"❌ 포트 열기 실패: {e}")
        sys.exit(1)

    try:
        if args.scan:
            cli_scan(bus)
        elif args.set:
            cli_set(bus, args.set[0], args.set[1])
        else:
            interactive_mode(bus)
    finally:
        bus.close()


if __name__ == '__main__':
    main()
