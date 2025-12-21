"""
🖨️ POS 프린터 관리 모듈
- Wi-Fi 연결 영수증 프린터 (ESC/POS)
- 블루투스 연결 영수증 프린터 지원
- 주방용, 카운터용, 배달용 3장 출력
"""

import streamlit as st
from datetime import datetime
import json

# ESC/POS 프린터 연결 시도
try:
    from escpos.printer import Network
    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False

# 블루투스 프린터 지원 확인
try:
    from escpos.printer import Serial
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False

# ==========================================
# 📱 블루투스 프린터 관련 상수
# ==========================================
BLUETOOTH_PRINTER_BRANDS = {
    'epson': {'name': 'Epson', 'baudrate': 9600},
    'star': {'name': 'Star Micronics', 'baudrate': 9600},
    'bixolon': {'name': 'Bixolon', 'baudrate': 115200},
    'xprinter': {'name': 'XPrinter', 'baudrate': 9600},
    'goojprt': {'name': 'GOOJPRT', 'baudrate': 9600},
    'other': {'name': '기타', 'baudrate': 9600}
}


class PrinterManager:
    """Wi-Fi POS 프린터 관리 클래스"""
    
    def __init__(self, ip_address, port=9100):
        self.ip_address = ip_address
        self.port = port
        self.printer = None
        self.connected = False
    
    def connect(self):
        """프린터 연결"""
        if not ESCPOS_AVAILABLE:
            return False, "python-escpos 라이브러리가 설치되지 않았습니다."
        
        if not self.ip_address:
            return False, "프린터 IP 주소가 설정되지 않았습니다."
        
        try:
            self.printer = Network(self.ip_address, port=self.port, timeout=5)
            self.connected = True
            return True, "프린터 연결 성공"
        except Exception as e:
            self.connected = False
            return False, f"프린터 연결 실패: {str(e)}"
    
    def disconnect(self):
        """프린터 연결 해제"""
        if self.printer:
            try:
                self.printer.close()
            except:
                pass
        self.connected = False
    
    def test_print(self):
        """테스트 출력"""
        success, msg = self.connect()
        if not success:
            return False, msg
        
        try:
            self.printer.set(align='center', font='a', bold=True, double_height=True)
            self.printer.text("=== 테스트 출력 ===\n")
            self.printer.set(align='center', font='a', bold=False, double_height=False)
            self.printer.text(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.printer.text("프린터 연결 성공!\n")
            self.printer.text("\n" * 2)
            self.printer.cut()
            self.disconnect()
            return True, "테스트 출력 완료"
        except Exception as e:
            self.disconnect()
            return False, f"테스트 출력 실패: {str(e)}"
    
    def print_order(self, order_data, copy_type="주방용"):
        """주문서 1장 출력"""
        success, msg = self.connect()
        if not success:
            return False, msg
        
        try:
            # 헤더
            self.printer.set(align='center', font='a', bold=True, double_height=True)
            self.printer.text(f"[ {copy_type} ]\n")
            self.printer.text("=" * 24 + "\n")
            
            # 주문 정보
            self.printer.set(align='center', font='a', bold=True, double_height=True)
            self.printer.text(f"주문번호: {order_data.get('order_id', 'N/A')}\n")
            
            self.printer.set(align='left', font='a', bold=False, double_height=False)
            self.printer.text("-" * 32 + "\n")
            
            # 접수시간
            self.printer.text(f"접수: {order_data.get('order_time', '')}\n")
            self.printer.text(f"가게: {order_data.get('store_name', '')}\n")
            self.printer.text("-" * 32 + "\n")
            
            # 메뉴 내용 (강조)
            self.printer.set(align='left', font='a', bold=True, double_height=True)
            self.printer.text("[주문내용]\n")
            self.printer.set(align='left', font='a', bold=False, double_height=True)
            
            order_content = order_data.get('order_content', '')
            for line in order_content.split('\n'):
                if line.strip():
                    self.printer.text(f"  {line}\n")
            
            self.printer.set(align='left', font='a', bold=False, double_height=False)
            self.printer.text("-" * 32 + "\n")
            
            # 금액
            total_price = order_data.get('total_price', '')
            if total_price:
                self.printer.set(align='right', font='a', bold=True, double_height=True)
                self.printer.text(f"합계: {total_price}원\n")
                self.printer.set(align='left', font='a', bold=False, double_height=False)
                self.printer.text("-" * 32 + "\n")
            
            # 배달 정보
            address = order_data.get('address', '')
            customer_phone = order_data.get('customer_phone', '')
            request = order_data.get('request', '')
            
            if address or customer_phone:
                self.printer.set(align='left', font='a', bold=True, double_height=False)
                self.printer.text("[배달정보]\n")
                self.printer.set(align='left', font='a', bold=False, double_height=False)
                
                if address:
                    self.printer.text(f"주소: {address}\n")
                if customer_phone:
                    self.printer.text(f"연락처: {customer_phone}\n")
            
            # 요청사항
            if request:
                self.printer.text("-" * 32 + "\n")
                self.printer.set(align='left', font='a', bold=True, double_height=False)
                self.printer.text("[요청사항]\n")
                self.printer.set(align='left', font='a', bold=False, double_height=False)
                self.printer.text(f"{request}\n")
            
            # 푸터
            self.printer.text("=" * 32 + "\n")
            self.printer.text("\n" * 3)
            self.printer.cut()
            
            return True, "출력 완료"
        except Exception as e:
            return False, f"출력 실패: {str(e)}"
        finally:
            self.disconnect()
    
    def print_order_3copies(self, order_data):
        """주문서 3장 출력 (주방용, 카운터용, 배달용)"""
        results = []
        copy_types = ["🍳 주방용", "💰 카운터용", "🛵 배달용"]
        
        for copy_type in copy_types:
            success, msg = self.print_order(order_data, copy_type)
            results.append({
                'type': copy_type,
                'success': success,
                'message': msg
            })
            
            if not success:
                # 첫 번째 출력 실패 시 나머지도 실패할 가능성 높음
                break
        
        return results


def print_order_receipt(order_data, printer_ip, printer_port=9100):
    """주문 영수증 출력 (외부 호출용)"""
    if not printer_ip:
        return False, "프린터 IP가 설정되지 않았습니다."
    
    if not ESCPOS_AVAILABLE:
        return False, "프린터 라이브러리가 설치되지 않았습니다. (python-escpos)"
    
    try:
        printer = PrinterManager(printer_ip, printer_port)
        results = printer.print_order_3copies(order_data)
        
        # 결과 분석
        success_count = sum(1 for r in results if r['success'])
        
        if success_count == 3:
            return True, "✅ 주문서 3장 출력 완료!"
        elif success_count > 0:
            return True, f"⚠️ {success_count}장 출력 완료 (일부 실패)"
        else:
            return False, f"❌ 출력 실패: {results[0]['message']}"
    
    except Exception as e:
        return False, f"❌ 프린터 오류: {str(e)}"


def test_printer_connection(printer_ip, printer_port=9100):
    """프린터 연결 테스트"""
    if not printer_ip:
        return False, "프린터 IP 주소를 입력해주세요."
    
    if not ESCPOS_AVAILABLE:
        return False, "python-escpos 라이브러리가 설치되지 않았습니다."
    
    try:
        printer = PrinterManager(printer_ip, printer_port)
        return printer.test_print()
    except Exception as e:
        return False, f"연결 테스트 실패: {str(e)}"


def format_order_for_print(order_id, order_time, store_name, order_content, 
                           address="", customer_phone="", total_price="", request=""):
    """주문 데이터 포맷팅"""
    return {
        'order_id': order_id,
        'order_time': order_time,
        'store_name': store_name,
        'order_content': order_content,
        'address': address,
        'customer_phone': customer_phone,
        'total_price': total_price,
        'request': request
    }


# ==========================================
# 📱 블루투스 프린터 웹 연동 (JavaScript)
# ==========================================
def get_bluetooth_printer_js():
    """블루투스 프린터 연결을 위한 JavaScript 코드"""
    return """
    <script>
    // Web Bluetooth API로 ESC/POS 프린터 연결
    let bluetoothDevice = null;
    let printerCharacteristic = null;
    
    async function connectBluetoothPrinter() {
        try {
            // 블루투스 장치 선택
            bluetoothDevice = await navigator.bluetooth.requestDevice({
                filters: [
                    { services: ['000018f0-0000-1000-8000-00805f9b34fb'] },  // 일반 프린터
                    { namePrefix: 'PT-' },  // 휴대용 프린터
                    { namePrefix: 'MTP-' },
                    { namePrefix: 'SPP-' },
                    { namePrefix: 'BT-' }
                ],
                optionalServices: ['000018f0-0000-1000-8000-00805f9b34fb']
            });
            
            const server = await bluetoothDevice.gatt.connect();
            const service = await server.getPrimaryService('000018f0-0000-1000-8000-00805f9b34fb');
            printerCharacteristic = await service.getCharacteristic('00002af1-0000-1000-8000-00805f9b34fb');
            
            // 연결 성공 알림
            alert('✅ 블루투스 프린터 연결 성공!\\n장치: ' + bluetoothDevice.name);
            
            // 연결 정보 저장
            window.parent.postMessage({
                type: 'bluetooth_connected',
                device_name: bluetoothDevice.name,
                device_id: bluetoothDevice.id
            }, '*');
            
            return true;
        } catch (error) {
            console.error('블루투스 연결 실패:', error);
            alert('❌ 블루투스 연결 실패\\n' + error.message);
            return false;
        }
    }
    
    async function printViaBluetoothFromText(text) {
        if (!printerCharacteristic) {
            alert('먼저 프린터를 연결해주세요.');
            return false;
        }
        
        try {
            const encoder = new TextEncoder();
            const data = encoder.encode(text);
            
            // 데이터를 20바이트 청크로 나눠서 전송
            const chunkSize = 20;
            for (let i = 0; i < data.length; i += chunkSize) {
                const chunk = data.slice(i, i + chunkSize);
                await printerCharacteristic.writeValue(chunk);
                await new Promise(resolve => setTimeout(resolve, 50));
            }
            
            return true;
        } catch (error) {
            console.error('출력 실패:', error);
            alert('❌ 출력 실패: ' + error.message);
            return false;
        }
    }
    
    function disconnectBluetoothPrinter() {
        if (bluetoothDevice && bluetoothDevice.gatt.connected) {
            bluetoothDevice.gatt.disconnect();
            alert('프린터 연결이 해제되었습니다.');
        }
    }
    </script>
    """


def get_bluetooth_printer_ui():
    """블루투스 프린터 설정 UI (Streamlit용 HTML)"""
    return """
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 1.5rem; border-radius: 15px; color: white; margin: 1rem 0;">
        <h3 style="margin: 0 0 1rem 0; color: white;">📱 블루투스 프린터 연결</h3>
        <p style="margin: 0 0 1rem 0; opacity: 0.9; font-size: 0.9rem;">
            핸드폰에서 블루투스 프린터를 직접 연결할 수 있습니다.
        </p>
        
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button onclick="connectBluetoothPrinter()" 
                    style="background: #4CAF50; color: white; border: none; 
                           padding: 12px 24px; border-radius: 25px; cursor: pointer;
                           font-weight: bold; font-size: 1rem;">
                🔗 프린터 연결
            </button>
            <button onclick="disconnectBluetoothPrinter()" 
                    style="background: #f44336; color: white; border: none; 
                           padding: 12px 24px; border-radius: 25px; cursor: pointer;
                           font-weight: bold; font-size: 1rem;">
                ❌ 연결 해제
            </button>
        </div>
        
        <div id="bt-status" style="margin-top: 1rem; padding: 0.5rem; 
                                    background: rgba(255,255,255,0.2); border-radius: 10px;">
            <span id="bt-status-text">연결 대기 중...</span>
        </div>
    </div>
    
    <div style="background: #f8f9fa; padding: 1rem; border-radius: 10px; margin-top: 1rem;">
        <h4 style="margin: 0 0 0.5rem 0;">📋 지원 프린터</h4>
        <ul style="margin: 0; padding-left: 1.5rem; color: #666;">
            <li>Epson TM 시리즈</li>
            <li>Star Micronics</li>
            <li>Bixolon SPP 시리즈</li>
            <li>XPrinter / GOOJPRT 휴대용 프린터</li>
            <li>기타 ESC/POS 호환 블루투스 프린터</li>
        </ul>
    </div>
    """


def get_bluetooth_setup_guide():
    """블루투스 프린터 설정 가이드"""
    return """
## 📱 블루투스 프린터 연결 가이드

### 1️⃣ 프린터 준비
1. 블루투스 프린터 전원을 켭니다
2. 프린터의 블루투스 모드가 활성화되어 있는지 확인합니다
3. 프린터 이름을 확인합니다 (예: PT-210, SPP-R200 등)

### 2️⃣ 핸드폰 블루투스 설정
1. **설정 → 블루투스**로 이동
2. 블루투스를 **켬**으로 설정
3. 프린터가 목록에 나타나면 **페어링** 진행
4. PIN 코드 입력 (보통 `0000` 또는 `1234`)

### 3️⃣ 웹앱에서 연결
1. 위의 **[🔗 프린터 연결]** 버튼 클릭
2. 브라우저에서 프린터 선택
3. 연결 완료!

### ⚠️ 주의사항
- **Chrome, Edge, Opera** 브라우저에서만 블루투스 연결 지원
- Safari, Firefox는 Web Bluetooth 미지원
- HTTPS 환경에서만 작동합니다

### 🔧 문제 해결
- 프린터가 목록에 없으면: 프린터를 껐다 켜고 다시 검색
- 연결 실패 시: 핸드폰 블루투스를 껐다 켜고 재시도
- 출력 안됨: 프린터 용지 및 배터리 확인
"""


def get_printer_connection_type_html():
    """프린터 연결 유형 선택 UI"""
    return """
    <style>
    .printer-type-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s;
    }
    .printer-type-card:hover {
        border-color: #667eea;
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
        transform: translateY(-3px);
    }
    .printer-type-card.selected {
        border-color: #667eea;
        background: linear-gradient(135deg, #667eea10 0%, #764ba210 100%);
    }
    .printer-icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    .printer-type-name {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 0.3rem;
    }
    .printer-type-desc {
        font-size: 0.85rem;
        color: #666;
    }
    </style>
    """

