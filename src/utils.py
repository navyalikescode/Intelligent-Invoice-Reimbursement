import os
import zipfile
import json
import re
from typing import List, Optional

import docx
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_google_genai import (
    GoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)

# Define DATA_PATH relative to the project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data")
VECTOR_STORE_PATH = os.path.join(BASE_DIR, "..", "vector_store")

def extract_text_from_docx(docx_path: str) -> str:
    """Extracts text from a DOCX file.

    Args:
        docx_path (str): The absolute path to the DOCX file.

    Returns:
        str: The extracted text content from the DOCX file.
    """
    doc = docx.Document(docx_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)


def process_zip_file(zip_file: UploadFile, employee_name: str) -> List[str]:
    """Saves and extracts a zip file, and recursively finds all PDF paths within it.

    Args:
        zip_file (UploadFile): The uploaded ZIP file containing invoice PDFs.
        employee_name (str): The name of the employee, used for creating an extraction directory.

    Returns:
        List[str]: A list of absolute paths to the extracted PDF files.
    """
    zip_path = os.path.join(DATA_PATH, zip_file.filename)
    with open(zip_path, "wb") as f:
        f.write(zip_file.file.read())

    extract_dir = os.path.join(DATA_PATH, employee_name)
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    os.remove(zip_path)

    pdf_paths = []
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_paths.append(os.path.join(root, file))
    return pdf_paths


def load_pdf_text(pdf_path: str) -> str:
    """Loads text from a PDF file using PyPDFLoader.

    Args:
        pdf_path (str): The absolute path to the PDF file.

    Returns:
        str: The extracted text content from the PDF file.
    """
    loader = PyPDFLoader(pdf_path)
    docs = loader.load_and_split()
    return " ".join([doc.page_content for doc in docs])


def analyze_single_invoice(
    invoice_path: str,
    policy_text: str,
    employee_name: str,
    analysis_prompt_template: str,
    google_api_key: str,
) -> Optional[dict]:
    """Analyzes a single invoice PDF and stores the analysis in the vector store.

    Args:
        invoice_path (str): The absolute path to the invoice PDF file.
        policy_text (str): The extracted text from the HR policy.
        employee_name (str): The name of the employee.
        analysis_prompt_template (str): The template string for the analysis prompt.
        google_api_key (str): The Google API key for LLM and Embeddings initialization.

    Returns:
        Optional[dict]: A dictionary containing the invoice filename and its analysis, or None if processing fails.
    """
    try:
        # Initialize LLM and Embeddings within the process using the passed API key
        llm_model = GoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=google_api_key)
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=google_api_key
        )

        invoice_text = load_pdf_text(invoice_path)

        analysis_prompt = PromptTemplate(
            input_variables=["policy", "invoice_text", "employee_name"],
            template=analysis_prompt_template,
        )
        chain = LLMChain(llm=llm_model, prompt=analysis_prompt)
        analysis_raw = chain.run(
            policy=policy_text,
            invoice_text=invoice_text,
            employee_name=employee_name,
        )

        try:
            # Extract JSON string from markdown code block
            json_match = re.search(r'```json\n([\s\S]*?)\n```', analysis_raw)
            if json_match:
                json_string = json_match.group(1).strip()
            else:
                # If no markdown block, assume it's pure JSON (for robustness)
                json_string = analysis_raw.strip()

            analysis_json = json.loads(json_string)
            reimbursement_status = analysis_json.get("reimbursement_status")
            reason = analysis_json.get("reason")
            invoice_date = analysis_json.get("invoice_date")

            metadata = {
                "employee_name": employee_name,
                "reimbursement_status": reimbursement_status,
                "reason": reason,
                "invoice_date": invoice_date,
                "invoice_filename": os.path.basename(invoice_path),
            }

            # Re-initialize Chroma within the process for thread safety
            vector_store_process = Chroma(
                persist_directory=VECTOR_STORE_PATH, embedding_function=embeddings_model
            )
            vector_store_process.add_texts(
                texts=[invoice_text, analysis_raw],
                metadatas=[
                    {**metadata, "type": "invoice_text"},
                    {**metadata, "type": "analysis_result"},
                ],
                ids=[f"{invoice_path}_invoice_text", f"{invoice_path}_analysis_result"],
            )

            return {"invoice": os.path.basename(invoice_path), "analysis": analysis_json}
        except json.JSONDecodeError:
            print(f"LLM did not return valid JSON for {invoice_path}: {analysis_raw}")
            return {
                "invoice": os.path.basename(invoice_path),
                "analysis": "LLM output was not valid JSON.",
                "raw_output": analysis_raw,
            }
    except Exception as e:
        print(f"Could not process invoice {invoice_path}: {e}")
        return None
    finally:
        if os.path.exists(invoice_path):
            os.remove(invoice_path)