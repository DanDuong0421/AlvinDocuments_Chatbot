import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def draw_evaluation_results():
    # --- SỬA ĐƯỜNG DẪN TẠI ĐÂY ---
    # Sử dụng os.path.join để tự động khớp với hệ điều hành Windows
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'backend', 'live_evaluation_log.csv')
    
    print(f"Đang kiểm tra file tại: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file tại {file_path}")
        print("Mẹo: Hãy kiểm tra xem file live_evaluation_log.csv đã có trong thư mục backend chưa nhé!")
        return

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Lỗi khi đọc file: {e}")
        return

    # Kiểm tra dữ liệu trống
    if df.empty:
        print("Lỗi: File CSV đang trống, Alvin hãy chat vài câu trên web trước nhé!")
        return

    # --- VẼ BIỂU ĐỒ RADAR (RAG TRIAD) ---
    categories = ['Faithfulness', 'Answer Relevance', 'Context Precision']
    # Lấy giá trị trung bình
    values = [
        df['faithfulness'].mean(), 
        df['answer_relevance'].mean(), 
        df['context_precision'].mean()
    ]
    
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    values += values[:1]
    angles += angles[:1]

    plt.figure(figsize=(7, 7))
    ax = plt.subplot(111, polar=True)
    plt.xticks(angles[:-1], categories, color='blue', size=12)
    
    # Thiết lập giới hạn trục từ 0 đến 1.0 cho đẹp
    ax.set_ylim(0, 1.0) 
    
    ax.plot(angles, values, linewidth=2, linestyle='solid', marker='o')
    ax.fill(angles, values, 'b', alpha=0.1)
    plt.title('Đánh giá chất lượng RAG (Radar Chart)', size=15, y=1.1)
    plt.savefig('radar_chart.png', bbox_inches='tight')
    print("✅ Đã xuất: radar_chart.png")

    # --- VẼ BIỂU ĐỒ LATENCY ---
    plt.figure(figsize=(10, 4))
    plt.plot(df['latency'], marker='o', color='orange', linestyle='-')
    plt.title('Biểu đồ thời gian phản hồi (Latency)')
    plt.xlabel('Lượt câu hỏi')
    plt.ylabel('Giây')
    plt.grid(True, alpha=0.3)
    plt.savefig('latency_chart.png', bbox_inches='tight')
    print("✅ Đã xuất: latency_chart.png")

if __name__ == "__main__":
    draw_evaluation_results()