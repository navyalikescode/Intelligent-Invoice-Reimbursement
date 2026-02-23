import os
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Initialize Google Generative AI for LLM operations
llm = GoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY)

# Initialize Google Generative AI Embeddings for creating vector representations of text
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001", google_api_key=GOOGLE_API_KEY
)
