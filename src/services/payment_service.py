import stripe
from decimal import Decimal
from src.config import Config
from src.utils.helpers import calculate_order_total

# Configure Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

class PaymentService:
    
    @staticmethod
    def create_payment_intent(order, payment_method):
        """Create Stripe payment intent"""
        try:
            # Calculate total with fees
            total_info = calculate_order_total(
                subtotal=order.subtotal,
                payment_method=payment_method,
                shipping_amount=order.shipping_amount
            )
            
            # Convert to cents (Stripe uses cents)
            amount_cents = int(total_info['total_amount'] * 100)
            
            # Payment method configuration
            payment_method_types = ['card']
            if payment_method == 'pix':
                payment_method_types = ['pix']
            elif payment_method == 'boleto':
                payment_method_types = ['boleto']
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='brl',
                payment_method_types=payment_method_types,
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'user_id': order.user_id,
                    'payment_method': payment_method
                },
                automatic_payment_methods={
                    'enabled': True
                } if payment_method == 'credit_card' else None
            )
            
            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'amount': total_info['total_amount'],
                'fee_breakdown': total_info['fee_breakdown']
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
        except Exception as e:
            raise Exception(f"Payment intent creation failed: {str(e)}")
    
    @staticmethod
    def confirm_payment(payment_intent_id, payment_method_id=None):
        """Confirm payment intent"""
        try:
            if payment_method_id:
                # For card payments
                intent = stripe.PaymentIntent.confirm(
                    payment_intent_id,
                    payment_method=payment_method_id
                )
            else:
                # For other payment methods
                intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                'status': intent.status,
                'payment_intent_id': intent.id,
                'amount_received': intent.amount_received / 100 if intent.amount_received else 0
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
        except Exception as e:
            raise Exception(f"Payment confirmation failed: {str(e)}")
    
    @staticmethod
    def handle_webhook(payload, signature):
        """Handle Stripe webhook"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, Config.STRIPE_WEBHOOK_SECRET
            )
            
            return event
            
        except ValueError:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise Exception("Invalid signature")
    
    @staticmethod
    def create_refund(payment_intent_id, amount=None, reason=None):
        """Create refund for payment"""
        try:
            refund_data = {
                'payment_intent': payment_intent_id
            }
            
            if amount:
                refund_data['amount'] = int(amount * 100)  # Convert to cents
            
            if reason:
                refund_data['reason'] = reason
            
            refund = stripe.Refund.create(**refund_data)
            
            return {
                'refund_id': refund.id,
                'status': refund.status,
                'amount': refund.amount / 100
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
        except Exception as e:
            raise Exception(f"Refund creation failed: {str(e)}")
    
    @staticmethod
    def get_payment_methods():
        """Get available payment methods with fees"""
        return {
            'credit_card': {
                'name': 'Cartão de Crédito',
                'tax_rate': Config.TAX_RATES['credit_card'],
                'fixed_fee': Config.FIXED_FEES['credit_card'] / 100,
                'description': 'Pagamento com cartão de crédito'
            },
            'debit_card': {
                'name': 'Cartão de Débito',
                'tax_rate': Config.TAX_RATES['debit_card'],
                'fixed_fee': Config.FIXED_FEES['debit_card'] / 100,
                'description': 'Pagamento com cartão de débito'
            },
            'pix': {
                'name': 'PIX',
                'tax_rate': Config.TAX_RATES['pix'],
                'fixed_fee': Config.FIXED_FEES['pix'] / 100,
                'description': 'Pagamento instantâneo via PIX'
            },
            'boleto': {
                'name': 'Boleto Bancário',
                'tax_rate': Config.TAX_RATES['boleto'],
                'fixed_fee': Config.FIXED_FEES['boleto'] / 100,
                'description': 'Pagamento via boleto bancário'
            }
        }

