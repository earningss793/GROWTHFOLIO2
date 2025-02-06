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
                { progress: 15 },
                { progress: 35 },
                { progress: 55 },
                { progress: 75 },
                { progress: 90 }
            ];

            let currentStep = 0;
            const stepInterval = setInterval(() => {
                if (currentStep < steps.length) {
                    const { progress } = steps[currentStep];
                    progressBarInner.style.width = `${progress}%`;
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