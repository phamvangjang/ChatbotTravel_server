import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
import os
import json

def process_diadiem():
    # Đường dẫn đến file diadiem.csv
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    csv_path = os.path.join(workspace_root, 'src', 'scape', 'diadiem.csv')
    
    # Đọc file CSV với encoding phù hợp cho tiếng Việt
    try:
        # Thử đọc với utf-8-sig trước (có BOM)
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        try:
            # Nếu không được thì thử với cp1252
            df = pd.read_csv(csv_path, encoding='cp1252')
        except UnicodeDecodeError:
            # Cuối cùng thử với utf-8
            df = pd.read_csv(csv_path, encoding='utf-8')
    
    # Khởi tạo ChromaDB client
    chroma_client = chromadb.PersistentClient(path=os.path.join(workspace_root, 'src', 'nlp_model', 'data', 'chroma_db'))
    
    # Sử dụng sentence-transformers làm embedding function
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="keepitreal/vietnamese-sbert"
    )
    
    # Tạo collection mới hoặc lấy collection đã tồn tại
    collection = chroma_client.get_or_create_collection(
        name="diadiem_collection",
        embedding_function=sentence_transformer_ef
    )
    
    # Chuẩn bị dữ liệu để thêm vào ChromaDB
    documents = []
    metadatas = []
    ids = []
    
    for _, row in df.iterrows():
        # Tạo nội dung từ các cột
        content = []
        if pd.notna(row['mo_ta']):
            content.append(row['mo_ta'])
        
        # Tạo document text
        doc_text = f"{row['ten_dia_diem']} {row['mo_ta'] if pd.notna(row['mo_ta']) else ''}"
        
        # Tạo metadata
        metadata = {
            'id': str(row['id']),
            'ten_dia_diem': row['ten_dia_diem'],
            'mo_ta': row['mo_ta'] if pd.notna(row['mo_ta']) else ''
        }
        
        documents.append(doc_text)
        metadatas.append(metadata)
        ids.append(str(row['id']))
    
    # Thêm dữ liệu vào collection
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"Đã xử lý và lưu {len(documents)} địa điểm vào ChromaDB")
    
    # Thử tìm kiếm
    query = "Gợi ý địa điểm tham quan ở Sài Gòn"
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    
    print("\nKết quả tìm kiếm mẫu:")
    for i, (doc, metadata, distance) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
        print(f"\nKết quả {i+1}:")
        print(f"ID: {metadata['id']}")
        print(f"Địa điểm: {metadata['ten_dia_diem']}")
        print(f"Độ tương đồng: {1 - distance:.2f}")  # Chuyển đổi distance thành similarity
        print(f"Mô tả: {metadata['mo_ta']}")
