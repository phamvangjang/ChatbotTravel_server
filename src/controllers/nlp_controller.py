from flask_restx import Namespace, Resource, fields, reqparse
from flask import request
from src.nlp_model.process_diadiem import process_diadiem
import os
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
import json
import math
import openai
from datetime import datetime

# Khởi tạo namespace
nlp_ns = Namespace('nlp', description='NLP operations for travel recommendations')

# Định nghĩa parser cho pagination
pagination_parser = reqparse.RequestParser()
pagination_parser.add_argument('page', type=int, default=1, help='Page number (starts from 1)')
pagination_parser.add_argument('limit', type=int, default=10, help='Number of items per page')
pagination_parser.add_argument('sort_by', type=str, default='id', help='Field to sort by')
pagination_parser.add_argument('sort_order', type=str, default='asc', help='Sort order (asc/desc)')

# Định nghĩa model cho request/response
question_model = nlp_ns.model('Question', {
    'question': fields.String(required=True, description='User question about travel in Ho Chi Minh City')
})

answer_model = nlp_ns.model('Answer', {
    'id': fields.String(description='Location ID'),
    'ten_dia_diem': fields.String(description='Location name'),
    'mo_ta': fields.String(description='Location description'),
    'similarity': fields.Float(description='Similarity score (0-1)')
})

search_response_model = nlp_ns.model('SearchResponse', {
    'status': fields.String(description='Status of the search operation'),
    'message': fields.String(description='Detailed message about the search operation'),
    'results': fields.List(fields.Nested(answer_model), description='Search results')
})

sync_response_model = nlp_ns.model('SyncResponse', {
    'status': fields.String(description='Status of the sync operation'),
    'message': fields.String(description='Detailed message about the sync operation'),
    'processed_count': fields.Integer(description='Number of locations processed')
})

# Model cho response của embeddings
embedding_model = nlp_ns.model('Embedding', {
    'id': fields.String(description='Location ID'),
    'embedding': fields.List(fields.Float, description='Vector embedding'),
    'document': fields.String(description='Original document text')
})

embeddings_response_model = nlp_ns.model('EmbeddingsResponse', {
    'status': fields.String(description='Status of the operation'),
    'message': fields.String(description='Detailed message'),
    'total': fields.Integer(description='Total number of embeddings'),
    'total_pages': fields.Integer(description='Total number of pages'),
    'current_page': fields.Integer(description='Current page number'),
    'items_per_page': fields.Integer(description='Number of items per page'),
    'embeddings': fields.List(fields.Nested(embedding_model), description='List of embeddings')
})

# Model cho response của metadata
metadata_model = nlp_ns.model('Metadata', {
    'id': fields.String(description='Location ID'),
    'ten_dia_diem': fields.String(description='Location name'),
    'mo_ta': fields.String(description='Location description'),
    'additional_info': fields.Raw(description='Additional metadata information')
})

metadata_response_model = nlp_ns.model('MetadataResponse', {
    'status': fields.String(description='Status of the operation'),
    'message': fields.String(description='Detailed message'),
    'total': fields.Integer(description='Total number of metadata entries'),
    'total_pages': fields.Integer(description='Total number of pages'),
    'current_page': fields.Integer(description='Current page number'),
    'items_per_page': fields.Integer(description='Number of items per page'),
    'metadata': fields.List(fields.Nested(metadata_model), description='List of metadata entries')
})

# Khởi tạo ChromaDB client
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
chroma_client = chromadb.PersistentClient(path=os.path.join(workspace_root, 'src', 'nlp_model', 'data', 'chroma_db'))

# Sử dụng sentence-transformers làm embedding function
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="keepitreal/vietnamese-sbert"
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
        'tu_khoa': 0.2,  # Từ khóa có trọng số cao nhất
        'loai_dia_diem': 0.15,
        'khu_vuc': 0.15,
        'dia_chi': 0.1,
        'thoi_gian_hoat_dong': 0.1,
        'gia_ve': 0.1
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

@nlp_ns.route('/search')
class SearchLocation(Resource):
    @nlp_ns.expect(question_model)
    @nlp_ns.marshal_with(search_response_model)
    def post(self):
        """Search for travel locations based on user question"""
        try:
            # Lấy câu hỏi từ request
            data = request.get_json()
            question = data.get('question')
            
            if not question:
                return {
                    'status': 'error',
                    'message': 'Question is required',
                    'results': []
                }, 400
            
            # Kiểm tra và lấy collection
            try:
                collection = get_or_create_collection()
            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'Error accessing collection. Please run sync first: {str(e)}',
                    'results': []
                }, 500
            
            # Kiểm tra collection có dữ liệu không
            try:
                count = collection.count()
                if count == 0:
                    return {
                        'status': 'error',
                        'message': 'No data in collection. Please run sync first.',
                        'results': []
                    }, 404
            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'Error checking collection data: {str(e)}',
                    'results': []
                }, 500
            
            # Chuẩn hóa câu hỏi
            question = question.strip().lower()
            question_words = set(question.split())
            
            # Thực hiện tìm kiếm
            results = collection.query(
                query_texts=[question],
                n_results=5,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format kết quả
            formatted_results = []
            for i, (doc, metadata, distance) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
                # Tính điểm tương đồng
                similarity_score = calculate_semantic_score(distance, question_words, metadata)
                
                # Chỉ thêm kết quả nếu điểm similarity > ngưỡng tối thiểu
                if similarity_score > MIN_SIMILARITY_THRESHOLD:
                    formatted_results.append({
                        'id': metadata['id'],
                        'ten_dia_diem': metadata['ten_dia_diem'],
                        'mo_ta': metadata['mo_ta'],
                        'similarity': round(similarity_score, 2)  # Làm tròn đến 2 chữ số thập phân
                    })
            
            # Sắp xếp kết quả theo similarity giảm dần
            formatted_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Giới hạn số lượng kết quả trả về
            formatted_results = formatted_results[:5]
            
            if not formatted_results:
                return {
                    'status': 'error',
                    'message': 'No relevant locations found for your question',
                    'results': []
                }, 404
            
            return {
                'status': 'success',
                'message': f'Found {len(formatted_results)} relevant locations',
                'results': formatted_results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error during search: {str(e)}',
                'results': []
            }, 500

@nlp_ns.route('/embeddings')
class GetEmbeddings(Resource):
    @nlp_ns.expect(pagination_parser)
    @nlp_ns.marshal_with(embeddings_response_model)
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

@nlp_ns.route('/metadata')
class GetMetadata(Resource):
    @nlp_ns.expect(pagination_parser)
    @nlp_ns.marshal_with(metadata_response_model)
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

@nlp_ns.route('/sync-diadiem')
class SyncDiadiem(Resource):
    @nlp_ns.marshal_with(sync_response_model)
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

@nlp_ns.route('/chat')
class ChatResponse(Resource):
    @nlp_ns.expect(question_model)
    @nlp_ns.marshal_with(nlp_ns.model('ChatResponse', {
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