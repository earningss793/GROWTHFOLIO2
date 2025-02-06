document.addEventListener('DOMContentLoaded', function() {
    const resumeForm = document.getElementById('resume-form');
    const fileInput = document.getElementById('resume-file');
    const textArea = document.getElementById('resume-text');
    const progressBar = document.querySelector('.progress');
    const progressBarInner = document.querySelector('.progress-bar');
    const alert = document.querySelector('.alert');

    // 이력서 분석 처리
    resumeForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const resumeText = textArea.value.trim();
        const resumeFile = fileInput.files[0];

        if (!resumeText && !resumeFile) {
            showAlert('이력서 파일을 업로드하거나 내용을 입력해주세요.', 'danger');
            return;
        }

        // 진행 상태 초기화 및 표시
        progressBar.style.display = 'block';
        progressBarInner.style.width = '0%';
        progressBarInner.textContent = '분석 준비중...';

        try {
            const formData = new FormData();
            if (resumeFile) {
                formData.append('resume_file', resumeFile);
            }
            if (resumeText) {
                formData.append('resume_text', resumeText);
            }

            // 분석 단계별 진행상황
            const steps = [
                { progress: 15, text: '이력서 파일 처리중...' },
                { progress: 35, text: '텍스트 추출 및 분석중...' },
                { progress: 55, text: '경력 정보 추출중...' },
                { progress: 75, text: '프로젝트 데이터 정리중...' },
                { progress: 90, text: '포트폴리오 생성중...' }
            ];

            let currentStep = 0;
            const stepInterval = setInterval(() => {
                if (currentStep < steps.length) {
                    const { progress, text } = steps[currentStep];
                    progressBarInner.style.width = `${progress}%`;
                    progressBarInner.textContent = text;
                    currentStep++;
                }
            }, 800);

            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            clearInterval(stepInterval);

            if (response.ok) {
                // 완료 상태 표시
                progressBarInner.style.width = '100%';
                progressBarInner.textContent = '분석 완료!';

                const result = await response.text();
                document.body.innerHTML = result;
            } else {
                const error = await response.json();
                showAlert(error.error, 'danger');
                progressBar.style.display = 'none';
            }

        } catch (error) {
            showAlert('분석 중 오류가 발생했습니다.', 'danger');
            progressBar.style.display = 'none';
        }
    });

    function showAlert(message, type) {
        alert.textContent = message;
        alert.className = `alert alert-${type}`;
        alert.style.display = 'block';
        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    }
});