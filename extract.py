#!/usr/bin/env python3
"""
Script to extract statistical data from PDF instructor evaluation files.
Automatically converts PDF to XML using pdftotext and extracts mean, standard deviation, 
count, and rating values from instructor evaluation data.
"""

import xml.etree.ElementTree as ET
import re
import subprocess
import tempfile
import os
import sys
import argparse
from typing import Dict, List, Optional, Tuple
import json
#PDFTOTEXT = os.path.join(os.path.dirname(__file__), "bin/pdftotext.exe")
LINE_TITLE = '15 Taking everything into account, the instructor was:'
LINE_COLS = 'Field Mean Std Deviation Count'

def extract_paren(s):
    return s[1:-1]

def extract_page(page):
    words = []
    for word in page.findall('.//*'):
        words.append({
            'text': word.text,
            'x': float(word.get('xMin', 0)),
            'y': float(word.get('yMin', 0))
        })

    # Sort words by position (top to bottom, left to right)
    words.sort(key=lambda w: (w['y'], w['x']))

    table = []
    line = []
    if len(words) == 0:
        return []
    last_y = words[0]["y"]
    for word in words:
        if last_y != word["y"]:
            table.append(" ".join(line))
            last_y = word["y"]
            line = []
        line.append(word["text"])
    table.append(" ".join(line))

    if len(table) > 0 and table[0] == 'There are no results yet to show. Please distribute your survey to gather responses.':
        del table[0]
    return table

def extract_frontpage(table) -> Optional[Dict]:
    if len(table) < 2:
        return
    line = table[1]
    # 2020 Spring Evals - CS4XX-01 Instructor Name
    before = None
    after = None
    for name in ["Eval", "Evals", "Evaluation"]:
        if name + " -" in line:
            before, after = line.split(name + " -")
            break
    if before is None and "CS" in line:
        before, after = line.split("CS", 1)
    if before is None:
        print(line, file=sys.stderr)
        return
    year, semester = before.strip().split(" ", 1)
    if ")" in after:
        course, instructor = after.split(")")
        course += ")"
        instructor = instructor.strip()
    else:
        #  CS4XX-01 Instructor Name
        course, instructor = after.strip().split(" ", 1)
    return {"course": course, "instructor": instructor, "year": year, "semester": semester}

def extract_data_from_page(table) -> Optional[Dict]:
    """
    Extract mean, std deviation, count, and rating counts from a page.

    Args:
        page: XML page element

    Returns:
        Dictionary with extracted data
    """
    if len(table) == 0:
        return
    if table[0] != LINE_TITLE or table[1] != LINE_COLS:
        return
    table = table[2:]
    # skip the offset of line2
    line1 = table[0][len(LINE_TITLE) + 2:].split(' ')[-3:]
    #print(line1)
    mean, stdev, count = line1
    # Last line: ['Poor', '(1)', 'Below', 'Average', '(2)', 'Average', '(7)', 'Good', '(7)', 'Excellent', '(10)']
    _, poor, _, _, below_average, _, average, _, good, _, excellent = table[-1].split(' ')
    return {
        "mean": mean,
        "std_deviation": stdev,
        "count": count,
        "poor": extract_paren(poor),
        "below_average": extract_paren(below_average),
        "average": extract_paren(average),
        "good": extract_paren(good),
        "excellent": extract_paren(excellent)
    }

def parse_pdf_xml(xml_content: str) -> Dict:
    """
    Parse the XML content from pdftotext and extract instructor evaluation data.

    Args:
        xml_content: XML string from pdftotext -htmlmeta -bbox

    Returns:
        Dictionary containing extracted data or None if not found
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None

    # Debug: Print the root element and first few child elements
    #print(f"XML root element: {root.tag}")
    
    # Handle XHTML namespace
    namespace = {'xhtml': 'http://www.w3.org/1999/xhtml'} if 'xhtml' in root.tag else {}
    
    # Try different element paths based on namespace
    if namespace:
        doc_elements = root.findall('.//xhtml:doc', namespace)
        page_elements = root.findall('.//xhtml:page', namespace)
    else:
        doc_elements = root.findall('.//doc')
        page_elements = root.findall('.//page')

    # Find pages containing the target question
    target_pages = []
    # Look for page elements regardless of namespace
    pages_to_search = page_elements
    if not pages_to_search:
        # If no page elements found, try searching all elements that might contain words
        pages_to_search = root.findall('.//*')
        print(f"No page elements found, searching all {len(pages_to_search)} elements")
    frontpage = None
    for idx, page in enumerate(pages_to_search):
        # Try to find word elements with and without namespace
        table = extract_page(page)
        if idx == 0:
            frontpage = extract_frontpage(table)
        else:
            res = extract_data_from_page(table)
            if res is not None:
                frontpage.update(res)
                return frontpage
    return None


def pdf_to_xml(pdf_path: str) -> Optional[str]:
    """
    Convert PDF to XML using pdftotext with -htmlmeta -bbox flags.
    
    Args:
        pdf_path: Path to the input PDF file
        
    Returns:
        XML content as string, or None if conversion failed
    """
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        return None
    
    # Create temporary file for XML output
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.xml', delete=False) as temp_file:
        temp_xml_path = temp_file.name
    
    try:
        # Run pdftotext command
        cmd = ['pdftotext', '-htmlmeta', '-bbox', pdf_path, temp_xml_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Read the generated XML file
        with open(temp_xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
            
        return xml_content
        
    except subprocess.CalledProcessError as e:
        print(f"Error running pdftotext: {e}")
        print(f"stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        print("Error: pdftotext command not found. Please install poppler-utils.")
        print("On Ubuntu/Debian: sudo apt install poppler-utils")
        print("On macOS: brew install poppler")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
    finally:
        # Clean up temporary file
        if os.path.exists(temp_xml_path):
            os.unlink(temp_xml_path)

def process_pdf_file(pdf_path: str) -> Optional[Dict]:
    """
    Process a PDF file end-to-end: convert to XML and extract data.
    
    Args:
        pdf_path: Path to the input PDF file
        
    Returns:
        Dictionary containing extracted data or None if processing failed
    """
    # Convert PDF to XML
    xml_content = pdf_to_xml(pdf_path)
    if not xml_content:
        return None
    
    # Extract data from XML
    data = parse_pdf_xml(xml_content)
    return data

def main():
    """Main function with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Extract instructor evaluation data from PDF files"
    )
    parser.add_argument(
        'pdf_file', 
        nargs='*',
        help='Path to the PDF file to process'
    )
    
    args = parser.parse_args()

    if False:
        # Process existing XML file
        try:
            with open(args.xml_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            data = parse_pdf_xml(xml_content)
        except FileNotFoundError:
            print(f"Error: XML file '{args.xml_file}' not found.", file=sys.stderr)
            return
    # Process PDF file
    output = []
    try:
        for f in args.pdf_file:
            result = process_pdf_file(f)
            if result is not None:
                output.append(result)
            else:
                print(f, file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        print(json.dumps(output))


if __name__ == "__main__":
    main()
