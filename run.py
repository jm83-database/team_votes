#!/usr/bin/env python3
"""
팀 투표 시스템 실행 스크립트
"""

import subprocess
import sys
import os

def check_requirements():
    """필요한 패키지들이 설치되어 있는지 확인"""
    try:
        import flask
        print("✓ Flask가 설치되어 있습니다.")
        return True
    except ImportError:
        print("✗ Flask가 설치되어 있지 않습니다.")
        print("다음 명령어로 설치해주세요: pip install -r requirements.txt")
        return False

def main():
    print("=" * 50)
    print("팀 프로젝트 투표 시스템 시작")
    print("=" * 50)
    
    # 현재 디렉토리 확인
    if not os.path.exists('app.py'):
        print("✗ app.py 파일을 찾을 수 없습니다.")
        print("팀 투표 시스템 디렉토리에서 실행해주세요.")
        sys.exit(1)
    
    # 필요한 파일들 확인
    required_files = ['students.json', 'teams.json', 'votes.json', 'templates/index.html']
    for file in required_files:
        if not os.path.exists(file):
            print(f"✗ {file} 파일이 없습니다.")
            sys.exit(1)
    
    print("✓ 모든 필요한 파일이 있습니다.")
    
    # 의존성 확인
    if not check_requirements():
        sys.exit(1)
    
    print("\n시스템 정보:")
    print(f"- Python 버전: {sys.version}")
    print(f"- 작업 디렉토리: {os.getcwd()}")
    
    print("\n=" * 50)
    print("서버를 시작합니다...")
    print("웹 브라우저에서 http://localhost:5000 으로 접속하세요")
    print("종료하려면 Ctrl+C를 누르세요")
    print("=" * 50)
    
    # Flask 앱 실행
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n\n시스템이 종료되었습니다.")
    except Exception as e:
        print(f"\n✗ 서버 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()