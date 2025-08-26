from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from src.models.user import db
from src.models.cart import Cart, CartItem
from src.models.product import Product
from src.schemas.order_schema import AddToCartSchema, UpdateCartItemSchema, CartResponseSchema
from src.utils.decorators import auth_required, handle_errors

cart_bp = Blueprint('cart', __name__)

# Schema instances
add_to_cart_schema = AddToCartSchema()
update_cart_item_schema = UpdateCartItemSchema()
cart_response_schema = CartResponseSchema()

def get_or_create_cart(user_id):
    """Get or create cart for user"""
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    return cart

@cart_bp.route('/', methods=['GET'])
@auth_required
@handle_errors
def get_cart():
    """Get user's cart"""
    current_user_id = get_jwt_identity()
    cart = get_or_create_cart(current_user_id)
    
    return jsonify({
        'cart': cart.to_dict()
    }), 200

@cart_bp.route('/items', methods=['POST'])
@auth_required
@handle_errors
def add_to_cart():
    """Add item to cart"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        # Validate input data
        data = add_to_cart_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    current_user_id = get_jwt_identity()
    cart = get_or_create_cart(current_user_id)
    
    # Get product
    product = Product.query.get(data['product_id'])
    if not product or not product.is_active:
        return jsonify({'error': 'Product not found or inactive'}), 404
    
    # Check stock availability
    if not product.is_in_stock(data['quantity']):
        return jsonify({'error': 'Insufficient stock'}), 400
    
    # Check if item already exists in cart
    existing_item = CartItem.query.filter_by(
        cart_id=cart.id, 
        product_id=data['product_id']
    ).first()
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item.quantity + data['quantity']
        if not product.is_in_stock(new_quantity):
            return jsonify({'error': 'Insufficient stock for requested quantity'}), 400
        
        existing_item.quantity = new_quantity
    else:
        # Create new cart item
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=data['product_id'],
            quantity=data['quantity'],
            price_at_time=product.price
        )
        db.session.add(cart_item)
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Item added to cart successfully',
            'cart': cart.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to add item to cart', 'details': str(e)}), 500

@cart_bp.route('/items/<int:item_id>', methods=['PUT'])
@auth_required
@handle_errors
def update_cart_item(item_id):
    """Update cart item quantity"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        # Validate input data
        data = update_cart_item_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    current_user_id = get_jwt_identity()
    
    # Get cart item
    cart_item = CartItem.query.join(Cart).filter(
        CartItem.id == item_id,
        Cart.user_id == current_user_id
    ).first()
    
    if not cart_item:
        return jsonify({'error': 'Cart item not found'}), 404
    
    # Check stock availability
    if not cart_item.product.is_in_stock(data['quantity']):
        return jsonify({'error': 'Insufficient stock'}), 400
    
    # Update quantity
    cart_item.quantity = data['quantity']
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Cart item updated successfully',
            'cart': cart_item.cart.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update cart item', 'details': str(e)}), 500

@cart_bp.route('/items/<int:item_id>', methods=['DELETE'])
@auth_required
@handle_errors
def remove_cart_item(item_id):
    """Remove item from cart"""
    current_user_id = get_jwt_identity()
    
    # Get cart item
    cart_item = CartItem.query.join(Cart).filter(
        CartItem.id == item_id,
        Cart.user_id == current_user_id
    ).first()
    
    if not cart_item:
        return jsonify({'error': 'Cart item not found'}), 404
    
    cart = cart_item.cart
    
    try:
        db.session.delete(cart_item)
        db.session.commit()
        
        return jsonify({
            'message': 'Item removed from cart successfully',
            'cart': cart.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to remove item from cart', 'details': str(e)}), 500

@cart_bp.route('/', methods=['DELETE'])
@auth_required
@handle_errors
def clear_cart():
    """Clear all items from cart"""
    current_user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=current_user_id).first()
    
    if not cart:
        return jsonify({'message': 'Cart is already empty'}), 200
    
    try:
        cart.clear()
        db.session.commit()
        
        return jsonify({
            'message': 'Cart cleared successfully',
            'cart': cart.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to clear cart', 'details': str(e)}), 500

