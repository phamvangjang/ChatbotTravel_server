import os
import json
import openai
from typing import Dict, List, Optional, Any
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
import re

# Khởi tạo OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')

# Khởi tạo ChromaDB client
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
chroma_client = chromadb.PersistentClient(path=os.path.join(workspace_root, 'src', 'nlp_model', 'data', 'chroma_db'))

# Sử dụng sentence-transformers làm embedding function
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

def get_or_create_collection():
    """Get existing collection or create new one if not exists"""
    try:
        collection = chroma_client.get_collection(
            name="diadiem_collection",
            embedding_function=sentence_transformer_ef
        )
        return collection
    except Exception as e:
        print(f"Collection not found, creating new one: {str(e)}")
        collection = chroma_client.create_collection(
            name="diadiem_collection",
            embedding_function=sentence_transformer_ef
        )
        return collection

def normalize_similarity(distance):
    """
    Chuyển đổi khoảng cách thành điểm tương đồng trong khoảng [0.3,1]
    """
    similarity = 1 / (1 + np.exp(distance))
    normalized = 0.3 + (0.7 * (similarity ** 1.5))
    return float(normalized)

def calculate_semantic_score(distance, question_words, metadata):
    """
    Tính điểm ngữ nghĩa dựa trên khoảng cách vector và các yếu tố ngữ nghĩa
    """
    base_score = normalize_similarity(distance)
    
    semantic_factors = {
        'tu_khoa': 0.25,
        'loai_dia_diem': 0.2,
        'khu_vuc': 0.2,
        'dia_chi': 0.15,
    }
    
    semantic_score = base_score
    for field, weight in semantic_factors.items():
        value = str(metadata.get(field, '')).lower().strip()
        if value and any(word in value for word in question_words):
            semantic_score += weight
    
    return min(semantic_score, 1.0)

def apply_filters_to_results(results: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """
    Áp dụng bộ lọc vào kết quả tìm kiếm
    
    Args:
        results (List[Dict]): Danh sách kết quả từ tìm kiếm vector
        filters (Dict[str, Any]): Các tiêu chí lọc từ thực thể trích xuất
        
    Returns:
        List[Dict]: Kết quả đã được lọc
    """
    if not filters:
        return results
    
    filtered_results = []
    
    for result in results:
        metadata = result.get('metadata', {})
        match_score = 0
        total_criteria = 0
        
        # Lọc theo loại địa điểm
        if filters.get('loai_dia_diem'):
            total_criteria += 1
            filter_type = str(filters['loai_dia_diem']).lower().strip()
            result_type = str(metadata.get('loai_dia_diem', '')).lower().strip()
            
            if filter_type and result_type:
                if filter_type in result_type or result_type in filter_type:
                    match_score += 1
                elif any(keyword in result_type for keyword in filter_type.split()):
                    match_score += 0.7
        
        # Lọc theo khu vực
        if filters.get('khu_vuc'):
            total_criteria += 1
            filter_area = str(filters['khu_vuc']).lower().strip()
            result_area = str(metadata.get('khu_vuc', '')).lower().strip()
            
            # Bỏ qua nếu khu_vuc là "Thành phố Hồ Chí Minh" hoặc tương tự (quá chung chung)
            if filter_area in ['thành phố hồ chí minh', 'tp.hcm', 'tp hcm', 'ho chi minh city']:
                # Nếu người dùng chỉ nói chung chung về TP.HCM, không lọc theo khu vực
                match_score += 0.5  # Cho điểm trung bình
            elif filter_area and result_area:
                if filter_area in result_area or result_area in filter_area:
                    match_score += 1
                elif any(keyword in result_area for keyword in filter_area.split()):
                    match_score += 0.7
        
        # Lọc theo đặc điểm
        if filters.get('dac_diem'):
            total_criteria += 1
            filter_features = str(filters['dac_diem']).lower().strip()
            result_desc = str(metadata.get('mo_ta', '')).lower().strip()
            result_name = str(metadata.get('ten_dia_diem', '')).lower().strip()
            
            if filter_features and (result_desc or result_name):
                if any(keyword in result_desc or keyword in result_name 
                       for keyword in filter_features.split()):
                    match_score += 1
        
        # Lọc theo mức giá (nếu có thông tin)
        if filters.get('muc_gia'):
            total_criteria += 1
            price_level = str(filters['muc_gia']).lower().strip()
            # Giả sử có thông tin về giá trong metadata
            result_price_info = str(metadata.get('gia_ve', '')).lower().strip()
            
            if price_level and result_price_info and price_level in result_price_info:
                match_score += 1
        
        # Chỉ thêm kết quả nếu đáp ứng ít nhất 50% tiêu chí
        if total_criteria > 0 and (match_score / total_criteria) >= 0.5:
            # Cập nhật điểm similarity dựa trên độ phù hợp với bộ lọc
            filter_bonus = (match_score / total_criteria) * 0.2
            result['similarity'] = min(result['similarity'] + filter_bonus, 1.0)
            filtered_results.append(result)
    
    return filtered_results

def combined_search_with_filters(question: str, extracted_features: Dict[str, Any], 
                                n_results: int = 10) -> Dict[str, Any]:
    """
    Thực hiện tìm kiếm kết hợp: tìm kiếm ngữ nghĩa + bộ lọc
    
    Args:
        question (str): Câu hỏi của người dùng
        extracted_features (Dict[str, Any]): Thực thể đã trích xuất
        n_results (int): Số lượng kết quả tối đa
        
    Returns:
        Dict[str, Any]: Kết quả tìm kiếm kết hợp
    """
    try:
        # Lấy collection
        collection = get_or_create_collection()
        
        # Kiểm tra collection có dữ liệu không
        count = collection.count()
        if count == 0:
            return {
                'status': 'error',
                'message': 'No data in collection. Please run sync first.',
                'results': []
            }
        
        # Chuẩn hóa câu hỏi
        question = question.strip().lower()
        question_words = set(question.split())
        
        # Thực hiện tìm kiếm vector với số lượng kết quả lớn hơn để có nhiều lựa chọn cho bộ lọc
        search_results = collection.query(
            query_texts=[question],
            n_results=min(n_results * 3, 50),  # Lấy nhiều hơn để lọc
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format kết quả ban đầu
        formatted_results = []
        for doc, metadata, distance in zip(search_results['documents'][0], 
                                         search_results['metadatas'][0], 
                                         search_results['distances'][0]):
            similarity_score = calculate_semantic_score(distance, question_words, metadata)
            
            # Xử lý an toàn các trường metadata có thể thiếu
            formatted_results.append({
                'id': metadata.get('id', ''),
                'ten_dia_diem': metadata.get('ten_dia_diem', ''),
                'mo_ta': metadata.get('mo_ta', ''),
                'loai_dia_diem': metadata.get('loai_dia_diem', ''),
                'khu_vuc': metadata.get('khu_vuc', ''),
                'dia_chi': metadata.get('dia_chi', ''),
                'similarity': round(similarity_score, 2),
                'metadata': metadata  # Giữ lại metadata để lọc
            })
        
        # Sắp xếp theo similarity giảm dần
        formatted_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Áp dụng bộ lọc nếu có thực thể trích xuất
        if extracted_features:
            print("=== ÁP DỤNG BỘ LỌC ===")
            print("Tiêu chí lọc:", extracted_features)
            
            filtered_results = apply_filters_to_results(formatted_results, extracted_features)
            
            print(f"Kết quả trước lọc: {len(formatted_results)}")
            print(f"Kết quả sau lọc: {len(filtered_results)}")
            print("==========================")
            
            # Sắp xếp lại kết quả đã lọc
            filtered_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Loại bỏ metadata khỏi kết quả cuối cùng
            final_results = []
            for result in filtered_results[:n_results]:
                final_result = {k: v for k, v in result.items() if k != 'metadata'}
                final_results.append(final_result)
            
            return {
                'status': 'success',
                'message': f'Found {len(final_results)} relevant locations after filtering',
                'results': final_results,
                'search_method': 'combined_semantic_and_filter'
            }
        else:
            # Nếu không có bộ lọc, trả về kết quả tìm kiếm ngữ nghĩa thuần túy
            final_results = []
            for result in formatted_results[:n_results]:
                final_result = {k: v for k, v in result.items() if k != 'metadata'}
                final_results.append(final_result)
            
            return {
                'status': 'success',
                'message': f'Found {len(final_results)} relevant locations',
                'results': final_results,
                'search_method': 'semantic_only'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error during combined search: {str(e)}',
            'results': []
        }

def extract_user_intent_and_features(question: str) -> Dict[str, Any]:
    """
    Trích xuất ý định và đặc trưng từ câu hỏi của người dùng sử dụng OpenAI API
    
    Args:
        question (str): Câu hỏi của người dùng
        
    Returns:
        Dict[str, Any]: Kết quả trích xuất bao gồm ý định chính và các đặc trưng
    """
    
    # Định nghĩa schema cho các loại ý định khác nhau
    tools_schema = [
        {
            "type": "function",
            "function": {
                "name": "tim_kiem_dia_diem",
                "description": "Trích xuất các tiêu chí để tìm kiếm địa điểm du lịch tại TP.HCM từ câu hỏi của người dùng.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "loai_dia_diem": {
                            "type": "string",
                            "description": "Loại hình của địa điểm, ví dụ: 'Bảo tàng', 'Quán cà phê', 'Công viên', 'Chùa', 'Nhà thờ', 'Chợ', 'Địa điểm ăn uống'."
                        },
                        "khu_vuc": {
                            "type": "string",
                            "description": "Khu vực hoặc quận/huyện mà người dùng muốn tìm kiếm, ví dụ: 'Quận 1', 'Quận 3', 'Thành phố Thủ Đức'."
                        },
                        "dac_diem": {
                            "type": "string",
                            "description": "Các đặc điểm, từ khóa hoặc sở thích cụ thể của người dùng, ví dụ: 'yên tĩnh', 'chụp ảnh', 'cổ kính', 'ngoài trời', 'miễn phí'."
                        },
                        "muc_gia": {
                            "type": "string",
                            "description": "Mức giá mong muốn của người dùng.",
                            "enum": ["Thấp", "Trung bình", "Cao"]
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "hoi_thong_tin_chi_tiet",
                "description": "Trích xuất thông tin khi người dùng hỏi chi tiết về một địa điểm cụ thể.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ten_dia_diem": {
                            "type": "string",
                            "description": "Tên địa điểm mà người dùng muốn biết thông tin chi tiết."
                        },
                        "loai_thong_tin": {
                            "type": "string",
                            "description": "Loại thông tin mà người dùng quan tâm.",
                            "enum": ["Địa chỉ", "Giờ mở cửa", "Giá vé", "Cách đi", "Đánh giá", "Hình ảnh", "Tất cả"]
                        }
                    },
                    "required": ["ten_dia_diem"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "lap_lich_trinh",
                "description": "Trích xuất thông tin khi người dùng muốn lập lịch trình du lịch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "so_ngay": {
                            "type": "integer",
                            "description": "Số ngày du lịch."
                        },
                        "so_nguoi": {
                            "type": "integer",
                            "description": "Số người trong đoàn."
                        },
                        "ngan_sach": {
                            "type": "string",
                            "description": "Ngân sách dự kiến.",
                            "enum": ["Thấp", "Trung bình", "Cao"]
                        },
                        "so_thich": {
                            "type": "string",
                            "description": "Sở thích hoặc mục đích du lịch, ví dụ: 'văn hóa', 'ẩm thực', 'mua sắm', 'chụp ảnh'."
                        },
                        "khu_vuc_uu_tien": {
                            "type": "string",
                            "description": "Khu vực ưu tiên cho lịch trình."
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "so_sanh_dia_diem",
                "description": "Trích xuất thông tin khi người dùng muốn so sánh các địa điểm.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dia_diem_1": {
                            "type": "string",
                            "description": "Tên địa điểm thứ nhất."
                        },
                        "dia_diem_2": {
                            "type": "string",
                            "description": "Tên địa điểm thứ hai."
                        },
                        "tieu_chi_so_sanh": {
                            "type": "string",
                            "description": "Tiêu chí so sánh, ví dụ: 'giá vé', 'vị trí', 'độ nổi tiếng', 'phù hợp cho gia đình'."
                        }
                    },
                    "required": ["dia_diem_1", "dia_diem_2"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "gop_y_va_danh_gia",
                "description": "Trích xuất thông tin khi người dùng muốn góp ý hoặc đánh giá địa điểm.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ten_dia_diem": {
                            "type": "string",
                            "description": "Tên địa điểm được đánh giá."
                        },
                        "loai_gop_y": {
                            "type": "string",
                            "description": "Loại góp ý hoặc đánh giá.",
                            "enum": ["Đánh giá tích cực", "Phàn nàn", "Góp ý cải thiện", "Hỏi thông tin"]
                        },
                        "noi_dung": {
                            "type": "string",
                            "description": "Nội dung góp ý hoặc đánh giá."
                        }
                    },
                    "required": ["ten_dia_diem"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "hoi_chung",
                "description": "Trích xuất thông tin cho các câu hỏi chung về du lịch TP.HCM.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chu_de": {
                            "type": "string",
                            "description": "Chủ đề của câu hỏi.",
                            "enum": ["Thời tiết", "Giao thông", "Văn hóa", "Lịch sử", "Ẩm thực", "Mua sắm", "Khác"]
                        },
                        "cau_hoi_cu_the": {
                            "type": "string",
                            "description": "Câu hỏi cụ thể của người dùng."
                        }
                    },
                    "required": ["cau_hoi_cu_the"]
                }
            }
        }
    ]
    
    try:
        # Gọi OpenAI API để trích xuất thông tin
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """Bạn là một trợ lý AI chuyên phân tích ý định và trích xuất thông tin từ câu hỏi của người dùng về du lịch TP.HCM. 
                    Hãy phân tích câu hỏi và trích xuất thông tin phù hợp nhất với các schema đã định nghĩa.
                    Nếu câu hỏi không phù hợp với bất kỳ schema nào, hãy sử dụng schema 'hoi_chung'.
                    Trả về kết quả bằng tiếng Việt."""
                },
                {
                    "role": "user",
                    "content": f"Câu hỏi của người dùng: {question}"
                }
            ],
            tools=tools_schema,
            tool_choice="auto",
            temperature=0.1
        )
        
        # Xử lý kết quả
        result = {
            "status": "success",
            "original_question": question,
            "intent": None,
            "extracted_features": {},
            "confidence": 0.0
        }
        
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            result["intent"] = tool_call.function.name
            result["extracted_features"] = json.loads(tool_call.function.arguments)
            result["confidence"] = 0.9  # Độ tin cậy cao khi có tool call
        else:
            # Nếu không có tool call, phân loại ý định cơ bản
            result["intent"] = "hoi_chung"
            result["extracted_features"] = {
                "chu_de": "Khác",
                "cau_hoi_cu_the": question
            }
            result["confidence"] = 0.5
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "original_question": question,
            "intent": "unknown",
            "extracted_features": {},
            "confidence": 0.0,
            "error": str(e)
        }

def get_intent_description(intent_name: str) -> str:
    """
    Lấy mô tả cho ý định
    
    Args:
        intent_name (str): Tên ý định
        
    Returns:
        str: Mô tả ý định
    """
    intent_descriptions = {
        "tim_kiem_dia_diem": "Tìm kiếm địa điểm du lịch",
        "hoi_thong_tin_chi_tiet": "Hỏi thông tin chi tiết về địa điểm",
        "lap_lich_trinh": "Lập lịch trình du lịch",
        "so_sanh_dia_diem": "So sánh các địa điểm",
        "gop_y_va_danh_gia": "Góp ý và đánh giá",
        "hoi_chung": "Câu hỏi chung về du lịch TP.HCM",
        "unknown": "Không xác định được ý định"
    }
    
    return intent_descriptions.get(intent_name, "Ý định không xác định")

def validate_extracted_features(intent: str, features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiểm tra và làm sạch dữ liệu trích xuất
    
    Args:
        intent (str): Ý định đã trích xuất
        features (Dict[str, Any]): Đặc trưng đã trích xuất
        
    Returns:
        Dict[str, Any]: Dữ liệu đã được làm sạch
    """
    cleaned_features = features.copy()
    
    # Loại bỏ các giá trị rỗng hoặc None
    cleaned_features = {k: v for k, v in cleaned_features.items() if v is not None and v != ""}
    
    # Chuẩn hóa các trường text
    for key, value in cleaned_features.items():
        if isinstance(value, str):
            cleaned_features[key] = value.strip()
    
    return cleaned_features

def format_extraction_result(result: Dict[str, Any]) -> str:
    """
    Format kết quả trích xuất thành văn bản dễ đọc
    
    Args:
        result (Dict[str, Any]): Kết quả trích xuất
        
    Returns:
        str: Văn bản đã format
    """
    if result["status"] == "error":
        return f"Lỗi trích xuất: {result.get('error', 'Không xác định')}"
    
    intent_desc = get_intent_description(result["intent"])
    features = result["extracted_features"]
    
    formatted_text = f"Ý định: {intent_desc}\n"
    formatted_text += f"Độ tin cậy: {result['confidence']:.1%}\n"
    formatted_text += "Thông tin trích xuất:\n"
    
    for key, value in features.items():
        formatted_text += f"  - {key}: {value}\n"
    
    return formatted_text

def detect_language(text: str) -> Dict[str, Any]:
    """
    Nhận biết ngôn ngữ của văn bản
    
    Args:
        text (str): Văn bản cần nhận biết ngôn ngữ
        
    Returns:
        Dict[str, Any]: Kết quả nhận biết ngôn ngữ
    """
    try:
        # Gọi OpenAI API để nhận biết ngôn ngữ
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """Bạn là một chuyên gia nhận biết ngôn ngữ. 
                    Hãy phân tích văn bản và trả về ngôn ngữ chính xác.
                    Chỉ hỗ trợ 5 ngôn ngữ: vietnamese, english, chinese, korean, japanese.
                    Nếu không phải 5 ngôn ngữ này, trả về "unsupported".
                    Trả về kết quả dưới dạng JSON với format:
                    {
                        "language": "tên_ngôn_ngữ",
                        "confidence": 0.95,
                        "is_supported": true/false
                    }"""
                },
                {
                    "role": "user",
                    "content": f"Văn bản cần nhận biết: {text}"
                }
            ],
            temperature=0.1
        )
        
        # Parse kết quả JSON
        result_text = response.choices[0].message.content
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # Fallback nếu không parse được JSON
            result = {
                "language": "unknown",
                "confidence": 0.0,
                "is_supported": False
            }
        
        # Đảm bảo có các trường cần thiết và chuẩn hóa ngôn ngữ
        result.setdefault("language", "unknown")
        result.setdefault("confidence", 0.0)
        result.setdefault("is_supported", False)
        
        # Chuẩn hóa tên ngôn ngữ về lowercase
        if result["language"]:
            result["language"] = result["language"].lower()
        
        return result
        
    except Exception as e:
        return {
            "language": "unknown",
            "confidence": 0.0,
            "is_supported": False,
            "error": str(e)
        }

def get_language_info(language: str) -> Dict[str, str]:
    """
    Lấy thông tin về ngôn ngữ
    
    Args:
        language (str): Tên ngôn ngữ
        
    Returns:
        Dict[str, str]: Thông tin ngôn ngữ
    """
    language_info = {
        "vietnamese": {
            "name": "Tiếng Việt",
            "greeting": "Xin chào! Tôi là hướng dẫn viên du lịch TP.HCM.",
            "unsupported_message": "Xin lỗi, chúng tôi chưa hỗ trợ ngôn ngữ này. Vui lòng sử dụng tiếng Việt, tiếng Anh, tiếng Trung, tiếng Hàn hoặc tiếng Nhật."
        },
        "english": {
            "name": "English",
            "greeting": "Hello! I'm your Ho Chi Minh City travel guide.",
            "unsupported_message": "Sorry, we don't support this language yet. Please use Vietnamese, English, Chinese, Korean, or Japanese."
        },
        "chinese": {
            "name": "中文",
            "greeting": "您好！我是胡志明市旅游指南。",
            "unsupported_message": "抱歉，我们还不支持这种语言。请使用越南语、英语、中文、韩语或日语。"
        },
        "korean": {
            "name": "한국어",
            "greeting": "안녕하세요! 저는 호치민시 여행 가이드입니다.",
            "unsupported_message": "죄송합니다. 아직 이 언어를 지원하지 않습니다. 베트남어, 영어, 중국어, 한국어 또는 일본어를 사용해 주세요."
        },
        "japanese": {
            "name": "日本語",
            "greeting": "こんにちは！私はホーチミン市の旅行ガイドです。",
            "unsupported_message": "申し訳ございませんが、この言語はまだサポートされていません。ベトナム語、英語、中国語、韓国語、または日本語をご利用ください。"
        }
    }
    
    return language_info.get(language.lower(), {
        "name": "Unknown",
        "greeting": "Hello! I'm your travel guide.",
        "unsupported_message": "Sorry, this language is not supported."
    })

def generate_natural_response(question: str, search_results: List[Dict], 
                            extracted_features: Dict[str, Any], 
                            language: str = "vietnamese") -> Dict[str, Any]:
    """
    Sinh câu trả lời tự nhiên cho chatbot hướng dẫn viên du lịch
    
    Args:
        question (str): Câu hỏi của người dùng
        search_results (List[Dict]): Kết quả tìm kiếm địa điểm
        extracted_features (Dict[str, Any]): Thực thể đã trích xuất
        language (str): Ngôn ngữ để trả lời
        
    Returns:
        Dict[str, Any]: Câu trả lời tự nhiên
    """
    try:
        # Debug logging
        print(f"=== DEBUG: generate_natural_response ===")
        print(f"Input language: '{language}'")
        print(f"Language type: {type(language)}")
        
        # Chuẩn hóa ngôn ngữ về lowercase
        language = language.lower().strip()
        print(f"Normalized language: '{language}'")
        
        # Lấy thông tin ngôn ngữ
        lang_info = get_language_info(language)
        print(f"Language info: {lang_info}")
        
        # Chuẩn bị context cho GPT
        context = {
            "question": question,
            "search_results": search_results,
            "extracted_features": extracted_features,
            "language": language,
            "language_name": lang_info["name"]
        }
        
        # Tạo prompt dựa trên ngôn ngữ
        if language == "vietnamese":
            system_prompt = """Bạn là một hướng dẫn viên du lịch thân thiện và chuyên nghiệp tại TP.HCM. 
            Hãy trả lời câu hỏi của khách du lịch một cách tự nhiên, thân thiện và hữu ích.
            
            Yêu cầu:
            1. Sử dụng giọng điệu thân thiện, nhiệt tình như một hướng dẫn viên thực thụ
            2. Giới thiệu các địa điểm phù hợp với sở thích của khách
            3. Thêm thông tin hữu ích như địa chỉ, đặc điểm nổi bật
            4. Đưa ra gợi ý hoặc lời khuyên du lịch
            5. Kết thúc bằng một câu hỏi để tiếp tục cuộc trò chuyện
            6. Giữ độ dài câu trả lời vừa phải (150-300 từ)
            
            QUAN TRỌNG: Bạn PHẢI trả lời bằng tiếng Việt, không được trả lời bằng tiếng Anh."""
            
            user_prompt = f"""
            Câu hỏi của khách: {question}
            
            Thông tin trích xuất:
            {json.dumps(extracted_features, ensure_ascii=False, indent=2)}
            
            Kết quả tìm kiếm ({len(search_results)} địa điểm):
            {json.dumps(search_results, ensure_ascii=False, indent=2)}
            
            QUAN TRỌNG: Hãy tạo câu trả lời tự nhiên và hữu ích bằng tiếng Việt. KHÔNG được trả lời bằng tiếng Anh."""
            
        elif language == "english":
            system_prompt = """You are a friendly and professional travel guide in Ho Chi Minh City. 
            Answer tourists' questions naturally, warmly, and helpfully.
            
            Requirements:
            1. Use a friendly, enthusiastic tone like a real tour guide
            2. Introduce places that match the tourist's preferences
            3. Add useful information like addresses, highlights
            4. Provide travel suggestions or advice
            5. End with a question to continue the conversation
            6. Keep response length moderate (150-300 words)
            
            IMPORTANT: You MUST respond in English."""
            
            user_prompt = f"""
            Tourist's question: {question}
            
            Extracted information:
            {json.dumps(extracted_features, ensure_ascii=False, indent=2)}
            
            Search results ({len(search_results)} locations):
            {json.dumps(search_results, ensure_ascii=False, indent=2)}
            
            IMPORTANT: Please create a natural and helpful response in English."""
            
        elif language == "chinese":
            system_prompt = """您是胡志明市的一位友好、专业的旅游指南。
            请以自然、热情和有用的方式回答游客的问题。
            
            要求：
            1. 使用友好、热情的语气，像真正的导游一样
            2. 介绍符合游客偏好的地方
            3. 添加有用信息，如地址、亮点
            4. 提供旅游建议或建议
            5. 以问题结尾以继续对话
            6. 保持回复长度适中（150-300字）
            
            重要：您必须用中文回复。"""
            
            user_prompt = f"""
            游客的问题: {question}
            
            提取的信息:
            {json.dumps(extracted_features, ensure_ascii=False, indent=2)}
            
            搜索结果 ({len(search_results)} 个地点):
            {json.dumps(search_results, ensure_ascii=False, indent=2)}
            
            重要：请用中文创建自然有用的回复。"""
            
        elif language == "korean":
            system_prompt = """당신은 호치민시의 친근하고 전문적인 여행 가이드입니다.
            관광객의 질문에 자연스럽고, 따뜻하고, 도움이 되게 답변해 주세요.
            
            요구사항:
            1. 진짜 가이드처럼 친근하고 열정적인 톤 사용
            2. 관광객의 선호도에 맞는 장소 소개
            3. 주소, 하이라이트 등 유용한 정보 추가
            4. 여행 제안이나 조언 제공
            5. 대화를 계속하기 위해 질문으로 끝내기
            6. 응답 길이를 적당히 유지 (150-300단어)
            
            중요: 한국어로 답변해야 합니다."""
            
            user_prompt = f"""
            관광객의 질문: {question}
            
            추출된 정보:
            {json.dumps(extracted_features, ensure_ascii=False, indent=2)}
            
            검색 결과 ({len(search_results)} 개 장소):
            {json.dumps(search_results, ensure_ascii=False, indent=2)}
            
            중요: 한국어로 자연스럽고 유용한 답변을 만들어 주세요."""
            
        elif language == "japanese":
            system_prompt = """あなたはホーチミン市の親しみやすく、プロフェッショナルな旅行ガイドです。
            観光客の質問に自然で、温かく、役立つ方法で答えてください。
            
            要件：
            1. 本当のガイドのように親しみやすく、情熱的なトーンを使用
            2. 観光客の好みに合った場所を紹介
            3. 住所、ハイライトなどの有用な情報を追加
            4. 旅行の提案やアドバイスを提供
            5. 会話を続けるために質問で終わる
            6. 応答の長さを適度に保つ（150-300語）
            
            重要：日本語で答えてください。"""
            
            user_prompt = f"""
            観光客の質問: {question}
            
            抽出された情報:
            {json.dumps(extracted_features, ensure_ascii=False, indent=2)}
            
            検索結果 ({len(search_results)} 箇所):
            {json.dumps(search_results, ensure_ascii=False, indent=2)}
            
            重要：日本語で自然で有用な回答を作成してください。"""
        
        else:
            print(f"WARNING: Unknown language '{language}', falling back to English")
            system_prompt = """You are a friendly travel guide. Please respond in English."""
            user_prompt = f"""
            Tourist's question: {question}
            
            Extracted information:
            {json.dumps(extracted_features, ensure_ascii=False, indent=2)}
            
            Search results ({len(search_results)} locations):
            {json.dumps(search_results, ensure_ascii=False, indent=2)}
            
            Please create a natural and helpful response in English."""
        
        print(f"Selected language branch: '{language}'")
        print(f"System prompt language instruction: {'Vietnamese' if language == 'vietnamese' else 'Other'}")
        print("=== END DEBUG ===")
        
        # Gọi OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        natural_response = response.choices[0].message.content
        
        return {
            "status": "success",
            "response": natural_response,
            "language": language,
            "language_name": lang_info["name"],
            "response_length": len(natural_response)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "response": f"Xin lỗi, có lỗi khi tạo câu trả lời: {str(e)}",
            "language": language,
            "error": str(e)
        }

def create_chatbot_response(question: str, search_results: List[Dict], 
                           extracted_features: Dict[str, Any], 
                           language: str = "vietnamese") -> Dict[str, Any]:
    """
    Tạo phản hồi hoàn chỉnh cho chatbot
    
    Args:
        question (str): Câu hỏi của người dùng
        search_results (List[Dict]): Kết quả tìm kiếm
        extracted_features (Dict[str, Any]): Thực thể trích xuất
        language (str): Ngôn ngữ
        
    Returns:
        Dict[str, Any]: Phản hồi hoàn chỉnh
    """
    # Sinh câu trả lời tự nhiên
    response_data = generate_natural_response(
        question=question,
        search_results=search_results,
        extracted_features=extracted_features,
        language=language
    )
    
    # Tạo danh sách gợi ý hoạt động
    suggested_activities = []
    if search_results:
        # Lấy tên các địa điểm có độ tương đồng cao
        high_similarity_results = [r for r in search_results if r.get('similarity', 0) > 0.6]
        suggested_activities = [r['ten_dia_diem'] for r in high_similarity_results[:3]]
    
    # Tạo gợi ý câu hỏi tiếp theo
    follow_up_questions = generate_follow_up_questions(language, extracted_features)
    
    return {
        "status": response_data["status"],
        "response": response_data["response"],
        "language": language,
        "search_results": search_results,
        "suggested_activities": suggested_activities,
        "follow_up_questions": follow_up_questions,
        "extracted_features": extracted_features
    }

def generate_follow_up_questions(language: str, features: Dict[str, Any]) -> List[str]:
    """
    Tạo câu hỏi gợi ý tiếp theo
    
    Args:
        language (str): Ngôn ngữ
        features (Dict[str, Any]): Thực thể trích xuất
        
    Returns:
        List[str]: Danh sách câu hỏi gợi ý
    """
    questions = {
        "vietnamese": [
            "Bạn có muốn biết thêm về địa điểm nào cụ thể không?",
            "Bạn có quan tâm đến ẩm thực địa phương không?",
            "Bạn muốn tìm hiểu về lịch sử và văn hóa TP.HCM không?",
            "Bạn có cần gợi ý về phương tiện di chuyển không?"
        ],
        "english": [
            "Would you like to know more about any specific place?",
            "Are you interested in local cuisine?",
            "Do you want to learn about Ho Chi Minh City's history and culture?",
            "Do you need suggestions for transportation?"
        ],
        "chinese": [
            "您想了解某个特定地方的更多信息吗？",
            "您对当地美食感兴趣吗？",
            "您想了解胡志明市的历史和文化吗？",
            "您需要交通建议吗？"
        ],
        "korean": [
            "특정 장소에 대해 더 알고 싶으신가요?",
            "현지 요리에 관심이 있으신가요?",
            "호치민시의 역사와 문화에 대해 알고 싶으신가요?",
            "교통편에 대한 제안이 필요하신가요?"
        ],
        "japanese": [
            "特定の場所についてもっと詳しく知りたいですか？",
            "地元の料理に興味がありますか？",
            "ホーチミン市の歴史と文化について知りたいですか？",
            "交通手段についての提案が必要ですか？"
        ]
    }
    
    return questions.get(language, questions["english"])
