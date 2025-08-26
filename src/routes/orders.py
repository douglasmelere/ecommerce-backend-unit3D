from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from src.models.user import db
from src.models.cart import Cart, Order, OrderItem, OrderStatus, PaymentStatus
from src.schemas.order_schema import CreateOrderSchema, OrderResponseSchema
from src.utils.decorators import auth_required, admin_required, handle_errors
from src.utils.helpers import paginate_query, calculate_order_total

orders_bp = Blueprint('orders', __name__)

# Schema instances
create_order_schema = CreateOrderSchema()
order_response_schema = OrderResponseSchema()

@orders_bp.route('/', methods=['GET'])
@auth_required
@handle_errors
def get_user_orders():
    """Get user's orders"""
    current_user_id = get_jwt_identity()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Query user's orders
    query = Order.query.filter_by(user_id=current_user_id).order_by(Order.created_at.desc())
    
    # Paginate results
    result = paginate_query(query, page=page, per_page=per_page)
    
    return jsonify({
        'orders': [order.to_dict() for order in result['items']],
        'pagination': {
            'total': result['total'],
            'page': result['page'],
            'per_page': result['per_page'],
            'pages': result['pages'],
            'has_prev': result['has_prev'],
            'has_next': result['has_next']
        }
    }), 200

@orders_bp.route('/<int:order_id>', methods=['GET'])
@auth_required
@handle_errors
def get_order(order_id):
    """Get order details"""
    current_user_id = get_jwt_identity()
    
    order = Order.query.filter_by(id=order_id, user_id=current_user_id).first()
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    return jsonify({
        'order': order.to_dict()
    }), 200

@orders_bp.route('/', methods=['POST'])
@auth_required
@handle_errors
def create_order():
    """Create order from cart"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        # Validate input data
        data = create_order_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    current_user_id = get_jwt_identity()
    
    # Get user's cart
    cart = Cart.query.filter_by(user_id=current_user_id).first()
    
    if not cart or not cart.items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Check stock availability for all items
    for item in cart.items:
        if not item.product.is_in_stock(item.quantity):
            return jsonify({
                'error': f'Insufficient stock for product: {item.product.name}'
            }), 400
    
    # Calculate order totals
    subtotal = cart.get_total()
    total_info = calculate_order_total(
        subtotal=subtotal,
        payment_method=data['payment_method'],
        shipping_amount=0  # Free shipping for now
    )
    
    # Create order
    order = Order(
        user_id=current_user_id,
        order_number=Order.generate_order_number(),
        subtotal=subtotal,
        tax_amount=total_info['tax_amount'],
        shipping_amount=total_info['shipping_amount'],
        total_amount=total_info['total_amount'],
        payment_method=data['payment_method'],
        shipping_address=data['shipping_address'],
        billing_address=data.get('billing_address', data['shipping_address']),
        notes=data.get('notes')
    )
    
    try:
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create order items and reduce stock
        for cart_item in cart.items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price_at_time=cart_item.price_at_time,
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku,
                product_image=cart_item.product.get_main_image()
            )
            db.session.add(order_item)
            
            # Reduce stock
            cart_item.product.reduce_stock(cart_item.quantity)
        
        # Clear cart
        cart.clear()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order created successfully',
            'order': order.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create order', 'details': str(e)}), 500

@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@auth_required
@handle_errors
def cancel_order(order_id):
    """Cancel order"""
    current_user_id = get_jwt_identity()
    
    order = Order.query.filter_by(id=order_id, user_id=current_user_id).first()
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    if not order.can_be_cancelled():
        return jsonify({'error': 'Order cannot be cancelled'}), 400
    
    try:
        order.cancel()
        db.session.commit()
        
        return jsonify({
            'message': 'Order cancelled successfully',
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel order', 'details': str(e)}), 500

# Admin routes
@orders_bp.route('/admin/all', methods=['GET'])
@admin_required
@handle_errors
def get_all_orders():
    """Get all orders (Admin only)"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Get filter parameters
    status = request.args.get('status')
    payment_status = request.args.get('payment_status')
    
    # Build query
    query = Order.query
    
    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.filter_by(status=status_enum)
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400
    
    if payment_status:
        try:
            payment_status_enum = PaymentStatus(payment_status)
            query = query.filter_by(payment_status=payment_status_enum)
        except ValueError:
            return jsonify({'error': 'Invalid payment status'}), 400
    
    query = query.order_by(Order.created_at.desc())
    
    # Paginate results
    result = paginate_query(query, page=page, per_page=per_page)
    
    return jsonify({
        'orders': [order.to_dict() for order in result['items']],
        'pagination': {
            'total': result['total'],
            'page': result['page'],
            'per_page': result['per_page'],
            'pages': result['pages'],
            'has_prev': result['has_prev'],
            'has_next': result['has_next']
        }
    }), 200

@orders_bp.route('/admin/<int:order_id>/status', methods=['PUT'])
@admin_required
@handle_errors
def update_order_status(order_id):
    """Update order status (Admin only)"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    try:
        status_enum = OrderStatus(new_status)
        order.status = status_enum
        
        # Update timestamps
        if status_enum == OrderStatus.SHIPPED:
            from datetime import datetime
            order.shipped_at = datetime.utcnow()
        elif status_enum == OrderStatus.DELIVERED:
            from datetime import datetime
            order.delivered_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order status updated successfully',
            'order': order.to_dict()
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update order status', 'details': str(e)}), 500

