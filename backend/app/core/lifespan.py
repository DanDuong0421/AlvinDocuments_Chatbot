import os
import google.generativeai as genai
from contextlib import asynccontextmanager
from fastapi import FastAPI
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from transformers import AutoTokenizer
from langchain_text_splitters import TokenTextSplitter

load_dotenv()

# ================== CACHE TOÀN CỤC ==================
models_cache = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Khởi động hệ thống RAG...")

    # ================== 1. GOOGLE GEMINI (LLM) ==================
    print("🔹 Cấu hình Google Gemini AI...")
    api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    # Lưu model vào cache để dùng trong chat_service
    models_cache["llm_rag"] = genai.GenerativeModel("gemini-2.5-flash")

    # ================== 2. EMBEDDING MODEL ==================
    model_name = os.getenv("MODEL_EMBEDDING", "intfloat/multilingual-e5-large")
    print(f"🔹 Loading embedding model: {model_name}")
    models_cache["embedding_model"] = SentenceTransformer(model_name)

    # ================== 3. TOKENIZER + TEXT SPLITTER ==================
    print("🔹 Loading tokenizer & text splitter...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    models_cache["tokenizer"] = tokenizer
    
    models_cache["text_splitter"] = TokenTextSplitter.from_huggingface_tokenizer(
        tokenizer=tokenizer,
        chunk_size=512,
        chunk_overlap=50
    )

    # ================== 4. QDRANT IN-MEMORY (Chạy trên RAM) ==================
    print("🔹 Khởi tạo Qdrant (in-memory mode)...")
    # Chế độ này giúp tốc độ truy xuất cực nhanh và không tốn dung lượng ổ cứng
    models_cache["qdrant_client"] = QdrantClient(location=":memory:")
    # Lưu tên Collection được upload gần nhất
    models_cache["last_collection"] = None

    print("✅ Hệ thống RAG đã sẵn sàng!")
    
    yield

    # ================== CLEANUP ==================
    print("🧹 Đang dọn dẹp cache và đóng kết nối...")
    models_cache.clear()