## PDF EXTRACTOR


A lightweight Flask-based web tool for extracting, analyzing, and structuring data from PDF files.
The app handles everything from uploading PDFs to parsing text, tables, annotations, and generating categorized Excel outputs for piping and instrumentation diagrams (P&IDs).

### Features

- Upload and process multiple PDFs directly from a browser
- Extract text, tables, and annotations using **pdfplumber** and **PyPDF2**
- Detect and classify P&ID components using pattern-based recognition
- Generate Excel reports with structured sheets for:
    - P&ID components
    - Equipment and line details
    - Metadata, coordinates, and annotation logs
- Real-time upload and processing progress with a simple web interface

## Tech Stack

### Frontend
- HTML, CSS, JavaScript
- AJAX for upload and status polling

### Backend
- Python (Flask)
- pdfplumber, PyPDF2, pandas, re, json
- Runs on Vercel-compatible filesystem (`/tmp` for uploads and outputs)

## Directory Overview
```
pdf-extractor/
│
├── app.py                         # Main Flask app entry point
├── pdf_data_extractor.py          # Core PDF parsing and data extraction
├── create_pid_structure.py        # Post-processing and Excel structuring
│
├── templates/
│   └── index.html                 # Upload UI and client logic
│
├── static/
│   └── js/
│       └── main.js                # Handles uploads, progress, and polling
│
└── requirements.txt               # Dependencies list
```

## Installation

1. Clone the repository
```
git clone https://github.com/yourusername/pdf-extractor.git
cd pdf-extractor
```

2. Create and activate a virtual environment
```
python -m venv venv
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate       # Windows
```

3. Install dependencies
```
pip install -r requirements.txt
```

4. Run the Flask app
```
flask run
```

The app will start on http://localhost:5000

### Usage
1. Open the web interface in your browser.
2. Select one or more PDF files and click **Upload and Process**.
3. Watch the upload and processing progress in real time.
4. When processing finishes, download the structured Excel files.

Each output Excel includes:

- **PID_Components**: categorized P&ID data
- **Component_Details**: equipment and line specs
- **All_Annotations**: extracted annotations
- Metadata, Tables, Text_Content: extracted document data

## API Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/` | GET | Render upload page |
| `/upload` | POST | Accept PDF files and start extraction |
| `/status/<task_id>` | GET | Check progress and completion status |
| `/download/<filename>` | GET | Download the final Excel file |
### Deployment Notes

- The project is configured for **Vercel**.
- Temporary file storage is managed in `/tmp/uploads` and `/tmp/outputs`.
- All processed PDFs are deleted after extraction to save space.

### Example Output

When processing a piping diagram, the extractor generates:

- Structured component tables (CV, PT, TT, PSV, etc.)
- Categorized lines, instruments, and annotations
- Detailed Excel report linking each tag to its drawing

### License

This project is open-source under the MIT License.
Feel free to use, modify, and extend it for your own PDF data processing workflows.