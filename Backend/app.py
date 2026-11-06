import os
import time
from google import genai
from dotenv import load_dotenv
from pypdf import PdfReader
import chromadb
from flask import Flask, request, jsonify
from flask_cors import CORS


load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
chroma_client = chromadb.PersistentClient(path="./chroma_db")

app = Flask(__name__)
CORS(app)


def get_collection_name(pdf_path):
    filename = os.path.basename(pdf_path)
    clean_name = filename.replace(".pdf", "").replace(" ", "_")
    return f"doc_{clean_name}"


def chunk_text(text, chunk_size=200):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


# ---------- Index a new PDF (skips if already indexed) ----------

@app.route("/index", methods=["POST"])
def index_document():
    data = request.get_json()
    pdf_path = data.get("pdf_path")

    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 400

    collection_name = get_collection_name(pdf_path)
    new_collection = chroma_client.get_or_create_collection(name=collection_name)

    if new_collection.count() > 0:
        return jsonify({"message": f"'{os.path.basename(pdf_path)}' is already indexed."})

    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()

        chunks = chunk_text(full_text)

        for i, chunk in enumerate(chunks):
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=chunk
            )
            embedding = result.embeddings[0].values

            new_collection.add(
                ids=[str(i)],
                embeddings=[embedding],
                documents=[chunk]
            )
            time.sleep(2)

        return jsonify({"message": f"'{os.path.basename(pdf_path)}' indexed successfully with {len(chunks)} chunks."})

    except Exception as e:
        return jsonify({"error": "Something went wrong while indexing. Please try again."}), 500


# ---------- List all documents already indexed ----------

@app.route("/documents", methods=["GET"])
def list_documents():
    collections = chroma_client.list_collections()
    doc_names = [c.name for c in collections]
    return jsonify(doc_names)


# ---------- Ask a question about a specific already-indexed document ----------

@app.route("/ask", methods=["POST"])
def ask_question():
    data = request.get_json()
    question = data.get("question")
    collection_name = data.get("collection_name")

    if not question or not collection_name:
        return jsonify({"error": "Question and document selection are both required"}), 400

    try:
        collection = chroma_client.get_or_create_collection(name=collection_name)

        question_embedding_result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=question
        )
        question_embedding = question_embedding_result.embeddings[0].values

        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=3
        )

        retrieved_chunks = results["documents"][0]
        context = "\n\n".join(retrieved_chunks)

        rag_prompt = f"""You are a helpful assistant. Answer the question using ONLY the context provided below. If the answer isn't in the context, say you don't know based on the given document.

Context:
{context}

Question: {question}

Answer:"""

        answer_response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=rag_prompt
        )

        return jsonify({"reply": answer_response.text})

    except Exception as e:
        return jsonify({"error": "Something went wrong answering your question. Please try again."}), 500


if __name__ == "__main__":
    app.run(debug=True)