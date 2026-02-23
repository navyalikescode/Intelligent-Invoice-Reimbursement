import os
import json
import logging
from typing import Optional
from concurrent.futures import ProcessPoolExecutor

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langchain.chains import LLMChain
from langchain_community.vectorstores import Chroma
from langchain.schema.runnable import RunnablePassthrough

from .utils import extract_text_from_docx, process_zip_file, load_pdf_text, analyze_single_invoice
from .llm_config import llm, embeddings
from .prompts import analysis_prompt, rag_prompt

# --- Environment and Path Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data")
VECTOR_STORE_PATH = os.path.join(BASE_DIR, "..", "vector_store")
STATIC_DIR = os.path.join(BASE_DIR, "..", "static")

os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(VECTOR_STORE_PATH, exist_ok=True)

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI App ---
app = FastAPI()

# Custom Exception Handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

# Mount static files to serve the frontend
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Vector Store ---
# Initialize ChromaDB as the vector store, persisting data to VECTOR_STORE_PATH
vector_store = Chroma(
    persist_directory=VECTOR_STORE_PATH, embedding_function=embeddings
)

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main HTML page for the application.

    Returns:
        HTMLResponse: The content of the index.html file.
    """
    logger.info("Serving index.html")
    with open(os.path.join(STATIC_DIR, "index.html"), "r") as f:
        return HTMLResponse(content=f.read())


@app.post("/analyze-invoices/")
async def analyze_invoices(
    policy: UploadFile = File(...),
    invoices: UploadFile = File(...),
    employee_name: str = Form(...),
):
    """Analyzes employee invoices against a policy, stores the analysis, and returns the results.
    Supports PDF and DOCX policy files.

    Args:
        policy (UploadFile): The HR reimbursement policy file (PDF or DOCX).
        invoices (UploadFile): A ZIP file containing one or more employee invoice PDFs.
        employee_name (str): The name of the employee associated with the invoices.

    Returns:
        dict: A dictionary containing the status of the analysis and a list of results for each invoice.

    Raises:
        HTTPException: If file types are invalid, policy processing fails, or no PDFs are found in the ZIP.
    """
    logger.info(f"Received request to analyze invoices for {employee_name}")
    # 1. Validate file types
    policy_filename_lower = policy.filename.lower()
    if not (policy_filename_lower.endswith(".pdf") or policy_filename_lower.endswith(".docx")):
        logger.warning(f"Invalid policy file type received: {policy.filename}")
        raise HTTPException(
            status_code=400, detail="Invalid policy file type. Please upload a PDF or DOCX."
        )
    if not invoices.filename.lower().endswith(".zip"):
        logger.warning(f"Invalid invoices file type received: {invoices.filename}")
        raise HTTPException(
            status_code=400, detail="Invalid invoices file type. Please upload a ZIP file."
        )

    try:
        # 2. Process Policy
        policy_path = os.path.join(DATA_PATH, policy.filename)
        with open(policy_path, "wb") as f:
            f.write(policy.file.read())
        logger.info(f"Policy file saved to {policy_path}")

        policy_text = ""
        try:
            if policy_filename_lower.endswith(".pdf"):
                policy_text = load_pdf_text(policy_path)
            elif policy_filename_lower.endswith(".docx"):
                policy_text = extract_text_from_docx(policy_path)
            logger.info("Policy text extracted successfully.")
        except Exception as e:
            logger.error(f"Failed to process policy file {policy.filename}: {e}")
            raise HTTPException(
                status_code=400, detail=f"Failed to process policy file: {e}"
            )
        finally:
            if os.path.exists(policy_path):
                os.remove(policy_path)
                logger.info(f"Policy file {policy_path} removed.")

        # 3. Process Invoices
        invoice_paths = process_zip_file(invoices, employee_name)
        if not invoice_paths:
            logger.warning(f"No PDF files found in ZIP for {employee_name}")
            raise HTTPException(
                status_code=400, detail="No PDF files found in the uploaded ZIP."
            )
        logger.info(f"Found {len(invoice_paths)} invoices for {employee_name}")

        # 4. Analyze each invoice using LLM in parallel
        results = []
        # Using ProcessPoolExecutor for parallel processing
        with ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(
                    analyze_single_invoice,
                    invoice_path,
                    policy_text,
                    employee_name,
                    analysis_prompt.template, # Pass the template string
                    os.environ.get("GOOGLE_API_KEY"), # Pass the API key
                )
                for invoice_path in invoice_paths
            ]
            for future in futures:
                result = future.result()
                if result:
                    results.append(result)
        logger.info(f"Finished analyzing {len(results)} invoices for {employee_name}")

        return {"status": "success", "results": results}

    except HTTPException as http_exc:
        # Re-raise FastAPI HTTPExceptions directly
        raise http_exc
    except Exception as e:
        # Catch any unexpected errors during the overall process
        logger.critical(f"An unexpected error occurred during invoice analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@app.post("/chatbot/")
async def chatbot(
    query: str,
    employee_name: Optional[str] = None,
    reimbursement_status: Optional[str] = None,
    invoice_date: Optional[str] = None,
):
    """A RAG chatbot to query and retrieve information about processed invoices.

    Args:
        query (str): The natural language question from the user.
        employee_name (Optional[str]): Optional filter for employee name.
        reimbursement_status (Optional[str]): Optional filter for reimbursement status (e.g., "Fully Reimbursed", "Partially Reimbursed", "Declined").
        invoice_date (Optional[str]): Optional filter for invoice date in YYYY-MM-DD format.

    Returns:
        dict: A dictionary containing the chatbot's response.

    Raises:
        HTTPException: If an unexpected error occurs during chatbot processing.
    """
    logger.info(f"Chatbot query received: '{query}' for employee: {employee_name}, status: {reimbursement_status}, date: {invoice_date}")
    try:
        # 1. Prepare filters for vector store search
        search_kwargs = {}
        filters = {}
        if employee_name:
            filters["employee_name"] = employee_name
        if reimbursement_status:
            filters["reimbursement_status"] = reimbursement_status
        if invoice_date:
            filters["invoice_date"] = invoice_date

        if filters:
            search_kwargs["filter"] = filters
            logger.info(f"Applying filters: {filters}")

        # Initialize retriever with potential filters
        retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

        # 2. Define RAG Chain
        # rag_prompt is imported from .prompts

        # Function to format retrieved documents for the LLM context
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Construct the RAG chain: retrieve documents, format them, pass to LLM with question
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | rag_prompt
            | llm
        )

        # 3. Invoke the RAG chain to get the chatbot's response
        response = rag_chain.invoke(query)
        logger.info("Chatbot response generated.")

        return {"response": response}
    except Exception as e:
        logger.critical(f"An unexpected error occurred during chatbot processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
