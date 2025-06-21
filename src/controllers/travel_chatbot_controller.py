from flask_restx import Namespace, Resource, fields, reqparse
from flask import request
from src.nlp_model.process_diadiem import process_diadiem
from src.services.travel_chatbot_service import (
    extract_user_intent_and_features, 
    format_extraction_result, 
    combined_search_with_filters,
    detect_language,
    get_language_info,
    create_chatbot_response
)
import os
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
import json
import math
import openai
from datetime import datetime
import traceback

# Khởi tạo namespace
travel_chatbot_ns = Namespace('travel-chatbot', description='Travel chatbot operations')

# Định nghĩa parser cho pagination
pagination_parser = reqparse.RequestParser()
pagination_parser.add_argument('page', type=int, default=1, help='Page number (starts from 1)')
pagination_parser.add_argument('limit', type=int, default=10, help='Number of items per page')
pagination_parser.add_argument('sort_by', type=str, default='id', help='Field to sort by')
pagination_parser.add_argument('sort_order', type=str, default='asc', help='Sort order (asc/desc)')

# Định nghĩa model cho request/response
question_model = travel_chatbot_ns.model('Question', {
    'question': fields.String(required=True, description='User question about travel in Ho Chi Minh City')
})

answer_model = travel_chatbot_ns.model('Answer', {
    'id': fields.String(description='Location ID'),
    'ten_dia_diem': fields.String(description='Location name'),
    'mo_ta': fields.String(description='Location description'),
    'loai_dia_diem': fields.String(description='Location type'),
    'khu_vuc': fields.String(description='Area/Region'),
    'dia_chi': fields.String(description='Address'),
    'similarity': fields.Float(description='Similarity score (0-1)'),
    'language': fields.String(description='Language of the result (vietnamese, english, chinese, korean, japanese)')
})

search_response_model = travel_chatbot_ns.model('SearchResponse', {
    'status': fields.String(description='Status of the search operation'),
    'message': fields.String(description='Detailed message about the search operation'),
    'results': fields.List(fields.Nested(answer_model), description='Search results')
})

sync_response_model = travel_chatbot_ns.model('SyncResponse', {
    'status': fields.String(description='Status of the sync operation'),
    'message': fields.String(description='Detailed message about the sync operation'),
    'processed_count': fields.Integer(description='Number of locations processed')
})

# Model cho response của embeddings
embedding_model = travel_chatbot_ns.model('Embedding', {
    'id': fields.String(description='Location ID'),
    'embedding': fields.List(fields.Float, description='Vector embedding'),
    'document': fields.String(description='Original document text')
})

embeddings_response_model = travel_chatbot_ns.model('EmbeddingsResponse', {
    'status': fields.String(description='Status of the operation'),
    'message': fields.String(description='Detailed message'),
    'total': fields.Integer(description='Total number of embeddings'),
    'total_pages': fields.Integer(description='Total number of pages'),
    'current_page': fields.Integer(description='Current page number'),
    'items_per_page': fields.Integer(description='Number of items per page'),
    'embeddings': fields.List(fields.Nested(embedding_model), description='List of embeddings')
})

# Model cho response của metadata
metadata_model = travel_chatbot_ns.model('Metadata', {
    'id': fields.String(description='Location ID'),
    'ten_dia_diem': fields.String(description='Location name'),
    'mo_ta': fields.String(description='Location description'),
    'additional_info': fields.Raw(description='Additional metadata information')
})

metadata_response_model = travel_chatbot_ns.model('MetadataResponse', {
    'status': fields.String(description='Status of the operation'),
    'message': fields.String(description='Detailed message'),
    'total': fields.Integer(description='Total number of metadata entries'),
    'total_pages': fields.Integer(description='Total number of pages'),
    'current_page': fields.Integer(description='Current page number'),
    'items_per_page': fields.Integer(description='Number of items per page'),
    'metadata': fields.List(fields.Nested(metadata_model), description='List of metadata entries')
})

# Cập nhật model response để hỗ trợ chatbot
chatbot_response_model = travel_chatbot_ns.model('ChatbotResponse', {
    'status': fields.String(description='Status of the operation'),
    'message': fields.String(description='Detailed message'),
    'response': fields.String(description='Natural language response from chatbot'),
    'language': fields.String(description='Detected language'),
    'language_name': fields.String(description='Language name in native script'),
    'search_results': fields.List(fields.Nested(answer_model), description='Search results'),
    'suggested_activities': fields.List(fields.String, description='Suggested activities'),
    'follow_up_questions': fields.List(fields.String, description='Follow-up questions'),
    'extracted_features': fields.Raw(description='Extracted entities and features')
})

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

# Lấy collection
collection = get_or_create_collection()

# Ngưỡng tối thiểu cho độ tương đồng
MIN_SIMILARITY_THRESHOLD = 0.1

def normalize_similarity(distance):
    """
    Chuyển đổi khoảng cách thành điểm tương đồng trong khoảng [0.3,1]
    Sử dụng hàm sigmoid có điều chỉnh để đảm bảo phân phối điểm phù hợp
    """
    # Chuyển đổi distance thành similarity bằng hàm sigmoid
    similarity = 1 / (1 + np.exp(distance))
    
    # Chuẩn hóa về khoảng [0.3,1] với phân phối phi tuyến
    # Sử dụng hàm mũ để tăng độ phân biệt giữa các mức độ tương đồng
    normalized = 0.3 + (0.7 * (similarity ** 1.5))
    return float(normalized)

def calculate_semantic_score(distance, question_words, metadata):
    """
    Tính điểm ngữ nghĩa dựa trên khoảng cách vector và các yếu tố ngữ nghĩa
    """
    # Điểm cơ bản từ khoảng cách vector
    base_score = normalize_similarity(distance)
    
    # Tính điểm từ các yếu tố ngữ nghĩa
    semantic_factors = {
        'tu_khoa': 0.25,  # Từ khóa có trọng số cao nhất
        'loai_dia_diem': 0.2,
        'khu_vuc': 0.2,
        'dia_chi': 0.15,
        # 'thoi_gian_hoat_dong': 0.1,
        # 'gia_ve': 0.1
    }
    
    semantic_score = base_score
    for field, weight in semantic_factors.items():
        value = metadata.get(field, '').lower()
        if any(word in value for word in question_words):
            semantic_score += weight
    
    return min(semantic_score, 1.0)

def paginate_results(results, page, limit, sort_by='id', sort_order='asc'):
    """
    Phân trang và sắp xếp kết quả
    """
    if not results:
        return [], 0, 0
    
    # Sắp xếp kết quả
    if sort_order.lower() == 'desc':
        results = sorted(results, key=lambda x: x.get(sort_by, ''), reverse=True)
    else:
        results = sorted(results, key=lambda x: x.get(sort_by, ''))
    
    # Tính toán phân trang
    total = len(results)
    total_pages = math.ceil(total / limit)
    page = min(max(1, page), total_pages)  # Đảm bảo page nằm trong khoảng hợp lệ
    
    # Lấy kết quả cho trang hiện tại
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_results = results[start_idx:end_idx]
    
    return paginated_results, total, total_pages

@travel_chatbot_ns.route('/search')
class SearchLocation(Resource):
    @travel_chatbot_ns.expect(question_model)
    @travel_chatbot_ns.marshal_with(chatbot_response_model)
    def post(self):
        """Search for travel locations with natural language chatbot response"""
        try:
            # Lấy câu hỏi từ request
            data = request.get_json()
            question = data.get('question')
            
            if not question:
                return {
                    'status': 'error',
                    'message': 'Question is required',
                    'response': '',
                    'language': 'unknown',
                    'language_name': 'Unknown',
                    'search_results': [],
                    'suggested_activities': [],
                    'follow_up_questions': [],
                    'extracted_features': {}
                }, 400
            
            # Bước 1: Nhận biết ngôn ngữ
            print("=== NHẬN BIẾT NGÔN NGỮ ===")
            language_result = detect_language(question)
            print("Kết quả nhận biết ngôn ngữ:", language_result)
            
            # Kiểm tra ngôn ngữ có được hỗ trợ không
            if not language_result.get('is_supported', False):
                lang_info = get_language_info('unknown')
                return {
                    'status': 'error',
                    'message': lang_info['unsupported_message'],
                    'response': lang_info['unsupported_message'],
                    'language': 'unsupported',
                    'language_name': 'Unsupported',
                    'search_results': [],
                    'suggested_activities': [],
                    'follow_up_questions': [],
                    'extracted_features': {}
                }, 400
            
            detected_language = language_result.get('language', 'vietnamese')
            lang_info = get_language_info(detected_language)
            print(f"Ngôn ngữ phát hiện: {lang_info['name']} (confidence: {language_result.get('confidence', 0):.1%})")
            print("==========================")
            
            # Bước 2: Trích xuất thực thể và ý định từ câu hỏi
            print("=== TRÍCH XUẤT THỰC THỂ ===")
            extraction_result = extract_user_intent_and_features(question)
            
            # In ra kết quả trích xuất
            print("Câu hỏi gốc:", extraction_result.get('original_question', question))
            print("Ý định:", extraction_result.get('intent', 'unknown'))
            print("Độ tin cậy:", f"{extraction_result.get('confidence', 0):.1%}")
            print("Thực thể trích xuất:")
            for key, value in extraction_result.get('extracted_features', {}).items():
                print(f"  - {key}: {value}")
            print("==========================")
            
            # Format kết quả trích xuất để hiển thị
            formatted_extraction = format_extraction_result(extraction_result)
            print("Kết quả trích xuất đã format:")
            print(formatted_extraction)
            print("==========================")
            
            # Bước 3: Thực hiện tìm kiếm kết hợp với bộ lọc
            print("=== THỰC HIỆN TÌM KIẾM KẾT HỢP ===")
            search_result = combined_search_with_filters(
                question=question,
                extracted_features=extraction_result.get('extracted_features', {}),
                n_results=8
            )
            
            # Debug: Kiểm tra kết quả tìm kiếm ngay sau khi nhận
            print("=== DEBUG: search_result received ===")
            print(f"search_result type: {type(search_result)}")
            print(f"search_result keys: {list(search_result.keys()) if isinstance(search_result, dict) else 'Not a dict'}")
            print(f"search_result['status']: {search_result.get('status', 'No status key')}")
            print(f"search_result['success']: {search_result.get('success', 'No success key')}")
            print("=== END DEBUG ===")
            
            # Kiểm tra kết quả tìm kiếm
            if search_result.get('status') == 'error' or search_result.get('success') == False:
                return {
                    'status': 'error',
                    'message': search_result.get('message', 'Unknown search error'),
                    'response': f"Xin lỗi, {search_result.get('message', 'Unknown search error')}",
                    'language': detected_language,
                    'language_name': lang_info['name'],
                    'search_results': [],
                    'suggested_activities': [],
                    'follow_up_questions': [],
                    'extracted_features': extraction_result.get('extracted_features', {})
                }, 500
            
            # In thông tin về phương pháp tìm kiếm
            print(f"Phương pháp tìm kiếm: {search_result.get('search_method', 'unknown')}")
            print(f"Số kết quả tìm thấy: {len(search_result['results'])}")
            print("==========================")
            
            # Format kết quả tìm kiếm để phù hợp với response model
            formatted_results = []
            for result in search_result['results']:
                metadata = result.get('metadata', {})
                distance = result.get('distance', 0)
                
                # Tính similarity score từ distance
                similarity = 1 / (1 + distance) if distance > 0 else 0
                
                # Xác định ngôn ngữ của kết quả dựa trên metadata
                result_language = 'unknown'
                if metadata.get('mo_ta'):
                    mo_ta = metadata.get('mo_ta', '')
                    # Kiểm tra ngôn ngữ dựa trên ký tự
                    if any(char in mo_ta for char in ['は', 'が', 'を', 'に', 'へ', 'で', 'から', 'まで', 'の', 'と', 'や', 'も']):
                        result_language = 'japanese'
                    elif any(char in mo_ta for char in ['은', '는', '이', '가', '을', '를', '의', '에', '에서', '로', '으로', '와', '과']):
                        result_language = 'korean'
                    elif any(char in mo_ta for char in ['的', '是', '在', '有', '和', '与', '或', '但', '因为', '所以', '如果', '虽然']):
                        result_language = 'chinese'
                    elif any(char in mo_ta for char in ['à', 'á', 'ạ', 'ả', 'ã', 'â', 'ầ', 'ấ', 'ậ', 'ẩ', 'ẫ', 'ă', 'ằ', 'ắ', 'ặ', 'ẳ', 'ẵ', 'è', 'é', 'ẹ', 'ẻ', 'ẽ', 'ê', 'ề', 'ế', 'ệ', 'ể', 'ễ', 'ì', 'í', 'ị', 'ỉ', 'ĩ', 'ò', 'ó', 'ọ', 'ỏ', 'õ', 'ô', 'ồ', 'ố', 'ộ', 'ổ', 'ỗ', 'ơ', 'ờ', 'ớ', 'ợ', 'ở', 'ỡ', 'ù', 'ú', 'ụ', 'ủ', 'ũ', 'ư', 'ừ', 'ứ', 'ự', 'ử', 'ữ', 'ỳ', 'ý', 'ỵ', 'ỷ', 'ỹ', 'đ']):
                        result_language = 'vietnamese'
                    else:
                        result_language = 'english'
                
                # Ưu tiên kết quả cùng ngôn ngữ với câu hỏi
                language_boost = 0.3 if result_language == detected_language else 0.0
                adjusted_similarity = min(similarity + language_boost, 1.0)
                
                formatted_result = {
                    'id': result.get('id', ''),
                    'ten_dia_diem': metadata.get('ten_dia_diem', ''),
                    'mo_ta': metadata.get('mo_ta', ''),
                    'loai_dia_diem': metadata.get('loai_dia_diem', ''),
                    'khu_vuc': metadata.get('khu_vuc', ''),
                    'dia_chi': metadata.get('dia_chi', ''),
                    'similarity': round(adjusted_similarity, 3),
                    'language': result_language
                }
                formatted_results.append(formatted_result)
            
            # Sắp xếp kết quả theo similarity (cao nhất trước) và ưu tiên ngôn ngữ
            formatted_results.sort(key=lambda x: (x['similarity'], x['language'] == detected_language), reverse=True)
            
            # Chỉ giữ lại kết quả có similarity > 0.1 để tránh kết quả không liên quan
            formatted_results = [r for r in formatted_results if r['similarity'] > 0.1]
            
            # Ưu tiên kết quả cùng ngôn ngữ với câu hỏi
            same_language_results = [r for r in formatted_results if r['language'] == detected_language]
            other_language_results = [r for r in formatted_results if r['language'] != detected_language]
            
            # Nếu có đủ kết quả cùng ngôn ngữ, chỉ trả về những kết quả đó
            if len(same_language_results) >= 3:
                formatted_results = same_language_results[:8]
                print(f"Using {len(formatted_results)} results in {detected_language}")
            else:
                # Nếu không đủ, bổ sung thêm kết quả từ ngôn ngữ khác
                formatted_results = same_language_results + other_language_results[:8-len(same_language_results)]
                print(f"Using {len(same_language_results)} same language + {len(other_language_results[:8-len(same_language_results)])} other language results")
            
            # Debug: Kiểm tra cấu trúc search_result
            print("=== DEBUG: search_result structure ===")
            print(f"search_result keys: {list(search_result.keys())}")
            print(f"search_result['status']: {search_result.get('status')}")
            print(f"search_result['results'] type: {type(search_result.get('results'))}")
            print(f"search_result['results'] length: {len(search_result.get('results', []))}")
            if search_result.get('results'):
                print(f"First result keys: {list(search_result['results'][0].keys())}")
                print(f"First result metadata keys: {list(search_result['results'][0].get('metadata', {}).keys())}")
            print("=== END DEBUG ===")
            
            # Bước 4: Tạo câu trả lời tự nhiên cho chatbot
            print("=== SINH CÂU TRẢ LỜI TỰ NHIÊN ===")
            try:
                print("About to call create_chatbot_response...")
                print(f"Question: {question}")
                print(f"Search results count: {len(formatted_results)}")
                print(f"Extracted features: {extraction_result.get('extracted_features', {})}")
                print(f"Language: {detected_language}")
                
                chatbot_response = create_chatbot_response(
                    question=question,
                    search_results=formatted_results,
                    extracted_features=extraction_result.get('extracted_features', {}),
                    language=detected_language
                )
                
                print("create_chatbot_response completed successfully")
                print("Câu trả lời chatbot đã được tạo")
                print("Độ dài câu trả lời:", len(chatbot_response.get('response', '')))
                print("Số hoạt động gợi ý:", len(chatbot_response.get('suggested_activities', [])))
                print("Số câu hỏi tiếp theo:", len(chatbot_response.get('follow_up_questions', [])))
                
            except Exception as e:
                print(f"ERROR in create_chatbot_response: {str(e)}")
                import traceback
                traceback.print_exc()
                raise e
                
            print("==========================")
            
            # Trả về kết quả hoàn chỉnh
            return {
                'status': 'success',
                'message': f'Generated natural response in {lang_info["name"]}',
                'response': chatbot_response.get('response', ''),
                'language': detected_language,
                'language_name': lang_info['name'],
                'search_results': formatted_results,
                'suggested_activities': chatbot_response.get('suggested_activities', []),
                'follow_up_questions': chatbot_response.get('follow_up_questions', []),
                'extracted_features': extraction_result.get('extracted_features', {})
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error during chatbot processing: {str(e)}',
                'response': f'Xin lỗi, có lỗi xảy ra: {str(e)}',
                'language': 'unknown',
                'language_name': 'Unknown',
                'search_results': [],
                'suggested_activities': [],
                'follow_up_questions': [],
                'extracted_features': {}
            }, 500

@travel_chatbot_ns.route('/embeddings')
class GetEmbeddings(Resource):
    @travel_chatbot_ns.expect(pagination_parser)
    @travel_chatbot_ns.marshal_with(embeddings_response_model)
    def get(self):
        """Get embeddings from the database with pagination"""
        try:
            # Parse parameters
            args = pagination_parser.parse_args()
            page = args['page']
            limit = args['limit']
            sort_by = args['sort_by']
            sort_order = args['sort_order']
            
            # Validate parameters
            if limit < 1 or limit > 100:
                return {
                    'status': 'error',
                    'message': 'Limit must be between 1 and 100',
                    'total': 0,
                    'total_pages': 0,
                    'current_page': page,
                    'items_per_page': limit,
                    'embeddings': []
                }, 400
            
            # Lấy tất cả dữ liệu
            results = collection.get(
                include=['embeddings', 'documents', 'metadatas']
            )
            
            if not results or not results['ids']:
                return {
                    'status': 'error',
                    'message': 'No data found in the collection',
                    'total': 0,
                    'total_pages': 0,
                    'current_page': page,
                    'items_per_page': limit,
                    'embeddings': []
                }, 404
            
            # Format kết quả
            formatted_embeddings = []
            for i, (id, embedding, document) in enumerate(zip(results['ids'], results['embeddings'], results['documents'])):
                if embedding is not None:
                    formatted_embeddings.append({
                        'id': id,
                        'embedding': embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
                        'document': document
                    })
            
            if not formatted_embeddings:
                return {
                    'status': 'error',
                    'message': 'No embeddings found in the collection',
                    'total': 0,
                    'total_pages': 0,
                    'current_page': page,
                    'items_per_page': limit,
                    'embeddings': []
                }, 404
            
            # Phân trang kết quả
            paginated_results, total, total_pages = paginate_results(
                formatted_embeddings, page, limit, sort_by, sort_order
            )
            
            return {
                'status': 'success',
                'message': f'Retrieved {len(paginated_results)} embeddings',
                'total': total,
                'total_pages': total_pages,
                'current_page': page,
                'items_per_page': limit,
                'embeddings': paginated_results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'total': 0,
                'total_pages': 0,
                'current_page': page,
                'items_per_page': limit,
                'embeddings': []
            }, 500

@travel_chatbot_ns.route('/metadata')
class GetMetadata(Resource):
    @travel_chatbot_ns.expect(pagination_parser)
    @travel_chatbot_ns.marshal_with(metadata_response_model)
    def get(self):
        """Get metadata from the database with pagination"""
        try:
            # Parse parameters
            args = pagination_parser.parse_args()
            page = args['page']
            limit = args['limit']
            sort_by = args['sort_by']
            sort_order = args['sort_order']
            
            # Validate parameters
            if limit < 1 or limit > 100:
                return {
                    'status': 'error',
                    'message': 'Limit must be between 1 and 100',
                    'total': 0,
                    'total_pages': 0,
                    'current_page': page,
                    'items_per_page': limit,
                    'metadata': []
                }, 400
            
            # Kiểm tra collection tồn tại
            try:
                collection = chroma_client.get_collection(
                    name="diadiem_collection",
                    embedding_function=sentence_transformer_ef
                )
            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'Collection not found. Please run sync first: {str(e)}',
                    'total': 0,
                    'total_pages': 0,
                    'current_page': page,
                    'items_per_page': limit,
                    'metadata': []
                }, 404
            
            # Lấy tất cả dữ liệu
            try:
                results = collection.get(
                    include=['metadatas']
                )
            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'Error getting data from collection: {str(e)}',
                    'total': 0,
                    'total_pages': 0,
                    'current_page': page,
                    'items_per_page': limit,
                    'metadata': []
                }, 500
            
            if not results or not results['ids']:
                return {
                    'status': 'error',
                    'message': 'No data found in the collection. Please run sync first.',
                    'total': 0,
                    'total_pages': 0,
                    'current_page': page,
                    'items_per_page': limit,
                    'metadata': []
                }, 404
            
            # Format kết quả
            formatted_metadata = []
            for i, (id, metadata) in enumerate(zip(results['ids'], results['metadatas'])):
                if metadata is not None:
                    formatted_metadata.append({
                        'id': id,
                        'ten_dia_diem': metadata.get('ten_dia_diem', ''),
                        'mo_ta': metadata.get('mo_ta', ''),
                        'additional_info': {k: v for k, v in metadata.items() if k not in ['ten_dia_diem', 'mo_ta']}
                    })
            
            if not formatted_metadata:
                return {
                    'status': 'error',
                    'message': 'No metadata found in the collection. Please check your data.',
                    'total': 0,
                    'total_pages': 0,
                    'current_page': page,
                    'items_per_page': limit,
                    'metadata': []
                }, 404
            
            # Phân trang kết quả
            paginated_results, total, total_pages = paginate_results(
                formatted_metadata, page, limit, sort_by, sort_order
            )
            
            return {
                'status': 'success',
                'message': f'Retrieved {len(paginated_results)} metadata entries',
                'total': total,
                'total_pages': total_pages,
                'current_page': page,
                'items_per_page': limit,
                'metadata': paginated_results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Unexpected error: {str(e)}',
                'total': 0,
                'total_pages': 0,
                'current_page': page,
                'items_per_page': limit,
                'metadata': []
            }, 500

@travel_chatbot_ns.route('/sync-diadiem')
class SyncDiadiem(Resource):
    @travel_chatbot_ns.marshal_with(sync_response_model)
    def post(self):
        """Sync and process diadiem.csv data"""
        try:
            # Xử lý file diadiem.csv
            process_diadiem()
            
            return {
                'status': 'success',
                'message': 'Successfully processed diadiem.csv and generated vectors',
                'processed_count': 1  # Số lượng file đã xử lý
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'processed_count': 0
            }, 500

# Khởi tạo OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')

def format_search_results(search_results):
    """Format kết quả tìm kiếm thành văn bản có cấu trúc"""
    formatted_text = []
    
    # Lọc kết quả có độ tương đồng cao
    high_similarity_results = [r for r in search_results if r['similarity'] > 0.7]
    
    if high_similarity_results:
        formatted_text.append("Dựa trên tìm kiếm của bạn, tôi tìm thấy những địa điểm phù hợp sau:")
        
        for result in high_similarity_results:
            formatted_text.append(f"\n- {result['ten_dia_diem']}")
            formatted_text.append(f"  {result['mo_ta']}")
    
    # Thêm các kết quả có độ tương đồng trung bình
    medium_similarity_results = [r for r in search_results if 0.5 <= r['similarity'] <= 0.7]
    if medium_similarity_results:
        formatted_text.append("\nNgoài ra, bạn có thể tham khảo thêm:")
        for result in medium_similarity_results:
            formatted_text.append(f"\n- {result['ten_dia_diem']}")
            formatted_text.append(f"  {result['mo_ta']}")
    
    return "\n".join(formatted_text)

def generate_natural_response(base_response, question):
    """Sử dụng GPT để làm cho câu trả lời tự nhiên hơn"""
    prompt = f"""Bạn là một trợ lý du lịch thông minh. Hãy viết lại câu trả lời sau một cách tự nhiên và thân thiện hơn, 
    nhưng vẫn giữ nguyên thông tin chính. Thêm một câu hỏi ở cuối để tiếp tục cuộc trò chuyện.

    Câu hỏi của người dùng: {question}

    Câu trả lời hiện tại:
    {base_response}

    Yêu cầu:
    1. Giữ nguyên tất cả thông tin về địa điểm
    2. Làm cho câu trả lời tự nhiên và thân thiện hơn
    3. Thêm một câu hỏi ở cuối để tiếp tục cuộc trò chuyện
    4. Giữ độ dài tương đương với câu trả lời gốc

    Hãy trả lời bằng tiếng Việt."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý du lịch thông minh và thân thiện."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        # Nếu có lỗi với GPT, trả về câu trả lời gốc
        return base_response

@travel_chatbot_ns.route('/chat')
class ChatResponse(Resource):
    @travel_chatbot_ns.expect(question_model)
    @travel_chatbot_ns.marshal_with(travel_chatbot_ns.model('ChatResponse', {
        'status': fields.String,
        'message': fields.String,
        'response': fields.String,
        'suggested_activities': fields.List(fields.String)
    }))
    def post(self):
        """Generate natural response based on vector search results"""
        try:
            # Lấy câu hỏi từ request
            data = request.get_json()
            question = data.get('question')
            
            if not question:
                return {
                    'status': 'error',
                    'message': 'Question is required',
                    'response': '',
                    'suggested_activities': []
                }, 400
            
            # Tìm kiếm địa điểm phù hợp bằng vector
            search_response = self.search_locations(question)
            if search_response[1] != 200:
                return {
                    'status': 'error',
                    'message': search_response[0]['message'],
                    'response': '',
                    'suggested_activities': []
                }, search_response[1]
            
            search_results = search_response[0]['results']
            
            # Tạo câu trả lời cơ bản từ kết quả tìm kiếm
            base_response = self.format_search_results(search_results)
            
            # Làm cho câu trả lời tự nhiên hơn bằng GPT
            natural_response = generate_natural_response(base_response, question)
            
            # Tạo danh sách hoạt động gợi ý
            suggested_activities = [
                result['ten_dia_diem']
                for result in search_results
                if result['similarity'] > 0.5  # Chỉ lấy các địa điểm có độ tương đồng cao
            ]
            
            return {
                'status': 'success',
                'message': 'Generated response successfully',
                'response': natural_response,
                'suggested_activities': suggested_activities
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error generating response: {str(e)}',
                'response': '',
                'suggested_activities': []
            }, 500
    
    def search_locations(self, question):
        """Helper method to perform vector search"""
        try:
            collection = get_or_create_collection()
            question = question.strip().lower()
            question_words = set(question.split())
            
            # Tìm kiếm với vector
            results = collection.query(
                query_texts=[question],
                n_results=10,  # Tăng số lượng kết quả để có nhiều lựa chọn hơn
                include=['documents', 'metadatas', 'distances']
            )
            
            formatted_results = []
            for doc, metadata, distance in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
                similarity_score = calculate_semantic_score(distance, question_words, metadata)
                if similarity_score > MIN_SIMILARITY_THRESHOLD:
                    formatted_results.append({
                        'id': metadata['id'],
                        'ten_dia_diem': metadata['ten_dia_diem'],
                        'mo_ta': metadata['mo_ta'],
                        'similarity': round(similarity_score, 2)
                    })
            
            # Sắp xếp kết quả theo độ tương đồng
            formatted_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            if not formatted_results:
                return {
                    'status': 'error',
                    'message': 'No relevant locations found',
                    'results': []
                }, 404
            
            return {
                'status': 'success',
                'message': f'Found {len(formatted_results)} relevant locations',
                'results': formatted_results
            }, 200
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error during search: {str(e)}',
                'results': []
            }, 500
    
    def format_search_results(self, search_results):
        """Format kết quả tìm kiếm thành văn bản có cấu trúc"""
        formatted_text = []
        
        # Lọc kết quả có độ tương đồng cao
        high_similarity_results = [r for r in search_results if r['similarity'] > 0.7]
        
        if high_similarity_results:
            formatted_text.append("Dựa trên tìm kiếm của bạn, tôi tìm thấy những địa điểm phù hợp sau:")
            
            for result in high_similarity_results:
                formatted_text.append(f"\n- {result['ten_dia_diem']}")
                formatted_text.append(f"  {result['mo_ta']}")
        
        # Thêm các kết quả có độ tương đồng trung bình
        medium_similarity_results = [r for r in search_results if 0.5 <= r['similarity'] <= 0.7]
        if medium_similarity_results:
            formatted_text.append("\nNgoài ra, bạn có thể tham khảo thêm:")
            for result in medium_similarity_results:
                formatted_text.append(f"\n- {result['ten_dia_diem']}")
                formatted_text.append(f"  {result['mo_ta']}")
        
        return "\n".join(formatted_text) 