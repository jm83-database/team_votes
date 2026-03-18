from flask import Flask, render_template, jsonify, request, Response, session
from functools import wraps
import os
import json
import re
import datetime
import csv
from io import StringIO
from datetime import timezone, timedelta
from dotenv import load_dotenv
from cosmos_service import CosmosService

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'team-votes-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 파일 업로드 2MB 제한

# 한국 시간대 설정 (KST = UTC+9)
KST = timezone(timedelta(hours=9))

TEACHER_PASSWORD = os.environ.get('TEACHER_PASSWORD', 'elixirrteacher')

# CosmosDB / JSON 이중 모드 서비스
db = CosmosService()

DEFAULT_VOTE_CONFIG = {
    'is_active': False,
    'start_time': None,
    'end_time': None,
    'duration_minutes': 60,
    'vote_mode': 'single'
}

# cohort_id 허용 패턴 (영문, 숫자, 하이픈, 언더스코어만)
COHORT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,50}$')


def validate_cohort_id(cohort_id):
    """cohort_id가 안전한 형식인지 검증 (경로 순회 방지)"""
    if not cohort_id or not COHORT_ID_PATTERN.match(cohort_id):
        return False
    return True


def require_admin(f):
    """관리자 세션 인증 데코레이터"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({"success": False, "message": "관리자 인증이 필요합니다."}), 401
        return f(*args, **kwargs)
    return decorated


def get_kst_now():
    return datetime.datetime.now(KST)


def get_vote_config(cohort_id):
    config = db.load_vote_config(cohort_id)
    if not config:
        config = dict(DEFAULT_VOTE_CONFIG)
    return config


def is_voting_active(cohort_id):
    config = get_vote_config(cohort_id)
    if not config.get('is_active', False):
        return False
    if not config.get('start_time') or not config.get('end_time'):
        return config.get('is_active', False)
    current_time = get_kst_now()
    current_time_str = current_time.strftime("%H:%M")
    return config['start_time'] <= current_time_str <= config['end_time']


def update_team_vote_counts(cohort_id):
    teams = db.load_teams(cohort_id)
    votes = db.load_votes(cohort_id)
    for team in teams:
        team['vote_count'] = 0
    for vote in votes:
        team_id = vote.get('voted_team_id')
        if team_id:
            for team in teams:
                if team['id'] == team_id:
                    team['vote_count'] = team.get('vote_count', 0) + 1
                    break
    db.save_teams(cohort_id, teams)
    return teams


# ========== 페이지 라우트 ==========

@app.route('/')
def index():
    return render_template('index.html')


# ========== 관리자 인증 API ==========

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    admin_password = data.get('admin_password')

    if admin_password != TEACHER_PASSWORD:
        return jsonify({"success": False, "message": "관리자 비밀번호가 올바르지 않습니다."}), 401

    session['is_admin'] = True
    return jsonify({"success": True, "message": "관리자 로그인 성공"})


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('is_admin', None)
    return jsonify({"success": True, "message": "로그아웃 되었습니다."})


@app.route('/api/admin/status', methods=['GET'])
def admin_status():
    return jsonify({"is_admin": session.get('is_admin', False)})


# ========== 과정(코호트) 관리 API (관리자 전용) ==========

@app.route('/api/cohorts', methods=['GET'])
def list_cohorts():
    cohorts = db.load_cohorts()
    return jsonify(cohorts)


@app.route('/api/cohorts', methods=['POST'])
@require_admin
def create_cohort():
    data = request.json
    cohort_id = data.get('cohort_id', '').strip()
    name = data.get('name', '').strip()

    if not cohort_id or not name:
        return jsonify({"success": False, "message": "과정 ID와 이름을 입력해주세요."}), 400

    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "과정 ID는 영문, 숫자, 하이픈, 언더스코어만 사용 가능합니다 (최대 50자)."}), 400

    cohorts = db.load_cohorts()
    if any(c['cohort_id'] == cohort_id for c in cohorts):
        return jsonify({"success": False, "message": "이미 존재하는 과정 ID입니다."}), 400

    cohorts.append({
        "cohort_id": cohort_id,
        "name": name,
        "created_at": get_kst_now().isoformat(),
        "active": True,
        "student_count": 0
    })
    db.save_cohorts(cohorts)
    return jsonify({"success": True, "message": f"과정 '{name}'이(가) 생성되었습니다."})


@app.route('/api/cohorts/<cohort_id>', methods=['PUT'])
@require_admin
def update_cohort(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    data = request.json
    cohorts = db.load_cohorts()
    for c in cohorts:
        if c['cohort_id'] == cohort_id:
            if 'name' in data:
                c['name'] = data['name']
            if 'active' in data:
                c['active'] = data['active']
            db.save_cohorts(cohorts)
            return jsonify({"success": True, "message": "과정이 업데이트되었습니다."})
    return jsonify({"success": False, "message": "과정을 찾을 수 없습니다."}), 404


@app.route('/api/cohorts/<cohort_id>', methods=['DELETE'])
@require_admin
def delete_cohort(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    cohorts = db.load_cohorts()
    cohorts = [c for c in cohorts if c['cohort_id'] != cohort_id]
    db.save_cohorts(cohorts)
    db.delete_cohort_data(cohort_id)
    return jsonify({"success": True, "message": "과정이 삭제되었습니다."})


# ========== 학생 관리 API (관리자 전용) ==========

@app.route('/api/cohorts/<cohort_id>/students', methods=['GET'])
@require_admin
def get_cohort_students(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    students = db.load_students(cohort_id)
    teams = db.load_teams(cohort_id)

    result = []
    for s in students:
        student_data = {k: v for k, v in s.items() if k != 'password'}
        for team in teams:
            if team['id'] == s.get('team_id'):
                student_data['team_name'] = team['name']
                break
        result.append(student_data)
    return jsonify(result)


@app.route('/api/cohorts/<cohort_id>/students/upload', methods=['POST'])
@require_admin
def upload_students(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    if 'file' not in request.files:
        return jsonify({"success": False, "message": "파일이 없습니다."}), 400

    file = request.files['file']
    if not file.filename.endswith('.json'):
        return jsonify({"success": False, "message": "JSON 파일만 업로드할 수 있습니다."}), 400

    try:
        content = file.read().decode('utf-8')
        students_data = json.loads(content)

        if not isinstance(students_data, list):
            return jsonify({"success": False, "message": "JSON 형식이 올바르지 않습니다 (배열이어야 합니다)."}), 400

        if len(students_data) > 500:
            return jsonify({"success": False, "message": "학생 수는 500명을 초과할 수 없습니다."}), 400

        # 학생 데이터 정규화 및 검증
        students = []
        seen_ids = set()
        for s in students_data:
            sid = s.get('id')
            sname = s.get('name', '')

            if not isinstance(sid, int) or sid <= 0:
                return jsonify({"success": False, "message": f"유효하지 않은 학생 ID: {sid}"}), 400
            if sid in seen_ids:
                return jsonify({"success": False, "message": f"중복된 학생 ID: {sid}"}), 400
            if not sname or not isinstance(sname, str):
                return jsonify({"success": False, "message": f"유효하지 않은 학생 이름 (ID: {sid})"}), 400

            seen_ids.add(sid)
            students.append({
                "id": sid,
                "name": sname.strip(),
                "password": str(s.get('password', '')),
                "team_id": s.get('team_id', None),
                "has_voted": False,
                "voted_teams": [],
                "vote_timestamp": None
            })

        db.save_students(cohort_id, students)

        # 코호트 학생 수 업데이트
        cohorts = db.load_cohorts()
        for c in cohorts:
            if c['cohort_id'] == cohort_id:
                c['student_count'] = len(students)
                break
        db.save_cohorts(cohorts)

        return jsonify({
            "success": True,
            "message": f"{len(students)}명의 학생이 업로드되었습니다.",
            "count": len(students)
        })
    except json.JSONDecodeError:
        return jsonify({"success": False, "message": "JSON 파싱 오류가 발생했습니다."}), 400
    except Exception as e:
        print(f"학생 업로드 오류: {e}")
        return jsonify({"success": False, "message": "파일 처리 중 오류가 발생했습니다."}), 500


# ========== 팀 관리 API (관리자 전용) ==========

@app.route('/api/cohorts/<cohort_id>/teams', methods=['GET'])
@require_admin
def get_cohort_teams(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    teams = db.load_teams(cohort_id)
    return jsonify(teams)


@app.route('/api/cohorts/<cohort_id>/teams', methods=['POST'])
@require_admin
def save_cohort_teams(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    data = request.json
    teams_data = data.get('teams', [])
    unassigned = data.get('unassigned', [])

    if len(teams_data) > 20:
        return jsonify({"success": False, "message": "팀 수는 20개를 초과할 수 없습니다."}), 400

    # 팀 데이터 저장
    teams = []
    for t in teams_data:
        teams.append({
            "id": t.get('id') or t.get('team_id'),
            "name": t.get('name', ''),
            "project_name": t.get('project_name', ''),
            "members": t.get('member_ids', t.get('members', [])),
            "vote_count": 0
        })
    db.save_teams(cohort_id, teams)

    # 학생의 team_id 업데이트
    students = db.load_students(cohort_id)
    for s in students:
        s['team_id'] = None

    for team in teams:
        for member_id in team['members']:
            for s in students:
                if s['id'] == member_id:
                    s['team_id'] = team['id']
                    break

    db.save_students(cohort_id, students)

    return jsonify({
        "success": True,
        "message": f"{len(teams)}개 팀이 저장되었습니다."
    })


# ========== 학생 투표 API ==========

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '')

    if not name or not password:
        return jsonify({"success": False, "message": "이름과 비밀번호를 입력해주세요."}), 400

    # 활성 과정에서 학생 검색
    cohorts = db.load_cohorts()
    for cohort in cohorts:
        if not cohort.get('active', True):
            continue

        cid = cohort['cohort_id']
        students = db.load_students(cid)
        for student in students:
            if student['name'].lower() == name.lower():
                if str(student.get('password', '')) == str(password):
                    student_info = {k: v for k, v in student.items() if k != 'password'}
                    student_info['cohort_id'] = cid
                    return jsonify({
                        "success": True,
                        "student": student_info,
                        "cohort_id": cid,
                        "message": "로그인 성공"
                    })
                else:
                    return jsonify({"success": False, "message": "비밀번호가 일치하지 않습니다."}), 401

    return jsonify({"success": False, "message": "등록되지 않은 학생입니다."}), 404


@app.route('/api/teams/<cohort_id>/<int:student_id>')
def get_votable_teams(cohort_id, student_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    students = db.load_students(cohort_id)
    teams = db.load_teams(cohort_id)

    student_team_id = None
    for student in students:
        if student['id'] == student_id:
            student_team_id = student.get('team_id')
            break

    if student_team_id is None:
        return jsonify({"success": False, "message": "학생을 찾을 수 없습니다."}), 404

    votable_teams = []
    for team in teams:
        if team['id'] != student_team_id:
            votable_teams.append({
                "id": team['id'],
                "name": team['name'],
                "project_name": team.get('project_name', ''),
            })

    return jsonify({"success": True, "teams": votable_teams})


@app.route('/api/vote', methods=['POST'])
def vote():
    data = request.json
    cohort_id = data.get('cohort_id')
    student_id = data.get('student_id')
    team_ids = data.get('team_ids')

    if not cohort_id or not student_id or not team_ids:
        return jsonify({"success": False, "message": "필수 데이터가 누락되었습니다."}), 400

    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    if not is_voting_active(cohort_id):
        return jsonify({"success": False, "message": "현재 투표가 비활성화되어 있습니다."}), 400

    if not isinstance(team_ids, list):
        team_ids = [team_ids]

    config = get_vote_config(cohort_id)
    vote_mode = config.get('vote_mode', 'single')
    if vote_mode == 'single' and len(team_ids) != 1:
        return jsonify({"success": False, "message": "단일 투표 모드에서는 1개 팀만 선택할 수 있습니다."}), 400
    elif vote_mode == 'multiple' and len(team_ids) != 3:
        return jsonify({"success": False, "message": "다중 투표 모드에서는 3개 팀을 선택해야 합니다."}), 400

    students = db.load_students(cohort_id)
    teams = db.load_teams(cohort_id)
    votes = db.load_votes(cohort_id)

    student = None
    for s in students:
        if s['id'] == student_id:
            student = s
            break

    if not student:
        return jsonify({"success": False, "message": "학생을 찾을 수 없습니다."}), 404

    if student.get('has_voted', False):
        return jsonify({"success": False, "message": "이미 투표하셨습니다."}), 400

    if student.get('team_id') in team_ids:
        return jsonify({"success": False, "message": "자신의 팀에는 투표할 수 없습니다."}), 400

    if len(team_ids) != len(set(team_ids)):
        return jsonify({"success": False, "message": "같은 팀을 중복으로 선택할 수 없습니다."}), 400

    target_teams = []
    for team_id in team_ids:
        target_team = None
        for team in teams:
            if team['id'] == team_id:
                target_team = team
                break
        if not target_team:
            return jsonify({"success": False, "message": f"투표 대상 팀을 찾을 수 없습니다."}), 404
        target_teams.append(target_team)

    current_time = get_kst_now()

    student['has_voted'] = True
    student['voted_teams'] = team_ids
    student['vote_timestamp'] = current_time.strftime("%Y-%m-%d %H:%M:%S")

    for i, tid in enumerate(team_ids):
        vote_record = {
            "id": len(votes) + 1,
            "student_id": student_id,
            "student_name": student['name'],
            "voted_team_id": tid,
            "voted_team_name": target_teams[i]['name'],
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "vote_mode": vote_mode
        }
        votes.append(vote_record)

    db.save_students(cohort_id, students)
    db.save_votes(cohort_id, votes)
    update_team_vote_counts(cohort_id)

    if vote_mode == 'single':
        message = f"{target_teams[0]['name']}에 투표가 완료되었습니다!"
    else:
        team_names = [t['name'] for t in target_teams]
        message = f"{', '.join(team_names)}에 투표가 완료되었습니다!"

    return jsonify({"success": True, "message": message})


# ========== 관리자 투표 제어 API (세션 인증) ==========

@app.route('/api/admin/<cohort_id>/students', methods=['GET'])
@require_admin
def get_admin_students(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    students = db.load_students(cohort_id)
    teams = db.load_teams(cohort_id)

    result = []
    for s in students:
        student_data = {k: v for k, v in s.items() if k != 'password'}
        for team in teams:
            if team['id'] == s.get('team_id'):
                student_data['team_name'] = team['name']
                break
        result.append(student_data)
    return jsonify(result)


@app.route('/api/admin/<cohort_id>/teams', methods=['GET'])
@require_admin
def get_admin_teams(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    teams = update_team_vote_counts(cohort_id)
    return jsonify(teams)


@app.route('/api/admin/<cohort_id>/votes', methods=['GET'])
@require_admin
def get_admin_votes(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    students = db.load_students(cohort_id)
    teams = update_team_vote_counts(cohort_id)
    votes = db.load_votes(cohort_id)

    total_students = len(students)
    voted_students = len([s for s in students if s.get('has_voted', False)])

    return jsonify({
        "total_votes": len(votes),
        "total_students": total_students,
        "voted_students": voted_students,
        "votes": votes,
        "teams": teams
    })


@app.route('/api/admin/<cohort_id>/vote-config', methods=['GET'])
def get_admin_vote_config(cohort_id):
    """투표 설정 조회 - 학생도 접근 가능 (마감 시간 표시용)"""
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    config = get_vote_config(cohort_id)
    return jsonify({"success": True, "config": config})


@app.route('/api/admin/<cohort_id>/start-vote', methods=['POST'])
@require_admin
def start_vote(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    data = request.json
    duration_minutes = data.get('duration_minutes', 60)
    vote_mode = data.get('vote_mode', 'single')

    if vote_mode not in ['single', 'multiple']:
        return jsonify({"success": False, "message": "잘못된 투표 방식입니다."}), 400

    if not isinstance(duration_minutes, (int, float)) or duration_minutes < 1 or duration_minutes > 1440:
        return jsonify({"success": False, "message": "투표 시간은 1~1440분 사이여야 합니다."}), 400

    current_time = get_kst_now()
    end_time = current_time + timedelta(minutes=int(duration_minutes))

    config = {
        'is_active': True,
        'start_time': current_time.strftime("%H:%M"),
        'end_time': end_time.strftime("%H:%M"),
        'duration_minutes': int(duration_minutes),
        'vote_mode': vote_mode
    }
    db.save_vote_config(cohort_id, config)

    mode_text = "1개 팀 선택" if vote_mode == 'single' else "3개 팀 선택"
    return jsonify({
        "success": True,
        "message": f"투표가 시작되었습니다. ({int(duration_minutes)}분간 진행, {mode_text} 방식)",
        "config": config
    })


@app.route('/api/admin/<cohort_id>/stop-vote', methods=['POST'])
@require_admin
def stop_vote(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    config = get_vote_config(cohort_id)
    config['is_active'] = False
    db.save_vote_config(cohort_id, config)

    return jsonify({
        "success": True,
        "message": "투표가 종료되었습니다.",
        "config": config
    })


@app.route('/api/admin/<cohort_id>/set-vote-time', methods=['POST'])
@require_admin
def set_vote_time(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    data = request.json
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    vote_mode = data.get('vote_mode', 'single')

    if vote_mode not in ['single', 'multiple']:
        return jsonify({"success": False, "message": "잘못된 투표 방식입니다."}), 400

    try:
        start_time = datetime.datetime.strptime(start_time_str, "%H:%M")
        end_time = datetime.datetime.strptime(end_time_str, "%H:%M")

        if end_time <= start_time:
            return jsonify({"success": False, "message": "종료 시간은 시작 시간보다 늦어야 합니다."}), 400

        config = {
            'start_time': start_time_str,
            'end_time': end_time_str,
            'duration_minutes': int((end_time - start_time).total_seconds() / 60),
            'vote_mode': vote_mode,
            'is_active': True
        }
        db.save_vote_config(cohort_id, config)

        mode_text = "1개 팀 선택" if vote_mode == 'single' else "3개 팀 선택"
        return jsonify({
            "success": True,
            "message": f"투표 시간이 설정되었습니다. ({start_time_str}~{end_time_str}, {mode_text} 방식)",
            "config": config
        })
    except ValueError:
        return jsonify({"success": False, "message": "잘못된 시간 형식입니다."}), 400


@app.route('/api/admin/<cohort_id>/reset', methods=['POST'])
@require_admin
def reset_votes(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    students = db.load_students(cohort_id)
    for student in students:
        student['has_voted'] = False
        student['voted_teams'] = []
        student['vote_timestamp'] = None
    db.save_students(cohort_id, students)

    db.save_votes(cohort_id, [])

    teams = db.load_teams(cohort_id)
    for team in teams:
        team['vote_count'] = 0
    db.save_teams(cohort_id, teams)

    return jsonify({"success": True, "message": "투표가 초기화되었습니다."})


@app.route('/api/admin/<cohort_id>/download', methods=['GET'])
@require_admin
def download_results(cohort_id):
    if not validate_cohort_id(cohort_id):
        return jsonify({"success": False, "message": "잘못된 과정 ID입니다."}), 400

    try:
        students = db.load_students(cohort_id)
        teams = db.load_teams(cohort_id)
        votes = db.load_votes(cohort_id)

        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)

        csv_writer.writerow(['투표자', '투표자팀', '투표받은팀', '프로젝트명', '투표시간'])

        for v in votes:
            voter_team = ""
            for student in students:
                if student['id'] == v['student_id']:
                    for team in teams:
                        if team['id'] == student.get('team_id'):
                            voter_team = team['name']
                            break
                    break

            project_name = ""
            for team in teams:
                if team['id'] == v['voted_team_id']:
                    project_name = team.get('project_name', '')
                    break

            csv_writer.writerow([
                v['student_name'],
                voter_team,
                v['voted_team_name'],
                project_name,
                v['timestamp']
            ])

        csv_writer.writerow([])
        csv_writer.writerow(['=== 팀별 투표 결과 ==='])
        csv_writer.writerow(['팀명', '프로젝트명', '받은 투표수'])

        update_team_vote_counts(cohort_id)
        teams = db.load_teams(cohort_id)
        sorted_teams = sorted(teams, key=lambda x: x.get('vote_count', 0), reverse=True)

        for team in sorted_teams:
            csv_writer.writerow([
                team['name'],
                team.get('project_name', ''),
                team.get('vote_count', 0)
            ])

        csv_buffer.seek(0)
        now = get_kst_now().strftime("%Y%m%d_%H%M")
        filename = f"vote_results_{cohort_id}_{now}.csv"

        return Response(
            csv_buffer.getvalue().encode('utf-8-sig'),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
    except Exception as e:
        print(f"CSV 다운로드 중 오류: {e}")
        return jsonify({"success": False, "message": "CSV 생성 중 오류가 발생했습니다."}), 500


# ========== 에러 핸들러 ==========

@app.errorhandler(413)
def too_large(e):
    return jsonify({"success": False, "message": "파일 크기가 2MB를 초과합니다."}), 413


if __name__ == '__main__':
    print("팀 투표 시스템을 시작합니다...")
    print("개발 서버 주소: http://localhost:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)
