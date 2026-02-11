#!/usr/bin/env python3
"""
test_i2c.py
I2C 장치 스캔 및 확인
부품이 제대로 연결되었는지 확인하는 첫 번째 테스트
"""

import subprocess

def scan_i2c():
    """I2C 버스 스캔"""
    print("🔍 I2C 장치 스캔 중...")
    print()
    
    try:
        result = subprocess.run(['i2cdetect', '-y', '1'], 
                              capture_output=True, text=True)
        print(result.stdout)
        
        # 예상 주소 확인
        expected = {
            '20': 'MCP23017 #1 (GPIO 확장)',
            '21': 'MCP23017 #2 (GPIO 확장)',
            '48': 'ADS1115 (ADC 아날로그 입력)'
        }
        
        print("📋 우리 프로젝트 예상 장치:")
        found_count = 0
        
        for addr, name in expected.items():
            if addr in result.stdout:
                print(f"  ✅ 0x{addr}: {name} 발견!")
                found_count += 1
            else:
                print(f"  ❌ 0x{addr}: {name} 없음")
        
        print()
        if found_count == 0:
            print("⚠️  아직 부품이 연결되지 않았습니다.")
            print("    부품을 연결하고 다시 실행하세요.")
        elif found_count == len(expected):
            print("🎉 모든 장치가 정상적으로 연결되었습니다!")
        else:
            print(f"📊 {found_count}/{len(expected)}개 장치 연결됨")
            
    except FileNotFoundError:
        print("❌ i2cdetect 명령어를 찾을 수 없습니다.")
        print("   I2C가 활성화되지 않았을 수 있습니다.")
        print("   sudo raspi-config 에서 I2C를 활성화하세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == '__main__':
    scan_i2c()
