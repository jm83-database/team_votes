from flask import Flask, render_template, jsonify, request, Response
import os
import json
import datetime
import csv
from io import StringIO
from datetime import timezone, timedelta

app = Flask(__name__)

# 한국 시간대 설정 (KST = UTC+9)
KST = timezone(timedelta(hours=9))

def get_kst_now():
    """현재 한국 시간을 반환하는 함수"""
    return datetime.datetime.now(KST)

# 데이터 파일 경로
STUDENTS_FILE = 'students.json'
TEAMS_FILE = 'teams.json'
VOTES_FILE = 'votes.json'

# 전역 변수
students = []
teams = []
votes = []

def load_data():
    """모든 데이터 파일을 로드합니다."""
    global students, teams, votes
    
    # 학생 데이터 로드
    try:
        if os.path.exists(STUDENTS_FILE):
            with open(STUDENTS_FILE, 'r', encoding='utf-8') as f:
                students = json.load(f)
        else:
            students = []
    except Exception as e:
        print(f"학생 데이터 로드 중 오류: {e}")
        students = []
    
    # 팀 데이터 로드
    try:
        if os.path.exists(TEAMS_FILE):
            with open(TEAMS_FILE, 'r', encoding='utf-8') as f:
                teams = json.load(f)
        else:
            teams = []
    except Exception as e:
        print(f"팀 데이터 로드 중 오류: {e}")
        teams = []
    
    # 투표 데이터 로드
    try:
        if os.path.exists(VOTES_FILE):
            with open(VOTES_FILE, 'r', encoding='utf-8') as f:
                votes = json.load(f)
        else:
            votes = []
    except Exception as e:
        print(f"투표 데이터 로드 중 오류: {e}")
        votes = []
        
    print(f"데이터 로드 완료: 학생 {len(students)}명, 팀 {len(teams)}개, 투표 {len(votes)}개")

def save_students():
    """학생 데이터를 저장합니다."""
    try:
        with open(STUDENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(students, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"학생 데이터 저장 중 오류: {e}")

def save_teams():
    """팀 데이터를 저장합니다."""
    try:
        with open(TEAMS_FILE, 'w', encoding='utf-8') as f:
            json.dump(teams, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"팀 데이터 저장 중 오류: {e}")

def save_votes():
    """투표 데이터를 저장합니다."""
    try:
        with open(VOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(votes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"투표 데이터 저장 중 오류: {e}")

def update_team_vote_counts():
    """팀별 투표 수를 업데이트합니다."""
    # 모든 팀의 투표 수를 0으로 초기화
    for team in teams:
        team['vote_count'] = 0
    
    # 투표 데이터를 기반으로 각 팀의 투표 수 계산
    for vote in votes:
        team_id = vote.get('voted_team_id')
        if team_id:
            for team in teams:
                if team['id'] == team_id:
                    team['vote_count'] = team.get('vote_count', 0) + 1
                    break

# 애플리케이션 시작 시 데이터 로드
load_data()

@app.route('/')
def index():
    return render_template('index.html')

# API: 학생 로그인
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '')
    
    if not name or not password:
        return jsonify({"success": False, "message": "이름과 비밀번호를 입력해주세요."}), 400
    
    # 학생 찾기
    for student in students:
        if student['name'].lower() == name.lower():
            if student['password'] == password:
                # 비밀번호를 제외한 학생 정보 반환
                student_info = {k: v for k, v in student.items() if k != 'password'}
                return jsonify({
                    "success": True, 
                    "student": student_info,
                    "message": "로그인 성공"
                })
            else:
                return jsonify({"success": False, "message": "비밀번호가 일치하지 않습니다."}), 401
    
    return jsonify({"success": False, "message": "등록되지 않은 학생입니다."}), 404

# API: 투표 가능한 팀 목록 조회
@app.route('/api/teams/<int:student_id>')
def get_votable_teams(student_id):
    # 학생의 팀 ID 찾기
    student_team_id = None
    for student in students:
        if student['id'] == student_id:
            student_team_id = student['team_id']
            break
    
    if student_team_id is None:
        return jsonify({"success": False, "message": "학생을 찾을 수 없습니다."}), 404
    
    # 자신의 팀을 제외한 팀 목록 반환
    votable_teams = []
    for team in teams:
        if team['id'] != student_team_id:
            votable_teams.append({
                "id": team['id'],
                "name": team['name'],
                "project_name": team.get('project_name', ''),
                "vote_count": team.get('vote_count', 0)
            })
    
    return jsonify({"success": True, "teams": votable_teams})

# API: 투표하기
@app.route('/api/vote', methods=['POST'])
def vote():
    data = request.json
    student_id = data.get('student_id')
    team_id = data.get('team_id')
    
    if not student_id or not team_id:
        return jsonify({"success": False, "message": "학생 ID와 팀 ID가 필요합니다."}), 400
    
    # 학생 찾기
    student = None
    for s in students:
        if s['id'] == student_id:
            student = s
            break
    
    if not student:
        return jsonify({"success": False, "message": "학생을 찾을 수 없습니다."}), 404
    
    # 이미 투표했는지 확인
    if student.get('has_voted', False):
        return jsonify({"success": False, "message": "이미 투표하셨습니다."}), 400
    
    # 자신의 팀에 투표하는지 확인
    if student['team_id'] == team_id:
        return jsonify({"success": False, "message": "자신의 팀에는 투표할 수 없습니다."}), 400
    
    # 투표 대상 팀이 존재하는지 확인
    target_team = None
    for team in teams:
        if team['id'] == team_id:
            target_team = team
            break
    
    if not target_team:
        return jsonify({"success": False, "message": "투표 대상 팀을 찾을 수 없습니다."}), 404
    
    # 투표 처리
    current_time = get_kst_now()
    
    # 학생 투표 상태 업데이트
    student['has_voted'] = True
    student['voted_team'] = team_id
    student['vote_timestamp'] = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 투표 기록 저장
    vote_record = {
        "id": len(votes) + 1,
        "student_id": student_id,
        "student_name": student['name'],
        "voted_team_id": team_id,
        "voted_team_name": target_team['name'],
        "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
    }
    votes.append(vote_record)
    
    # 팀 투표 수 업데이트
    update_team_vote_counts()
    
    # 데이터 저장
    save_students()
    save_votes()
    save_teams()
    
    return jsonify({
        "success": True, 
        "message": f"{target_team['name']}에 투표가 완료되었습니다!"
    })

# API: 관리자 - 모든 학생 목록
@app.route('/api/admin/students', methods=['GET'])
def get_all_students():
    # 비밀번호를 제외한 학생 정보 반환
    students_without_password = []
    for student in students:
        student_data = {k: v for k, v in student.items() if k != 'password'}
        # 팀 이름 추가
        for team in teams:
            if team['id'] == student['team_id']:
                student_data['team_name'] = team['name']
                break
        students_without_password.append(student_data)
    
    return jsonify(students_without_password)

# API: 관리자 - 모든 팀 목록
@app.route('/api/admin/teams', methods=['GET'])
def get_all_teams():
    # 팀 투표 수 업데이트
    update_team_vote_counts()
    save_teams()
    
    return jsonify(teams)

# API: 관리자 - 투표 결과
@app.route('/api/admin/votes', methods=['GET'])
def get_vote_results():
    # 팀별 투표 수 업데이트
    update_team_vote_counts()
    
    # 투표 결과 요약
    total_votes = len(votes)
    total_students = len(students)
    voted_students = len([s for s in students if s.get('has_voted', False)])
    
    return jsonify({
        "total_votes": total_votes,
        "total_students": total_students,
        "voted_students": voted_students,
        "votes": votes,
        "teams": teams
    })

# API: 관리자 - 로그인 인증
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    admin_password = data.get('admin_password')
    
    if admin_password != 'elixirrteacher':  # 관리자 비밀번호
        return jsonify({"success": False, "message": "관리자 비밀번호가 올바르지 않습니다."}), 401
    
    return jsonify({"success": True, "message": "관리자 로그인 성공"})

# API: 관리자 - 투표 초기화
@app.route('/api/admin/reset', methods=['POST'])
def reset_votes():
    data = request.json
    admin_password = data.get('admin_password')
    
    if admin_password != 'elixirrteacher':  # 관리자 비밀번호
        return jsonify({"success": False, "message": "관리자 비밀번호가 올바르지 않습니다."}), 401
    
    # 학생 투표 상태 초기화
    for student in students:
        student['has_voted'] = False
        student['voted_team'] = None
        student['vote_timestamp'] = None
    
    # 투표 기록 삭제
    global votes
    votes = []
    
    # 팀 투표 수 초기화
    for team in teams:
        team['vote_count'] = 0
    
    # 데이터 저장
    save_students()
    save_votes()
    save_teams()
    
    return jsonify({"success": True, "message": "투표가 초기화되었습니다."})

# API: 관리자 - 투표 결과 CSV 다운로드
@app.route('/api/admin/download', methods=['GET'])
def download_results():
    try:
        # CSV 버퍼 생성
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        
        # 헤더 작성
        csv_writer.writerow(['투표자', '투표자팀', '투표받은팀', '프로젝트명', '투표시간'])
        
        # 투표 데이터 작성
        for vote in votes:
            # 투표자 팀 이름 찾기
            voter_team = ""
            for student in students:
                if student['id'] == vote['student_id']:
                    for team in teams:
                        if team['id'] == student['team_id']:
                            voter_team = team['name']
                            break
                    break
            
            # 투표받은 팀 프로젝트명 찾기
            project_name = ""
            for team in teams:
                if team['id'] == vote['voted_team_id']:
                    project_name = team.get('project_name', '')
                    break
            
            csv_writer.writerow([
                vote['student_name'],
                voter_team,
                vote['voted_team_name'],
                project_name,
                vote['timestamp']
            ])
        
        # 팀별 투표 결과 요약 추가
        csv_writer.writerow([])  # 빈 줄
        csv_writer.writerow(['=== 팀별 투표 결과 ==='])
        csv_writer.writerow(['팀명', '프로젝트명', '받은 투표수'])
        
        # 투표 수 기준 내림차순 정렬
        sorted_teams = sorted(teams, key=lambda x: x.get('vote_count', 0), reverse=True)
        
        for team in sorted_teams:
            csv_writer.writerow([
                team['name'],
                team.get('project_name', ''),
                team.get('vote_count', 0)
            ])
        
        csv_buffer.seek(0)
        
        # 파일명 생성
        now = get_kst_now().strftime("%Y%m%d_%H%M")
        filename = f"vote_results_{now}.csv"
        
        return Response(
            csv_buffer.getvalue().encode('utf-8-sig'),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
        
    except Exception as e:
        print(f"CSV 다운로드 중 오류: {e}")
        return jsonify({"success": False, "message": f"오류 발생: {e}"}), 500

if __name__ == '__main__':
    print("팀 투표 시스템을 시작합니다...")
    print("개발 서버 주소: http://localhost:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)