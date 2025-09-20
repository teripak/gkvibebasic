// 메인 JavaScript 파일
document.addEventListener('DOMContentLoaded', function() {
    console.log('AI 에이전트 페이지가 로드되었습니다.');
    
    // 패널 토글 기능 초기화
    initializePanelToggles();
    
    // 반응형 처리
    handleResponsiveLayout();
    
    // 윈도우 리사이즈 이벤트 리스너
    window.addEventListener('resize', handleResponsiveLayout);
    
    // 채팅 기능 초기화
    initializeChat();
    
    // 파일 업로드 기능 초기화
    initializeFileUpload();
    
    // 문서 클릭 이벤트 초기화
    initializeDocumentClicks();
});

// 패널 토글 기능 초기화
function initializePanelToggles() {
    // 초기 상태 설정
    const leftPanel = document.getElementById('leftPanel');
    const rightPanel = document.getElementById('rightPanel');
    const centerPanel = document.getElementById('centerPanel');
    
    if (leftPanel && rightPanel && centerPanel) {
        // 로컬 스토리지에서 패널 상태 복원
        const leftHidden = localStorage.getItem('leftPanelHidden') === 'true';
        const rightHidden = localStorage.getItem('rightPanelHidden') === 'true';
        
        if (leftHidden) {
            hidePanel('left');
        }
        if (rightHidden) {
            hidePanel('right');
        }
    }
}

// 패널 토글 (숨김/보이기)
function togglePanel(side) {
    const panel = document.getElementById(side + 'Panel');
    
    if (panel.classList.contains('panel-hidden')) {
        showPanel(side);
    } else {
        hidePanel(side);
    }
}

// 패널 숨기기 - 보이기 버튼 width만큼 남기고 숨김
function hidePanel(side) {
    const panel = document.getElementById(side + 'Panel');
    const toggleBtn = document.getElementById(side + 'ToggleBtn');
    
    if (panel && toggleBtn) {
        // 패널을 숨김 상태로 설정
        panel.classList.add('panel-hidden');
        
        // 토글 버튼 아이콘과 툴팁 변경
        const icon = toggleBtn.querySelector('.icon');
        if (side === 'left') {
            icon.textContent = '›';
            toggleBtn.title = '보이기';
        } else {
            icon.textContent = '‹';
            toggleBtn.title = '보이기';
        }
        
        // 로컬 스토리지에 상태 저장
        localStorage.setItem(side + 'PanelHidden', 'true');
        
        // 중간 패널 크기 조정
        adjustCenterPanel();
        
        // 애니메이션 효과
        panel.classList.add('panel-hide');
    }
}

// 패널 보이기 - 전체 패널 다시 표시
function showPanel(side) {
    const panel = document.getElementById(side + 'Panel');
    const toggleBtn = document.getElementById(side + 'ToggleBtn');
    
    if (panel && toggleBtn) {
        // 패널을 보이게 함
        panel.classList.remove('panel-hidden');
        
        // 토글 버튼 아이콘과 툴팁 변경
        const icon = toggleBtn.querySelector('.icon');
        if (side === 'left') {
            icon.textContent = '‹';
            toggleBtn.title = '숨기기';
        } else {
            icon.textContent = '›';
            toggleBtn.title = '숨기기';
        }
        
        // 로컬 스토리지에서 상태 제거
        localStorage.removeItem(side + 'PanelHidden');
        
        // 중간 패널 크기 조정
        adjustCenterPanel();
        
        // 애니메이션 효과
        panel.classList.remove('panel-hide');
        panel.classList.add('panel-show');
        setTimeout(() => {
            panel.classList.remove('panel-show');
        }, 300);
    }
}

// 중간 패널 크기 조정
function adjustCenterPanel() {
    const leftPanel = document.getElementById('leftPanel');
    const rightPanel = document.getElementById('rightPanel');
    const centerPanel = document.getElementById('centerPanel');
    
    if (!leftPanel || !rightPanel || !centerPanel) return;
    
    const leftHidden = leftPanel.classList.contains('panel-hidden');
    const rightHidden = rightPanel.classList.contains('panel-hidden');
    
    if (leftHidden && rightHidden) {
        centerPanel.style.width = '100%';
    } else if (leftHidden || rightHidden) {
        centerPanel.style.width = '75%';
    } else {
        centerPanel.style.width = '50%';
    }
}

// 반응형 레이아웃 처리
function handleResponsiveLayout() {
    const mainLayout = document.querySelector('.main-layout');
    
    if (window.innerWidth <= 768) {
        // 모바일에서는 모든 패널을 세로로 배치
        if (mainLayout) {
            mainLayout.style.flexDirection = 'column';
        }
        
        const panels = document.querySelectorAll('.left-panel, .center-panel, .right-panel');
        panels.forEach(panel => {
            panel.style.width = '100%';
            panel.style.height = '33.33%';
            panel.style.display = 'block';
            panel.style.overflow = 'visible';
            
            // 모바일에서는 모든 패널 콘텐츠 보이기
            const panelContent = panel.querySelector('.panel-content');
            if (panelContent) {
                panelContent.style.display = 'block';
            }
            
            // 모바일에서는 숨김 상태 해제
            panel.classList.remove('panel-hidden');
        });
    } else {
        // 데스크톱에서는 가로 배치로 복원
        if (mainLayout) {
            mainLayout.style.flexDirection = 'row';
        }
        
        // 패널 상태 복원
        adjustCenterPanel();
    }
}

// 채팅 기능 초기화
function initializeChat() {
    const chatInput = document.querySelector('.chat-input');
    const sendBtn = document.querySelector('.send-btn');
    const chatMessages = document.querySelector('.chat-messages');
    
    if (chatInput && sendBtn && chatMessages) {
        // 전송 버튼 클릭 이벤트
        sendBtn.addEventListener('click', function() {
            sendMessage();
        });
        
        // 엔터키 이벤트
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
}

// 메시지 전송
function sendMessage() {
    const chatInput = document.querySelector('.chat-input');
    const chatMessages = document.querySelector('.chat-messages');
    
    if (chatInput && chatMessages && chatInput.value.trim()) {
        const message = chatInput.value.trim();
        
        // 사용자 메시지 추가
        addMessage(message, 'user');
        
        // 입력창 초기화
        chatInput.value = '';
        
        // AI 응답 시뮬레이션 (1초 후)
        setTimeout(() => {
            const aiResponse = generateAIResponse(message);
            addMessage(aiResponse, 'ai');
        }, 1000);
    }
}

// 메시지 추가
function addMessage(content, type) {
    const chatMessages = document.querySelector('.chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    if (type === 'ai') {
        messageDiv.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">${content}</div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-content">${content}</div>
            <div class="message-avatar">👤</div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// AI 응답 생성 (간단한 시뮬레이션)
function generateAIResponse(userMessage) {
    const responses = [
        "문서를 분석해보겠습니다. 관련 정보를 찾아드릴게요.",
        "흥미로운 질문이네요. 근거 자료를 확인해보겠습니다.",
        "해당 내용에 대해 더 자세히 알아보겠습니다.",
        "문서에서 관련 정보를 찾았습니다. 참조해주세요.",
        "좋은 지적입니다. 추가 분석이 필요할 것 같습니다."
    ];
    
    return responses[Math.floor(Math.random() * responses.length)];
}

// 파일 업로드 관련 기능 초기화
function initializeFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.querySelector('.upload-btn');
    const selectAllCheckbox = document.querySelector('.select-all-checkbox');
    
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            handleFileSelection(e.target.files);
        });
    }
    
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function() {
            uploadFiles();
        });
    }
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            toggleSelectAll(this.checked);
        });
    }
    
    // 개별 파일 체크박스 이벤트
    initializeFileCheckboxes();
    
    // 설정 버튼 이벤트
    initializeSettingsButton();
}

// 파일 선택 처리
function handleFileSelection(files) {
    if (files.length > 0) {
        console.log(`${files.length}개의 파일이 선택되었습니다.`);
        // 선택된 파일들을 목록에 추가 (시뮬레이션)
        addFilesToList(files);
    }
}

// 선택된 파일들을 목록에 추가
function addFilesToList(files) {
    const fileListBody = document.getElementById('fileListBody');
    
    Array.from(files).forEach(file => {
        const fileItem = createFileItem(file.name, 'active');
        fileListBody.appendChild(fileItem);
    });
    
    // 새로 추가된 파일들에 이벤트 리스너 추가
    initializeFileCheckboxes();
}

// 파일 아이템 생성
function createFileItem(fileName, status = 'active') {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    
    const statusClass = status === 'active' ? 'active' : 'inactive';
    
    fileItem.innerHTML = `
        <div class="status-indicator ${statusClass}"></div>
        <div class="file-name">${fileName}</div>
        <input type="checkbox" class="file-checkbox">
    `;
    
    return fileItem;
}

// 파일 업로드 함수 (시뮬레이션)
function uploadFiles() {
    const fileInput = document.getElementById('fileInput');
    const backgroundUpload = document.getElementById('backgroundUpload');
    
    if (fileInput.files.length === 0) {
        alert('업로드할 파일을 선택해주세요.');
        return;
    }
    
    // 업로드 진행 상태 표시
    showUploadProgress();
    
    // 시뮬레이션: 2초 후 완료
    setTimeout(() => {
        hideUploadProgress();
        console.log('파일 업로드 완료 (시뮬레이션)');
        fileInput.value = ''; // 파일 입력 초기화
    }, 2000);
}

// 업로드 진행 상태 표시
function showUploadProgress() {
    const uploadBtn = document.querySelector('.upload-btn');
    const originalText = uploadBtn.innerHTML;
    
    uploadBtn.innerHTML = '<span class="upload-icon">⏳</span>';
    uploadBtn.disabled = true;
    
    uploadBtn.dataset.originalText = originalText;
}

// 업로드 진행 상태 숨기기
function hideUploadProgress() {
    const uploadBtn = document.querySelector('.upload-btn');
    const originalText = uploadBtn.dataset.originalText;
    
    uploadBtn.innerHTML = originalText || '<span class="upload-icon">↑</span>';
    uploadBtn.disabled = false;
}

// 파일 목록 새로고침
function reloadFileList() {
    console.log('파일 목록을 새로고침합니다.');
    
    // 새로고침 아이콘 애니메이션
    const reloadBtn = document.querySelector('.reload-btn');
    if (reloadBtn) {
        reloadBtn.style.transform = 'rotate(360deg)';
        setTimeout(() => {
            reloadBtn.style.transform = 'rotate(0deg)';
        }, 500);
    }
}

// 파일 체크박스 이벤트 초기화
function initializeFileCheckboxes() {
    const fileCheckboxes = document.querySelectorAll('.file-checkbox');
    
    fileCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateSelectAllCheckbox();
        });
    });
}

// 전체 선택/해제 기능
function toggleSelectAll(checked) {
    const fileCheckboxes = document.querySelectorAll('.file-checkbox');
    
    fileCheckboxes.forEach(checkbox => {
        checkbox.checked = checked;
    });
}

// 전체 선택 체크박스 상태 업데이트
function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.querySelector('.select-all-checkbox');
    const fileCheckboxes = document.querySelectorAll('.file-checkbox');
    
    if (selectAllCheckbox && fileCheckboxes.length > 0) {
        const checkedCount = document.querySelectorAll('.file-checkbox:checked').length;
        
        if (checkedCount === 0) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = false;
        } else if (checkedCount === fileCheckboxes.length) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = true;
        } else {
            selectAllCheckbox.indeterminate = true;
        }
    }
}

// 문서 클릭 이벤트 초기화
function initializeDocumentClicks() {
    const fileItems = document.querySelectorAll('.file-item');
    
    fileItems.forEach(item => {
        item.addEventListener('click', function(e) {
            // 체크박스 클릭은 별도 처리
            if (e.target.type === 'checkbox') {
                return;
            }
            
            // 활성 문서 표시
            fileItems.forEach(file => file.classList.remove('active'));
            this.classList.add('active');
            
            // 근거 영역에 관련 정보 표시 (시뮬레이션)
            const fileName = this.querySelector('.file-name').textContent;
            updateEvidence(fileName);
        });
    });
}

// 설정 버튼 초기화
function initializeSettingsButton() {
    const settingsBtn = document.querySelector('.settings-btn');
    
    if (settingsBtn) {
        settingsBtn.addEventListener('click', function() {
            openSettingsModal();
        });
    }
}

// 설정 모달 열기
function openSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // 배경 스크롤 방지
        
        // 기존 설정값 로드
        loadSettingsFromServer();
    }
}

// 설정 모달 닫기
function closeSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto'; // 배경 스크롤 복원
    }
}

// 서버에서 설정 로드
async function loadSettingsFromServer() {
    try {
        const response = await fetch('/api/get-upload-settings/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success && data.settings) {
            // 폼에 설정값 적용
            const llmSelect = document.getElementById('llmSelect');
            const promptText = document.getElementById('promptText');
            const chunkSize = document.getElementById('chunkSize');
            const chunkOverlap = document.getElementById('chunkOverlap');
            
            if (llmSelect && data.settings.selected_llm) {
                llmSelect.value = data.settings.selected_llm;
            }
            
            if (promptText && data.settings.prompt_text) {
                promptText.value = data.settings.prompt_text;
            }
            
            if (chunkSize && data.settings.chunk_size) {
                chunkSize.value = data.settings.chunk_size;
            }
            
            if (chunkOverlap && data.settings.chunk_overlap) {
                chunkOverlap.value = data.settings.chunk_overlap;
            }
        }
    } catch (error) {
        console.error('설정 로드 중 오류 발생:', error);
    }
}

// 설정 저장
async function saveUploadSettings() {
    const form = document.getElementById('uploadSettingsForm');
    const formData = new FormData(form);
    
    // 폼 유효성 검사
    if (!validateSettingsForm()) {
        return;
    }
    
    // 설정값을 객체로 변환
    const settings = {
        selected_llm: formData.get('selected_llm'),
        prompt_text: formData.get('prompt_text'),
        chunk_size: parseInt(formData.get('chunk_size')),
        chunk_overlap: parseInt(formData.get('chunk_overlap'))
    };
    
    try {
        const response = await fetch('/api/save-upload-settings/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            closeSettingsModal();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('설정 저장 중 오류 발생:', error);
        showNotification('설정 저장 중 오류가 발생했습니다.', 'error');
    }
}

// 폼 유효성 검사
function validateSettingsForm() {
    const llmSelect = document.getElementById('llmSelect');
    const chunkSize = document.getElementById('chunkSize');
    const chunkOverlap = document.getElementById('chunkOverlap');
    
    if (!llmSelect.value) {
        showNotification('LLM 모델을 선택해주세요.', 'error');
        llmSelect.focus();
        return false;
    }
    
    if (chunkSize.value < 100 || chunkSize.value > 5000) {
        showNotification('청크 글자수는 100-5000 사이여야 합니다.', 'error');
        chunkSize.focus();
        return false;
    }
    
    if (chunkOverlap.value < 0 || chunkOverlap.value > 1000) {
        showNotification('청크 겹침 글자수는 0-1000 사이여야 합니다.', 'error');
        chunkOverlap.focus();
        return false;
    }
    
    if (chunkOverlap.value >= chunkSize.value) {
        showNotification('청크 겹침 글자수는 청크 글자수보다 작아야 합니다.', 'error');
        chunkOverlap.focus();
        return false;
    }
    
    return true;
}

// 알림 메시지 표시
function showNotification(message, type = 'info') {
    // 기존 알림 제거
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 새 알림 생성
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // 스타일 적용
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 4px;
        color: white;
        font-weight: 500;
        z-index: 1001;
        animation: slideInRight 0.3s ease-out;
        max-width: 300px;
        word-wrap: break-word;
    `;
    
    // 타입별 색상 설정
    if (type === 'success') {
        notification.style.backgroundColor = '#28a745';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#dc3545';
    } else {
        notification.style.backgroundColor = '#0066cc';
    }
    
    // 애니메이션 CSS 추가
    if (!document.querySelector('#notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(notification);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideInRight 0.3s ease-out reverse';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, 3000);
}

// 모달 외부 클릭 시 닫기
document.addEventListener('click', function(event) {
    const modal = document.getElementById('settingsModal');
    if (event.target === modal) {
        closeSettingsModal();
    }
});

// ESC 키로 모달 닫기
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('settingsModal');
        if (modal && modal.style.display === 'block') {
            closeSettingsModal();
        }
    }
});

// 근거 정보 업데이트
function updateEvidence(documentTitle) {
    const evidenceItems = document.querySelectorAll('.evidence-item');
    
    evidenceItems.forEach((item, index) => {
        const source = item.querySelector('.evidence-source');
        const text = item.querySelector('.evidence-text');
        
        source.textContent = `${documentTitle} - 페이지 ${index + 1}`;
        text.textContent = `${documentTitle}와 관련된 내용이 여기에 표시됩니다. 실제 구현에서는 문서 내용을 분석하여 관련 정보를 추출합니다.`;
    });
}

// 유틸리티 함수들
function showNotification(message, type = 'info') {
    // 간단한 알림 시스템 (향후 확장 가능)
    console.log(`${type.toUpperCase()}: ${message}`);
}

// 키보드 단축키 지원
document.addEventListener('keydown', function(e) {
    // Ctrl + 1: 왼쪽 패널 토글
    if (e.ctrlKey && e.key === '1') {
        e.preventDefault();
        togglePanel('left');
    }
    
    // Ctrl + 3: 오른쪽 패널 토글
    if (e.ctrlKey && e.key === '3') {
        e.preventDefault();
        togglePanel('right');
    }
    
    // Ctrl + 2: 모든 패널 보이기
    if (e.ctrlKey && e.key === '2') {
        e.preventDefault();
        showPanel('left');
        showPanel('right');
    }
});

// 페이지 언로드 시 상태 저장
window.addEventListener('beforeunload', function() {
    // 이미 로컬 스토리지에 저장되어 있으므로 추가 작업 불필요
});

// 아이콘 버튼 호버 효과
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtns = document.querySelectorAll('.toggle-btn');
    
    toggleBtns.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
});
