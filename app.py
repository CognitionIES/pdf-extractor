import os
import uuid
from flask import Flask, render_template, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

# Import your modules
from pdf_data_extractor import extract_pdf_data, analyze_piping_data, save_results
from create_pid_structure import (
    load_extracted_data, create_pid_scrape_format,
    create_detailed_components_sheet, save_to_excel
)

app = Flask(__name__)

# Vercel uses /tmp for writable storage
app.config['UPLOAD_FOLDER'] = '/tmp/uploads/'
app.config['OUTPUT_FOLDER'] = '/tmp/outputs/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Create folders on every cold start
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# In-memory task tracking (per invocation)
tasks = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files'}), 400

    files = request.files.getlist('files')
    task_id = str(uuid.uuid4())
    tasks[task_id] = {'total': len(files), 'processed': 0, 'downloads': []}

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_path)

            # --- Extraction Pipeline ---
            results = extract_pdf_data(pdf_path)
            piping_analysis = analyze_piping_data(results)
            save_results(results, piping_analysis, app.config['OUTPUT_FOLDER'])

            piping_data, _ = load_extracted_data(app.config['OUTPUT_FOLDER'])
            pid_df = create_pid_scrape_format(piping_data, None)
            detailed_df = create_detailed_components_sheet(piping_data, None)

            excel_name = f"PID_Extract_Structured_Data_{filename}.xlsx"
            output_excel = os.path.join(app.config['OUTPUT_FOLDER'], excel_name)
            save_to_excel(pid_df, detailed_df, piping_data, output_excel)

            tasks[task_id]['downloads'].append(f"/download/{excel_name}")
            tasks[task_id]['processed'] += 1

            os.remove(pdf_path)  # Clean up

    return jsonify({'task_id': task_id})

@app.route('/status/<task_id>')
def get_status(task_id):
    task = tasks.get(task_id, {})
    return jsonify({
        'total': task.get('total', 0),
        'processed': task.get('processed', 0),
        'downloads': task.get('downloads', []),
        'done': task.get('processed', 0) == task.get('total', 0)
    })

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# Vercel looks for `app` variable
app = app