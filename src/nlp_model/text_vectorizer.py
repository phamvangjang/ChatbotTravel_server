import torch
from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
from typing import List, Dict, Union
import os
import json
from underthesea import word_tokenize, sent_tokenize

class TextVectorizer:
    def __init__(self, model_name: str = "vinai/phobert-base-v2"):
        """
        Khởi tạo TextVectorizer với mô hình PhoBERT
        
        Args:
            model_name: Tên mô hình PhoBERT (mặc định: vinai/phobert-base-v2)
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SentenceTransformer(model_name, device=self.device)
        
    def preprocess_text(self, text: str) -> str:
        """
        Tiền xử lý văn bản tiếng Việt
        
        Args:
            text: Văn bản đầu vào
            
        Returns:
            Văn bản đã được tiền xử lý
        """
        # Tách câu
        sentences = sent_tokenize(text)
        processed_sentences = []
        
        for sentence in sentences:
            # Tách từ
            words = word_tokenize(sentence, format="text")
            processed_sentences.append(words)
            
        return " ".join(processed_sentences)
    
    def vectorize_text(self, text: str) -> np.ndarray:
        """
        Chuyển đổi văn bản thành vector
        
        Args:
            text: Văn bản đầu vào
            
        Returns:
            Vector biểu diễn của văn bản
        """
        # Tiền xử lý văn bản
        processed_text = self.preprocess_text(text)
        
        # Vector hóa
        with torch.no_grad():
            embedding = self.model.encode(processed_text, convert_to_numpy=True)
            
        return embedding
    
    def vectorize_documents(self, documents: List[Dict]) -> pd.DataFrame:
        """
        Vector hóa nhiều tài liệu
        
        Args:
            documents: Danh sách các tài liệu, mỗi tài liệu là một dict chứa:
                      - title: Tiêu đề
                      - content: Nội dung
                      - metadata: Thông tin bổ sung (tùy chọn)
                      
        Returns:
            DataFrame chứa các vector và metadata
        """
        vectors = []
        metadata = []
        
        for doc in documents:
            # Kết hợp tiêu đề và nội dung
            text = f"{doc['title']} {' '.join(doc['content'])}"
            
            # Vector hóa
            vector = self.vectorize_text(text)
            
            # Lưu vector và metadata
            vectors.append(vector)
            metadata.append({
                'title': doc['title'],
                'content': doc['content'],
                **(doc.get('metadata', {}))
            })
            
        # Tạo DataFrame
        df = pd.DataFrame({
            'vector': vectors,
            'metadata': metadata
        })
        
        return df
    
    def save_vectors(self, df: pd.DataFrame, output_path: str):
        """
        Lưu các vector vào file
        
        Args:
            df: DataFrame chứa các vector
            output_path: Đường dẫn file đầu ra
        """
        # Chuyển đổi DataFrame thành dict
        data = {
            'vectors': df['vector'].tolist(),
            'metadata': df['metadata'].tolist()
        }
        
        # Lưu vào file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def load_vectors(self, input_path: str) -> pd.DataFrame:
        """
        Đọc các vector từ file
        
        Args:
            input_path: Đường dẫn file đầu vào
            
        Returns:
            DataFrame chứa các vector
        """
        # Đọc từ file
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Tạo DataFrame
        df = pd.DataFrame({
            'vector': data['vectors'],
            'metadata': data['metadata']
        })
        
        return df
    
    def find_similar_documents(self, query: str, df: pd.DataFrame, top_k: int = 3) -> List[Dict]:
        """
        Tìm các tài liệu tương tự với câu hỏi
        
        Args:
            query: Câu hỏi
            df: DataFrame chứa các vector
            top_k: Số lượng kết quả trả về
            
        Returns:
            Danh sách các tài liệu tương tự
        """
        # Vector hóa câu hỏi
        query_vector = self.vectorize_text(query)
        
        # Tính độ tương đồng cosine
        similarities = []
        for vector in df['vector']:
            similarity = np.dot(query_vector, vector) / (np.linalg.norm(query_vector) * np.linalg.norm(vector))
            similarities.append(similarity)
            
        # Lấy top k kết quả
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Tạo kết quả
        results = []
        for idx in top_indices:
            results.append({
                'document': df['metadata'].iloc[idx],
                'similarity': similarities[idx]
            })
            
        return results

if __name__ == "__main__":
    # Ví dụ sử dụng
    vectorizer = TextVectorizer()
    
    # Tạo dữ liệu mẫu
    documents = [
        {
            'title': 'Nhà thờ Đức Bà',
            'content': ['Nhà thờ Đức Bà là một trong những công trình kiến trúc nổi tiếng nhất của Sài Gòn.',
                       'Được xây dựng từ năm 1877 đến năm 1880.'],
            'metadata': {'type': 'attraction', 'location': 'Quận 1'}
        },
        {
            'title': 'Phở Hòa',
            'content': ['Phở Hòa là một trong những quán phở nổi tiếng nhất Sài Gòn.',
                       'Đặc biệt nổi tiếng với món phở bò.'],
            'metadata': {'type': 'food', 'location': 'Quận 3'}
        }
    ]
    
    # Vector hóa tài liệu
    df = vectorizer.vectorize_documents(documents)
    
    # Lưu vectors
    vectorizer.save_vectors(df, 'vectors.json')
    
    # Tìm tài liệu tương tự
    query = "Gợi ý địa điểm tham quan ở Sài Gòn"
    similar_docs = vectorizer.find_similar_documents(query, df)
    
    print("Các tài liệu tương tự:")
    for doc in similar_docs:
        print(f"\nTiêu đề: {doc['document']['title']}")
        print(f"Độ tương đồng: {doc['similarity']:.2f}")
        print(f"Nội dung: {' '.join(doc['document']['content'])}") 