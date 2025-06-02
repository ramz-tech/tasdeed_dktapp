# Tasdeed Extraction Dashboard - Web UI

A modern web interface for the Tasdeed Extraction Dashboard, providing a user-friendly way to upload account files, track extraction progress, and view logs in real-time.

## Features

- **Modern UI**: Clean, responsive design using Bootstrap 5
- **Real-time Updates**: WebSocket-based progress tracking and logging
- **File Upload**: Easy Excel/CSV file upload with validation
- **Progress Tracking**: Visual progress bar and statistics
- **Detailed Logs**: Real-time log display with color-coded messages

## Screenshots

![Upload Page](screenshots/upload.png)
![Processing Page](screenshots/processing.png)

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure you have the necessary permissions to access the Oracle CRM website.

## Running the Web UI

From the project root directory, run:

```bash
python -m web
```

This will start the web server on port 8080. You can access the dashboard by opening a web browser and navigating to:

```
http://localhost:8080
```

You can specify a different port using the `PORT` environment variable:

```bash
PORT=9000 python -m web
```

## Usage

1. **Upload File**: 
   - Click "Select Excel or CSV File" to upload your account file
   - The file must contain `ACCOUNTNO` and `SUBTYPE` columns
   - Only one `SUBTYPE` value should exist in the file

2. **Select Output Directory**:
   - Specify where the extracted data should be saved
   - Default is `./output` in the current directory

3. **Start Extraction**:
   - Click "Start Extraction" to begin the process
   - The dashboard will switch to the processing view

4. **Monitor Progress**:
   - Watch the progress bar and statistics update in real-time
   - View detailed logs in the log container
   - Success and failure counts are updated as accounts are processed

5. **Finish or Cancel**:
   - You can cancel the process at any time by clicking "Cancel"
   - When processing is complete, click "Finish" to return to the upload page

## Troubleshooting

- **Connection Issues**: Ensure you have VPN access if required to connect to the Oracle CRM website
- **File Format Errors**: Make sure your Excel/CSV file has the required columns
- **WebSocket Connection Failures**: Check if your network allows WebSocket connections

## License

See the main project license file for details.