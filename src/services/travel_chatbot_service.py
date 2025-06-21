import os
import json
import openai
from typing import Dict, List, Optional, Any
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
import re
import traceback

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
    
    print("=== DEBUG: apply_filters_to_results ===")
    print(f"Input filters: {filters}")
    print(f"Input results count: {len(results)}")
    
    filtered_results = []
    
    for result in results:
        metadata = result.get('metadata', {})
        match_score = 0
        total_criteria = 0
        
        # Lọc theo loại địa điểm (nếu có)
        if filters.get('loai_dia_diem'):
            total_criteria += 1
            target_loai = filters['loai_dia_diem'].lower()
            
            # Kiểm tra trong các trường có thể chứa loại địa điểm
            loai_fields = [
                metadata.get('loai_dia_diem', '').lower(),
                metadata.get('category', '').lower(),
                metadata.get('type', '').lower()
            ]
            
            # Tìm kiếm lỏng hơn - chỉ cần chứa từ khóa
            if any(target_loai in field for field in loai_fields if field):
                match_score += 1
                print(f"✓ Loại địa điểm match: {target_loai} in {loai_fields}")
            else:
                print(f"✗ Loại địa điểm no match: {target_loai} vs {loai_fields}")
        
        # Lọc theo khu vực (nếu có)
        if filters.get('khu_vuc'):
            total_criteria += 1
            target_khu_vuc = filters['khu_vuc'].lower()
            
            # Kiểm tra trong các trường có thể chứa khu vực
            khu_vuc_fields = [
                metadata.get('khu_vuc', '').lower(),
                metadata.get('district', '').lower(),
                metadata.get('area', '').lower(),
                metadata.get('location', '').lower()
            ]
            
            # Tìm kiếm lỏng hơn
            if any(target_khu_vuc in field for field in khu_vuc_fields if field):
                match_score += 1
                print(f"✓ Khu vực match: {target_khu_vuc} in {khu_vuc_fields}")
            else:
                print(f"✗ Khu vực no match: {target_khu_vuc} vs {khu_vuc_fields}")
        
        # Lọc theo từ khóa (nếu có)
        if filters.get('tu_khoa'):
            total_criteria += 1
            target_keywords = filters['tu_khoa'].lower().split()
            
            # Kiểm tra trong tất cả các trường text
            text_fields = [
                metadata.get('ten_dia_diem', ''),
                metadata.get('mo_ta', ''),
                metadata.get('name', ''),
                metadata.get('description', ''),
                metadata.get('title', ''),
                metadata.get('content', '')
            ]
            
            all_text = ' '.join(text_fields).lower()
            keyword_matches = sum(1 for keyword in target_keywords if keyword in all_text)
            
            # Chỉ cần match ít nhất 1 từ khóa
            if keyword_matches > 0:
                match_score += 1
                print(f"✓ Từ khóa match: {keyword_matches}/{len(target_keywords)} keywords")
            else:
                print(f"✗ Từ khóa no match: {target_keywords}")
        
        # Lọc theo giá (nếu có)
        if filters.get('gia'):
            total_criteria += 1
            target_gia = filters['gia'].lower()
            
            gia_fields = [
                metadata.get('gia', '').lower(),
                metadata.get('price', '').lower(),
                metadata.get('cost', '').lower()
            ]
            
            if any(target_gia in field for field in gia_fields if field):
                match_score += 1
                print(f"✓ Giá match: {target_gia}")
            else:
                print(f"✗ Giá no match: {target_gia}")
        
        # Tính tỷ lệ match
        if total_criteria > 0:
            match_ratio = match_score / total_criteria
            print(f"Match ratio: {match_score}/{total_criteria} = {match_ratio:.2f}")
            
            # Lỏng hơn: chỉ cần match ít nhất 50% tiêu chí
            if match_ratio >= 0.5:
                filtered_results.append(result)
                print(f"✓ Accepted: {metadata.get('ten_dia_diem', 'Unknown')}")
            else:
                print(f"✗ Rejected: {metadata.get('ten_dia_diem', 'Unknown')}")
        else:
            # Nếu không có tiêu chí nào, chấp nhận tất cả
            filtered_results.append(result)
    
    print(f"Filtered results count: {len(filtered_results)}")
    print("=== END DEBUG ===")
    
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
                "success": False,
                "message": "Không có dữ liệu trong cơ sở dữ liệu",
                "results": []
            }
        
        print(f"=== DEBUG: combined_search_with_filters ===")
        print(f"Question: {question}")
        print(f"Extracted features: {extracted_features}")
        print(f"Total documents in collection: {count}")
        
        # Lấy filters từ extracted_features
        filters = extracted_features.get('filters', {})
        
        # Thực hiện tìm kiếm ngữ nghĩa với câu hỏi gốc
        print(f"Performing semantic search with question: {question}")
        semantic_results = collection.query(
            query_texts=[question],
            n_results=min(n_results * 3, count),  # Lấy nhiều hơn để có thể lọc
            include=["metadatas", "documents", "distances"]
        )
        
        print(f"Semantic search returned {len(semantic_results['ids'][0])} results")
        
        # Chuyển đổi kết quả sang format dễ xử lý
        results = []
        for i in range(len(semantic_results['ids'][0])):
            result = {
                'id': semantic_results['ids'][0][i],
                'metadata': semantic_results['metadatas'][0][i],
                'document': semantic_results['documents'][0][i],
                'distance': semantic_results['distances'][0][i]
            }
            results.append(result)
        
        print(f"First few results distances: {[r['distance'] for r in results[:5]]}")
        
        # Áp dụng bộ lọc nếu có
        if filters:
            print(f"Applying filters: {filters}")
            filtered_results = apply_filters_to_results(results, filters)
            print(f"After filtering: {len(filtered_results)} results")
        else:
            filtered_results = results
            print("No filters applied")
        
        # Sắp xếp theo khoảng cách (gần nhất trước)
        filtered_results.sort(key=lambda x: x['distance'])
        
        # Giới hạn số lượng kết quả
        final_results = filtered_results[:n_results]
        
        print(f"Final results count: {len(final_results)}")
        
        return {
            "success": True,
            "results": final_results,
            "total_found": len(filtered_results),
            "filters_applied": bool(filters)
        }
        
    except Exception as e:
        print(f"Error in combined_search_with_filters: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi tìm kiếm: {str(e)}",
            "results": []
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
                            "description": "Loại địa điểm (bảo tàng, công viên, nhà hàng, khách sạn, chợ, v.v.)"
                        },
                        "khu_vuc": {
                            "type": "string", 
                            "description": "Khu vực cụ thể (quận 1, quận 3, Bến Thành, v.v.)"
                        },
                        "tu_khoa": {
                            "type": "string",
                            "description": "Từ khóa tìm kiếm (từ tiếng Việt, Anh, Trung, Nhật, Hàn)"
                        },
                        "gia": {
                            "type": "string",
                            "description": "Mức giá (rẻ, trung bình, cao, miễn phí, v.v.)"
                        }
                    },
                    "required": []
                }
            }
        }
    ]
    
    # System prompt cải tiến để hỗ trợ đa ngôn ngữ
    system_prompt = """Bạn là trợ lý AI chuyên về du lịch TP.HCM. Hãy phân tích câu hỏi của người dùng và trích xuất thông tin để tìm kiếm địa điểm phù hợp.

Hỗ trợ các ngôn ngữ: Tiếng Việt, Tiếng Anh, Tiếng Trung, Tiếng Nhật, Tiếng Hàn

Từ khóa tiếng Anh phổ biến:
- Museum, Park, Restaurant, Hotel, Market, Shopping mall, Temple, Church, Coffee shop, Bar, Nightlife, Entertainment
- District 1, District 3, Ben Thanh, Saigon, Ho Chi Minh City
- Cheap, Expensive, Free, Budget, Luxury, Food, Cuisine

Từ khóa tiếng Việt phổ biến:
- Bảo tàng, Công viên, Nhà hàng, Khách sạn, Chợ, Trung tâm thương mại, Chùa, Nhà thờ, Quán cà phê, Bar, Cuộc sống về đêm, Giải trí
- Quận 1, Quận 3, Bến Thành, Sài Gòn, TP.HCM
- Rẻ, Đắt, Miễn phí, Bình dân, Cao cấp, Ẩm thực, Món ăn

Hãy trích xuất chính xác các thông tin từ câu hỏi và trả về dưới dạng JSON."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            tools=tools_schema,
            tool_choice={"type": "function", "function": {"name": "tim_kiem_dia_diem"}}
        )
        
        # Xử lý response
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            function_call = tool_calls[0]
            function_args = json.loads(function_call.function.arguments)
            
            print(f"=== DEBUG: extract_user_intent_and_features ===")
            print(f"Question: {question}")
            print(f"Extracted features: {function_args}")
            
            return {
                "original_question": question,
                "intent": "tim_kiem_dia_diem",
                "confidence": 0.9,
                "extracted_features": function_args
            }
        else:
            print("No tool calls found in response")
            return {
                "original_question": question,
                "intent": "general_question",
                "confidence": 0.5,
                "extracted_features": {}
            }
            
    except Exception as e:
        print(f"Error in extract_user_intent_and_features: {str(e)}")
        return {
            "original_question": question,
            "intent": "error",
            "confidence": 0.0,
            "extracted_features": {}
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
    if result.get("intent") == "error":
        return f"Lỗi trích xuất: {result.get('error', 'Không xác định')}"
    
    intent_desc = get_intent_description(result.get("intent", "unknown"))
    features = result.get("extracted_features", {})
    confidence = result.get("confidence", 0.0)
    
    formatted_text = f"Ý định: {intent_desc}\n"
    formatted_text += f"Độ tin cậy: {confidence:.1%}\n"
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
        # Fallback detection bằng từ khóa trước khi gọi API
        text_lower = text.lower().strip()
        
        # Từ khóa tiếng Anh phổ biến
        english_keywords = [
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'can', 'could', 'will', 'would', 'should', 'may', 'might', 'must',
            'what', 'where', 'when', 'why', 'how', 'which', 'who', 'whom',
            'museum', 'park', 'restaurant', 'hotel', 'shopping', 'tourist', 'visit', 'see',
            'food', 'culture', 'history', 'architecture', 'beautiful', 'famous', 'popular'
        ]
        
        # Từ khóa tiếng Trung phổ biến
        chinese_keywords = ['的', '是', '在', '有', '和', '与', '或', '但', '因为', '所以', '如果', '虽然']
        
        # Từ khóa tiếng Hàn phổ biến
        korean_keywords = ['은', '는', '이', '가', '을', '를', '의', '에', '에서', '로', '으로', '와', '과']
        
        # Từ khóa tiếng Nhật phổ biến
        japanese_keywords = ['は', 'が', 'を', 'に', 'へ', 'で', 'から', 'まで', 'の', 'と', 'や', 'も']
        
        # Từ khóa tiếng Việt phổ biến
        vietnamese_keywords = [
            'của', 'và', 'hoặc', 'nhưng', 'trong', 'trên', 'dưới', 'đến', 'cho', 'về', 'với', 'bởi',
            'là', 'có', 'được', 'bị', 'phải', 'cần', 'muốn', 'thích', 'ghét',
            'gì', 'đâu', 'khi', 'tại sao', 'như thế nào', 'nào', 'ai', 'của ai',
            'bảo tàng', 'công viên', 'nhà hàng', 'khách sạn', 'mua sắm', 'du lịch', 'thăm', 'xem',
            'ẩm thực', 'văn hóa', 'lịch sử', 'kiến trúc', 'đẹp', 'nổi tiếng', 'phổ biến'
        ]
        
        # Đếm từ khóa cho mỗi ngôn ngữ
        english_count = sum(1 for word in text_lower.split() if word in english_keywords)
        chinese_count = sum(1 for char in text_lower if char in chinese_keywords)
        korean_count = sum(1 for char in text_lower if char in korean_keywords)
        japanese_count = sum(1 for char in text_lower if char in japanese_keywords)
        vietnamese_count = sum(1 for word in text_lower.split() if word in vietnamese_keywords)
        
        # Nếu có đủ từ khóa để xác định ngôn ngữ
        if english_count >= 2 and english_count > max(chinese_count, korean_count, japanese_count, vietnamese_count):
            return {
                "language": "english",
                "confidence": 0.8,
                "is_supported": True,
                "detection_method": "keyword_fallback"
            }
        elif chinese_count >= 2:
            return {
                "language": "chinese",
                "confidence": 0.8,
                "is_supported": True,
                "detection_method": "keyword_fallback"
            }
        elif korean_count >= 2:
            return {
                "language": "korean",
                "confidence": 0.8,
                "is_supported": True,
                "detection_method": "keyword_fallback"
            }
        elif japanese_count >= 2:
            return {
                "language": "japanese",
                "confidence": 0.8,
                "is_supported": True,
                "detection_method": "keyword_fallback"
            }
        elif vietnamese_count >= 2:
            return {
                "language": "vietnamese",
                "confidence": 0.8,
                "is_supported": True,
                "detection_method": "keyword_fallback"
            }
        
        # Nếu không xác định được bằng từ khóa, gọi OpenAI API
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
        result.setdefault("detection_method", "openai_api")
        
        # Chuẩn hóa tên ngôn ngữ về lowercase
        if result["language"]:
            result["language"] = result["language"].lower()
        
        return result
        
    except Exception as e:
        # Fallback cuối cùng - giả sử là tiếng Việt nếu có dấu tiếng Việt
        vietnamese_chars = ['à', 'á', 'ạ', 'ả', 'ã', 'â', 'ầ', 'ấ', 'ậ', 'ẩ', 'ẫ', 'ă', 'ằ', 'ắ', 'ặ', 'ẳ', 'ẵ',
                           'è', 'é', 'ẹ', 'ẻ', 'ẽ', 'ê', 'ề', 'ế', 'ệ', 'ể', 'ễ',
                           'ì', 'í', 'ị', 'ỉ', 'ĩ',
                           'ò', 'ó', 'ọ', 'ỏ', 'õ', 'ô', 'ồ', 'ố', 'ộ', 'ổ', 'ỗ', 'ơ', 'ờ', 'ớ', 'ợ', 'ở', 'ỡ',
                           'ù', 'ú', 'ụ', 'ủ', 'ũ', 'ư', 'ừ', 'ứ', 'ự', 'ử', 'ữ',
                           'ỳ', 'ý', 'ỵ', 'ỷ', 'ỹ',
                           'đ']
        
        has_vietnamese = any(char in text.lower() for char in vietnamese_chars)
        
        if has_vietnamese:
            return {
                "language": "vietnamese",
                "confidence": 0.6,
                "is_supported": True,
                "detection_method": "vietnamese_chars_fallback"
            }
        else:
            # Nếu không có dấu tiếng Việt, giả sử là tiếng Anh
            return {
                "language": "english",
                "confidence": 0.5,
                "is_supported": True,
                "detection_method": "default_fallback"
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
        print(f"Search results count: {len(search_results)}")
        print(f"Search results type: {type(search_results)}")
        print(f"Extracted features: {extracted_features}")
        
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
        print("About to call OpenAI API...")
        
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
        
        print("OpenAI API call successful")
        natural_response = response.choices[0].message.content
        print(f"Generated response length: {len(natural_response)}")
        
        return {
            "status": "success",
            "response": natural_response,
            "language": language,
            "language_name": lang_info["name"],
            "response_length": len(natural_response)
        }
        
    except Exception as e:
        print(f"ERROR in generate_natural_response: {str(e)}")
        import traceback
        traceback.print_exc()
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
