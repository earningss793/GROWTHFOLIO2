document.addEventListener('DOMContentLoaded', function() {
    const resumeForm = document.getElementById('resume-form');
    const fileInput = document.getElementById('resume-file');
    const textArea = document.getElementById('resume-text');
    const progressBar = document.querySelector('.progress');
    const progressBarInner = document.querySelector('.progress-bar');
    const alert = document.querySelector('.alert');
    const addProjectBtn = document.getElementById('addProjectBtn');
    const additionalProjects = document.getElementById('additional-projects');

    if (addProjectBtn) {
        addProjectBtn.addEventListener('click', function() {
            const projectSection = createProjectInputSection();
            document.getElementById('additional-projects').appendChild(projectSection);
            window.scrollTo({
                top: projectSection.offsetTop,
                behavior: 'smooth'
            });
        });
    }

    // 이력서 분석 처리
    if (resumeForm) {
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
    }

    function showAlert(message, type) {
        alert.textContent = message;
        alert.className = `alert alert-${type}`;
        alert.style.display = 'block';
        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    }

    function createProjectInputSection() {
        const section = document.createElement('div');
        section.className = 'card mb-4 project-section';
        section.innerHTML = `
            <div class="card-body">
                <div class="input-group">
                    <input type="text" class="form-control" placeholder="프로젝트명을 입력하세요">
                    <button class="btn btn-primary submit-project">확인</button>
                </div>
            </div>
        `;

        const input = section.querySelector('input');
        const submitBtn = section.querySelector('.submit-project');

        submitBtn.addEventListener('click', async () => {
            const projectName = input.value.trim();
            if (!projectName) {
                showAlert('프로젝트명을 입력해주세요.', 'danger');
                return;
            }

            submitBtn.disabled = true;
            input.disabled = true;

            try {
                const response = await fetch('/api/projects', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ project_name: projectName })
                });

                const result = await response.json();

                if (response.ok) {
                    // 입력 섹션을 결과로 교체
                    section.innerHTML = `
                        <div class="card-header">
                            <h5 class="mb-0">프로젝트명: ${result.project_name}</h5>
                        </div>
                        <div class="card-body">
                            <div class="mb-4">
                                <strong>업무 내용:</strong>
                                <ul>
                                    ${result.details.map(detail => `<li>${detail}</li>`).join('')}
                                </ul>
                                <strong>성과:</strong>
                                <ul>
                                    ${result.results.map(result => `<li>${result}</li>`).join('')}
                                </ul>
                            </div>
                        </div>
                    `;
                } else {
                    showAlert(result.error || '프로젝트 추가 중 오류가 발생했습니다.', 'danger');
                    submitBtn.disabled = false;
                    input.disabled = false;
                }
            } catch (error) {
                showAlert('서버와의 통신 중 오류가 발생했습니다.', 'danger');
                submitBtn.disabled = false;
                input.disabled = false;
            }
        });

        return section;
    }
});