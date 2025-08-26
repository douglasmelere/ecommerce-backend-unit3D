from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from src.models.user import db
from src.models.cart import Order, PaymentStatus
from src.schemas.order_schema import PaymentIntentSchema, ConfirmPaymentSchema
from src.services.payment_service import PaymentService
from src.utils.decorators import auth_required, handle_errors

payments_bp = Blueprint('payments', __name__)

# Schema instances
payment_intent_schema = PaymentIntentSchema()
confirm_payment_schema = ConfirmPaymentSchema()

@payments_bp.route('/methods', methods=['GET'])
@handle_errors
def get_payment_methods():
    """Get available payment methods"""
    methods = PaymentService.get_payment_methods()
    
    return jsonify({
        'payment_methods': methods
    }), 200

@payments_bp.route('/create-intent', methods=['POST'])
@auth_required
@handle_errors
def create_payment_intent():
    """Create payment intent"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        # Validate input data
        data = payment_intent_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    current_user_id = get_jwt_identity()
    
    # Get order
    order = Order.query.filter_by(
        id=data['order_id'], 
        user_id=current_user_id
    ).first()
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    if order.payment_status != PaymentStatus.PENDING:
        return jsonify({'error': 'Order payment is not pending'}), 400
    
    try:
        # Create payment intent
        intent_data = PaymentService.create_payment_intent(
            order=order,
            payment_method=data['payment_method']
        )
        
        # Update order with payment intent ID
        order.stripe_payment_intent_id = intent_data['payment_intent_id']
        order.payment_method = data['payment_method']
        
        # Update order totals with fees
        order.tax_amount = intent_data['fee_breakdown']['total_fee']
        order.total_amount = intent_data['amount']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment intent created successfully',
            'client_secret': intent_data['client_secret'],
            'payment_intent_id': intent_data['payment_intent_id'],
            'amount': intent_data['amount'],
            'fee_breakdown': intent_data['fee_breakdown']
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create payment intent', 'details': str(e)}), 500

@payments_bp.route('/confirm', methods=['POST'])
@auth_required
@handle_errors
def confirm_payment():
    """Confirm payment"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        # Validate input data
        data = confirm_payment_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    
    current_user_id = get_jwt_identity()
    
    # Get order by payment intent ID
    order = Order.query.filter_by(
        stripe_payment_intent_id=data['payment_intent_id'],
        user_id=current_user_id
    ).first()
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    try:
        # Confirm payment with Stripe
        payment_result = PaymentService.confirm_payment(
            payment_intent_id=data['payment_intent_id'],
            payment_method_id=data.get('payment_method_id')
        )
        
        # Update order payment status based on Stripe response
        if payment_result['status'] == 'succeeded':
            order.payment_status = PaymentStatus.COMPLETED
        elif payment_result['status'] == 'requires_action':
            # Payment requires additional action (3D Secure, etc.)
            return jsonify({
                'requires_action': True,
                'payment_intent_id': data['payment_intent_id'],
                'status': payment_result['status']
            }), 200
        else:
            order.payment_status = PaymentStatus.FAILED
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment processed successfully',
            'status': payment_result['status'],
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Payment confirmation failed', 'details': str(e)}), 500

@payments_bp.route('/webhook', methods=['POST'])
@handle_errors
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    signature = request.headers.get('Stripe-Signature')
    
    try:
        # Verify webhook signature
        event = PaymentService.handle_webhook(payload, signature)
        
        # Handle different event types
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            
            # Find order by payment intent ID
            order = Order.query.filter_by(
                stripe_payment_intent_id=payment_intent['id']
            ).first()
            
            if order:
                order.payment_status = PaymentStatus.COMPLETED
                db.session.commit()
        
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            
            # Find order by payment intent ID
            order = Order.query.filter_by(
                stripe_payment_intent_id=payment_intent['id']
            ).first()
            
            if order:
                order.payment_status = PaymentStatus.FAILED
                db.session.commit()
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        return jsonify({'error': 'Webhook processing failed', 'details': str(e)}), 400

@payments_bp.route('/refund', methods=['POST'])
@auth_required
@handle_errors
def create_refund():
    """Create refund for order"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    order_id = data.get('order_id')
    amount = data.get('amount')  # Optional partial refund
    reason = data.get('reason')
    
    if not order_id:
        return jsonify({'error': 'Order ID is required'}), 400
    
    current_user_id = get_jwt_identity()
    
    # Get order
    order = Order.query.filter_by(
        id=order_id,
        user_id=current_user_id
    ).first()
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    if order.payment_status != PaymentStatus.COMPLETED:
        return jsonify({'error': 'Order payment is not completed'}), 400
    
    if not order.stripe_payment_intent_id:
        return jsonify({'error': 'No payment intent found for this order'}), 400
    
    try:
        # Create refund with Stripe
        refund_result = PaymentService.create_refund(
            payment_intent_id=order.stripe_payment_intent_id,
            amount=amount,
            reason=reason
        )
        
        # Update order payment status
        if amount and amount < float(order.total_amount):
            order.payment_status = PaymentStatus.PARTIALLY_REFUNDED
        else:
            order.payment_status = PaymentStatus.REFUNDED
        
        db.session.commit()
        
        return jsonify({
            'message': 'Refund created successfully',
            'refund_id': refund_result['refund_id'],
            'status': refund_result['status'],
            'amount': refund_result['amount'],
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Refund creation failed', 'details': str(e)}), 500

