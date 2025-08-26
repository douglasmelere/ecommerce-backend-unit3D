from marshmallow import Schema, fields, validate, validates, ValidationError
from src.models.product import Product, Category

class CategorySchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(required=False)
    parent_id = fields.Int(required=False, allow_none=True)
    is_active = fields.Bool(required=False, load_default=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class ProductCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(required=False)
    price = fields.Decimal(required=True, validate=validate.Range(min=0))
    category_id = fields.Int(required=True)
    brand = fields.Str(required=False, validate=validate.Length(max=100))
    model = fields.Str(required=False, validate=validate.Length(max=100))
    stock_quantity = fields.Int(required=True, validate=validate.Range(min=0))
    sku = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    images = fields.List(fields.Url(), required=False, load_default=list)
    specifications = fields.Dict(required=False, load_default=dict)
    is_active = fields.Bool(required=False, load_default=True)
    is_featured = fields.Bool(required=False, load_default=False)
    meta_title = fields.Str(required=False, validate=validate.Length(max=200))
    meta_description = fields.Str(required=False)

    @validates('sku')
    def validate_sku_unique(self, value):
        if Product.query.filter_by(sku=value).first():
            raise ValidationError('SKU already exists.')

    @validates('category_id')
    def validate_category_exists(self, value):
        if not Category.query.get(value):
            raise ValidationError('Category does not exist.')

class ProductUpdateSchema(Schema):
    name = fields.Str(required=False, validate=validate.Length(min=1, max=200))
    description = fields.Str(required=False)
    price = fields.Decimal(required=False, validate=validate.Range(min=0))
    category_id = fields.Int(required=False)
    brand = fields.Str(required=False, validate=validate.Length(max=100))
    model = fields.Str(required=False, validate=validate.Length(max=100))
    stock_quantity = fields.Int(required=False, validate=validate.Range(min=0))
    images = fields.List(fields.Url(), required=False)
    specifications = fields.Dict(required=False)
    is_active = fields.Bool(required=False)
    is_featured = fields.Bool(required=False)
    meta_title = fields.Str(required=False, validate=validate.Length(max=200))
    meta_description = fields.Str(required=False)

    @validates('category_id')
    def validate_category_exists(self, value):
        if value and not Category.query.get(value):
            raise ValidationError('Category does not exist.')

class ProductResponseSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    price = fields.Decimal()
    category_id = fields.Int()
    category = fields.Nested(CategorySchema)
    brand = fields.Str()
    model = fields.Str()
    stock_quantity = fields.Int()
    sku = fields.Str()
    images = fields.List(fields.Str())
    specifications = fields.Dict()
    is_active = fields.Bool()
    is_featured = fields.Bool()
    meta_title = fields.Str()
    meta_description = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class ProductSearchSchema(Schema):
    query = fields.Str(required=False)
    category_id = fields.Int(required=False)
    brand = fields.Str(required=False)
    min_price = fields.Decimal(required=False, validate=validate.Range(min=0))
    max_price = fields.Decimal(required=False, validate=validate.Range(min=0))
    in_stock_only = fields.Bool(required=False, load_default=True)
    page = fields.Int(required=False, load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(required=False, load_default=20, validate=validate.Range(min=1, max=100))

