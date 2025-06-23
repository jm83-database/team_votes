#!/usr/bin/env python3
"""
팀 투표 시스템 Playwright 테스트 스크립트
"""

import asyncio
import subprocess
import time
import sys
import requests
from playwright.async_api import async_playwright

class TeamVoteTests:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.server_process = None
        
    async def start_server(self):
        """Flask 서버 시작"""
        print("Flask 서버를 시작합니다...")
        try:
            # 서버가 이미 실행 중인지 확인
            response = requests.get(self.base_url, timeout=2)
            print("서버가 이미 실행 중입니다.")
            return True
        except:
            print("서버를 시작합니다...")
            return False
            
    async def wait_for_server(self, timeout=30):
        """서버가 응답할 때까지 대기"""
        print("서버 응답을 기다리는 중...")
        for _ in range(timeout):
            try:
                response = requests.get(self.base_url, timeout=2)
                if response.status_code == 200:
                    print("서버가 응답합니다!")
                    return True
            except:
                pass
            time.sleep(1)
        return False
        
    async def test_page_load(self, page):
        """페이지 로드 테스트"""
        print("\n=== 페이지 로드 테스트 ===")
        await page.goto(self.base_url)
        
        # 페이지 제목 확인
        title = await page.title()
        assert "팀 프로젝트 투표 시스템" in title, f"페이지 제목이 올바르지 않습니다: {title}"
        print("✓ 페이지 제목이 올바릅니다")
        
        # 메인 헤더 확인
        header = await page.locator("h1").first.text_content()
        assert "팀 프로젝트 투표 시스템" in header, "메인 헤더를 찾을 수 없습니다"
        print("✓ 메인 헤더가 표시됩니다")
        
        # 학생 모드와 관리자 모드 버튼 확인
        student_button = page.locator("button:has-text('학생 모드')")
        admin_button = page.locator("button:has-text('관리자 모드')")
        
        await student_button.wait_for(state="visible")
        await admin_button.wait_for(state="visible")
        print("✓ 모드 선택 버튼들이 표시됩니다")
        
    async def test_student_login(self, page):
        """학생 로그인 테스트"""
        print("\n=== 학생 로그인 테스트 ===")
        await page.goto(self.base_url)
        
        # 학생 모드 선택 (기본값이지만 명시적으로 클릭)
        await page.locator("button:has-text('학생 모드')").click()
        
        # 로그인 폼 확인
        await page.locator("input[name='name']").wait_for(state="visible")
        await page.locator("input[name='password']").wait_for(state="visible")
        print("✓ 로그인 폼이 표시됩니다")
        
        # 잘못된 로그인 시도
        await page.fill("input[name='name']", "존재하지않는사용자")
        await page.fill("input[name='password']", "wrongpassword")
        await page.click("button[type='submit']")
        
        # 에러 메시지 확인
        error_message = page.locator(".bg-red-500")
        await error_message.wait_for(state="visible", timeout=5000)
        print("✓ 잘못된 로그인 시 에러 메시지가 표시됩니다")
        
        # 올바른 로그인
        await page.fill("input[name='name']", "김민준")
        await page.fill("input[name='password']", "1234")
        await page.click("button[type='submit']")
        
        # 로그인 성공 확인
        welcome_message = page.locator("text=안녕하세요, 김민준님!")
        await welcome_message.wait_for(state="visible", timeout=5000)
        print("✓ 올바른 로그인 시 환영 메시지가 표시됩니다")
        
    async def test_voting_process(self, page):
        """투표 과정 테스트"""
        print("\n=== 투표 과정 테스트 ===")
        
        # 김민준으로 이미 로그인된 상태에서 시작
        # 투표 가능한 팀 목록 확인
        team_cards = page.locator(".vote-card")
        team_count = await team_cards.count()
        assert team_count >= 2, "투표 가능한 팀이 충분하지 않습니다"
        print(f"✓ {team_count}개의 팀이 표시됩니다")
        
        # 첫 번째 팀 선택
        first_team = team_cards.first
        await first_team.click()
        
        # 선택된 팀 확인
        selected_team = page.locator(".vote-card.selected")
        await selected_team.wait_for(state="visible")
        print("✓ 팀 선택이 정상적으로 작동합니다")
        
        # 투표 버튼 확인 및 클릭
        vote_button = page.locator("button:has-text('투표하기')")
        await vote_button.wait_for(state="visible")
        await vote_button.click()
        
        # 투표 완료 메시지 확인
        success_message = page.locator(".bg-green-500")
        await success_message.wait_for(state="visible", timeout=5000)
        print("✓ 투표 완료 메시지가 표시됩니다")
        
        # 투표 완료 페이지 확인
        completion_message = page.locator("text=투표 완료!")
        await completion_message.wait_for(state="visible", timeout=5000)
        print("✓ 투표 완료 페이지가 표시됩니다")
        
    async def test_admin_mode(self, page):
        """관리자 모드 테스트"""
        print("\n=== 관리자 모드 테스트 ===")
        await page.goto(self.base_url)
        
        # 관리자 모드 선택
        await page.click("button:has-text('관리자 모드')")
        
        # 관리자 대시보드 확인
        dashboard_title = page.locator("text=관리자 대시보드")
        await dashboard_title.wait_for(state="visible")
        print("✓ 관리자 대시보드가 표시됩니다")
        
        # 통계 정보 확인
        total_students = page.locator("text=전체 학생")
        voted_students = page.locator("text=투표 완료")
        vote_rate = page.locator("text=투표율")
        
        await total_students.wait_for(state="visible")
        await voted_students.wait_for(state="visible")
        await vote_rate.wait_for(state="visible")
        print("✓ 통계 정보가 표시됩니다")
        
        # 탭 전환 테스트
        students_tab = page.locator("button:has-text('학생 현황')")
        await students_tab.click()
        
        # 학생 현황 테이블 확인
        student_table = page.locator("table")
        await student_table.wait_for(state="visible")
        print("✓ 학생 현황 테이블이 표시됩니다")
        
        # 투표 결과 탭으로 돌아가기
        results_tab = page.locator("button:has-text('투표 결과')")
        await results_tab.click()
        
        team_results = page.locator("text=팀별 투표 결과")
        await team_results.wait_for(state="visible")
        print("✓ 팀별 투표 결과가 표시됩니다")
        
    async def test_api_endpoints(self, page):
        """API 엔드포인트 테스트"""
        print("\n=== API 엔드포인트 테스트 ===")
        
        # 학생 목록 API 테스트
        response = await page.evaluate("""
            fetch('/api/admin/students').then(r => r.json())
        """)
        assert isinstance(response, list), "학생 목록 API가 올바른 형식을 반환하지 않습니다"
        print("✓ 학생 목록 API가 정상 작동합니다")
        
        # 팀 목록 API 테스트
        response = await page.evaluate("""
            fetch('/api/admin/teams').then(r => r.json())
        """)
        assert isinstance(response, list), "팀 목록 API가 올바른 형식을 반환하지 않습니다"
        print("✓ 팀 목록 API가 정상 작동합니다")
        
        # 투표 결과 API 테스트
        response = await page.evaluate("""
            fetch('/api/admin/votes').then(r => r.json())
        """)
        assert 'total_votes' in response, "투표 결과 API가 올바른 형식을 반환하지 않습니다"
        print("✓ 투표 결과 API가 정상 작동합니다")
        
    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("팀 투표 시스템 Playwright 테스트를 시작합니다...\n")
        
        # 서버 시작 및 대기
        if not await self.start_server():
            if not await self.wait_for_server():
                print("❌ 서버를 시작할 수 없습니다.")
                return False
                
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # headless=False로 브라우저 창 표시
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # 각 테스트 실행
                await self.test_page_load(page)
                await self.test_student_login(page)
                await self.test_voting_process(page)
                await self.test_admin_mode(page)
                await self.test_api_endpoints(page)
                
                print("\n" + "="*50)
                print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
                print("="*50)
                return True
                
            except Exception as e:
                print(f"\n❌ 테스트 실패: {e}")
                return False
            finally:
                await browser.close()

async def main():
    """메인 함수"""
    tester = TeamVoteTests()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)