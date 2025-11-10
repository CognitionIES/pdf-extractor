// main.js - PDF Extractor Pro
// Handles upload, progress, polling, and results

document.getElementById('uploadForm').addEventListener('submit', function (e) {
  e.preventDefault();

  const files = document.getElementById('files').files;
  if (files.length === 0) {
    alert('Please select at least one PDF file.');
    return;
  }

  const formData = new FormData();
  for (let file of files) {
    formData.append('files', file);
  }

  // UI Elements
  const progressSection = document.getElementById('progressSection');
  const uploadBar = document.getElementById('uploadBar');
  const uploadPercent = document.getElementById('uploadPercent');
  const processingStatus = document.getElementById('processingStatus');
  const processingText = document.getElementById('processingText');
  const resultsDiv = document.getElementById('results');

  // Reset UI
  progressSection.classList.remove('hidden');
  uploadBar.style.width = '0%';
  uploadPercent.textContent = '0%';
  processingStatus.classList.add('hidden');
  resultsDiv.innerHTML = '';

  let taskId = null;

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/upload', true);

  // Upload Progress
  xhr.upload.addEventListener('progress', function (event) {
    if (event.lengthComputable) {
      const percent = (event.loaded / event.total) * 100;
      uploadBar.style.width = `${percent}%`;
      uploadPercent.textContent = `${Math.round(percent)}%`;
    }
  });

  xhr.onload = function () {
    if (xhr.status === 200) {
      const data = JSON.parse(xhr.responseText);
      taskId = data.task_id;

      // Hide upload bar, show processing
      uploadBar.style.width = '100%';
      uploadPercent.textContent = '100%';
      setTimeout(() => {
        processingStatus.classList.remove('hidden');
        processingText.textContent = 'Processing: 0 of 0...';
        pollStatus(taskId);
      }, 600);
    } else {
      showError('Upload failed. Please try again.');
    }
  };

  xhr.onerror = function () {
    showError('Network error. Check your connection.');
  };

  xhr.send(formData);
});

// Poll for processing status
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
          showResults(data.downloads);
        }
      })
      .catch(err => {
        clearInterval(interval);
        showError('Failed to check status. Please refresh.');
      });
  }, 1000);
}

// Show download links
function showResults(downloads) {
  const resultsDiv = document.getElementById('results');
  resultsDiv.innerHTML = `
    <div class="text-center p-6 bg-green-50 rounded-lg border border-green-200">
      <i class="fas fa-check-circle text-4xl text-green-600 mb-3"></i>
      <p class="text-lg font-semibold text-green-800">All PDFs processed!</p>
      <p class="text-sm text-green-700 mt-1">Download your structured Excel reports:</p>
    </div>
  `;

  const linksContainer = document.createElement('div');
  linksContainer.className = 'mt-6 space-y-3';

  downloads.forEach((link, index) => {
    const a = document.createElement('a');
    a.href = link;
    a.download = '';
    a.className = 'block w-full text-center bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg shadow transition duration-200 flex items-center justify-center';
    a.innerHTML = `<i class="fas fa-download mr-2"></i> Download Report ${index + 1}`;
    linksContainer.appendChild(a);
  });

  resultsDiv.appendChild(linksContainer);
}

// Error handler
function showError(message) {
  const resultsDiv = document.getElementById('results');
  resultsDiv.innerHTML = `
    <div class="text-center p-6 bg-red-50 rounded-lg border border-red-200">
      <i class="fas fa-exclamation-triangle text-4xl text-red-600 mb-3"></i>
      <p class="text-lg font-semibold text-red-800">Error</p>
      <p class="text-sm text-red-700 mt-1">${message}</p>
    </div>
  `;
}