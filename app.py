import os
import uuid
import traceback
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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files')
        
        if not files or files[0].filename == '':
            return jsonify({'error': 'No files selected'}), 400

        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            'total': len(files), 
            'processed': 0, 
            'downloads': [],
            'errors': []
        }

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                try:
                    # Save uploaded file
                    file.save(pdf_path)
                    
                    print(f"Processing: {filename}")
                    
                    # --- Extraction Pipeline ---
                    results = extract_pdf_data(pdf_path)
                    piping_analysis = analyze_piping_data(results)
                    save_results(results, piping_analysis, app.config['OUTPUT_FOLDER'])

                    piping_data, raw_data = load_extracted_data(app.config['OUTPUT_FOLDER'])
                    pid_df = create_pid_scrape_format(piping_data, raw_data)
                    detailed_df = create_detailed_components_sheet(piping_data, raw_data)

                    excel_name = f"PID_Extract_{filename.replace('.pdf', '')}.xlsx"
                    output_excel = os.path.join(app.config['OUTPUT_FOLDER'], excel_name)
                    save_to_excel(pid_df, detailed_df, piping_data, output_excel)

                    tasks[task_id]['downloads'].append(f"/download/{excel_name}")
                    tasks[task_id]['processed'] += 1
                    
                    print(f"Success: {filename}")

                except Exception as e:
                    error_msg = f"Error processing {filename}: {str(e)}"
                    print(error_msg)
                    print(traceback.format_exc())
                    tasks[task_id]['errors'].append(error_msg)
                    tasks[task_id]['processed'] += 1  # Still count as processed
                
                finally:
                    # Clean up uploaded file
                    if os.path.exists(pdf_path):
                        try:
                            os.remove(pdf_path)
                        except:
                            pass

        return jsonify({'task_id': task_id})

    except Exception as e:
        error_msg = f"Upload error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return jsonify({'error': error_msg}), 500

@app.route('/status/<task_id>')
def get_status(task_id):
    task = tasks.get(task_id, {})
    return jsonify({
        'total': task.get('total', 0),
        'processed': task.get('processed', 0),
        'downloads': task.get('downloads', []),
        'errors': task.get('errors', []),
        'done': task.get('processed', 0) == task.get('total', 0)
    })

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(
            app.config['OUTPUT_FOLDER'], 
            filename, 
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'details': str(error)}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

# Vercel looks for `app` variable
if __name__ == '__main__':
    app.run(debug=True)