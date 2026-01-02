document.getElementById('uploadForm').addEventListener('submit', function (e) {
    e.preventDefault();
    const files = document.getElementById('files').files;
    if (files.length === 0) {
        alert('Please select at least one PDF.');
        return;
    }

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    // UI Elements
    const progressBar = document.getElementById('progressBar');
    const uploadStatus = document.getElementById('uploadStatus');
    const processingStatus = document.getElementById('processingStatus');
    const processingText = document.getElementById('processingText');
    const resultsDiv = document.getElementById('results');

    // Reset UI
    progressBar.classList.remove('hidden');
    uploadStatus.textContent = 'Uploading...';
    processingStatus.classList.add('hidden');
    resultsDiv.innerHTML = '';

    let taskId = null;

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);

    // Upload Progress
    xhr.upload.addEventListener('progress', function (event) {
        if (event.lengthComputable) {
            const percent = (event.loaded / event.total) * 100;
            progressBar.value = percent;
            uploadStatus.textContent = `Uploading: ${Math.round(percent)}%`;
        }
    });

    xhr.onload = function () {
        if (xhr.status === 200) {
            const data = JSON.parse(xhr.responseText);
            taskId = data.task_id;

            progressBar.classList.add('hidden');
            uploadStatus.textContent = 'Upload complete. Processing...';
            processingStatus.classList.remove('hidden');
            processingText.textContent = 'Processing: 0 of 0...';

            pollStatus(taskId);
        } else {
            // Show error details
            try {
                const errorData = JSON.parse(xhr.responseText);
                uploadStatus.textContent = `Upload failed: ${errorData.error || 'Unknown error'}`;
            } catch {
                uploadStatus.textContent = `Upload failed with status ${xhr.status}`;
            }
            console.error('Server response:', xhr.responseText);
        }
    };

    xhr.onerror = function () {
        uploadStatus.textContent = 'Upload error.';
    };

    xhr.send(formData);
});

function pollStatus(taskId) {
    const processingText = document.getElementById('processingText');
    const resultsDiv = document.getElementById('results');
    const processingStatus = document.getElementById('processingStatus');

    const interval = setInterval(() => {
        fetch(`/status/${taskId}`)
            .then(res => res.json())
            .then(data => {
                processingText.textContent = `Processing: ${data.processed} of ${data.total}...`;

                if (data.done) {
                    clearInterval(interval);
                    processingStatus.classList.add('hidden');
                    resultsDiv.innerHTML = '<strong>Processing Complete!</strong><br>';

                    data.downloads.forEach((link, i) => {
                        const a = document.createElement('a');
                        a.href = link;
                        a.textContent = `Download Output ${i + 1}`;
                        a.download = '';
                        a.style.display = 'block';
                        a.style.margin = '5px 0';
                        resultsDiv.appendChild(a);
                    });
                }
            })
            .catch(err => {
                clearInterval(interval);
                processingText.textContent = 'Error checking status.';
            });
    }, 1000); // Poll every 1s
}