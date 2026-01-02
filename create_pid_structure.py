import pandas as pd
import json
import re
from pathlib import Path

def load_extracted_data(output_dir):
    """Load the previously extracted data"""
    with open(Path(output_dir) / 'piping_analysis.json', 'r', encoding='utf-8') as f:
        piping_data = json.load(f)
    with open(Path(output_dir) / 'pdf_extraction_results.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    return piping_data, raw_data

def extract_drawing_name(raw_data):
    """Extract drawing name from PDF text content"""
    drawing_name = "Unknown Drawing"
    
    # Try to find drawing number and title from text content
    for page_text in raw_data.get('text_content', []):
        text = page_text.get('text', '')
        
        # Look for common P&ID drawing number patterns
        # Pattern: XXX-XX-XXX-XXX followed by description
        pattern = r'(\d{2,3}-[A-Z]{2}-\d{3}-\d{3})\s*[-:]?\s*([A-Z\s&,\-]+(?:UNIT|SYSTEM|FURNACE|PUMP|VESSEL|TOWER|REACTOR)[A-Z\s&,\-]*)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            drawing_num = match.group(1)
            drawing_desc = match.group(2).strip()
            drawing_name = f"{drawing_num} - {drawing_desc}"
            break
    
    return drawing_name

def categorize_components(annotations_text):
    """Categorize extracted components into PID categories"""

    categories = {
        'Drawing_Name': [],
        'CV #': [],
        'Equipment #': [],
        'Flow Element #': [],
        'Flow Indicator #': [],
        'Flow Transmitter #': [],
        'High Switch #': [],
        'IPF #': [],
        'Injection Point #': [],
        'Level Gauge #': [],
        'Level Transmitter #': [],
        'Line #': [],
        'Orfice #': [],
        'PID #': [],
        'Pressure Gauge #': [],
        'Pressure Transmitter #': [],
        'PSV #': [],
        'SP #': [],
        'Temperature Element #': [],
        'Temperature Transmitter #': [],
        'Thermal Weld #': []
    }

    # --- Extended pattern definitions ---
    patterns = {
        'Equipment #': [
            r'\b(P|M|E|F|V|C|H|T|R)-\d{3,6}\b',                    # Basic equipment tags
            r'\b[PMEFVCHTR]-\d{3,6}(?:-[A-Z0-9]+)?\b',              # With suffixes
        ],
        'PID #': [r'\b\d{2,3}-[A-Z]{2}-\d{3}-\d{3}\b'],
        'Line #': [
            r'\b[A-Z]{1,3}-\d{3,6}(?:-\d+)?["]?[-~]?[A-Z0-9"\-\(\)]*\b',  # General line pattern
            r'\bP-\d{3,6}(?:-\d+)?["]?-?[A-Z0-9"~\-\(\)]*[A-Z]{1,3}\b',   # P- prefix lines
            r'\b(?:RO|MS|HS|CS|SS)-\d+["\-].*\b',                         # Special material lines
        ],
        'Flow Element #': [r'\bFE-\d+[A-Z]?\b', r'\d+-FE-\d+[A-Z]?\b'],
        'Flow Indicator #': [r'\bFI-\d+[A-Z]?\b', r'\d+-FI-\d+[A-Z]?\b'],
        'Flow Transmitter #': [r'\bFT-\d+[A-Z]?\b', r'\d+-FT-\d+[A-Z]?\b'],
        'Pressure Gauge #': [r'\b(?:PG|PI)-\d+[A-Z]?\b', r'\d+-(?:PG|PI)-\d+[A-Z]?\b'],
        'Pressure Transmitter #': [r'\bPT-\d+[A-Z]?\b', r'\d+-PT-\d+[A-Z]?\b'],
        'PSV #': [r'\b(?:PSV|PRV)-\d+[A-Z]?\b', r'\d+-(?:PSV|PRV)-\d+[A-Z]?\b'],
        'Temperature Element #': [r'\bTE-\d+[A-Z]?\b', r'\d+-TE-\d+[A-Z]?\b'],
        'Temperature Transmitter #': [r'\bTT-\d+[A-Z]?\b', r'\d+-TT-\d+[A-Z]?\b'],
        'Level Gauge #': [r'\b(?:LG|LI)-\d+[A-Z]?\b', r'\d+-(?:LG|LI)-\d+[A-Z]?\b'],
        'Level Transmitter #': [r'\bLT-\d+[A-Z]?\b', r'\d+-LT-\d+[A-Z]?\b'],
        'CV #': [r'\b(?:CV|HV|PV|FV)-\d+[A-Z]?\b', r'\d+-(?:CV|HV|PV|FV)-\d+[A-Z]?\b'],
        'High Switch #': [r'\bHS-\d+[A-Z]?\b', r'\d+-HS-\d+[A-Z]?\b'],
        'IPF #': [r'\bIPF-\d+[A-Z]?\b'],
        'Orfice #': [r'\b(?:FO|OR)-\d+[A-Z]?\b'],
    }

    # --- Categorization logic ---
    for text in annotations_text:
        if not text or not str(text).strip():
            continue

        text_str = str(text).strip()
        categorized = False

        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, text_str, re.IGNORECASE):
                    categories[category].append(text_str)
                    categorized = True
                    break
            if categorized:
                break

    # --- Cleanup unwanted text from Line # ---
    cleaned_lines = []
    skip_keywords = ['TO ', 'FROM ', 'HOT OIL', 'TRIM', 'AS-BUILT', 'UPDATE', 'FILTER', 'DWG', 'SHEET', 'REV']
    for line in categories['Line #']:
        upper_line = line.upper()
        if any(word in upper_line for word in skip_keywords):
            continue
        # Only keep if it looks like a proper line number
        if re.match(r'^[A-Z]{1,3}-\d+', line) or '"' in line:
            cleaned_lines.append(line)
    categories['Line #'] = list(set(cleaned_lines))  # Remove duplicates

    return categories

def extract_equipment_details(raw_data, piping_data):
    """Extract equipment specifications from PDF text"""
    equipment_details = []
    all_text = []
    
    # Combine all text from PDF
    for page_text in raw_data.get('text_content', []):
        all_text.append(page_text.get('text', ''))
    
    combined_text = ' '.join(all_text)
    
    # Find all equipment tags
    equipment_pattern = r'\b([PMEFVCHTR]-\d{3,6}[A-Z]?)\b'
    equipment_tags = re.findall(equipment_pattern, combined_text)
    equipment_tags = list(set(equipment_tags))  # Remove duplicates
    
    for tag in equipment_tags:
        detail = {'Component_ID': tag, 'Category': 'Equipment'}
        
        # Try to find specifications near the tag
        # Look for text within 200 characters after the tag
        tag_index = combined_text.find(tag)
        if tag_index != -1:
            context = combined_text[tag_index:tag_index + 300]
            
            # Extract common specs
            flow_match = re.search(r'(\d+[,\d]*)\s*(?:GPM|gpm|LPM)', context)
            if flow_match:
                detail['Flow'] = flow_match.group(0)
            
            pressure_match = re.search(r'(\d+)\s*(?:PSI|psi|bar|Bar)', context)
            if pressure_match:
                detail['Pressure'] = pressure_match.group(0)
            
            temp_match = re.search(r'(\d+)\s*(?:°F|F|°C|C)', context)
            if temp_match:
                detail['Temperature'] = temp_match.group(0)
            
            rpm_match = re.search(r'(\d+)\s*(?:RPM|rpm)', context)
            if rpm_match:
                detail['RPM'] = rpm_match.group(0)
        
        equipment_details.append(detail)
    
    return equipment_details

def extract_line_connections(raw_data, piping_data):
    """Extract line connections and descriptions from PDF"""
    line_connections = []
    all_text = []
    
    for page_text in raw_data.get('text_content', []):
        all_text.append(page_text.get('text', ''))
    
    combined_text = ' '.join(all_text)
    
    # Find PID numbers (line identifiers)
    pid_pattern = r'(\d{2,3}-[A-Z]{2}-\d{3}-\d{3})'
    pid_numbers = re.findall(pid_pattern, combined_text)
    pid_numbers = list(set(pid_numbers))
    
    for pid_num in pid_numbers:
        connection = {'Component_ID': pid_num, 'Category': 'Line'}
        
        # Try to find description after PID number
        pid_index = combined_text.find(pid_num)
        if pid_index != -1:
            context = combined_text[pid_index:pid_index + 200]
            
            # Look for TO/FROM patterns
            to_match = re.search(r'(?:TO|to)\s+([A-Z0-9\-\s]+?)(?:\n|$|TO|FROM)', context)
            from_match = re.search(r'(?:FROM|from)\s+([A-Z0-9\-\s]+?)(?:\n|$|TO|FROM)', context)
            
            desc_parts = []
            if from_match:
                desc_parts.append(f"FROM {from_match.group(1).strip()}")
            if to_match:
                desc_parts.append(f"TO {to_match.group(1).strip()}")
            
            if desc_parts:
                connection['Description'] = ' '.join(desc_parts)
            else:
                # Generic description
                connection['Description'] = 'Process Line'
        
        line_connections.append(connection)
    
    return line_connections

def create_pid_scrape_format(piping_data, raw_data):
    """Create structured data in the same format as PID scrape reference"""
    
    # Extract drawing name from actual PDF content
    drawing_name = extract_drawing_name(raw_data)
    
    # Get all annotations
    all_annotations = piping_data.get('annotations_text', [])
    
    # Categorize components
    categories = categorize_components(all_annotations)
    
    rows = []
    max_items = max(len(items) for items in categories.values()) if categories else 1

    for i in range(max_items):
        row = {'Drawing_Name': drawing_name if i == 0 else ''}
        for category in categories.keys():
            if category == 'Drawing_Name':
                continue
            items = categories[category]
            row[category] = items[i] if i < len(items) else '<does not exist>'
        rows.append(row)

    df = pd.DataFrame(rows)

    # Column order to match PID scrape file
    column_order = [
        'Drawing_Name', 'CV #', 'Equipment #', 'Flow Element #', 'Flow Indicator #',
        'Flow Transmitter #', 'High Switch #', 'IPF #', 'Injection Point #',
        'Level Gauge #', 'Level Transmitter #', 'Line #', 'Orfice #', 'PID #',
        'Pressure Gauge #', 'Pressure Transmitter #', 'PSV #', 'SP #',
        'Temperature Element #', 'Temperature Transmitter #', 'Thermal Weld #'
    ]

    for col in column_order:
        if col not in df.columns:
            df[col] = '<does not exist>'

    return df[column_order]

def create_detailed_components_sheet(piping_data, raw_data):
    """Detailed component sheet with specifications - REAL DATA"""
    detailed_data = []
    
    # Extract equipment details from actual PDF
    equipment_details = extract_equipment_details(raw_data, piping_data)
    detailed_data.extend(equipment_details)
    
    # Extract line connections from actual PDF
    line_connections = extract_line_connections(raw_data, piping_data)
    detailed_data.extend(line_connections)
    
    # If no data was extracted, add a note
    if not detailed_data:
        detailed_data.append({
            'Component_ID': 'N/A',
            'Category': 'Note',
            'Description': 'No detailed specifications found in PDF'
        })
    
    return pd.DataFrame(detailed_data)

def save_to_excel(pid_df, detailed_df, piping_data, output_file):
    output_path = Path(output_file)
    if output_path.exists():
        output_path.unlink()  # Overwrite if exists

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: PID Components (categorized)
        pid_df.to_excel(writer, sheet_name='PID_Components', index=False)
        
        # Sheet 2: Component Details (specifications)
        detailed_df.to_excel(writer, sheet_name='Component_Details', index=False)
        
        # Sheet 3: All Annotations (raw data for reference)
        annotations_df = pd.DataFrame({'Annotation': piping_data['annotations_text']})
        annotations_df.to_excel(writer, sheet_name='All_Annotations', index=False)
        
    print(f"Excel file saved: {output_file}")