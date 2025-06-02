/**
 * Tasdeed Extraction Dashboard - Main JavaScript
 */

// DOM Elements
const uploadPage = document.getElementById('upload-page');
const processingPage = document.getElementById('processing-page');
const uploadForm = document.getElementById('upload-form');
const fileUpload = document.getElementById('file-upload');
const outputDir = document.getElementById('output-dir');
const startBtn = document.getElementById('start-btn');
const cancelBtn = document.getElementById('cancel-btn');
const finishBtn = document.getElementById('finish-btn');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const progressPercentage = document.getElementById('progress-percentage');
const successCount = document.getElementById('success-count');
const failedCount = document.getElementById('failed-count');
const totalCount = document.getElementById('total-count');
const logContainer = document.getElementById('log-container');

// Global variables
let socket = null;
let processing = false;

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Set up event listeners
    setupEventListeners();

    // Check for Firefox and show guidance if needed
    checkBrowserCompatibility();
});

/**
 * Check browser compatibility and show guidance for unsupported features
 */
function checkBrowserCompatibility() {
    // Check if the browser is Firefox
    const isFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1;

    // Check if the File System Access API is supported
    const supportsFileSystemAccess = 'showDirectoryPicker' in window;

    // If using Firefox, show guidance about directory selection
    if (isFirefox && !supportsFileSystemAccess) {
        // Add a note to the output directory label
        const outputDirLabel = document.querySelector('label[for="output-dir"]');
        if (outputDirLabel) {
            outputDirLabel.innerHTML += ' <span class="badge bg-info">Manual Entry Required</span>';
        }

        // Suggest a default path based on OS if the input is empty
        if (outputDir && !outputDir.value.trim()) {
            // Detect OS
            const isWindows = navigator.platform.indexOf('Win') > -1;
            const isMac = navigator.platform.indexOf('Mac') > -1;

            if (isWindows) {
                // Suggest Documents folder on Windows
                outputDir.value = 'C:\\Users\\' + (navigator.userAgent.split('Windows NT ')[1]?.split(';')[0] || 'YourUsername') + '\\Documents\\tasdeed_output';
                outputDir.placeholder = 'Example: C:\\Users\\YourUsername\\Documents\\tasdeed_output';
            } else if (isMac) {
                // Suggest Documents folder on Mac
                outputDir.value = '/Users/YourUsername/Documents/tasdeed_output';
                outputDir.placeholder = 'Example: /Users/YourUsername/Documents/tasdeed_output';
            } else {
                // Suggest home directory on Linux
                outputDir.value = '/home/YourUsername/tasdeed_output';
                outputDir.placeholder = 'Example: /home/YourUsername/tasdeed_output';
            }

            // Add a note to select and edit the suggested path
            showAlert('A default output path has been suggested. Please replace "YourUsername" with your actual username or enter a different path.', 'info');

            // Select the text to make it easy to edit
            outputDir.select();
        }

        // Show the help modal automatically for Firefox users
        // Use setTimeout to ensure the modal is shown after the page is fully loaded
        setTimeout(() => {
            const pathHelpModal = new bootstrap.Modal(document.getElementById('pathHelpModal'));
            pathHelpModal.show();
        }, 1000);
    }
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // Form submission
    uploadForm.addEventListener('submit', handleFormSubmit);

    // Cancel button
    cancelBtn.addEventListener('click', cancelProcessing);

    // Finish button
    finishBtn.addEventListener('click', () => {
        showPage(uploadPage);
        resetUI();
    });

    // Output directory button
    const outputDirBtn = document.getElementById('output-dir-btn');
    if (outputDirBtn) {
        outputDirBtn.addEventListener('click', async () => {
            try {
                // Check if the File System Access API is supported
                if ('showDirectoryPicker' in window) {
                    // Use the File System Access API to select a directory
                    const directoryHandle = await window.showDirectoryPicker();

                    // Get directory information
                    const directoryName = directoryHandle.name;

                    // For web security reasons, we can't get the full path
                    // We'll use the directory name and let the user modify it if needed

                    // If there's already a path in the input, try to preserve the parent path
                    let currentPath = outputDir.value.trim();
                    let newPath = '';

                    if (currentPath) {
                        // If the current path ends with a slash, append the directory name
                        if (currentPath.endsWith('/') || currentPath.endsWith('\\')) {
                            newPath = currentPath + directoryName;
                        } else {
                            // Otherwise, replace the last part of the path with the new directory name
                            const parts = currentPath.split(/[\/\\]/);
                            parts.pop(); // Remove the last part
                            parts.push(directoryName); // Add the new directory name
                            newPath = parts.join('/');
                        }
                    } else {
                        // If there's no current path, just use the directory name
                        // Prepend with ./ to indicate it's relative to the current directory
                        newPath = './' + directoryName;
                    }

                    // Update the output directory input field
                    outputDir.value = newPath;

                    // Show a success message with guidance
                    showAlert(`Directory selected: ${directoryName}. Path set to: ${newPath}. You can edit this path if needed.`, 'success');
                } else {
                    // Fallback for browsers that don't support the File System Access API
                    const isFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1;
                    if (isFirefox) {
                        showAlert('Firefox doesn\'t support directory browsing for security reasons. We\'ve suggested a path below, but you\'ll need to customize it for your system. Make sure the directory exists or will be created automatically.', 'info');
                    } else {
                        showAlert('Your browser doesn\'t support directory browsing. Please enter the output directory path manually. Use an absolute path for best results.', 'info');
                    }

                    // Focus on the input field to encourage the user to type a path
                    outputDir.focus();
                }
            } catch (error) {
                // Handle errors (e.g., user cancelled the directory picker)
                console.error('Error selecting directory:', error);
                if (error.name !== 'AbortError') {
                    showAlert('Error selecting directory: ' + error.message, 'error');
                }
            }
        });
    }
}

/**
 * Handle form submission
 * @param {Event} e - Form submit event
 */
function handleFormSubmit(e) {
    e.preventDefault();

    // Validate form
    if (!fileUpload.files || fileUpload.files.length === 0) {
        showAlert('Please select a file', 'warning');
        return;
    }

    // Get form data
    const formData = new FormData();
    formData.append('file', fileUpload.files[0]);

    // Validate output directory
    if (!outputDir.value.trim()) {
        showAlert('Please enter an output directory', 'warning');
        return;
    }
    formData.append('output_dir', outputDir.value);

    // Start processing
    startProcessing(formData);
}

/**
 * Start the processing of accounts
 * @param {FormData} formData - Form data with file and output directory
 */
function startProcessing(formData) {
    // Reset UI
    resetUI();

    // Show processing page
    showPage(processingPage);

    // Set processing flag
    processing = true;

    // Upload file and start processing
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('File upload failed');
        }
        return response.json();
    })
    .then(data => {
        // Connect to WebSocket for real-time updates
        connectWebSocket(data.task_id);

        // Add initial log
        addLog('⏳ Starting extraction process...', 'info');
        addLog(`📂 File: ${fileUpload.files[0].name}`, 'info');
        addLog(`💾 Output directory: ${outputDir.value || './output'}`, 'info');

        // Update total count
        totalCount.textContent = data.total_accounts || '0';
    })
    .catch(error => {
        console.error('Error:', error);
        addLog(`❌ Error: ${error.message}`, 'error');
        finishProcessing(false);
    });
}

/**
 * Connect to WebSocket for real-time updates
 * @param {string} taskId - Task ID for the current processing job
 */
function connectWebSocket(taskId) {
    // Close existing socket if any
    if (socket) {
        socket.close();
    }

    // Create new WebSocket connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${taskId}`;

    socket = new WebSocket(wsUrl);

    // Store the task ID on the socket object for later use
    socket.taskId = taskId;

    // WebSocket event handlers
    socket.onopen = () => {
        console.log('WebSocket connected');
        addLog('🔌 Connected to server', 'info');
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        addLog('❌ Connection error', 'error');
    };

    socket.onclose = () => {
        console.log('WebSocket disconnected');
        if (processing) {
            addLog('🔌 Disconnected from server', 'warning');
        }
    };
}

/**
 * Handle WebSocket messages
 * @param {Object} data - Message data
 */
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'progress':
            updateProgress(data.current, data.total, data.message);
            break;

        case 'log':
            addLog(data.message, data.level || 'info');
            break;

        case 'stats':
            updateStats(data.success, data.failed, data.total);
            break;

        case 'complete':
            addLog('✅ Processing complete!', 'success');
            addLog(`📊 Summary: Success: ${data.success}, Failed: ${data.failed}, Total: ${data.total}`, 'info');
            if (data.output_file) {
                addLog(`📂 Output saved to: ${data.output_file}`, 'success');
            }
            finishProcessing(true);
            break;

        case 'error':
            addLog(`❌ Error: ${data.message}`, 'error');
            finishProcessing(false);
            break;
    }
}

/**
 * Update progress bar and text
 * @param {number} current - Current progress
 * @param {number} total - Total items
 * @param {string} message - Progress message
 */
function updateProgress(current, total, message) {
    // Update progress bar
    const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
    progressBar.style.width = `${percentage}%`;
    progressText.textContent = `Progress: ${current} / ${total}`;
    progressPercentage.textContent = `${percentage}%`;

    // Add log message if provided
    if (message) {
        let logType = 'info';
        if (message.includes('✅ Success')) {
            logType = 'success';
        } else if (message.includes('❌ Failed')) {
            logType = 'error';
        } else if (message.includes('⚠️')) {
            logType = 'warning';
        }

        addLog(message, logType);
    }
}

/**
 * Update statistics counters
 * @param {number} success - Success count
 * @param {number} failed - Failed count
 * @param {number} total - Total count
 */
function updateStats(success, failed, total) {
    successCount.textContent = success;
    failedCount.textContent = failed;
    totalCount.textContent = total;
}

/**
 * Add a log message to the log container
 * @param {string} message - Log message
 * @param {string} level - Log level (info, success, warning, error)
 */
function addLog(message, level = 'info') {
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${level}`;

    const timestamp = new Date().toLocaleTimeString();
    logEntry.textContent = `[${timestamp}] ${message}`;

    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

/**
 * Show an alert message
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, warning, danger)
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alertEl = document.createElement('div');
    alertEl.className = `alert alert-${type} alert-dismissible fade show`;
    alertEl.setAttribute('role', 'alert');

    // Add message
    alertEl.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    // Add to page
    const alertContainer = document.createElement('div');
    alertContainer.className = 'container mt-3';
    alertContainer.appendChild(alertEl);

    document.body.insertBefore(alertContainer, document.body.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertEl.classList.remove('show');
        setTimeout(() => alertContainer.remove(), 150);
    }, 5000);
}

/**
 * Cancel the current processing
 */
function cancelProcessing() {
    if (!processing) return;

    // Confirm cancellation
    if (!confirm('Are you sure you want to cancel the current process?')) {
        return;
    }

    // Send cancel request
    fetch('/api/cancel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ task_id: socket ? socket.taskId : null })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to cancel process');
        }
        return response.json();
    })
    .then(data => {
        addLog('❌ Process cancelled by user', 'warning');
        finishProcessing(false);
    })
    .catch(error => {
        console.error('Error:', error);
        addLog(`❌ Error cancelling: ${error.message}`, 'error');
    });
}

/**
 * Finish the processing
 * @param {boolean} success - Whether processing completed successfully
 */
function finishProcessing(success) {
    processing = false;

    // Update UI
    cancelBtn.style.display = 'none';
    finishBtn.style.display = 'block';

    // Close WebSocket
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }
}

/**
 * Reset the UI for a new processing job
 */
function resetUI() {
    // Reset progress
    progressBar.style.width = '0%';
    progressText.textContent = 'Progress: 0 / 0';
    progressPercentage.textContent = '0%';

    // Reset stats
    successCount.textContent = '0';
    failedCount.textContent = '0';
    totalCount.textContent = '0';

    // Reset log
    logContainer.innerHTML = '';

    // Reset buttons
    cancelBtn.style.display = 'block';
    finishBtn.style.display = 'none';
}

/**
 * Show a specific page and hide others
 * @param {HTMLElement} page - Page to show
 */
function showPage(page) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
    });

    // Show the specified page
    page.classList.add('active');
}
