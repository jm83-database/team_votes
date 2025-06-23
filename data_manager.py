#!/usr/bin/env python3
"""
팀 투표 시스템 데이터 관리 유틸리티
교육과정별로 학생과 팀 데이터를 쉽게 변경할 수 있는 스크립트
"""

import json
import csv
import sys
from typing import List, Dict

def load_json(filename: str) -> List[Dict]:
    """JSON 파일을 로드합니다."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {filename}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON 형식 오류: {e}")
        return []

def save_json(filename: str, data: List[Dict]) -> bool:
    """JSON 파일로 저장합니다."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ {filename} 파일이 저장되었습니다.")
        return True
    except Exception as e:
        print(f"✗ 저장 실패: {e}")
        return False

def create_sample_data():
    """샘플 데이터를 생성합니다."""
    print("샘플 데이터를 생성합니다...")
    
    # 샘플 학생 데이터
    students = [
        {"id": 1, "name": "김민준", "password": "1234", "team_id": 1, "has_voted": False, "voted_team": None, "vote_timestamp": None},
        {"id": 2, "name": "이서연", "password": "2345", "team_id": 1, "has_voted": False, "voted_team": None, "vote_timestamp": None},
        {"id": 3, "name": "박지호", "password": "3456", "team_id": 2, "has_voted": False, "voted_team": None, "vote_timestamp": None},
        {"id": 4, "name": "최수아", "password": "4567", "team_id": 2, "has_voted": False, "voted_team": None, "vote_timestamp": None},
        {"id": 5, "name": "정우진", "password": "5678", "team_id": 3, "has_voted": False, "voted_team": None, "vote_timestamp": None},
        {"id": 6, "name": "황예은", "password": "6789", "team_id": 3, "has_voted": False, "voted_team": None, "vote_timestamp": None},
    ]
    
    # 샘플 팀 데이터
    teams = [
        {"id": 1, "name": "A팀", "project_name": "AI 챗봇 개발", "members": [1, 2], "vote_count": 0},
        {"id": 2, "name": "B팀", "project_name": "스마트 홈 IoT 시스템", "members": [3, 4], "vote_count": 0},
        {"id": 3, "name": "C팀", "project_name": "모바일 학습 관리 앱", "members": [5, 6], "vote_count": 0},
    ]
    
    # 빈 투표 데이터
    votes = []
    
    save_json('students.json', students)
    save_json('teams.json', teams)
    save_json('votes.json', votes)
    
    print("샘플 데이터 생성이 완료되었습니다.")

def import_from_csv():
    """CSV 파일에서 학생 데이터를 가져옵니다."""
    csv_file = input("CSV 파일 경로를 입력하세요: ").strip()
    
    try:
        students = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                student = {
                    "id": i,
                    "name": row.get('name', row.get('이름', '')),
                    "password": row.get('password', row.get('비밀번호', str(1000 + i))),
                    "team_id": int(row.get('team_id', row.get('팀ID', 1))),
                    "has_voted": False,
                    "voted_team": None,
                    "vote_timestamp": None
                }
                students.append(student)
        
        if save_json('students.json', students):
            print(f"✓ {len(students)}명의 학생 데이터를 가져왔습니다.")
        
    except FileNotFoundError:
        print("CSV 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"CSV 가져오기 실패: {e}")

def reset_votes():
    """모든 투표 데이터를 초기화합니다."""
    confirm = input("모든 투표 데이터를 초기화하시겠습니까? (y/N): ")
    if confirm.lower() == 'y':
        # 학생 투표 상태 초기화
        students = load_json('students.json')
        for student in students:
            student['has_voted'] = False
            student['voted_team'] = None
            student['vote_timestamp'] = None
        
        # 팀 투표 수 초기화
        teams = load_json('teams.json')
        for team in teams:
            team['vote_count'] = 0
        
        # 투표 기록 초기화
        votes = []
        
        save_json('students.json', students)
        save_json('teams.json', teams)
        save_json('votes.json', votes)
        
        print("✓ 모든 투표 데이터가 초기화되었습니다.")
    else:
        print("취소되었습니다.")

def export_student_passwords():
    """학생 비밀번호를 CSV로 내보냅니다."""
    students = load_json('students.json')
    if not students:
        print("학생 데이터가 없습니다.")
        return
    
    filename = 'student_passwords.csv'
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['학생ID', '이름', '비밀번호', '팀ID'])
            for student in students:
                writer.writerow([
                    student['id'],
                    student['name'],
                    student['password'],
                    student['team_id']
                ])
        print(f"✓ {filename} 파일로 비밀번호가 내보내졌습니다.")
    except Exception as e:
        print(f"✗ 내보내기 실패: {e}")

def show_status():
    """현재 데이터 상태를 표시합니다."""
    students = load_json('students.json')
    teams = load_json('teams.json')
    votes = load_json('votes.json')
    
    print("\n=== 현재 데이터 상태 ===")
    print(f"학생 수: {len(students)}명")
    print(f"팀 수: {len(teams)}개")
    print(f"투표 수: {len(votes)}개")
    
    if students:
        voted_count = sum(1 for s in students if s.get('has_voted', False))
        print(f"투표 완료: {voted_count}명 ({voted_count/len(students)*100:.1f}%)")
    
    print("\n=== 팀별 현황 ===")
    for team in teams:
        member_names = []
        for student in students:
            if student['team_id'] == team['id']:
                member_names.append(student['name'])
        
        print(f"{team['name']}: {team.get('project_name', '')} (멤버: {', '.join(member_names)}) - 투표 {team.get('vote_count', 0)}표")

def main():
    """메인 메뉴를 표시합니다."""
    while True:
        print("\n" + "=" * 50)
        print("팀 투표 시스템 데이터 관리")
        print("=" * 50)
        print("1. 현재 상태 확인")
        print("2. 샘플 데이터 생성")
        print("3. CSV에서 학생 데이터 가져오기")
        print("4. 투표 데이터 초기화")
        print("5. 학생 비밀번호 CSV 내보내기")
        print("0. 종료")
        print("=" * 50)
        
        choice = input("선택하세요 (0-5): ").strip()
        
        if choice == '1':
            show_status()
        elif choice == '2':
            create_sample_data()
        elif choice == '3':
            import_from_csv()
        elif choice == '4':
            reset_votes()
        elif choice == '5':
            export_student_passwords()
        elif choice == '0':
            print("프로그램을 종료합니다.")
            break
        else:
            print("올바른 번호를 선택해주세요.")

if __name__ == "__main__":
    main()