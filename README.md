# Doctalk
DocTalk — Chat with your PDF

An AI-powered Flutter app that lets you upload any PDF and have a 
conversation with it. Built with RAG architecture using Mistral AI 
and Supabase pgvector.

Tech Stack
- Flutter (frontend)
- FastAPI + Python (backend)
- Mistral AI (embeddings + answers)
- Supabase pgvector (vector storage)
- Chat history with session persistence

How it works
1. Upload any PDF
2. App splits it into chunks and stores embeddings in Supabase
3. When you ask a question, relevant chunks are retrieved
4. Mistral answers using only the document context

How to run locally
1. Clone the repo
2. cd backend && pip install -r requirements.txt
3. Fill in .env with your API keys
4. uvicorn main:app --reload
5. Run Flutter app and connect to localhost:8000
