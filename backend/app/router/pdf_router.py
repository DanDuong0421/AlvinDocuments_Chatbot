from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schema.chat_schema import QueryResponse 
from app.services import pdf_service
import shutil
import os
from pydantic import BaseModel
from typing import Dict

router = APIRouter()
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# Danh sách các định dạng file được hỗ trợ cho luận văn
ALLOWED_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/plain": ".txt"
}

class DocumentUploadResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, str]

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_and_index_document(file: UploadFile = File(...)):
    # 1. Kiểm tra định dạng file
    if file.content_type not in ALLOWED_EXTENSIONS:
        allowed_str = ", ".join(ALLOWED_EXTENSIONS.values())
        raise HTTPException(
            status_code=400, 
            detail=f"Định dạng file không hỗ trợ. Chỉ chấp nhận: {allowed_str}"
        )

    temp_file_path = os.path.join(TEMP_DIR, file.filename)

    try:
        # 2. Lưu tạm file để xử lý
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. Gọi service xử lý đa năng (Hàm index_document_file đã viết ở trên)
        # Lưu ý: Nếu bạn chưa đổi tên file pdf_service.py thì vẫn gọi qua nó
        collection_name = pdf_service.index_document_file(file, temp_file_path)
        
        return DocumentUploadResponse(
            success=True,
            message=f"Tài liệu '{file.filename}' đã được phân tích và lưu trữ thành công.",
            data={
                "collection_id": collection_name, 
                "file_name": file.filename,
                "file_type": ALLOWED_EXTENSIONS[file.content_type]
            }
        )

    except Exception as e:
        # Log lỗi chi tiết cho bạn debug
        print(f"Error during upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")
    
    finally:
        # 4. Luôn dọn dẹp file tạm sau khi xong
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)