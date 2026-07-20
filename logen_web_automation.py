"""
로젠 웹 자동화 - 프로덕션 강화 버전
✅ try-finally 완전 종료 보장
✅ 단계별 타임아웃 설정
✅ 최대 2회 재시도
✅ 선택자 실패 시 명확한 에러 메시지
"""
import asyncio
import os
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/var/playwright"

LOGEN_ID = "71050257"
LOGEN_PW = "ab30695810"
API_BASE = "https://logis.ilogen.com/api/lrm01b-reserve"

PAGE_TIMEOUT = 30_000    # 개별 작업 타임아웃 30초
TOTAL_TIMEOUT = 90       # 전체 실행 타임아웃 90초
MAX_RETRIES = 2          # 최대 재시도 횟수


async def _run_once(order: dict) -> dict:
    """브라우저 1회 실행 - 모든 예외에서 browser.close() 보장"""
    from playwright.async_api import async_playwright

    browser = None
    start = time.time()

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox","--disable-setuid-sandbox",
                      "--disable-dev-shm-usage","--disable-gpu",
                      "--single-process","--memory-pressure-off"]
            )
            ctx = await browser.new_context(locale="ko-KR")
            page = await ctx.new_page()
            page.set_default_timeout(PAGE_TIMEOUT)

            # ── 1. 로그인 ─────────────────────────────────────────
            await page.goto(
                "https://logis.ilogen.com/common/html/login-51b.html",
                wait_until="networkidle", timeout=PAGE_TIMEOUT
            )
            await page.locator('[id="user.id"]').fill(LOGEN_ID)
            await page.locator('[id="user.pw"]').fill(LOGEN_PW)
            await page.locator('a:has-text("로그인")').click()
            await page.wait_for_url("**/main.html", timeout=PAGE_TIMEOUT)
            logger.info(f"[로젠] 로그인 성공 ({time.time()-start:.1f}s)")

            # ── 2. 주문등록 폼 이동 ───────────────────────────────
            links = await page.locator("a").all()
            for lnk in links:
                try:
                    if (await lnk.inner_text(timeout=2000)).strip() == "예약관리":
                        await lnk.dispatch_event("click"); await asyncio.sleep(1); break
                except: pass

            init_done = asyncio.Event()
            async def watch_init(response):
                if "getFixcustInfo" in response.url:
                    await asyncio.sleep(0.3); init_done.set()
            page.on("response", watch_init)

            links = await page.locator("a").all()
            for lnk in links:
                try:
                    txt = (await lnk.inner_text(timeout=2000)).strip()
                    if "주문등록" in txt and "단건" in txt:
                        await lnk.dispatch_event("click"); break
                except: pass

            try: await asyncio.wait_for(init_done.wait(), timeout=12)
            except asyncio.TimeoutError:
                raise RuntimeError("폼 초기화 타임아웃 (getFixcustInfo 미수신) - 로젠 사이트 구조 변경 가능성")
            await asyncio.sleep(1.5)

            # 폼 프레임 검증
            form_frame = next((f for f in page.frames if "lrm01f0050" in f.url), None)
            if not form_frame:
                raise RuntimeError("폼 프레임 미발견 - 로젠 페이지 구조 변경됨")

            # ── 3. 주소 → 건물코드/배송지점 자동 조회 ──────────────
            addr_lookup = await form_frame.evaluate(f"""
                (async function() {{
                    try {{
                        const token = typeof BASE_PC_ACCESS_TOKEN !== 'undefined' ? BASE_PC_ACCESS_TOKEN : null;
                        const pageId = typeof BASE_PC_JS !== 'undefined' ? BASE_PC_JS.getCurrentPageId() : '';
                        const userInfo = typeof BASE_PC_JS !== 'undefined' ? encodeURIComponent(JSON.stringify(BASE_PC_JS.getUserInfo())) : '';
                        const hdrs = {{
                            'Content-Type': 'application/json',
                            'x-token': token, 'x-pageId': pageId, 'x-userInfo': userInfo
                        }};

                        // 수신 주소 파싱 (로젠 내장 함수 사용)
                        const addr = '{order.get("receiver_addr1","")} {order.get("receiver_addr2","")}'.trim();
                        const commParam = typeof fn_addressDivided_new === 'function'
                            ? fn_addressDivided_new(addr.replace(/  +/g, ' '))
                            : {{schVal: addr, schClass: '2'}};

                        const resp = await fetch('/api/lmm01b-standard/lmm01bp416/pop/addrInfos', {{
                            method: 'POST', headers: hdrs, credentials: 'include',
                            body: JSON.stringify(commParam)
                        }});
                        if (!resp.ok) return {{error: resp.status + ': ' + (await resp.text()).substring(0,100)}};

                        const data = await resp.json();
                        if (!data || data.length === 0) return {{error: '주소 검색 결과 없음: ' + addr}};

                        // 첫 번째 결과 사용 (가장 정확한 매칭)
                        const ent = data[0];
                        return {{
                            bldgCd: ent.bldgCd || '',
                            branCd: ent.branCd || '',
                            branNm: ent.branNm || '',
                            zipCode: ent.bsiZonNo || '',
                            addr1: ent.sidoNam + ' ' + ent.sigunguNam + ' ' + ent.dongRoadNam + ' ' + ent.strcNum + '(' + ent.dongRiNam + ' ' + ent.bunjiHo + ')',
                            resultCount: data.length
                        }};
                    }} catch(e) {{ return {{error: e.toString()}}; }}
                }})()
            """)

            if 'error' in addr_lookup:
                raise RuntimeError(f"주소 조회 실패: {addr_lookup['error']}")

            logger.info(f"[로젠] 주소 조회: bldgCd={addr_lookup['bldgCd']}, branCd={addr_lookup['branCd']}({addr_lookup['branNm']}), 결과 {addr_lookup['resultCount']}건")


            today = datetime.now().strftime("%Y-%m-%d")
            js_fill = f"""(function() {{
                function setField(id, val) {{
                    const el = document.getElementById(id) || document.querySelector('[name="' + id + '"]');
                    if (!el) return false;
                    el.removeAttribute('disabled'); el.removeAttribute('readonly');
                    el.value = val;
                    ['input','change','blur'].forEach(ev => el.dispatchEvent(new Event(ev, {{bubbles:true}})));
                    return true;
                }}
                const results = {{}};
                results.date   = setField('yearMonthDaySelect1', '{today}');
                results.sndNm  = setField('strSndCustNm', '탄탄제작소');
                results.sndTel = setField('strSndCustTelNo', '01023847447');
                results.sndCell= setField('strSndCustCellNo', '01023847447');
                results.sndAddr= setField('strSndCustAddr1', '강원도 태백시 황지동');
                results.sndAddr2=setField('strSndCustAddr2', '123-1');
                results.sndZip = setField('strSndZipCd', '26000');
                results.pickBr = setField('strPickBranCd', '710');
                results.pickNm = setField('strPickBranNm', '태백');
                results.rcvNm  = setField('strRcvCustNm', '{order.get("receiver_name","")}');
                results.rcvTel = setField('strRcvCustTelNo', '{order.get("receiver_phone","")}');
                results.rcvCell= setField('strRcvCustCellNo', '{order.get("receiver_phone","")}');
                results.rcvAddr= setField('strRcvCustAddr1', '{order.get("receiver_addr1","")}');
                results.rcvAddr2=setField('strRcvCustAddr2', '{order.get("receiver_addr2","")}');
                results.rcvZip = setField('strRcvZipCd', '{addr_lookup["zipCode"]}');
                results.rcvBldg= setField('strRcvBldgCd', '{addr_lookup["bldgCd"]}');
                results.dlvBr  = setField('strDlvBranCd', '{addr_lookup["branCd"]}');
                results.dlvNm  = setField('strDlvBranNm', '{addr_lookup["branNm"]}');
                results.item   = setField('strItemNm', '{order.get("item_name","일반상품")}');
                results.qty    = setField('strQty', '{order.get("item_qty",1)}');
                results.wt     = setField('strWT', '{order.get("item_weight",3)}');
                results.amt    = setField('strGoodAmt', '{order.get("item_price",30000)}');
                results.msg    = setField('strDlvMsg', '{order.get("message","")}');

                // 필수 필드 누락 검증
                const missing = Object.entries(results)
                    .filter(([k,v]) => !v && !['rcvAddr2','msg'].includes(k))
                    .map(([k]) => k);
                return missing.length > 0 ? 'MISSING:' + missing.join(',') : 'OK';
            }})()"""
            res = await form_frame.evaluate(js_fill)
            if res.startswith("MISSING:"):
                raise RuntimeError(f"폼 필드 누락: {res} - 로젠 DOM 구조 변경됨")
            logger.info(f"[로젠] 폼 입력 완료 ({time.time()-start:.1f}s)")

            # ── 4. 저장 ───────────────────────────────────────────
            list_response = []
            save_ok = False

            async def capture_apis(response):
                nonlocal save_ok
                try:
                    if "saveResv" in response.url:
                        b = await response.json()
                        if b.get('rtnNo') == '99': save_ok = True
                    elif "getResvList" in response.url:
                        b = await response.json()
                        list_response.clear()
                        list_response.extend(b if isinstance(b, list) else [])
                except: pass

            page.on("response", capture_apis)
            page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

            await form_frame.evaluate("fn_save()")
            await asyncio.sleep(4)

            if not save_ok:
                raise RuntimeError("주문 저장 실패 (saveResv rtnNo != 99)")
            logger.info(f"[로젠] 저장 성공 ({time.time()-start:.1f}s)")

            # ── 5. 목록 조회 ──────────────────────────────────────
            await form_frame.evaluate("fn_retrieve('noprint')")
            await asyncio.sleep(5)

            if not list_response:
                raise RuntimeError("주문 목록 조회 실패 (getResvList 응답 없음)")

            our_order = sorted(list_response, key=lambda x: int(x.get('seq',0)), reverse=True)[0]
            seq = our_order.get('seq')
            ord_seq = our_order.get('ordSeq','99')
            take_dt = our_order.get('takeDt', today.replace('-',''))
            logger.info(f"[로젠] 주문 확인: seq={seq}, rcv={our_order.get('rcvCustNm')} ({time.time()-start:.1f}s)")

            # ── 6. 송장번호 채번 ──────────────────────────────────
            slip_result = await form_frame.evaluate(f"""
                (async function() {{
                    try {{
                        const token = typeof BASE_PC_ACCESS_TOKEN !== 'undefined' ? BASE_PC_ACCESS_TOKEN : null;
                        const pageId = typeof BASE_PC_JS !== 'undefined' ? BASE_PC_JS.getCurrentPageId() : 'lrm01f0050';
                        const userInfo = typeof BASE_PC_JS !== 'undefined' ? encodeURIComponent(JSON.stringify(BASE_PC_JS.getUserInfo())) : '';
                        const hdrs = {{'Content-Type':'application/json','x-token':token,'x-pageId':pageId,'x-userInfo':userInfo}};

                        const r1 = await fetch('{API_BASE}/lrm01bp500/getSlipNoSave', {{
                            method:'POST', headers:hdrs, credentials:'include',
                            body: JSON.stringify({{qty:1}})
                        }});
                        if (!r1.ok) return {{error: 'getSlipNoSave ' + r1.status + ': ' + (await r1.text()).substring(0,200)}};

                        const raw = (await r1.text()).replace(/"/g,'').trim();
                        const base10 = parseInt(raw.substring(0,10));
                        const slipNo = base10.toString() + (base10 % 7).toString();

                        const r2 = await fetch('{API_BASE}/lrm01bp500/updateSlipNo', {{
                            method:'POST', headers:hdrs, credentials:'include',
                            body: JSON.stringify({{
                                gubn:'S',
                                fixcustCd:'{our_order.get("fixcustCd", LOGEN_ID)}',
                                takeDt:'{take_dt}', ordSeq:'{ord_seq}', seq:'{seq}',
                                mgmtFixcust:'{our_order.get("mgmtFixcust", LOGEN_ID)}',
                                takeTy:'{our_order.get("takeTy","100")}',
                                ordQty:{our_order.get("ordQty",1)},
                                dlvFare:{our_order.get("dlvFare",4000)},
                                jejuFare:{our_order.get("jejuFare",0)},
                                shipAmt:{our_order.get("shipAmt",0)},
                                extraAmt:{our_order.get("extraAmt",0)},
                                slipNo:slipNo, newSlipNo:null
                            }})
                        }});
                        if (!r2.ok) return {{error: 'updateSlipNo ' + r2.status}};

                        return {{slipNo, raw, updateOk: true}};
                    }} catch(e) {{ return {{error: e.toString()}}; }}
                }})()
            """)

            if 'error' in slip_result:
                raise RuntimeError(f"채번 실패: {slip_result['error']}")
            if not slip_result.get('updateOk'):
                raise RuntimeError(f"DB 저장 실패: {slip_result}")

            logger.info(f"[로젠] ✅ 송장번호: {slip_result['slipNo']} ({time.time()-start:.1f}s)")
            return {
                "success": True,
                "slip_no": slip_result['slipNo'],
                "seq": seq,
                "pickup_dt": our_order.get("pickExpDt",""),
                "delivery_dt": our_order.get("dlvPlanDt",""),
                "error": None
            }

        finally:
            # ✅ 항상 브라우저 종료 (좀비 프로세스 방지)
            if browser:
                try:
                    await browser.close()
                    logger.debug("[로젠] 브라우저 정상 종료")
                except Exception as e:
                    logger.warning(f"[로젠] 브라우저 종료 경고: {e}")


async def create_logen_waybill(order: dict) -> dict:
    """
    재시도 로직 포함 메인 함수
    최대 MAX_RETRIES회 재시도, 전체 타임아웃 TOTAL_TIMEOUT초
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 2):  # 1, 2, 3 (총 3회 시도)
        if attempt > 1:
            wait = attempt * 5  # 5초, 10초 대기
            logger.info(f"[로젠] {attempt}번째 시도 ({wait}초 후)...")
            await asyncio.sleep(wait)

        try:
            result = await asyncio.wait_for(
                _run_once(order),
                timeout=TOTAL_TIMEOUT
            )
            return result

        except asyncio.TimeoutError:
            last_error = f"전체 타임아웃 ({TOTAL_TIMEOUT}초 초과)"
            logger.error(f"[로젠] 시도 {attempt} 타임아웃")
        except RuntimeError as e:
            last_error = str(e)
            # UI 구조 변경 에러는 재시도 무의미
            if "구조 변경" in last_error or "DOM" in last_error or "프레임" in last_error:
                logger.error(f"[로젠] 구조 변경 감지 - 재시도 중단: {last_error}")
                break
            logger.error(f"[로젠] 시도 {attempt} 실패: {last_error}")
        except Exception as e:
            last_error = str(e)
            logger.error(f"[로젠] 시도 {attempt} 예외: {last_error}")

    return {"success": False, "slip_no": None, "seq": None, "error": last_error}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    test_order = {
        "receiver_name": "테스트고객",
        "receiver_phone": "01099998888",
        "receiver_addr1": "서울특별시 강남구 테헤란로 152",
        "receiver_addr2": "강남파이낸스센터",
        "receiver_zipcode": "06236",
        "item_name": "농산물",
        "item_qty": 1, "item_weight": 3, "item_price": 30000,
        "message": "동네비서 자동접수",
    }
    import asyncio
    result = asyncio.run(create_logen_waybill(test_order))
    print(f"\n{'='*50}\n결과: {result}\n{'='*50}")
