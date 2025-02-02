document.addEventListener('DOMContentLoaded', function() {
    const resumeForm = document.getElementById('resume-form');
    const templateForm = document.getElementById('template-form');
    const textArea = document.getElementById('resume-text');
    const progressBar = document.querySelector('.progress');
    const progressBarInner = document.querySelector('.progress-bar');
    const alert = document.querySelector('.alert');
    const templateAlert = document.querySelector('.template-alert');

    // 템플릿 업로드 처리
    templateForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(templateForm);

        try {
            const response = await fetch('/upload_template', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                showTemplateAlert('템플릿이 성공적으로 업로드되었습니다.', 'success');
            } else {
                const error = await response.json();
                showTemplateAlert(error.error, 'danger');
            }
        } catch (error) {
            showTemplateAlert('템플릿 업로드 중 오류가 발생했습니다.', 'danger');
        }
    });

    // 이력서 분석 처리
    resumeForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const resumeText = textArea.value.trim();

        if (!resumeText) {
            showAlert('이력서 내용을 입력해주세요.', 'danger');
            return;
        }

        // Show progress bar
        progressBar.style.display = 'block';
        progressBarInner.style.width = '0%';

        try {
            // Simulate progress
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += 10;
                if (progress <= 90) {
                    progressBarInner.style.width = progress + '%';
                }
            }, 500);

            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    resume_text: resumeText
                })
            });

            clearInterval(progressInterval);
            progressBarInner.style.width = '100%';

            if (response.ok) {
                const result = await response.text();
                document.body.innerHTML = result;
            } else {
                const error = await response.json();
                showAlert(error.error, 'danger');
            }

        } catch (error) {
            showAlert('분석 중 오류가 발생했습니다.', 'danger');
        }
    });

    function showAlert(message, type) {
        alert.textContent = message;
        alert.className = `alert alert-${type} fade-in`;
        alert.style.display = 'block';

        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    }

    function showTemplateAlert(message, type) {
        templateAlert.textContent = message;
        templateAlert.className = `alert alert-${type} fade-in`;
        templateAlert.style.display = 'block';

        setTimeout(() => {
            templateAlert.style.display = 'none';
        }, 5000);
    }
});