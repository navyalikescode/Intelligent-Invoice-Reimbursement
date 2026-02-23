# Intelligent Invoice Reimbursement System

## I. Project Overview

The Intelligent Invoice Reimbursement System is designed to automate and streamline the process of analyzing employee invoice reimbursements against company policies. It leverages Large Language Models (LLMs) and vector databases to provide two core functionalities:

1.  **Invoice Reimbursement Analysis:** An API endpoint that processes PDF invoices and HR reimbursement policies to determine the reimbursement status (Fully Reimbursed, Partially Reimbursed, or Declined) and provides detailed reasons for the decision. This analysis is then stored in a vector database for efficient retrieval.
2.  **RAG LLM Chatbot:** A Retrieval Augmented Generation (RAG) LLM chatbot that allows users to query processed invoice data using natural language. The chatbot can retrieve relevant information based on criteria such as employee name, invoice date, and reimbursement status, providing coherent and helpful responses in markdown format.

The system aims to enhance efficiency, accuracy, and transparency in managing employee expenses by automating analysis, providing efficient data storage and retrieval, and enabling intelligent querying.

## II. Installation Instructions

To set up and run the application locally, follow these steps:

### Prerequisites

*   Python 3.9+
*   `pip` (Python package installer)
*   `poetry` (Python dependency management - recommended)
*   A Google Cloud Project with the Gemini API enabled and a `GOOGLE_API_KEY`.

### Steps

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-repo/invoice-reimbursement-system.git
    cd invoice-reimbursement-system
    ```

2.  **Set up Python environment and install dependencies:**

    Using `poetry` (recommended):

    ```bash
    poetry install
    poetry shell
    ```

    Using `pip`:

    ```bash
    pip install -r requirements.txt
    ```

3.  **Set your Google API Key:**

    Create a `.env` file in the `src/` directory and add your Google API Key:

    ```
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    ```

    Alternatively, set it as an environment variable before running the application:

    ```bash
    export GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    ```

4.  **Run the application:**

    ```bash
    python src/main.py
    ```

    The application will start on `http://0.0.0.0:8000` (or `http://127.0.0.1:8000`).

## III. Usage Guide

Once the application is running, you can interact with it via the web UI or directly through the API endpoints.

### Web UI

Open your web browser and navigate to `http://127.0.0.1:8000`.

*   **Invoice Analysis:**
    *   Enter the employee's name.
    *   Upload an HR Policy file (PDF or DOCX).
    *   Upload a ZIP file containing one or more invoice PDFs.
    *   Click "Analyze Invoices" to process and store the analysis. The results will be displayed, and you can download or copy the JSON output.
*   **Invoice Chatbot:**
    *   Type your natural language query (e.g., "Show me fully reimbursed invoices for John Doe", "What was the total amount for travel bills in March?").
    *   Optionally, provide an employee name to filter the search.
    *   Click "Ask" to get a response based on the processed invoice data.

### API Endpoints

You can also interact with the API directly using tools like `curl`, Postman, or programmatically.

#### 1. Invoice Reimbursement Analysis Endpoint

*   **URL:** `/analyze-invoices/`
*   **Method:** `POST`
*   **Content-Type:** `multipart/form-data`
*   **Form Fields:**
    *   `policy`: File (PDF or DOCX)
    *   `invoices`: File (ZIP containing PDFs)
    *   `employee_name`: String
*   **Example (using `curl` - conceptual, as file uploads are complex with curl):**

    ```bash
    # This is a simplified example. For actual file uploads, consider using a client like Postman or a Python script.
    # curl -X POST -H "Content-Type: multipart/form-data" \
    #   -F "policy=@./path/to/policy.pdf" \
    #   -F "invoices=@./path/to/invoices.zip" \
    #   -F "employee_name=Jane Doe" \
    #   http://127.0.0.1:8000/analyze-invoices/
    ```

#### 2. RAG LLM Chatbot Endpoint

*   **URL:** `/chatbot/`
*   **Method:** `POST`
*   **Query Parameters:**
    *   `query`: String (required) - The natural language question.
    *   `employee_name`: String (optional) - Filter by employee name.
    *   `reimbursement_status`: String (optional) - Filter by reimbursement status (e.g., "Fully Reimbursed", "Partially Reimbursed", "Declined").
    *   `invoice_date`: String (optional) - Filter by invoice date (YYYY-MM-DD).
*   **Example (using `curl`):**

    ```bash
    curl -X POST "http://127.0.0.1:8000/chatbot/?query=Show%20me%20all%20fully%20reimbursed%20invoices%20for%20Mr.%20C&employee_name=Mr.%20C&reimbursement_status=Fully%20Reimbursed"
    ```

## IV. Technical Details

### Architecture

The system is built using a client-server architecture:

*   **Frontend:** A simple HTML, CSS, and JavaScript UI for user interaction.
*   **Backend:** A FastAPI application that exposes two main API endpoints.
*   **LLM Integration:** Utilizes Google's Gemini models for natural language understanding and generation.
*   **Vector Store:** ChromaDB is used as the vector database to store embeddings of invoice content and analysis results, enabling efficient semantic search.

### Libraries Used

*   **FastAPI:** For building the web API.
*   **LangChain:** An AI framework used for orchestrating LLM interactions, prompt management, and integrating with vector stores.
*   **`langchain-google-genai`:** Provides LangChain integrations for Google's Gemini models and embeddings.
*   **`PyPDFLoader` (from `langchain_community`):** For extracting text from PDF documents.
*   **`python-docx`:** For extracting text from DOCX policy files.
*   **`uvicorn`:** ASGI server to run the FastAPI application.
*   **`python-multipart`:** For handling `multipart/form-data` (file uploads).

### LLM and Embedding Model Choices

*   **LLM:** `gemini-2.5-flash` (via `GoogleGenerativeAI`) is chosen for its balance of performance and cost-effectiveness in generating analysis and chatbot responses.
*   **Embedding Model:** `models/embedding-001` (via `GoogleGenerativeAIEmbeddings`) is used to generate vector embeddings for text content, crucial for similarity search in the vector store.

### Vector Store Integration

*   **ChromaDB:** Selected for its ease of use and ability to run locally without external dependencies.
*   **Data Storage:**
    *   For invoice analysis, both the raw invoice text and the LLM-generated analysis (in JSON format) are embedded and stored.
    *   Metadata such as `employee_name`, `reimbursement_status`, `reason`, `invoice_date`, and `invoice_filename` are explicitly stored alongside the embeddings. This allows for precise filtering during retrieval.
*   **Retrieval:** The chatbot uses ChromaDB's retriever, which performs similarity search on embeddings and applies metadata filters to narrow down relevant documents.

## V. Prompt Design

### For Invoice Processing (Part One)

The system prompt for invoice analysis is designed to guide the LLM to extract specific information and format its output as JSON. This ensures consistency and facilitates programmatic parsing of the results.

```
Analyze the following invoice based on the provided HR reimbursement policy.
Extract the invoice date if available.

**HR Policy:**
{policy}

**Invoice:**
{invoice_text}

**Employee Name:** {employee_name}

Determine the reimbursement status and provide a detailed reason. The status must be one of: "Fully Reimbursed", "Partially Reimbursed", or "Declined".

Provide the analysis in a JSON format with the following keys:
- "reimbursement_status": (string, one of "Fully Reimbursed", "Partially Reimbursed", "Declined")
- "reason": (string, detailed explanation for the status)
- "invoice_date": (string, date of the invoice in YYYY-MM-DD format, or null if not found)

**JSON Analysis:**
```

### For Chatbot (Part Two)

The chatbot's system prompt focuses on enabling the LLM to effectively use the vector search tool and synthesize information into coherent, markdown-formatted responses.

```
Answer the following question based on the provided context.

**Context:**
{context}

**Question:**
{question}
```

The `context` is dynamically populated by the vector store retriever based on the user's query and any specified metadata filters.

## VI. Challenges & Solutions

*   **Structured LLM Output:** Initially, getting the LLM to consistently output structured JSON was a challenge. This was addressed by refining the prompt with clear instructions on the desired JSON format and keys, along with explicit examples.
*   **Metadata Filtering in Vector Store:** Ensuring that specific criteria like `reimbursement_status` and `invoice_date` could be used for filtering required modifying the `analyze-invoices` endpoint to parse and store these as distinct metadata fields during ingestion.
*   **Frontend-Backend Communication for Filters:** Passing optional filters from the frontend UI to the backend chatbot endpoint required careful handling of query parameters and dynamic construction of the search filters for the vector store.

## VII. Code Comments

The codebase includes comments and docstrings to explain the purpose of functions, complex logic, and key architectural decisions, particularly around LLM interactions, vector store integration, and data processing.