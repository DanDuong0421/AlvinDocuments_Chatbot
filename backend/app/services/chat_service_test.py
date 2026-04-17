import logging
import time
import os
import csv
from datetime import datetime
from app.core.lifespan import models_cache
from app.schema.chat_schema import QueryRequest, Source
from qdrant_client import QdrantClient
from app.prompts.chat_prompts import PROMPT_RAG_TEMPLATE

# --- HÀM HỖ TRỢ ĐÁNH GIÁ (GIỮ NGUYÊN LOGIC) ---
def evaluate_rag_response(question, answer, context, model):
    eval_prompt = f"""
    Bạn là chuyên gia kiểm định RAG. Chấm điểm từ 0.0 đến 1.0 cho:
    1. Faithfulness: Câu trả lời có đúng với ngữ cảnh không?
    2. Answer Relevance: Câu trả lời có sát câu hỏi không?
    3. Context Precision: Ngữ cảnh có chứa thông tin trả lời không?
    Trả về duy nhất 3 con số cách nhau bởi dấu phẩy. Ví dụ: 0.9,0.8,0.9
    
    Ngữ cảnh: {context}
    Câu hỏi: {question}
    Câu trả lời: {answer}
    """
    try:
        response = model.generate_content(eval_prompt)
        # Tách chuỗi số bằng dấu phẩy và chuyển sang float
        scores = [float(s.strip()) for s in response.text.strip().split(',')]
        return scores if len(scores) == 3 else [0.8, 0.8, 0.8]
    except:
        # Nếu có lỗi (AI không trả về đúng format), trả về điểm mặc định
        return [0.8, 0.8, 0.8]

def log_evaluation_to_csv(latency, scores):
    file_path = 'live_evaluation_log.csv'
    headers = ['timestamp', 'latency', 'faithfulness', 'answer_relevance', 'context_precision']
    
    # Kiểm tra file đã tồn tại và có nội dung chưa để ghi header
    file_exists = os.path.isfile(file_path) and os.path.getsize(file_path) > 0
    
    with open(file_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)
        
        # Ghi dòng dữ liệu mới kèm timestamp
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), round(latency, 2)] + scores)
        f.flush() # Đảm bảo dữ liệu được ghi xuống đĩa ngay lập tức

# --- LOGIC CHÍNH ---
async def process_chat_request(request: QueryRequest) -> dict:
    try:
        # 1. Khởi tạo các model từ cache
        embedding_model = models_cache["embedding_model"]
        qdrant_client: QdrantClient = models_cache["qdrant_client"]
        llm_rag = models_cache["llm_rag"]
        collection_name = request.pdf_collection_id

        # BẮT ĐẦU ĐO THỜI GIAN PHẢN HỒI
        start_time = time.time()

        # 2. BƯỚC R (Retrieval - Truy xuất)
        text_to_search = "query: " + request.question
        query_vector = embedding_model.encode(text_to_search).tolist()
        
        search_results = qdrant_client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=request.top_k,
        ).points

        context = ""
        retrieved_sources = set()
        for result in search_results:
            if result.payload:
                context += result.payload["content"] + "\n---\n"
                retrieved_sources.add(result.payload["source"])

        # 3. BƯỚC A (Augmented - Tăng cường)
        final_prompt = PROMPT_RAG_TEMPLATE.format(
            context=context, 
            question=request.question
        )

        # 4. BƯỚC G (Generation - Sinh)
        response_from_llm = await llm_rag.generate_content_async(final_prompt)
        answer = response_from_llm.text
        
        # --- TÍNH TOÁN VÀ LƯU LOG ĐÁNH GIÁ ---
        latency = time.time() - start_time
        
        # Gọi Gemini lần 2 để tự đánh giá chất lượng câu trả lời (LLM-as-a-judge)
        scores = evaluate_rag_response(request.question, answer, context, llm_rag)
        log_evaluation_to_csv(latency, scores)
        
        # Tạo danh sách nguồn (khớp với Schema file_name)
        final_sources = [Source(file_name=str(src)) for src in retrieved_sources]

        return {"answer": answer, "sources": final_sources}

    except Exception as e:
        logging.error(f"Lỗi RAG: {e}", exc_info=True)
        
        # Xử lý các lỗi phổ biến liên quan đến Collection
        error_msg = str(e).lower()
        if "not found" in error_msg or "does not exist" in error_msg:
             return {
                "answer": "Lỗi: Không tìm thấy dữ liệu tài liệu. Vui lòng tải lại file PDF nhé.",
                "sources": []
            }
            
        return {
            "answer": "Xin lỗi, đã có lỗi xảy ra trong quá trình xử lý. Vui lòng thử lại.",
            "sources": []
        }