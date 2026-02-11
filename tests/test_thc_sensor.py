#!/usr/bin/env python3
"""
test_thc_sensor.py
THC-S 토양 센서 (온도/습도/EC) RS485 Modbus 테스트
센서 1개를 연결하여 데이터 읽기 확인
"""

import minimalmodbus
import time

def test_thc_sensor(port='/dev/ttyS0', address=1, duration=10):
    """
    THC-S 센서 테스트
    
    Args:
        port: 시리얼 포트 (기본 /dev/ttyS0)
        address: 센서 주소 (1-12)
        duration: 측정 시간 (초)
    """
    print("=" * 50)
    print("🧪 THC-S 토양 센서 테스트")
    print("=" * 50)
    print()
    
    try:
        # Modbus 설정
        print(f"1️⃣ RS485 Modbus 초기화 중...")
        print(f"   포트: {port}")
        print(f"   센서 주소: {address}")
        print(f"   보드레이트: 4800")
        
        sensor = minimalmodbus.Instrument(port, address)
        sensor.serial.baudrate = 4800
        sensor.serial.timeout = 1
        
        print("   ✓ RS485 Modbus 초기화 완료")
        print()
        
        # 첫 번째 읽기 시도
        print("2️⃣ 센서 연결 확인 중...")
        try:
            test_humidity = sensor.read_register(0x0000, 1)
            print(f"   ✓ 센서 응답 확인 (습도: {test_humidity}%)")
        except Exception as e:
            print(f"   ❌ 센서 응답 없음: {e}")
            raise
        print()
        
        # 센서 데이터 읽기
        print(f"3️⃣ 센서 데이터 측정 ({duration}초)")
        print()
        print("   측정 항목:")
        print("   - 토양 습도 (0-100%)")
        print("   - 토양 온도 (-40~80°C)")
        print("   - 토양 EC (0-20000 μS/cm)")
        print()
        print("   📊 측정 시작...")
        print("   " + "-" * 45)
        
        success_count = 0
        fail_count = 0
        
        for i in range(duration):
            try:
                # 습도 읽기 (레지스터 0x0000, 소수점 1자리)
                humidity = sensor.read_register(0x0000, 1)
                
                # 온도 읽기 (레지스터 0x0001, 소수점 1자리)
                temperature = sensor.read_register(0x0001, 1)
                
                # EC 읽기 (레지스터 0x0002, 소수점 0자리)
                ec = sensor.read_register(0x0002, 0)
                
                # 결과 출력
                print(f"   [{i+1:2d}/{duration:2d}] ✅ 습도: {humidity:5.1f}% | "
                      f"온도: {temperature:5.1f}°C | EC: {ec:5d} μS/cm")
                
                success_count += 1
                time.sleep(1)
                
            except Exception as e:
                print(f"   [{i+1:2d}/{duration:2d}] ❌ 읽기 실패: {e}")
                fail_count += 1
                time.sleep(1)
        
        print("   " + "-" * 45)
        print()
        print("=" * 50)
        print("✅ THC-S 센서 테스트 완료!")
        print("=" * 50)
        print()
        print(f"📊 통계:")
        print(f"   성공: {success_count}/{duration} ({success_count/duration*100:.1f}%)")
        print(f"   실패: {fail_count}/{duration} ({fail_count/duration*100:.1f}%)")
        
        if success_count / duration >= 0.9:
            print()
            print("🎉 센서가 안정적으로 동작합니다!")
            return True
        else:
            print()
            print("⚠️  센서가 불안정합니다. 배선과 전원을 확인하세요.")
            return False
        
    except FileNotFoundError:
        print()
        print(f"❌ {port} 포트를 찾을 수 없습니다!")
        print()
        print("🔍 문제 해결 방법:")
        print("   1. UART 활성화 확인:")
        print("      sudo raspi-config → Interface → Serial Port")
        print("      - Login shell: No")
        print("      - Serial hardware: Yes")
        print("   2. 재부팅: sudo reboot")
        print("   3. 포트 확인: ls -l /dev/ttyS0")
        return False
        
    except Exception as e:
        print()
        print(f"❌ 테스트 실패: {e}")
        print()
        print("🔍 문제 해결 방법:")
        print("   1. MAX485 배선 확인:")
        print("      - VCC → 5V (Pin 2)")
        print("      - GND → GND (Pin 6)")
        print("      - DI → TX (GPIO 14, Pin 8)")
        print("      - RO → RX (GPIO 15, Pin 10)")
        print("      - DE, RE → GPIO 4 (Pin 7) - 묶어서 연결")
        print()
        print("   2. THC-S 센서 배선 확인:")
        print("      - 갈색(Brown) → 12V+")
        print("      - 검정(Black) → GND")
        print("      - 노랑(Yellow) → MAX485 A+")
        print("      - 파랑(Blue) → MAX485 B-")
        print()
        print("   3. 센서 주소 확인:")
        print(f"      현재 주소: {address}")
        print("      센서 공장 초기값은 주소 1입니다.")
        return False

if __name__ == '__main__':
    # 기본 테스트 (주소 1, 10초)
    test_thc_sensor(address=1, duration=10)
    
    # 다른 주소 테스트 (주석 해제하여 사용)
    # test_thc_sensor(address=2, duration=10)
    # test_thc_sensor(address=3, duration=10)
