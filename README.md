# DocuMind AI — Build Log

## What's built so far (Milestone 1: Auth + RBAC)
- FastAPI project structure (`app/core`, `app/db`, `app/models`, `app/routes`, `app/services`, `app/utils`)
- MongoDB connection via Motor (async driver)
- Password hashing (bcrypt) + JWT issuing/verification
- `/auth/register` and `/auth/login` endpoints
- RBAC dependency (`get_current_user`, `require_admin`) — ready to protect future routes

## How to run it

1. **Install MongoDB** locally, or use a free MongoDB Atlas cluster (no local install needed — recommended for you since you've used Atlas before on YTS Chitwan).

2. **Set up the backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # edit .env: set MONGO_URI (Atlas connection string) and JWT_SECRET_KEY (any long random string)
   ```

3. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Test it** — go to `http://localhost:8000/docs` (FastAPI's auto-generated Swagger UI). You can:
   - Call `POST /auth/register` with `{"name": "Jatin", "email": "test@test.com", "password": "test123"}`
   - Copy the `access_token` from the response
   - Click "Authorize" in the Swagger UI top-right, paste the token, and you're authenticated for protected routes

5. **Make yourself an admin** (manually, in MongoDB) — find your user document in the `users` collection and change `"role": "user"` to `"role": "admin"`. This is intentional: nobody should be able to self-promote to admin via the API.

## Milestone roadmap (what's next, in order)

### Milestone 2 — Document upload + text extraction
- `POST /documents/upload` (admin-only) — accept a PDF, save it to `storage/uploads/`
- Extract text using `pdfplumber`
- Store document metadata (filename, upload date, uploader) in MongoDB

### Milestone 3 — Chunking + embeddings + FAISS
- Split extracted text into ~500-token chunks with ~50-token overlap
- Generate embeddings using `sentence-transformers` (`bge-base-en-v1.5`)
- Build/update a FAISS index; persist it to `storage/vector_index/`
- Store chunk text + metadata (which document, position) in MongoDB so you can map FAISS results back to source text

### Milestone 4 — Query endpoint (the RAG core)
- `POST /query` (any authenticated user)
- Embed the user's question
- FAISS similarity search → top-k chunks
- Build a prompt: system instruction + retrieved chunks + user question
- Call Gemini API, return the answer + which chunks it came from
- Log the exchange to `chat_history`

### Milestone 5 — Frontend (React)
- Login/register pages
- Admin: document upload UI
- User: chat-style Q&A interface with source citations shown

### Milestone 6 — Hardening + polish
- Rate limiting on `/query` (slowapi)
- Basic request logging (latency, success/failure of Gemini calls)
- Dockerfile for the backend

### Future upgrades (from your portfolio-RAG design notes — do these after v1 works end-to-end)
- Hybrid search: combine FAISS (semantic) with BM25 (keyword) using Reciprocal Rank Fusion
- Cross-encoder reranking of top candidates (`ms-marco-MiniLM-L-6-v2`) before sending to Gemini
- RAGAS-based evaluation to measure answer quality objectively
- Persist BM25 index alongside FAISS for the hybrid step

## Why things were built this way (so you can explain it in interviews)
- **Role is never accepted from the client on register** — hardcoded to `"user"` server-side, admin is DB-promoted only. This closes a real privilege-escalation hole.
- **Motor (async) instead of PyMongo (sync)** — FastAPI's whole performance benefit comes from async I/O; a blocking DB call would stall the event loop for every other request.
- **RBAC logic centralized in `deps.py`** — one place to audit/update permission logic instead of scattered checks per route.
- **Chunk text stored in MongoDB, vectors in FAISS** — FAISS is fast at similarity search but doesn't store metadata well; MongoDB is the source of truth for what a chunk actually says.
