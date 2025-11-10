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
            r'\b(P|M|E|F|V|C|H)-\d{3,6}\b',                    # Basic equipment tags
            r'\bP-\d{3,6}(?:-\d+)?(?:[A-Z0-9"~\-]+)?\b',        # Composite pipe/equipment tags
            r'\bM-\d+\b', r'\bE-\d+\b', r'\bV-\d+\b', r'\bC-\d+\b', r'\bH-\d+\b'
        ],
        'PID #': [r'\b\d{2,3}-DA-\d{3}-\d{3}\b'],
        'Line #': [
            r'\bP-\d{3,6}(?:-\d+)?["]?-?[A-Z0-9"~\-\(\)]*[A-Z]{1,3}\b',  # P-6682-4"-CDH5-Ih style
            r'\bRO-\d+.*["-].*\b', r'\bMS-\d+.*["-].*\b', r'\bHS-\d+.*["-].*\b'
        ],
        'Flow Element #': [r'\bFE-\d+\b', r'\d+-FE-\d+'],
        'Flow Indicator #': [r'\bFI-\d+\b', r'\d+-FI-\d+'],
        'Flow Transmitter #': [r'\bFT-\d+\b', r'\d+-FT-\d+'],
        'Pressure Gauge #': [r'\bPG-\d+\b', r'\bPI-\d+\b', r'\d+-PG-\d+', r'\d+-PI-\d+'],
        'Pressure Transmitter #': [r'\bPT-\d+\b', r'\d+-PT-\d+'],
        'PSV #': [r'\bPSV-\d+\b', r'\bPRV-\d+\b', r'\d+-PSV-\d+'],
        'Temperature Element #': [r'\bTE-\d+\b', r'\d+-TE-\d+'],
        'Temperature Transmitter #': [r'\bTT-\d+\b', r'\d+-TT-\d+'],
        'Level Gauge #': [r'\bLG-\d+\b', r'\bLI-\d+\b', r'\d+-LG-\d+'],
        'Level Transmitter #': [r'\bLT-\d+\b', r'\d+-LT-\d+'],
        'CV #': [r'\bCV-\d+\b', r'\bHV-\d+\b', r'\bPV-\d+\b', r'\d+-CV-\d+'],
        'High Switch #': [r'\bHS-\d+\b', r'\d+-HS-\d+'],
        'IPF #': [r'\bIPF-\d+\b']
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

        # If still uncategorized
        if not categorized:
            if 'DELAYED COKER' in text_str.upper() or 'FURNACE' in text_str.upper():
                categories['Drawing_Name'].append(text_str)
            elif re.match(r'\d{3}-DA-\d{3}-\d{3}', text_str):
                categories['PID #'].append(text_str)

    # --- Cleanup unwanted text from Line # ---
    cleaned_lines = []
    skip_keywords = ['TO ', 'FROM ', 'HOT OIL', 'TRIM', 'AS-BUILT', 'UPDATE', 'FILTER', 'DWG']
    for line in categories['Line #']:
        upper_line = line.upper()
        if any(word in upper_line for word in skip_keywords):
            continue
        if re.match(r'^(P|RO|MS|HS)-\d+', line) or '"' in line:
            cleaned_lines.append(line)
    categories['Line #'] = cleaned_lines

    return categories

def create_pid_scrape_format(piping_data, raw_data):
    """Create structured data in the same format as PID scrape reference"""
    drawing_name = "102-DA-111-001 - DELAYED COKER UNIT FURNACE CHARGE PUMPS"
    all_annotations = piping_data.get('annotations_text', [])
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
    """Detailed component sheet with specifications"""
    detailed_data = []

    equipment_specs = {
        'P-10226': {'Type': 'Hot Oil Charge Pump', 'Flow': '1,481 GPM', 'Pressure': '503 PSI', 'Motor': 'M-6366'},
        'P-10227': {'Type': 'Hot Oil Charge Pump', 'Flow': '1,481 GPM', 'Pressure': '503 PSI', 'Motor': 'M-6366'},
        'M-6366': {'Type': 'Motor', 'RPM': '1800', 'Design_Pressure': '900 PSI', 'Temperature': '455°F'}
    }

    for equip, specs in equipment_specs.items():
        row = {'Component_ID': equip, 'Category': 'Equipment'}
        row.update(specs)
        detailed_data.append(row)

    line_connections = [
        {'Component_ID': '102-DA-111-002', 'Category': 'Line', 'Description': 'HOT OIL TO F-78 PASS 1'},
        {'Component_ID': '102-DA-111-003', 'Category': 'Line', 'Description': 'HOT OIL TO F-78 PASS 2'},
        {'Component_ID': '102-DA-111-004', 'Category': 'Line', 'Description': 'HOT OIL TO F-78 PASS 3'},
        {'Component_ID': '102-DA-112-002', 'Category': 'Line', 'Description': 'CHARGE TO F-79 PASS 1'},
        {'Component_ID': '102-DA-112-003', 'Category': 'Line', 'Description': 'CHARGE TO F-79 PASS 2'},
        {'Component_ID': '102-DA-112-004', 'Category': 'Line', 'Description': 'CHARGE TO F-79 PASS 3'},
    ]
    detailed_data.extend(line_connections)

    return pd.DataFrame(detailed_data)

def save_to_excel(pid_df, detailed_df, piping_data, output_file):
    output_path = Path(output_file)
    if output_path.exists():
        output_path.unlink()  # Overwrite if exists

    with pd.ExcelWriter(output_path) as writer:
        pid_df.to_excel(writer, sheet_name='PID_Components', index=False)
        detailed_df.to_excel(writer, sheet_name='Component_Details', index=False)
        annotations_df = pd.DataFrame({'Annotation': piping_data['annotations_text']})
        annotations_df.to_excel(writer, sheet_name='All_Annotations', index=False)