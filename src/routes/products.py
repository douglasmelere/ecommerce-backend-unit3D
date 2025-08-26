from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from src.models.user import db
from src.models.product import Product, Category
from src.schemas.product_schema import (
    ProductCreateSchema, ProductUpdateSchema, ProductResponseSchema, 
    ProductSearchSchema, CategorySchema
)
from src.utils.decorators import admin_required, handle_errors
from src.utils.helpers import paginate_query

products_bp = Blueprint('products', __name__)

# Schema instances
product_create_schema = ProductCreateSchema()
product_update_schema = ProductUpdateSchema()
product_response_schema = ProductResponseSchema()
product_search_schema = ProductSearchSchema()
category_schema = CategorySchema()

# Public routes
@products_bp.route('/', methods=['GET'])
@handle_errors
def get_products():
    """Get products with search and filters"""
    try:
        # Validate query parameters
        args = product_search_schema.load(request.args)
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    # Build query
    query = Product.search(
        query=args.get('query'),
        category_id=args.get('category_id'),
        brand=args.get('brand'),
        min_price=args.get('min_price'),
        max_price=args.get('max_price'),
        in_stock_only=args.get('in_stock_only', True)
    )
    
    # Order by featured first, then by name
    query = query.order_by(Product.is_featured.desc(), Product.name)
    
    # Paginate results
    result = paginate_query(
        query, 
        page=args.get('page', 1), 
        per_page=args.get('per_page', 20)
    )
    
    return jsonify({
        'products': [product_response_schema.dump(product) for product in result['items']],
        'pagination': {
            'total': result['total'],
            'page': result['page'],
            'per_page': result['per_page'],
            'pages': result['pages'],
            'has_prev': result['has_prev'],
            'has_next': result['has_next']
        }
    }), 200

@products_bp.route('/<int:product_id>', methods=['GET'])
@handle_errors
def get_product(product_id):
    """Get single product by ID"""
    product = Product.query.get(product_id)
    
    if not product or not product.is_active:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify({
        'product': product_response_schema.dump(product)
    }), 200

@products_bp.route('/categories', methods=['GET'])
@handle_errors
def get_categories():
    """Get all active categories"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    
    return jsonify({
        'categories': [category_schema.dump(category) for category in categories]
    }), 200

# Admin routes
@products_bp.route('/', methods=['POST'])
@admin_required
@handle_errors
def create_product():
    """Create new product (Admin only)"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        # Validate input data
        data = product_create_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    # Create new product
    product = Product(
        name=data['name'],
        description=data.get('description'),
        price=data['price'],
        category_id=data['category_id'],
        brand=data.get('brand'),
        model=data.get('model'),
        stock_quantity=data['stock_quantity'],
        sku=data['sku'],
        images=data.get('images', []),
        specifications=data.get('specifications', {}),
        is_active=data.get('is_active', True),
        is_featured=data.get('is_featured', False),
        meta_title=data.get('meta_title'),
        meta_description=data.get('meta_description')
    )
    
    try:
        db.session.add(product)
        db.session.commit()
        
        return jsonify({
            'message': 'Product created successfully',
            'product': product_response_schema.dump(product)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create product', 'details': str(e)}), 500

@products_bp.route('/<int:product_id>', methods=['PUT'])
@admin_required
@handle_errors
def update_product(product_id):
    """Update product (Admin only)"""
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        # Validate input data
        data = product_update_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    # Update product fields
    for field, value in data.items():
        if hasattr(product, field):
            setattr(product, field, value)
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Product updated successfully',
            'product': product_response_schema.dump(product)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update product', 'details': str(e)}), 500

@products_bp.route('/<int:product_id>', methods=['DELETE'])
@admin_required
@handle_errors
def delete_product(product_id):
    """Delete product (Admin only)"""
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    try:
        # Soft delete - just mark as inactive
        product.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Product deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete product', 'details': str(e)}), 500

@products_bp.route('/categories', methods=['POST'])
@admin_required
@handle_errors
def create_category():
    """Create new category (Admin only)"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        # Validate input data
        data = category_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    # Create new category
    category = Category(
        name=data['name'],
        description=data.get('description'),
        parent_id=data.get('parent_id'),
        is_active=data.get('is_active', True)
    )
    
    try:
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'message': 'Category created successfully',
            'category': category_schema.dump(category)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create category', 'details': str(e)}), 500

