from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from src.models.user import db, User, UserRole
from src.models.product import Product, Category
from src.models.cart import Order, OrderStatus, PaymentStatus
from src.schemas.user_schema import AdminUserCreateSchema, UserResponseSchema
from src.utils.decorators import admin_required, handle_errors
from src.utils.helpers import paginate_query

admin_bp = Blueprint('admin', __name__)

# Schema instances
admin_user_create_schema = AdminUserCreateSchema()
user_response_schema = UserResponseSchema()

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
@handle_errors
def get_dashboard_stats():
    """Get dashboard statistics"""
    # Date ranges
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Total counts
    total_users = User.query.count()
    total_products = Product.query.filter_by(is_active=True).count()
    total_orders = Order.query.count()
    
    # Recent stats
    orders_today = Order.query.filter(func.date(Order.created_at) == today).count()
    orders_this_week = Order.query.filter(func.date(Order.created_at) >= week_ago).count()
    orders_this_month = Order.query.filter(func.date(Order.created_at) >= month_ago).count()
    
    # Revenue stats
    revenue_today = db.session.query(func.sum(Order.total_amount)).filter(
        func.date(Order.created_at) == today,
        Order.payment_status == PaymentStatus.COMPLETED
    ).scalar() or 0
    
    revenue_this_week = db.session.query(func.sum(Order.total_amount)).filter(
        func.date(Order.created_at) >= week_ago,
        Order.payment_status == PaymentStatus.COMPLETED
    ).scalar() or 0
    
    revenue_this_month = db.session.query(func.sum(Order.total_amount)).filter(
        func.date(Order.created_at) >= month_ago,
        Order.payment_status == PaymentStatus.COMPLETED
    ).scalar() or 0
    
    # Order status distribution
    order_status_stats = db.session.query(
        Order.status, func.count(Order.id)
    ).group_by(Order.status).all()
    
    # Payment status distribution
    payment_status_stats = db.session.query(
        Order.payment_status, func.count(Order.id)
    ).group_by(Order.payment_status).all()
    
    # Top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(Order.items.any()).label('total_sold')
    ).join(Order.items).filter(
        Order.payment_status == PaymentStatus.COMPLETED
    ).group_by(Product.id, Product.name).order_by(desc('total_sold')).limit(5).all()
    
    # Low stock products
    low_stock_products = Product.query.filter(
        Product.is_active == True,
        Product.stock_quantity <= 10
    ).order_by(Product.stock_quantity).limit(10).all()
    
    return jsonify({
        'totals': {
            'users': total_users,
            'products': total_products,
            'orders': total_orders
        },
        'orders': {
            'today': orders_today,
            'this_week': orders_this_week,
            'this_month': orders_this_month
        },
        'revenue': {
            'today': float(revenue_today),
            'this_week': float(revenue_this_week),
            'this_month': float(revenue_this_month)
        },
        'order_status_distribution': [
            {'status': status.value, 'count': count} 
            for status, count in order_status_stats
        ],
        'payment_status_distribution': [
            {'status': status.value, 'count': count} 
            for status, count in payment_status_stats
        ],
        'top_products': [
            {'name': name, 'total_sold': total_sold} 
            for name, total_sold in top_products
        ],
        'low_stock_products': [
            product.to_dict(include_stock=True) 
            for product in low_stock_products
        ]
    }), 200

@admin_bp.route('/users', methods=['GET'])
@admin_required
@handle_errors
def get_users():
    """Get all users"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Get filter parameters
    role = request.args.get('role')
    is_active = request.args.get('is_active')
    search = request.args.get('search')
    
    # Build query
    query = User.query
    
    if role:
        try:
            role_enum = UserRole(role)
            query = query.filter_by(role=role_enum)
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400
    
    if is_active is not None:
        is_active_bool = is_active.lower() == 'true'
        query = query.filter_by(is_active=is_active_bool)
    
    if search:
        query = query.filter(
            db.or_(
                User.email.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%')
            )
        )
    
    query = query.order_by(User.created_at.desc())
    
    # Paginate results
    result = paginate_query(query, page=page, per_page=per_page)
    
    return jsonify({
        'users': [user_response_schema.dump(user) for user in result['items']],
        'pagination': {
            'total': result['total'],
            'page': result['page'],
            'per_page': result['per_page'],
            'pages': result['pages'],
            'has_prev': result['has_prev'],
            'has_next': result['has_next']
        }
    }), 200

@admin_bp.route('/users', methods=['POST'])
@admin_required
@handle_errors
def create_user():
    """Create new user (Admin only)"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        # Validate input data
        data = admin_user_create_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    # Create new user
    user = User(
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone=data.get('phone'),
        role=data.get('role', UserRole.USER)
    )
    user.set_password(data['password'])
    
    try:
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user': user_response_schema.dump(user)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create user', 'details': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
@handle_errors
def update_user(user_id):
    """Update user (Admin only)"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    
    # Update allowed fields
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'phone' in data:
        user.phone = data['phone']
    if 'role' in data:
        try:
            user.role = UserRole(data['role'])
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400
    if 'is_active' in data:
        user.is_active = data['is_active']
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user_response_schema.dump(user)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update user', 'details': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
@handle_errors
def delete_user(user_id):
    """Deactivate user (Admin only)"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Don't allow deleting the current admin
    current_user_id = get_jwt_identity()
    if user_id == current_user_id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    try:
        # Soft delete - just deactivate
        user.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'User deactivated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to deactivate user', 'details': str(e)}), 500

@admin_bp.route('/analytics', methods=['GET'])
@admin_required
@handle_errors
def get_analytics():
    """Get detailed analytics"""
    # Date range parameters
    days = request.args.get('days', 30, type=int)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    # Daily sales data
    daily_sales = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('orders'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(
        func.date(Order.created_at) >= start_date,
        Order.payment_status == PaymentStatus.COMPLETED
    ).group_by(func.date(Order.created_at)).order_by('date').all()
    
    # Category performance
    category_performance = db.session.query(
        Category.name,
        func.count(Order.id).label('orders'),
        func.sum(Order.total_amount).label('revenue')
    ).join(Product).join(Order.items).join(Order).filter(
        func.date(Order.created_at) >= start_date,
        Order.payment_status == PaymentStatus.COMPLETED
    ).group_by(Category.id, Category.name).order_by(desc('revenue')).all()
    
    # Payment method distribution
    payment_methods = db.session.query(
        Order.payment_method,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(
        func.date(Order.created_at) >= start_date,
        Order.payment_status == PaymentStatus.COMPLETED
    ).group_by(Order.payment_method).all()
    
    return jsonify({
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'days': days
        },
        'daily_sales': [
            {
                'date': date.isoformat(),
                'orders': orders,
                'revenue': float(revenue or 0)
            }
            for date, orders, revenue in daily_sales
        ],
        'category_performance': [
            {
                'category': name,
                'orders': orders,
                'revenue': float(revenue or 0)
            }
            for name, orders, revenue in category_performance
        ],
        'payment_methods': [
            {
                'method': method,
                'count': count,
                'revenue': float(revenue or 0)
            }
            for method, count, revenue in payment_methods
        ]
    }), 200

