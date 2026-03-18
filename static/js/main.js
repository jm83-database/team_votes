const { useState, useEffect, useRef } = React;

// ===== 상수 정의 =====
const CONSTANTS = {
    VOTE_RESULT_DISPLAY_TIME: 5,
    TIMER_INTERVAL: 1000,
    MESSAGE_DISPLAY_TIME: 4000,
    VOTE_MODES: { SINGLE: 'single', MULTIPLE: 'multiple' },
    RANK_COLORS: { 1: 'bg-yellow-500', 2: 'bg-gray-400', 3: 'bg-orange-600', DEFAULT: 'bg-blue-500' },
    VOTE_COUNTS: { SINGLE: 1, MULTIPLE: 3 }
};

// ===== API 헬퍼 =====
const api = async (url, options = {}) => {
    const config = { headers: { 'Content-Type': 'application/json' }, ...options };
    if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
        config.body = JSON.stringify(config.body);
    }
    const res = await fetch(url, config);
    if (url.includes('/download')) return res;
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);
    return data;
};

// ===== 유틸리티 =====
const utils = {
    formatTime: (h, m, s) => {
        if (h > 0) return `${h}시간 ${m}분 ${s}초`;
        if (m > 0) return `${m}분 ${s}초`;
        return `${s}초`;
    },
    calculateTeamRanks: (teams) => {
        const sorted = [...teams].sort((a, b) => (b.vote_count || 0) - (a.vote_count || 0));
        let rank = 1;
        return sorted.map((t, i) => {
            if (i > 0 && sorted[i - 1].vote_count !== t.vote_count) rank = i + 1;
            return { ...t, rank };
        });
    },
    getRankColor: (rank) => CONSTANTS.RANK_COLORS[rank] || CONSTANTS.RANK_COLORS.DEFAULT,
    getVoteModeText: (mode) => mode === 'single' ? '1개 팀 선택' : '3개 팀 선택',
    getVotedTeamNames: (student, teams) => {
        if (!student.has_voted) return '-';
        if (student.voted_teams && Array.isArray(student.voted_teams)) {
            return student.voted_teams.map(tid => teams.find(t => t.id === tid)?.name).filter(Boolean).join(', ');
        }
        return '-';
    }
};

// ===== 커스텀 훅 =====
function useMessage() {
    const [message, setMessage] = useState('');
    const [messageType, setMessageType] = useState('');
    const showMessage = (msg, type = 'success') => {
        setMessage(msg); setMessageType(type);
        setTimeout(() => setMessage(''), CONSTANTS.MESSAGE_DISPLAY_TIME);
    };
    return { message, messageType, showMessage };
}

function useCountdown(initial) {
    const [countdown, setCountdown] = useState(initial);
    useEffect(() => {
        if (countdown <= 0) return;
        const timer = setInterval(() => {
            setCountdown(prev => { if (prev <= 1) { clearInterval(timer); return 0; } return prev - 1; });
        }, CONSTANTS.TIMER_INTERVAL);
        return () => clearInterval(timer);
    }, [countdown]);
    return { countdown, startCountdown: setCountdown };
}

function useVoteTimer(endTime, isActive) {
    const [remaining, setRemaining] = useState(null);
    useEffect(() => {
        if (!endTime || !isActive) { setRemaining(null); return; }
        const interval = setInterval(() => {
            const now = new Date();
            const [h, m] = endTime.split(':').map(Number);
            const end = new Date(); end.setHours(h, m, 0, 0);
            if (end <= now) end.setDate(end.getDate() + 1);
            const diff = end - now;
            if (diff <= 0) { setRemaining('투표가 종료되었습니다'); clearInterval(interval); }
            else {
                const hh = Math.floor(diff / 3600000);
                const mm = Math.floor((diff % 3600000) / 60000);
                const ss = Math.floor((diff % 60000) / 1000);
                setRemaining(utils.formatTime(hh, mm, ss));
            }
        }, CONSTANTS.TIMER_INTERVAL);
        return () => clearInterval(interval);
    }, [endTime, isActive]);
    return remaining;
}

// ===== 시간 선택 컴포넌트 =====
function TimeSelector({ name, required = false }) {
    const [hour, setHour] = useState('09');
    const [minute, setMinute] = useState('00');
    const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));
    const minutes = Array.from({ length: 60 }, (_, i) => i.toString().padStart(2, '0'));
    return (
        <div className="flex items-center gap-2">
            <select value={hour} onChange={e => setHour(e.target.value)} className="px-3 py-2 border rounded-lg bg-white text-sm min-w-16 text-center" required={required}>
                {hours.map(h => <option key={h} value={h}>{h}</option>)}
            </select>
            <span className="text-gray-600">:</span>
            <select value={minute} onChange={e => setMinute(e.target.value)} className="px-3 py-2 border rounded-lg bg-white text-sm min-w-16 text-center" required={required}>
                {minutes.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <input type="hidden" name={name} value={`${hour}:${minute}`} />
        </div>
    );
}

// ===== 메인 앱 =====
function App() {
    const [mode, setMode] = useState('student');
    const [currentUser, setCurrentUser] = useState(null);
    const [showHelp, setShowHelp] = useState(false);
    const { message, messageType, showMessage } = useMessage();

    return (
        <div className="min-h-screen">
            <header className="bg-white shadow-lg">
                <div className="container mx-auto px-4 py-6">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-4">
                            <img src="/static/elixerr logo_resize.png" alt="Logo" className="w-16 h-16 rounded-full border-2 border-blue-500 shadow-md" />
                            <div>
                                <h1 className="text-3xl font-bold text-gray-800">팀 프로젝트 투표 시스템</h1>
                                <p className="text-gray-600 mt-1">최고의 프로젝트를 선택해주세요</p>
                            </div>
                        </div>
                        <div className="flex items-center space-x-4">
                            <button onClick={() => setShowHelp(true)} className="p-2 rounded-full hover:bg-gray-100 transition-colors" title="도움말">
                                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </button>
                            <button onClick={() => { setMode('student'); setCurrentUser(null); }}
                                className={`px-4 py-2 rounded-lg font-medium transition-colors ${mode === 'student' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>
                                학생 모드
                            </button>
                            <button onClick={() => { setMode('admin'); setCurrentUser(null); }}
                                className={`px-4 py-2 rounded-lg font-medium transition-colors ${mode === 'admin' ? 'bg-indigo-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>
                                관리자 모드
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {message && (
                <div className={`fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg fade-in ${messageType === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'}`}>
                    {message}
                </div>
            )}

            {showHelp && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-screen overflow-hidden">
                        <div className="p-6 border-b flex justify-between items-center">
                            <h3 className="text-2xl font-bold text-gray-800">사용법</h3>
                            <button onClick={() => setShowHelp(false)} className="p-2 hover:bg-gray-100 rounded-full">
                                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto space-y-6" style={{ maxHeight: '70vh' }}>
                            {/* 학생 모드 */}
                            <div>
                                <div className="flex items-center space-x-2 mb-3">
                                    <span className="bg-blue-100 text-blue-700 text-sm font-semibold px-3 py-1 rounded-full">학생 모드</span>
                                </div>
                                <ul className="space-y-2 text-gray-700 text-sm">
                                    <li>• <strong>로그인</strong>: 이름과 비밀번호를 입력해 로그인합니다.</li>
                                    <li>• <strong>팀 선택</strong>: 관리자가 설정한 방식에 따라 1개(단일 모드) 또는 3개(다중 모드) 팀을 선택합니다.</li>
                                    <li>• <strong>투표 마감 타이머</strong>: 투표 종료까지 남은 시간이 실시간으로 표시됩니다.</li>
                                    <li>• <strong>제한 사항</strong>: 본인이 속한 팀은 선택할 수 없습니다.</li>
                                    <li>• 투표 완료 후 확인 화면이 표시됩니다.</li>
                                </ul>
                            </div>

                            <hr className="border-gray-200" />

                            {/* 관리자 모드 */}
                            <div>
                                <div className="flex items-center space-x-2 mb-3">
                                    <span className="bg-indigo-100 text-indigo-700 text-sm font-semibold px-3 py-1 rounded-full">관리자 모드</span>
                                </div>
                                <div className="space-y-4 text-gray-700 text-sm">
                                    <div>
                                        <p className="font-semibold text-gray-800 mb-1">① 과정(코호트) 관리</p>
                                        <ul className="space-y-1 pl-2">
                                            <li>• 새 과정을 ID와 이름으로 생성합니다.</li>
                                            <li>• JSON 파일로 학생 명단을 한번에 업로드할 수 있습니다.</li>
                                            <li>• 과정별 활성화/비활성화 토글 및 삭제가 가능합니다.</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <p className="font-semibold text-gray-800 mb-1">② 팀 구성</p>
                                        <ul className="space-y-1 pl-2">
                                            <li>• PC: 드래그앤드롭으로 학생을 팀에 배정합니다.</li>
                                            <li>• 모바일: 드롭다운으로 팀을 선택합니다.</li>
                                            <li>• 팀 이름, 프로젝트명 설정 및 균등 배분 기능을 제공합니다.</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <p className="font-semibold text-gray-800 mb-1">③ 투표 제어</p>
                                        <ul className="space-y-1 pl-2">
                                            <li>• <strong>즉시 시작</strong>: 지속 시간(분)을 설정해 바로 시작합니다.</li>
                                            <li>• <strong>예약 시작</strong>: 시작/종료 시간을 직접 지정합니다.</li>
                                            <li>• 투표 모드를 단일(1개 팀) 또는 다중(3개 팀)으로 선택합니다.</li>
                                            <li>• 투표 중지 및 전체 결과 초기화가 가능합니다.</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <p className="font-semibold text-gray-800 mb-1">④ 투표 결과</p>
                                        <ul className="space-y-1 pl-2">
                                            <li>• 팀 순위를 실시간으로 확인합니다 (금/은/동 색상 구분).</li>
                                            <li>• 학생별 투표 현황을 테이블로 확인합니다.</li>
                                            <li>• 결과를 CSV 파일로 다운로드할 수 있습니다.</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <main className="container mx-auto px-4 py-8">
                {mode === 'student' ? (
                    <StudentMode currentUser={currentUser} setCurrentUser={setCurrentUser} showMessage={showMessage} />
                ) : (
                    <AdminMode showMessage={showMessage} />
                )}
            </main>
        </div>
    );
}

// ===== 학생 모드 =====
function StudentMode({ currentUser, setCurrentUser, showMessage }) {
    const [teams, setTeams] = useState([]);
    const [selectedTeams, setSelectedTeams] = useState([]);
    const [justVoted, setJustVoted] = useState(false);
    const [voteMode, setVoteMode] = useState('single');
    const [voteEndTime, setVoteEndTime] = useState(null);
    const [loading, setLoading] = useState(false);
    const { countdown, startCountdown } = useCountdown(0);
    const timeRemaining = useVoteTimer(voteEndTime, !currentUser?.has_voted);

    useEffect(() => {
        if (currentUser) loadVotableTeams();
    }, [currentUser]);

    const loadVotableTeams = async () => {
        try {
            const [teamsData, configData] = await Promise.all([
                api(`/api/teams/${currentUser.cohort_id}/${currentUser.id}`),
                api(`/api/admin/${currentUser.cohort_id}/vote-config`)
            ]);
            if (teamsData.success) setTeams(teamsData.teams);
            if (configData.success) {
                setVoteMode(configData.config.vote_mode || 'single');
                if (configData.config.end_time) setVoteEndTime(configData.config.end_time);
            }
        } catch { showMessage('데이터를 불러오는데 실패했습니다.', 'error'); }
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const fd = new FormData(e.target);
            const data = await api('/api/login', { method: 'POST', body: { name: fd.get('name'), password: fd.get('password') } });
            if (data.success) { setCurrentUser(data.student); showMessage(`${data.student.name}님, 환영합니다!`); }
        } catch (err) { showMessage(err.message || '로그인 실패', 'error'); }
        finally { setLoading(false); }
    };

    const handleTeamSelect = (team) => {
        if (voteMode === 'single') { setSelectedTeams([team]); }
        else {
            const isSelected = selectedTeams.some(t => t.id === team.id);
            if (isSelected) setSelectedTeams(selectedTeams.filter(t => t.id !== team.id));
            else if (selectedTeams.length < CONSTANTS.VOTE_COUNTS.MULTIPLE) setSelectedTeams([...selectedTeams, team]);
            else showMessage(`${CONSTANTS.VOTE_COUNTS.MULTIPLE}개 팀까지만 선택할 수 있습니다.`, 'error');
        }
    };

    const handleVote = async () => {
        const required = voteMode === 'single' ? 1 : 3;
        if (selectedTeams.length !== required) {
            showMessage(voteMode === 'single' ? '투표할 팀을 선택해주세요.' : `정확히 ${required}개 팀을 선택해주세요.`, 'error');
            return;
        }
        setLoading(true);
        try {
            const data = await api('/api/vote', {
                method: 'POST',
                body: { cohort_id: currentUser.cohort_id, student_id: currentUser.id, team_ids: selectedTeams.map(t => t.id) }
            });
            if (data.success) {
                showMessage(data.message);
                setJustVoted(true);
                setCurrentUser({ ...currentUser, has_voted: true, voted_teams: selectedTeams.map(t => t.id) });
                startCountdown(CONSTANTS.VOTE_RESULT_DISPLAY_TIME);
                setTimeout(() => setJustVoted(false), CONSTANTS.VOTE_RESULT_DISPLAY_TIME * 1000);
            }
        } catch (err) { showMessage(err.message || '투표 실패', 'error'); }
        finally { setLoading(false); }
    };

    if (!currentUser) {
        return (
            <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg p-8">
                <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">학생 로그인</h2>
                <form onSubmit={handleLogin} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">이름</label>
                        <input type="text" name="name" required className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="이름을 입력하세요" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">비밀번호</label>
                        <input type="password" name="password" required className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="비밀번호를 입력하세요" />
                    </div>
                    <button type="submit" disabled={loading}
                        className={`w-full py-3 px-4 rounded-lg font-medium text-white ${loading ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'}`}>
                        {loading ? '로그인 중...' : '로그인'}
                    </button>
                </form>
            </div>
        );
    }

    if (currentUser.has_voted) {
        return (
            <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-lg p-8 text-center">
                <div className="text-6xl mb-4">🎉</div>
                <h2 className="text-2xl font-bold text-gray-800 mb-4">{justVoted ? '투표 완료!' : '투표를 이미 하셨습니다.'}</h2>
                <p className="text-gray-600 mb-6">{justVoted ? `${currentUser.name}님의 투표가 성공적으로 완료되었습니다.` : `${currentUser.name}님은 이미 투표를 완료하셨습니다.`}</p>
                {justVoted && (
                    <div className="bg-blue-50 p-4 rounded-lg mb-6">
                        <p className="text-sm text-blue-800 mb-2">
                            투표한 팀: <span className="font-semibold">{currentUser.voted_teams?.map(tid => teams.find(t => t.id === tid)?.name).filter(Boolean).join(', ') || '알 수 없음'}</span>
                        </p>
                        {countdown > 0 && <p className="text-xs text-blue-600">{countdown}초 후 투표한 결과가 가려집니다...</p>}
                    </div>
                )}
                <button onClick={() => setCurrentUser(null)} className="mt-6 px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600">로그아웃</button>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
                <div className="flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-800">안녕하세요, {currentUser.name}님!</h2>
                        <p className="text-gray-600">
                            {voteMode === 'single' ? '투표할 팀을 1개 선택해주세요' : '투표할 팀을 3개 선택해주세요'}
                            {voteMode === 'multiple' && <span className="ml-2 text-sm text-blue-600">({selectedTeams.length}/{CONSTANTS.VOTE_COUNTS.MULTIPLE} 선택됨)</span>}
                        </p>
                        {timeRemaining && voteEndTime && (
                            <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                                <p className="text-sm text-red-800">⏰ <span className="font-semibold">투표 마감까지: </span><span className="countdown-timer font-bold text-red-600">{timeRemaining}</span></p>
                            </div>
                        )}
                    </div>
                    <button onClick={() => setCurrentUser(null)} className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600">로그아웃</button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                {teams.map(team => {
                    const isSelected = selectedTeams.some(t => t.id === team.id);
                    return (
                        <div key={team.id} onClick={() => handleTeamSelect(team)}
                            className={`vote-card p-6 bg-white rounded-xl shadow-lg cursor-pointer ${isSelected ? 'selected' : ''}`}>
                            <h3 className="text-xl font-bold text-gray-800 mb-2">{team.name}</h3>
                            <p className="text-gray-600 mb-4">{team.project_name}</p>
                            <div className="flex justify-end items-center">
                                {isSelected && (
                                    <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                                        <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                        </svg>
                                    </div>
                                )}
                                {voteMode === 'multiple' && isSelected && (
                                    <span className="ml-2 text-sm font-bold text-blue-600">{selectedTeams.findIndex(t => t.id === team.id) + 1}</span>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {selectedTeams.length > 0 && (
                <div className="text-center">
                    <button onClick={handleVote} disabled={loading || selectedTeams.length !== (voteMode === 'single' ? 1 : 3)}
                        className={`vote-button py-4 px-8 rounded-xl font-bold text-white text-lg ${loading || selectedTeams.length !== (voteMode === 'single' ? 1 : 3) ? 'bg-gray-400 cursor-not-allowed' : 'bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg'}`}>
                        {loading ? '투표 중...' : voteMode === 'single' ? `${selectedTeams[0]?.name}에 투표하기` : selectedTeams.length === 3 ? '선택한 3개 팀에 투표하기' : `${3 - selectedTeams.length}개 팀 더 선택해주세요`}
                    </button>
                </div>
            )}
        </div>
    );
}

// ===== 관리자 모드 =====
function AdminMode({ showMessage }) {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [activeTab, setActiveTab] = useState('cohorts');
    const [selectedCohort, setSelectedCohort] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const fd = new FormData(e.target);
            const data = await api('/api/admin/login', { method: 'POST', body: { admin_password: fd.get('admin_password') } });
            if (data.success) { setIsLoggedIn(true); showMessage('관리자 로그인 성공'); }
        } catch { showMessage('관리자 비밀번호가 올바르지 않습니다.', 'error'); }
        finally { setLoading(false); }
    };

    if (!isLoggedIn) {
        return (
            <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg p-8">
                <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">관리자 로그인</h2>
                <form onSubmit={handleLogin} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">관리자 비밀번호</label>
                        <input type="password" name="admin_password" required className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" placeholder="비밀번호 입력" />
                    </div>
                    <button type="submit" disabled={loading}
                        className={`w-full py-3 px-4 rounded-lg font-medium text-white ${loading ? 'bg-gray-400' : 'bg-indigo-500 hover:bg-indigo-600'}`}>
                        {loading ? '로그인 중...' : '관리자 로그인'}
                    </button>
                </form>
            </div>
        );
    }

    const tabs = [
        { id: 'cohorts', label: '과정 관리' },
        { id: 'teams', label: '팀 관리' },
        { id: 'vote', label: '투표 제어' },
        { id: 'results', label: '투표 결과' }
    ];

    return (
        <div className="max-w-6xl mx-auto">
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold text-gray-800">관리자 대시보드</h2>
                    <button onClick={() => setIsLoggedIn(false)} className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600">로그아웃</button>
                </div>

                {/* 과정 선택 */}
                {activeTab !== 'cohorts' && (
                    <CohortSelector selectedCohort={selectedCohort} onSelect={setSelectedCohort} />
                )}
            </div>

            {/* 탭 */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
                <div className="flex border-b">
                    {tabs.map(tab => (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                            className={`px-6 py-4 font-medium transition-colors ${activeTab === tab.id ? 'bg-indigo-500 text-white' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}`}>
                            {tab.label}
                        </button>
                    ))}
                </div>
                <div className="p-6">
                    {activeTab === 'cohorts' && <CohortManagement showMessage={showMessage} />}
                    {activeTab === 'teams' && selectedCohort && <TeamManagement cohortId={selectedCohort} showMessage={showMessage} />}
                    {activeTab === 'vote' && selectedCohort && <VoteControl cohortId={selectedCohort} showMessage={showMessage} />}
                    {activeTab === 'results' && selectedCohort && <VoteResults cohortId={selectedCohort} showMessage={showMessage} />}
                    {activeTab !== 'cohorts' && !selectedCohort && (
                        <p className="text-gray-500 text-center py-8">위에서 과정을 선택해주세요.</p>
                    )}
                </div>
            </div>
        </div>
    );
}

// ===== 과정 선택 드롭다운 =====
function CohortSelector({ selectedCohort, onSelect }) {
    const [cohorts, setCohorts] = useState([]);

    useEffect(() => {
        api('/api/cohorts').then(data => {
            setCohorts(data);
            if (data.length > 0 && !selectedCohort) {
                const active = data.find(c => c.active);
                if (active) onSelect(active.cohort_id);
            }
        });
    }, []);

    return (
        <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">과정 선택:</label>
            <select value={selectedCohort || ''} onChange={e => onSelect(e.target.value)}
                className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 min-w-48">
                <option value="">-- 선택 --</option>
                {cohorts.filter(c => c.active).map(c => (
                    <option key={c.cohort_id} value={c.cohort_id}>{c.name} ({c.cohort_id})</option>
                ))}
            </select>
        </div>
    );
}

// ===== 과정 관리 =====
function CohortManagement({ showMessage }) {
    const [cohorts, setCohorts] = useState([]);
    const [newId, setNewId] = useState('');
    const [newName, setNewName] = useState('');
    const [uploadCohort, setUploadCohort] = useState('');

    const loadCohorts = async () => {
        const data = await api('/api/cohorts');
        setCohorts(data);
    };

    useEffect(() => { loadCohorts(); }, []);

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            const data = await api('/api/cohorts', { method: 'POST', body: { cohort_id: newId, name: newName } });
            if (data.success) { showMessage(data.message); setNewId(''); setNewName(''); loadCohorts(); }
        } catch (err) { showMessage(err.message, 'error'); }
    };

    const handleToggle = async (cohort) => {
        try {
            await api(`/api/cohorts/${cohort.cohort_id}`, { method: 'PUT', body: { active: !cohort.active } });
            loadCohorts();
        } catch (err) { showMessage(err.message, 'error'); }
    };

    const handleDelete = async (cohortId) => {
        if (!confirm('정말 삭제하시겠습니까? 모든 데이터가 삭제됩니다.')) return;
        try {
            await api(`/api/cohorts/${cohortId}`, { method: 'DELETE' });
            showMessage('과정이 삭제되었습니다.');
            loadCohorts();
        } catch (err) { showMessage(err.message, 'error'); }
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        const fileInput = e.target.querySelector('input[type="file"]');
        if (!fileInput.files[0] || !uploadCohort) { showMessage('과정과 파일을 선택해주세요.', 'error'); return; }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        try {
            const res = await fetch(`/api/cohorts/${uploadCohort}/students/upload`, { method: 'POST', body: formData });
            const data = await res.json();
            if (data.success) { showMessage(data.message); fileInput.value = ''; loadCohorts(); }
            else showMessage(data.message, 'error');
        } catch { showMessage('업로드 실패', 'error'); }
    };

    return (
        <div className="space-y-6">
            {/* 과정 생성 */}
            <div className="bg-gray-50 rounded-xl p-5">
                <h3 className="font-bold text-lg mb-3">새 과정 만들기</h3>
                <form onSubmit={handleCreate} className="flex gap-3 items-end flex-wrap">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">과정 ID</label>
                        <input value={newId} onChange={e => setNewId(e.target.value)} required placeholder="예: DT4" className="px-3 py-2 border rounded-lg w-32" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">과정 이름</label>
                        <input value={newName} onChange={e => setNewName(e.target.value)} required placeholder="예: MS Data 4기" className="px-3 py-2 border rounded-lg w-48" />
                    </div>
                    <button type="submit" className="bg-indigo-600 text-white px-5 py-2 rounded-lg hover:bg-indigo-700">생성</button>
                </form>
            </div>

            {/* 학생 업로드 */}
            <div className="bg-gray-50 rounded-xl p-5">
                <h3 className="font-bold text-lg mb-3">학생 업로드 (students.json)</h3>
                <form onSubmit={handleUpload} className="flex gap-3 items-end flex-wrap">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">대상 과정</label>
                        <select value={uploadCohort} onChange={e => setUploadCohort(e.target.value)} required className="px-3 py-2 border rounded-lg min-w-48">
                            <option value="">-- 선택 --</option>
                            {cohorts.map(c => <option key={c.cohort_id} value={c.cohort_id}>{c.name}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">파일</label>
                        <input type="file" accept=".json" required className="px-3 py-2 border rounded-lg" />
                    </div>
                    <button type="submit" className="bg-green-600 text-white px-5 py-2 rounded-lg hover:bg-green-700">업로드</button>
                </form>
            </div>

            {/* 과정 목록 */}
            <div>
                <h3 className="font-bold text-lg mb-3">과정 목록</h3>
                {cohorts.length === 0 ? (
                    <p className="text-gray-500">등록된 과정이 없습니다.</p>
                ) : (
                    <div className="space-y-2">
                        {cohorts.map(c => (
                            <div key={c.cohort_id} className="flex items-center justify-between bg-white border rounded-lg p-4">
                                <div className="flex items-center gap-3">
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${c.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                                        {c.active ? '활성' : '비활성'}
                                    </span>
                                    <span className="font-semibold">{c.name}</span>
                                    <span className="text-gray-500 text-sm">({c.cohort_id})</span>
                                    <span className="text-gray-400 text-sm">{c.student_count || 0}명</span>
                                </div>
                                <div className="flex gap-2">
                                    <button onClick={() => handleToggle(c)}
                                        className={`px-3 py-1 rounded text-sm ${c.active ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200' : 'bg-green-100 text-green-800 hover:bg-green-200'}`}>
                                        {c.active ? '비활성화' : '활성화'}
                                    </button>
                                    <button onClick={() => handleDelete(c.cohort_id)} className="px-3 py-1 rounded text-sm bg-red-100 text-red-800 hover:bg-red-200">삭제</button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

// ===== 팀 관리 =====
function TeamManagement({ cohortId, showMessage }) {
    const [students, setStudents] = useState([]);
    const [teams, setTeams] = useState([]);
    const [showBuilder, setShowBuilder] = useState(false);

    const loadData = async () => {
        const [studentsData, teamsData] = await Promise.all([
            api(`/api/cohorts/${cohortId}/students`),
            api(`/api/cohorts/${cohortId}/teams`)
        ]);
        setStudents(studentsData);
        setTeams(teamsData);
    };

    useEffect(() => { loadData(); }, [cohortId]);

    if (showBuilder) {
        return <TeamBuilder
            cohortId={cohortId}
            students={students}
            existingTeams={teams}
            onSave={() => { setShowBuilder(false); loadData(); }}
            onCancel={() => setShowBuilder(false)}
            showMessage={showMessage}
        />;
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h3 className="font-bold text-lg">팀 구성</h3>
                <button onClick={() => setShowBuilder(true)} className="bg-indigo-600 text-white px-5 py-2 rounded-lg hover:bg-indigo-700">
                    {teams.length > 0 ? '팀 편집' : '팀 만들기'}
                </button>
            </div>

            {teams.length === 0 ? (
                <p className="text-gray-500">구성된 팀이 없습니다. '팀 만들기' 버튼을 클릭해주세요.</p>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {teams.map(team => (
                        <div key={team.id} className="border rounded-xl p-4">
                            <h4 className="font-semibold text-indigo-700">{team.name}</h4>
                            {team.project_name && <p className="text-sm text-gray-500 mb-2">{team.project_name}</p>}
                            <div className="flex flex-wrap gap-1">
                                {(team.members || []).map(mid => {
                                    const s = students.find(st => st.id === mid);
                                    return <span key={mid} className="bg-gray-100 px-2 py-1 rounded text-xs">{s ? s.name : `ID:${mid}`}</span>;
                                })}
                            </div>
                            <p className="text-xs text-gray-400 mt-2">{(team.members || []).length}명</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ===== 팀 빌더 (드래그앤드롭) =====
function TeamBuilder({ cohortId, students, existingTeams, onSave, onCancel, showMessage }) {
    const [numTeams, setNumTeams] = useState(existingTeams.length || 5);
    const [teams, setTeams] = useState([]);
    const [unassigned, setUnassigned] = useState([]);
    const dragItem = useRef(null);

    useEffect(() => {
        if (existingTeams.length > 0) {
            setTeams(existingTeams.map(t => ({
                id: t.id,
                name: t.name,
                project_name: t.project_name || '',
                member_ids: [...(t.members || [])]
            })));
            const assignedIds = new Set(existingTeams.flatMap(t => t.members || []));
            setUnassigned(students.filter(s => !assignedIds.has(s.id)).map(s => s.id));
        } else {
            const newTeams = Array.from({ length: numTeams }, (_, i) => ({
                id: i + 1, name: `팀 ${i + 1}`, project_name: '', member_ids: []
            }));
            setTeams(newTeams);
            setUnassigned(students.map(s => s.id));
        }
    }, []);

    const adjustTeamCount = (count) => {
        count = Math.max(1, Math.min(20, count));
        setNumTeams(count);
        setTeams(prev => {
            if (count > prev.length) {
                const newTeams = [...prev];
                for (let i = prev.length; i < count; i++) {
                    newTeams.push({ id: i + 1, name: `팀 ${i + 1}`, project_name: '', member_ids: [] });
                }
                return newTeams;
            } else {
                const removed = prev.slice(count);
                const removedIds = removed.flatMap(t => t.member_ids);
                setUnassigned(u => [...u, ...removedIds]);
                return prev.slice(0, count);
            }
        });
    };

    const autoDistribute = () => {
        const newTeams = teams.map(t => ({ ...t, member_ids: [] }));
        const allIds = [...unassigned, ...teams.flatMap(t => t.member_ids)];
        for (let i = allIds.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [allIds[i], allIds[j]] = [allIds[j], allIds[i]];
        }
        allIds.forEach((id, i) => { newTeams[i % newTeams.length].member_ids.push(id); });
        setTeams(newTeams);
        setUnassigned([]);
    };

    const getName = (id) => { const s = students.find(s => s.id === id); return s ? s.name : `ID:${id}`; };

    // Drag & Drop
    const handleDragStart = (e, studentId, sourceType, sourceIndex) => {
        dragItem.current = { studentId, sourceType, sourceIndex };
        e.dataTransfer.effectAllowed = 'move';
        e.target.classList.add('dragging');
    };
    const handleDragEnd = (e) => { e.target.classList.remove('dragging'); };
    const handleDragOver = (e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; };
    const handleDragEnter = (e) => { e.preventDefault(); e.currentTarget.classList.add('drag-over'); };
    const handleDragLeave = (e) => { e.currentTarget.classList.remove('drag-over'); };

    const handleDrop = (e, targetType, targetIndex) => {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        const { studentId, sourceType, sourceIndex } = dragItem.current;

        if (sourceType === 'unassigned') setUnassigned(prev => prev.filter(id => id !== studentId));
        else setTeams(prev => prev.map((t, i) => i === sourceIndex ? { ...t, member_ids: t.member_ids.filter(id => id !== studentId) } : t));

        if (targetType === 'unassigned') setUnassigned(prev => [...prev, studentId]);
        else setTeams(prev => prev.map((t, i) => i === targetIndex ? { ...t, member_ids: [...t.member_ids, studentId] } : t));
    };

    // Mobile move
    const moveStudent = (studentId, fromType, fromIndex, toType, toIndex) => {
        if (fromType === 'unassigned') setUnassigned(prev => prev.filter(id => id !== studentId));
        else setTeams(prev => prev.map((t, i) => i === fromIndex ? { ...t, member_ids: t.member_ids.filter(id => id !== studentId) } : t));

        if (toType === 'unassigned') setUnassigned(prev => [...prev, studentId]);
        else setTeams(prev => prev.map((t, i) => i === toIndex ? { ...t, member_ids: [...t.member_ids, studentId] } : t));
    };

    const handleSave = async () => {
        try {
            const payload = {
                teams: teams.map(t => ({ id: t.id, name: t.name, project_name: t.project_name, member_ids: t.member_ids })),
                unassigned
            };
            const data = await api(`/api/cohorts/${cohortId}/teams`, { method: 'POST', body: payload });
            if (data.success) { showMessage(data.message); onSave(); }
            else showMessage(data.message, 'error');
        } catch (err) { showMessage(err.message || '저장 실패', 'error'); }
    };

    const StudentChip = ({ id, type, index }) => (
        <div draggable onDragStart={e => handleDragStart(e, id, type, index)} onDragEnd={handleDragEnd}
            className="bg-white border rounded-lg px-3 py-2 text-sm cursor-move hover:shadow-sm transition flex items-center justify-between gap-2">
            <span>{getName(id)}</span>
            <select className="text-xs border rounded px-1 py-0.5 bg-gray-50 md:hidden" value=""
                onChange={e => {
                    const val = e.target.value;
                    if (val === 'unassigned') moveStudent(id, type, index, 'unassigned', -1);
                    else moveStudent(id, type, index, 'team', parseInt(val));
                    e.target.value = '';
                }}>
                <option value="">이동</option>
                <option value="unassigned">미배정</option>
                {teams.map((t, i) => <option key={t.id} value={i}>{t.name}</option>)}
            </select>
        </div>
    );

    return (
        <div className="space-y-5">
            <h3 className="font-bold text-lg">팀 구성 편집</h3>

            {/* 팀 수 & 액션 */}
            <div className="flex items-center gap-3 flex-wrap">
                <label className="text-sm font-medium">팀 수:</label>
                <input type="number" min="1" max="20" className="border rounded-lg px-3 py-2 w-20"
                    value={numTeams} onChange={e => adjustTeamCount(parseInt(e.target.value) || 1)} />
                <button onClick={autoDistribute} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700">균등 배분</button>
            </div>

            {/* 미배정 풀 */}
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-4 min-h-16"
                onDragOver={handleDragOver} onDragEnter={handleDragEnter} onDragLeave={handleDragLeave}
                onDrop={e => handleDrop(e, 'unassigned', -1)}>
                <h4 className="text-sm font-semibold text-gray-500 mb-2">미배정 ({unassigned.length}명)</h4>
                <div className="flex flex-wrap gap-2">
                    {unassigned.map(id => <StudentChip key={id} id={id} type="unassigned" index={-1} />)}
                </div>
            </div>

            {/* 팀 컬럼 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {teams.map((team, idx) => (
                    <div key={team.id} className="border-2 border-gray-200 rounded-xl p-3 min-h-32"
                        onDragOver={handleDragOver} onDragEnter={handleDragEnter} onDragLeave={handleDragLeave}
                        onDrop={e => handleDrop(e, 'team', idx)}>
                        <div className="flex items-center justify-between mb-1">
                            <input className="font-semibold text-sm bg-transparent border-b border-transparent focus:border-indigo-400 px-1 w-full"
                                value={team.name} placeholder="팀명"
                                onChange={e => { const nt = [...teams]; nt[idx] = { ...nt[idx], name: e.target.value }; setTeams(nt); }} />
                            <span className="text-xs text-gray-400 ml-1 whitespace-nowrap">{team.member_ids.length}명</span>
                        </div>
                        <input className="text-xs text-gray-500 bg-transparent border-b border-transparent focus:border-indigo-300 px-1 w-full mb-2"
                            value={team.project_name} placeholder="프로젝트명"
                            onChange={e => { const nt = [...teams]; nt[idx] = { ...nt[idx], project_name: e.target.value }; setTeams(nt); }} />
                        <div className="space-y-1">
                            {team.member_ids.map(id => <StudentChip key={id} id={id} type="team" index={idx} />)}
                        </div>
                    </div>
                ))}
            </div>

            {/* 저장/취소 */}
            <div className="flex gap-3 justify-end">
                <button onClick={onCancel} className="px-6 py-2 border rounded-lg text-gray-600 hover:bg-gray-50">취소</button>
                <button onClick={handleSave} className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700">팀 저장</button>
            </div>
        </div>
    );
}

// ===== 투표 제어 =====
function VoteControl({ cohortId, showMessage }) {
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(false);
    const [voteStartMode, setVoteStartMode] = useState('immediate');

    const loadConfig = async () => {
        try {
            const data = await api(`/api/admin/${cohortId}/vote-config`);
            if (data.success) setConfig(data.config);
        } catch {}
    };

    useEffect(() => { loadConfig(); }, [cohortId]);

    const handleStartVote = async (e) => {
        e.preventDefault();
        setLoading(true);
        const fd = new FormData(e.target);
        try {
            let data;
            if (voteStartMode === 'immediate') {
                data = await api(`/api/admin/${cohortId}/start-vote`, {
                    method: 'POST',
                    body: { duration_minutes: parseInt(fd.get('duration_minutes')) || 60, vote_mode: fd.get('vote_mode') || 'single' }
                });
            } else {
                data = await api(`/api/admin/${cohortId}/set-vote-time`, {
                    method: 'POST',
                    body: { start_time: fd.get('start_time'), end_time: fd.get('end_time'), vote_mode: fd.get('vote_mode') || 'single' }
                });
            }
            if (data.success) { showMessage(data.message); setConfig(data.config); }
        } catch (err) { showMessage(err.message || '오류', 'error'); }
        finally { setLoading(false); }
    };

    const handleStopVote = async () => {
        setLoading(true);
        try {
            const data = await api(`/api/admin/${cohortId}/stop-vote`, { method: 'POST', body: {} });
            if (data.success) { showMessage(data.message); setConfig(data.config); }
        } catch (err) { showMessage(err.message || '오류', 'error'); }
        finally { setLoading(false); }
    };

    const handleReset = async () => {
        if (!confirm('정말 모든 투표를 초기화하시겠습니까? 복구할 수 없습니다.')) return;
        setLoading(true);
        try {
            const data = await api(`/api/admin/${cohortId}/reset`, { method: 'POST', body: {} });
            if (data.success) { showMessage(data.message); loadConfig(); }
        } catch (err) { showMessage(err.message || '오류', 'error'); }
        finally { setLoading(false); }
    };

    if (!config) return <p className="text-gray-500">로딩 중...</p>;

    return (
        <div className="space-y-6">
            {/* 현재 상태 */}
            <div className={`p-4 rounded-lg border-2 ${config.is_active ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                <h3 className={`text-lg font-semibold ${config.is_active ? 'text-green-800' : 'text-red-800'}`}>
                    투표 상태: {config.is_active ? '활성화' : '비활성화'}
                </h3>
                {config.start_time && config.end_time && (
                    <p className="text-sm text-gray-600 mt-1">
                        시간: {config.start_time} ~ {config.end_time} | 방식: {utils.getVoteModeText(config.vote_mode)}
                    </p>
                )}
            </div>

            {/* 투표 시작/종료 */}
            {config.is_active ? (
                <div className="flex gap-3">
                    <button onClick={handleStopVote} disabled={loading}
                        className="bg-red-500 text-white px-6 py-2 rounded-lg hover:bg-red-600 disabled:opacity-50">
                        {loading ? '처리 중...' : '투표 종료'}
                    </button>
                    <button onClick={handleReset} disabled={loading}
                        className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600 disabled:opacity-50">투표 초기화</button>
                </div>
            ) : (
                <form onSubmit={handleStartVote} className="bg-gray-50 rounded-xl p-5 space-y-4">
                    <h3 className="font-bold">투표 시작 설정</h3>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">투표 방식</label>
                        <select name="vote_mode" defaultValue="single" className="px-3 py-2 border rounded-lg w-full">
                            <option value="single">1개 팀 선택</option>
                            <option value="multiple">3개 팀 선택</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">시작 방식</label>
                        <div className="space-y-2">
                            <label className="flex items-center">
                                <input type="radio" name="start_mode" value="immediate" defaultChecked onChange={e => setVoteStartMode(e.target.value)} className="mr-2" />
                                즉시 시작 (지정한 시간 동안)
                            </label>
                            <label className="flex items-center">
                                <input type="radio" name="start_mode" value="scheduled" onChange={e => setVoteStartMode(e.target.value)} className="mr-2" />
                                시간 설정 (특정 시간대에 진행)
                            </label>
                        </div>
                    </div>

                    {voteStartMode === 'immediate' ? (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">투표 시간 (분)</label>
                            <input type="number" name="duration_minutes" defaultValue={60} min="1" max="1440"
                                className="px-3 py-2 border rounded-lg w-full" />
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">시작 시간</label>
                                <TimeSelector name="start_time" required={true} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">종료 시간</label>
                                <TimeSelector name="end_time" required={true} />
                            </div>
                        </div>
                    )}

                    <div className="flex gap-3">
                        <button type="submit" disabled={loading}
                            className="bg-green-500 text-white px-6 py-2 rounded-lg hover:bg-green-600 disabled:opacity-50">
                            {loading ? '처리 중...' : '투표 시작'}
                        </button>
                        <button type="button" onClick={handleReset} disabled={loading}
                            className="bg-red-500 text-white px-6 py-2 rounded-lg hover:bg-red-600 disabled:opacity-50">투표 초기화</button>
                    </div>
                </form>
            )}
        </div>
    );
}

// ===== 투표 결과 =====
function VoteResults({ cohortId, showMessage }) {
    const [students, setStudents] = useState([]);
    const [teams, setTeams] = useState([]);
    const [votes, setVotes] = useState([]);
    const [stats, setStats] = useState({});
    const [subTab, setSubTab] = useState('results');

    const loadData = async () => {
        try {
            const [studentsData, votesData] = await Promise.all([
                api(`/api/admin/${cohortId}/students`),
                api(`/api/admin/${cohortId}/votes`)
            ]);
            setStudents(studentsData);
            setVotes(votesData.votes || []);
            setTeams(votesData.teams || []);
            setStats({ total_votes: votesData.total_votes, total_students: votesData.total_students, voted_students: votesData.voted_students });
        } catch { showMessage('데이터 로딩 실패', 'error'); }
    };

    useEffect(() => { loadData(); }, [cohortId]);

    const finalTeams = utils.calculateTeamRanks(teams);

    return (
        <div className="space-y-6">
            {/* 통계 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                    <h3 className="text-lg font-semibold text-blue-800">전체 학생</h3>
                    <p className="text-3xl font-bold text-blue-600">{stats.total_students || 0}</p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                    <h3 className="text-lg font-semibold text-green-800">투표 완료</h3>
                    <p className="text-3xl font-bold text-green-600">{stats.voted_students || 0}</p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                    <h3 className="text-lg font-semibold text-purple-800">투표율</h3>
                    <p className="text-3xl font-bold text-purple-600">
                        {stats.total_students > 0 ? Math.round((stats.voted_students || 0) / stats.total_students * 100) : 0}%
                    </p>
                </div>
            </div>

            {/* 액션 */}
            <div className="flex gap-3">
                <button onClick={loadData} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">새로고침</button>
                <button onClick={() => { window.location.href = `/api/admin/${cohortId}/download`; }}
                    className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">결과 다운로드</button>
            </div>

            {/* 서브 탭 */}
            <div className="flex border-b">
                <button onClick={() => setSubTab('results')}
                    className={`px-4 py-2 font-medium ${subTab === 'results' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}>
                    투표 결과
                </button>
                <button onClick={() => setSubTab('students')}
                    className={`px-4 py-2 font-medium ${subTab === 'students' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500'}`}>
                    학생 현황
                </button>
            </div>

            {subTab === 'results' ? (
                <div className="space-y-4">
                    {finalTeams.map(team => (
                        <div key={team.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                            <div className="flex items-center space-x-4">
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-white ${utils.getRankColor(team.rank)}`}>
                                    {team.rank}
                                </div>
                                <div>
                                    <h4 className="font-semibold text-gray-800">{team.name}</h4>
                                    <p className="text-sm text-gray-600">{team.project_name}</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-2xl font-bold text-blue-600">{team.vote_count || 0}</p>
                                <p className="text-sm text-gray-500">표</p>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b">
                                <th className="text-left py-2">이름</th>
                                <th className="text-left py-2">소속팀</th>
                                <th className="text-left py-2">투표상태</th>
                                <th className="text-left py-2">투표팀</th>
                                <th className="text-left py-2">투표시간</th>
                            </tr>
                        </thead>
                        <tbody>
                            {students.map(s => (
                                <tr key={s.id} className="border-b">
                                    <td className="py-2">{s.name}</td>
                                    <td className="py-2">{s.team_name || '-'}</td>
                                    <td className="py-2">
                                        <span className={`px-2 py-1 rounded-full text-xs ${s.has_voted ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                                            {s.has_voted ? '완료' : '미완료'}
                                        </span>
                                    </td>
                                    <td className="py-2">{utils.getVotedTeamNames(s, teams)}</td>
                                    <td className="py-2">{s.vote_timestamp || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

ReactDOM.render(<App />, document.getElementById('app'));
