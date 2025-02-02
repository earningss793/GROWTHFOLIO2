document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const progressBar = document.querySelector('.progress');
    const progressBarInner = document.querySelector('.progress-bar');
    const alert = document.querySelector('.alert');
    
    fileInput.addEventListener('change', function(e) {
        const fileName = e.target.files[0]?.name;
        if (fileName) {
            document.querySelector('.upload-btn').textContent = fileName;
        }
    });
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        if (!fileInput.files[0]) {
            showAlert('파일을 선택해주세요.', 'danger');
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
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
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
            showAlert('파일 업로드 중 오류가 발생했습니다.', 'danger');
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
