import pdfplumber
import PyPDF2
import pandas as pd
import re
import json
from pathlib import Path

def convert_to_serializable(obj):
    """Convert PyPDF2 objects to JSON-serializable types"""
    if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        if isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        else:
            return list(obj)
    elif hasattr(obj, 'get_object'):
        return convert_to_serializable(obj.get_object())
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        # Convert any other type to string (includes FloatObject, etc.)
        return str(obj)

def extract_pdf_data(pdf_path):
    results = {
        'text_content': [],
        'tables': [],
        'metadata': {},
        'annotations': [],
        'coordinates_data': []
    }
    
    print(f"Processing PDF: {pdf_path}")
    
    # Method 1: Using pdfplumber for comprehensive extraction
    try:
        with pdfplumber.open(pdf_path) as pdf:
            results['metadata']['total_pages'] = len(pdf.pages)
            print(f"Total pages: {len(pdf.pages)}")
            
            for i, page in enumerate(pdf.pages):
                print(f"Processing page {i+1}...")
                
                # Extract text
                text = page.extract_text()
                if text:
                    results['text_content'].append({
                        'page': i+1,
                        'text': text
                    })
                
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    for j, table in enumerate(tables):
                        results['tables'].append({
                            'page': i+1,
                            'table_number': j+1,
                            'data': table
                        })
                
                # Extract text with coordinates (useful for piping diagrams)
                chars = page.chars
                if chars:
                    page_coords = []
                    for char in chars:
                        page_coords.append({
                            'text': char['text'],
                            'x0': float(char['x0']),
                            'y0': float(char['y0']),
                            'x1': float(char['x1']),
                            'y1': float(char['y1']),
                            'size': float(char['size'])
                        })
                    results['coordinates_data'].append({
                        'page': i+1,
                        'characters': page_coords
                    })
                
                # Extract lines (important for piping diagrams)
                lines = page.lines
                if lines:
                    page_lines = []
                    for line in lines:
                        page_lines.append({
                            'x0': float(line['x0']),
                            'y0': float(line['y0']),
                            'x1': float(line['x1']),
                            'y1': float(line['y1']),
                            'width': float(line.get('width', 0))
                        })
                    if 'lines' not in results:
                        results['lines'] = []
                    results['lines'].append({
                        'page': i+1,
                        'lines': page_lines
                    })
                
                # Extract rectangles and curves (for symbols and components)
                rects = page.rects
                if rects:
                    page_rects = []
                    for rect in rects:
                        page_rects.append({
                            'x0': float(rect['x0']),
                            'y0': float(rect['y0']),
                            'x1': float(rect['x1']),
                            'y1': float(rect['y1']),
                            'width': float(rect.get('width', 0)),
                            'height': float(rect.get('height', 0))
                        })
                    if 'rectangles' not in results:
                        results['rectangles'] = []
                    results['rectangles'].append({
                        'page': i+1,
                        'rectangles': page_rects
                    })
                
    except Exception as e:
        print(f"Error with pdfplumber: {e}")
    
    # Method 2: Using PyPDF2 for annotations and metadata
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Get metadata
            if pdf_reader.metadata:
                results['metadata'].update({
                    'title': str(pdf_reader.metadata.get('/Title', '')),
                    'author': str(pdf_reader.metadata.get('/Author', '')),
                    'subject': str(pdf_reader.metadata.get('/Subject', '')),
                    'creator': str(pdf_reader.metadata.get('/Creator', '')),
                    'producer': str(pdf_reader.metadata.get('/Producer', '')),
                    'creation_date': str(pdf_reader.metadata.get('/CreationDate', '')),
                    'modification_date': str(pdf_reader.metadata.get('/ModDate', ''))
                })
            
            # Extract annotations
            for i, page in enumerate(pdf_reader.pages):
                if '/Annots' in page:
                    for annot in page['/Annots']:
                        try:
                            annotation = annot.get_object()
                            if annotation:
                                # Convert rect to list of floats
                                rect = annotation.get('/Rect', [])
                                rect_list = [float(x) for x in rect] if rect else []
                                
                                results['annotations'].append({
                                    'page': i+1,
                                    'type': str(annotation.get('/Subtype', '')),
                                    'content': str(annotation.get('/Contents', '')),
                                    'rect': rect_list,
                                    'name': str(annotation.get('/NM', ''))
                                })
                        except Exception as e:
                            print(f"Error extracting annotation on page {i+1}: {e}")
                            continue
                
    except Exception as e:
        print(f"Error with PyPDF2: {e}")
    
    return results

def analyze_piping_data(results):
    piping_analysis = {
        'pipe_numbers': [],
        'dimensions': [],
        'annotations_text': [],
        'coordinate_patterns': [],
        'potential_components': []
    }
    
    # Extract pipe numbers and dimensions from text
    for page_text in results['text_content']:
        text = page_text['text']
        
        # Look for pipe numbers (common patterns)
        pipe_patterns = [
            r'\b\d+"?\s*[xX×]\s*\d+"?\b',  # Pipe dimensions like 6" x 4"
            r'\bPipe\s*\d+\b',  # Pipe numbers
            r'\bP-\d+\b',  # P- prefix pipe numbers
            r'\b\d+"\s*Ø\b',  # Diameter notations
            r'\bDN\s*\d+\b',  # DN (Diameter Nominal)
            r'\bNPS\s*\d+\b'   # NPS (Nominal Pipe Size)
        ]
        
        for pattern in pipe_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                piping_analysis['dimensions'].extend(matches)
    
    # Extract annotation text (often contains component labels)
    for annot in results['annotations']:
        if annot['content']:
            content = annot['content'].replace('\\ufeff', '').replace('feff', '')
            if content and content not in piping_analysis['annotations_text']:
                piping_analysis['annotations_text'].append(content)
    
    # Analyze coordinate patterns for systematic layout
    if results['coordinates_data']:
        for page_coords in results['coordinates_data']:
            chars = page_coords['characters']
            # Group characters by y-coordinate (horizontal lines)
            y_groups = {}
            for char in chars:
                y = round(char['y0'])
                if y not in y_groups:
                    y_groups[y] = []
                y_groups[y].append(char)
            
            # Look for repeated patterns
            for y, chars_at_y in y_groups.items():
                if len(chars_at_y) > 5:  # Significant grouping
                    text_line = ''.join([c['text'] for c in sorted(chars_at_y, key=lambda x: x['x0'])])
                    if text_line.strip():
                        piping_analysis['coordinate_patterns'].append({
                            'y_coordinate': y,
                            'text': text_line.strip(),
                            'page': page_coords['page']
                        })
    
    return piping_analysis

def save_results(results, piping_analysis, output_dir):
    output_path = Path(output_dir)
    
    # Convert results to JSON-serializable format
    serializable_results = convert_to_serializable(results)
    serializable_analysis = convert_to_serializable(piping_analysis)
    
    # Save raw results as JSON
    with open(output_path / 'pdf_extraction_results.json', 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, indent=2, ensure_ascii=False)
    
    # Save piping analysis as JSON
    with open(output_path / 'piping_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(serializable_analysis, f, indent=2, ensure_ascii=False)
    
    # Create Excel file with different sheets
    with pd.ExcelWriter(output_path / 'piping_data_extracted.xlsx', engine='openpyxl') as writer:
        
        # Metadata sheet
        if results['metadata']:
            metadata_df = pd.DataFrame([results['metadata']])
            metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Text content sheet
        if results['text_content']:
            text_df = pd.DataFrame(results['text_content'])
            text_df.to_excel(writer, sheet_name='Text_Content', index=False)
        
        # Tables sheet
        if results['tables']:
            tables_data = []
            for table_info in results['tables']:
                page = table_info['page']
                table_num = table_info['table_number']
                table_data = table_info['data']
                
                for row_idx, row in enumerate(table_data):
                    for col_idx, cell in enumerate(row):
                        tables_data.append({
                            'Page': page,
                            'Table': table_num,
                            'Row': row_idx,
                            'Column': col_idx,
                            'Value': cell
                        })
            
            if tables_data:
                tables_df = pd.DataFrame(tables_data)
                tables_df.to_excel(writer, sheet_name='Tables', index=False)
        
        # Annotations sheet
        if results['annotations']:
            annotations_df = pd.DataFrame(results['annotations'])
            annotations_df.to_excel(writer, sheet_name='Annotations', index=False)
        
        # Piping analysis sheets
        if piping_analysis['dimensions']:
            dimensions_df = pd.DataFrame({'Dimensions': piping_analysis['dimensions']})
            dimensions_df.to_excel(writer, sheet_name='Pipe_Dimensions', index=False)
        
        if piping_analysis['annotations_text']:
            annot_text_df = pd.DataFrame({'Annotation_Text': piping_analysis['annotations_text']})
            annot_text_df.to_excel(writer, sheet_name='Component_Labels', index=False)
        
        if piping_analysis['coordinate_patterns']:
            coord_df = pd.DataFrame(piping_analysis['coordinate_patterns'])
            coord_df.to_excel(writer, sheet_name='Coordinate_Patterns', index=False)
    
    print(f"Results saved to {output_path}")