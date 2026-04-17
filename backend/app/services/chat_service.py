import logging
from app.core.lifespan import models_cache
from app.schema.chat_schema import QueryRequest, Source
from qdrant_client import QdrantClient
from app.prompts.chat_prompts import PROMPT_RAG_TEMPLATE

async def process_chat_request(request: QueryRequest) -> dict:
    try:
        # 1. Lấy models và client từ cache
        embedding_model = models_cache["embedding_model"]
        qdrant_client: QdrantClient = models_cache["qdrant_client"]
        llm_rag = models_cache["llm_rag"]
        collection_name = request.pdf_collection_id

        # 2. Bước R (Retrieval - Truy xuất)
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
                # Gộp text làm ngữ cảnh
                context += result.payload["content"] + "\n---\n"
                # Chỉ lấy tên file (file_name)
                retrieved_sources.add(result.payload["source"])

        # 3. Bước A (Augmented - Tăng cường)
        final_prompt = PROMPT_RAG_TEMPLATE.format(
            context=context, 
            question=request.question
        )

        # 4. Bước G (Generation - Sinh câu trả lời)
        response_from_llm = await llm_rag.generate_content_async(final_prompt)
        answer = response_from_llm.text
        
        # 5. Định dạng nguồn trả về (Sửa name -> file_name để tránh lỗi Pydantic)
        # Đồng thời lọc để chỉ trả về duy nhất 1 thẻ nguồn cho mỗi file
        final_sources = [Source(file_name=str(src)) for src in retrieved_sources]

        return { "answer": answer, "sources": final_sources }

    except Exception as e:
        logging.error(f"Lỗi RAG: {e}", exc_info=True)
        
        # Xử lý lỗi mất Collection khi server restart
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
             return {
                "answer": "Hệ thống không tìm thấy tài liệu này. Alvin vui lòng tải lại file PDF nhé!",
                "sources": []
            }
        
        return {
            "answer": "Xin lỗi, Alvin AI gặp chút trục trặc khi đọc tài liệu. Bạn thử lại nhé!",
            "sources": []
        }