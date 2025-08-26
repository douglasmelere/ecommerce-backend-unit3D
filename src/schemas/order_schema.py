from marshmallow import Schema, fields, validate, validates, ValidationError
from src.models.cart import OrderStatus, PaymentStatus
from src.models.product import Product

class AddToCartSchema(Schema):
    product_id = fields.Int(required=True)
    quantity = fields.Int(required=True, validate=validate.Range(min=1))

    @validates('product_id')
    def validate_product_exists(self, value):
        product = Product.query.get(value)
        if not product:
            raise ValidationError('Product does not exist.')
        if not product.is_active:
            raise ValidationError('Product is not available.')

class UpdateCartItemSchema(Schema):
    quantity = fields.Int(required=True, validate=validate.Range(min=1))

class AddressSchema(Schema):
    street = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    number = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    complement = fields.Str(required=False, validate=validate.Length(max=100))
    neighborhood = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    city = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    state = fields.Str(required=True, validate=validate.Length(min=2, max=2))
    zip_code = fields.Str(required=True, validate=validate.Length(min=8, max=9))
    country = fields.Str(required=False, load_default='BR', validate=validate.Length(min=2, max=2))

class CreateOrderSchema(Schema):
    shipping_address = fields.Nested(AddressSchema, required=True)
    billing_address = fields.Nested(AddressSchema, required=False)
    payment_method = fields.Str(required=True, validate=validate.OneOf(['credit_card', 'debit_card', 'pix', 'boleto']))
    notes = fields.Str(required=False)

class OrderResponseSchema(Schema):
    id = fields.Int()
    user_id = fields.Int()
    order_number = fields.Str()
    status = fields.Str()
    payment_status = fields.Str()
    subtotal = fields.Decimal()
    tax_amount = fields.Decimal()
    shipping_amount = fields.Decimal()
    total_amount = fields.Decimal()
    payment_method = fields.Str()
    shipping_address = fields.Dict()
    billing_address = fields.Dict()
    notes = fields.Str()
    items = fields.List(fields.Dict())
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    shipped_at = fields.DateTime()
    delivered_at = fields.DateTime()

class UpdateOrderStatusSchema(Schema):
    status = fields.Enum(OrderStatus, required=True)

class CartResponseSchema(Schema):
    id = fields.Int()
    user_id = fields.Int()
    items = fields.List(fields.Dict())
    total = fields.Decimal()
    items_count = fields.Int()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class PaymentIntentSchema(Schema):
    order_id = fields.Int(required=True)
    payment_method = fields.Str(required=True, validate=validate.OneOf(['credit_card', 'debit_card', 'pix', 'boleto']))

class ConfirmPaymentSchema(Schema):
    payment_intent_id = fields.Str(required=True)
    payment_method_id = fields.Str(required=False)  # For card payments

