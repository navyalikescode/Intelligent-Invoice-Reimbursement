from langchain.prompts import PromptTemplate

# Prompt template for analyzing invoices against HR policy
analysis_prompt_template = """
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
"""
analysis_prompt = PromptTemplate(
    input_variables=["policy", "invoice_text", "employee_name"],
    template=analysis_prompt_template,
)

# Prompt template for the RAG chatbot
rag_prompt_template = """
Answer the following question based on the provided context.

**Context:**
{context}

**Question:**
{question}
"""
rag_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=rag_prompt_template,
)
