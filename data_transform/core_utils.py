import re
import unicodedata
import fitz
import os
import io
import csv
import logging

import pandas as pd

from .pdf_typs import pdf_types
from typing import Dict, Optional, List

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def save_text_to_csv(output_directory, extracted_text, filename='output.csv'):
    """
    Save extracted text data to a CSV file.

    Args:
        output_directory (str): Directory to save the CSV file
        extracted_text (dict): Dictionary containing extracted data
        filename (str, optional): Name of the CSV file. Defaults to 'output.csv'.

    Raises:
        ValueError: If extracted_text is empty or invalid
        OSError: If there's an issue with file operations
        Exception: For any other unexpected errors
    """
    try:
        # Validate input data
        if not extracted_text or not isinstance(extracted_text, dict) or 0 not in extracted_text:
            raise ValueError("Invalid or empty extracted text data")

        # Ensure the output directory exists, create it if not
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            logger.info(f"Created directory: {output_directory}")

        csv_path = os.path.join(output_directory, filename)

        # Extract the data from extracted_text[0]
        extracted_data = extracted_text[0]

        if not extracted_data or not isinstance(extracted_data, dict):
            raise ValueError("Invalid data format in extracted text")

        # Check if CSV exists; if not, create it with headers
        file_exists = os.path.exists(csv_path)

        with open(csv_path, mode='a', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=extracted_data.keys())

            # If file doesn't exist, write the headers
            if not file_exists:
                writer.writeheader()

            # Write the extracted data (as a row in the CSV)
            writer.writerow(extracted_data)

        logger.info(f"Appended extracted data to {csv_path}")

    except ValueError as e:
        logger.error(f"Data validation error in save_text_to_csv: {e}")
        raise
    except OSError as e:
        logger.error(f"File operation error in save_text_to_csv: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in save_text_to_csv: {e}")
        raise

def save_text_to_xlsx(output_directory, extracted_text, filename='output.xlsx'):
    """
    Save extracted text data to an Excel file.

    Args:
        output_directory (str): Directory to save the Excel file
        extracted_text (dict): Dictionary containing extracted data
        filename (str, optional): Name of the Excel file. Defaults to 'output.xlsx'.

    Raises:
        ValueError: If extracted_text is empty or invalid
        OSError: If there's an issue with file operations
        Exception: For any other unexpected errors
    """
    try:
        # Validate input data
        if not extracted_text or not isinstance(extracted_text, dict) or 0 not in extracted_text:
            raise ValueError("Invalid or empty extracted text data")

        # Ensure the output directory exists, create it if not
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            logger.info(f"Created directory: {output_directory}")

        excel_path = os.path.join(output_directory, filename)

        # Extract the data from extracted_text[0]
        extracted_data = extracted_text[0]

        if not extracted_data or not isinstance(extracted_data, dict):
            raise ValueError("Invalid data format in extracted text")

        # Check if Excel file exists; if it does, read existing data
        if os.path.exists(excel_path):
            try:
                # Read existing Excel file
                existing_df = pd.read_excel(excel_path)

                # Convert the new data to DataFrame
                new_df = pd.DataFrame([extracted_data])

                # Concatenate the existing data with new data
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)

            except Exception as e:
                logger.warning(f"Error reading existing Excel file, creating new one: {e}")
                # If there's an error reading the existing file, create a new DataFrame
                combined_df = pd.DataFrame([extracted_data])
        else:
            # Create new DataFrame with the extracted data
            combined_df = pd.DataFrame([extracted_data])

        # Save the DataFrame to Excel file
        combined_df.to_excel(excel_path, index=False, engine='openpyxl')

        logger.info(f"Appended extracted data to {excel_path}")

    except ValueError as e:
        logger.error(f"Data validation error in save_text_to_excel: {e}")
        raise
    except OSError as e:
        logger.error(f"File operation error in save_text_to_excel: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in save_text_to_excel: {e}")
        raise

def delete_pdf(pdf_path):
    """
    Delete a PDF file at the specified path.

    Args:
        pdf_path (str): Path to the PDF file to delete

    Raises:
        FileNotFoundError: If the file does not exist
        PermissionError: If there's a permission issue
        OSError: If there's another OS-related error
    """
    if not pdf_path or not isinstance(pdf_path, str):
        logger.warning("Invalid PDF path provided for deletion")
        return

    try:
        os.remove(pdf_path)
        logger.info(f"Deleted PDF file at {pdf_path}")
    except FileNotFoundError:
        logger.warning(f"File {pdf_path} not found, cannot delete.")
    except PermissionError as e:
        logger.error(f"Permission denied when trying to delete {pdf_path}: {e}")
        raise
    except OSError as e:
        logger.error(f"OS error occurred while trying to delete {pdf_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error occurred while trying to delete {pdf_path}: {e}")
        raise

def split_string(string):
    pattern = r"-"
    matches = re.finditer(pattern, string)
    last_index = len(string)
    for match in matches:
        last_index = match.start()
    return string[last_index:]

def extract_text_by_coordinates(pdf_path, page_num, rect):
    """
    Extracts text from a specified rectangular area on a PDF page.

    :param pdf_path: Path to the PDF file.
    :param page_num: Page number (starting from 0) to extract text from.
    :param rect: Tuple (left, top, right, bottom) representing the rectangular coordinates.
    :return: Extracted text from the specified area.
    """
    pdf_document = fitz.open(pdf_path)
    page = pdf_document[page_num]
    rect_region = fitz.Rect(*rect)
    text = page.get_text("text", clip=rect_region)
    pdf_document.close()
    return text

def is_arabic(text: str) -> bool:
    """
    Checks if the given text contains Arabic characters.

    Parameters
    ----------
    text : str
        The text to check.

    Returns
    -------
    bool
        True if the text contains Arabic characters, False otherwise.
    """
    for char in text:
        if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or '\u08A0' <= char <= '\u08FF' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF':
            return True
    return False

def handle_reverse_replace_newline(text):
    return text[::-1].replace('\n', '')

def handle_split_index(text, index):
    parts = text.split('\n')
    if len(parts) > index:
        return unicodedata.normalize('NFKC', parts[index])
    else:
        return None

def handle_replace_newline(text):
    return unicodedata.normalize('NFKC', text.replace('\n', ''))

def handle_reading_type(text):
    out_text = text.replace('\n', '')
    raTy = out_text.split("-")
    if len(raTy) > 1:
        return f"{raTy[0]} - {unicodedata.normalize('NFKC', raTy[1])}"
    else:
        raTy = out_text.split(" ")
        if len(raTy) > 1:
            return f"{raTy[0]} - {unicodedata.normalize('NFKC', raTy[1])}"
        else:
            return unicodedata.normalize('NFKC', out_text)

def extract_text_by_coordinates_new(page, coordinates):
    rect = fitz.Rect(coordinates)
    text = page.get_textbox(rect)
    return text

def determine_pdf_type(page):
    thabit_coordinates = (16.98, 198.00, 169.96, 306.00)
    nama_vat_coordinates = (57.11219787597656, 142.0579833984375, 133.68218994140625, 159.81597900390625)
    is_thabit = extract_text_by_coordinates_new(page, thabit_coordinates)
    is_nama_vat = extract_text_by_coordinates_new(page, nama_vat_coordinates)

    if "Thabit" in is_thabit:
        return 'new_nama'
    elif ('1100004061' in is_nama_vat) and ("Thabit" not in is_thabit):
        return 'old_nama'
    else:
        return 'dofar'

def extract_pdf_data(pdf_file):
    """
    Extract data from a PDF file based on predefined coordinates and field types.

    Args:
        pdf_file (str): Path to the PDF file

    Returns:
        dict: Dictionary containing extracted data from each page

    Raises:
        FileNotFoundError: If the PDF file does not exist
        ValueError: If the PDF file is invalid or corrupted
        KeyError: If required field definitions are missing
        Exception: For any other unexpected errors
    """
    if not pdf_file or not isinstance(pdf_file, str):
        logger.error("Invalid PDF file path provided")
        raise ValueError("Invalid PDF file path provided")

    if not os.path.exists(pdf_file):
        logger.error(f"PDF file not found: {pdf_file}")
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    try:
        doc = fitz.open(pdf_file)
    except Exception as e:
        logger.error(f"Error opening PDF file {pdf_file}: {e}")
        raise ValueError(f"Could not open PDF file: {str(e)}")

    try:
        data = {}
        num = 0
        for page_number in range(len(doc)):
            try:
                page = doc[page_number]
                pdf_type = determine_pdf_type(page)

                try:
                    fields = pdf_types[pdf_type]['fields']
                except KeyError as e:
                    data[num] = _dummy_data(num)
                    logger.error(f"PDF type '{pdf_type}' not defined in pdf_types or missing 'fields': {e}")
                    raise KeyError(f"PDF type configuration error: {str(e)}")

                page_data = {}
                for field_name, field_info in fields.items():
                    try:
                        coordinates = field_info['coordinates']
                        handler = field_info.get('handler', lambda x: x)

                        try:
                            extracted_text = extract_text_by_coordinates_new(page, coordinates)
                            value = handler(extracted_text)
                            page_data[field_name] = value
                        except Exception as e:
                            logger.error(f"Error processing field '{field_name}': {e}")
                            page_data[field_name] = None
                            # Don't replace the entire page data with dummy data for a single field error

                    except KeyError as e:
                        logger.error(f"Missing required field info for '{field_name}': {e}")
                        page_data[field_name] = None
                        data[num] = _dummy_data(num)

                data[num] = page_data
                num += 1
            except Exception as e:
                data[num] = _dummy_data(num)
                logger.error(f"Error processing page {page_number} in {pdf_file}: {e}")
                # Continue with next page instead of failing the whole process

        return data
    except Exception as e:
        logger.error(f"Unexpected error extracting data from PDF {pdf_file}: {e}")
        raise
    finally:
        try:
            if 'doc' in locals():
                doc.close()
        except Exception as e:
            logger.warning(f"Error closing PDF document: {e}")
            # Don't raise here as the main operation might have succeeded

def _dummy_data(acc):
    return {0: {
        "Customer": "null",
        "Customer_No": "null",
        "Account_No": f"{acc}",
        "Meter_No": "null",
        "Previous_Reading_Date": "null",
        "Previous_Reading": "null",
        "Current_Reading_Date": "null",
        "Current_Reading": "null",
        "Due_Date": "null",
        "Reading_Type": "null",
        "Tariff_Type": "null",
        "Invoice_Month": "null",
        "Government_Subsidy": "null",
        "Consumption_KWH_1": "null",
        "Rate_1": "null",
        "Consumption_KWH_2": "null",
        "Rate_2": "null",
        "Consumption_KWH_3": "null",
        "Rate_3": "null",
        "Consumption_KWH_4": "null",
        "Rate_4": "null",
        "Consumption_KWH_5": "null",
        "Rate_5": "null",
        "Consumption_KWH_6": "null",
        "Rate_6": "null",
        "Total_Before_VAT": "null",
        "VAT": "null",
        "Total_After_VAT": "null",
        "Total_Payable_Amount": "null"
    }}

def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

def generate_csv_from_docs(docs: List[Dict]) -> Optional[io.StringIO]:
    """
    Generate CSV data from a list of documents.
    """
    if not docs:
        return None
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=docs[0].keys(), quoting=csv.QUOTE_MINIMAL, escapechar='\\')
    writer.writeheader()
    writer.writerows(docs)
    csv_buffer.seek(0)
    return csv_buffer
