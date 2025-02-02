document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('resume-form');
    const textArea = document.getElementById('resume-text');
    const progressBar = document.querySelector('.progress');
    const progressBarInner = document.querySelector('.progress-bar');
    const alert = document.querySelector('.alert');

    form.addEventListener('submit', async function(e) {
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
});