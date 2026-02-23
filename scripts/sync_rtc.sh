#!/bin/bash
PYTHON="/home/pi/smart_farm_env/bin/python3"
$PYTHON << 'PYEOF'
import smbus2, datetime, time, sys
def dec_to_bcd(val): return (val // 10) << 4 | (val % 10)
def bcd_to_dec(val): return ((val >> 4) * 10) + (val & 0x0F)
try:
    bus = smbus2.SMBus(1)
    now = datetime.datetime.now()
    data = [dec_to_bcd(now.second)&0x7F, dec_to_bcd(now.minute),
            dec_to_bcd(now.hour)&0x3F, dec_to_bcd(now.isoweekday()),
            dec_to_bcd(now.day), dec_to_bcd(now.month), dec_to_bcd(now.year-2000)]
    bus.write_i2c_block_data(0x68, 0, data)
    time.sleep(0.1)
    print(f"✅ RTC 동기화 완료: {now.strftime('%Y-%m-%d %H:%M:%S')}")
except Exception as e:
    print(f"❌ RTC 오류: {e}"); sys.exit(1)
PYEOF
