from src.models.user import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Text

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(Text, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Self-referential relationship for subcategories
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy=True)
    products = db.relationship('Product', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    brand = db.Column(db.String(100), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # JSON fields for flexibility
    images = db.Column(JSON, nullable=True, default=list)  # List of image URLs
    specifications = db.Column(JSON, nullable=True, default=dict)  # Technical specs
    
    # Product status
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    
    # SEO fields
    meta_title = db.Column(db.String(200), nullable=True)
    meta_description = db.Column(Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cart_items = db.relationship('CartItem', backref='product', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def __repr__(self):
        return f'<Product {self.name}>'

    def is_in_stock(self, quantity=1):
        """Check if product has enough stock"""
        return self.stock_quantity >= quantity

    def reduce_stock(self, quantity):
        """Reduce stock quantity"""
        if self.is_in_stock(quantity):
            self.stock_quantity -= quantity
            return True
        return False

    def increase_stock(self, quantity):
        """Increase stock quantity"""
        self.stock_quantity += quantity

    def get_main_image(self):
        """Get main product image"""
        if self.images and len(self.images) > 0:
            return self.images[0]
        return None

    def to_dict(self, include_stock=False):
        """Convert product to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'category_id': self.category_id,
            'category': self.category.to_dict() if self.category else None,
            'brand': self.brand,
            'model': self.model,
            'sku': self.sku,
            'images': self.images or [],
            'specifications': self.specifications or {},
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_stock:
            data['stock_quantity'] = self.stock_quantity
            
        return data

    @staticmethod
    def search(query, category_id=None, brand=None, min_price=None, max_price=None, in_stock_only=True):
        """Search products with filters"""
        filters = [Product.is_active == True]
        
        if query:
            filters.append(
                db.or_(
                    Product.name.ilike(f'%{query}%'),
                    Product.description.ilike(f'%{query}%'),
                    Product.brand.ilike(f'%{query}%'),
                    Product.model.ilike(f'%{query}%')
                )
            )
        
        if category_id:
            filters.append(Product.category_id == category_id)
            
        if brand:
            filters.append(Product.brand.ilike(f'%{brand}%'))
            
        if min_price is not None:
            filters.append(Product.price >= min_price)
            
        if max_price is not None:
            filters.append(Product.price <= max_price)
            
        if in_stock_only:
            filters.append(Product.stock_quantity > 0)
        
        return Product.query.filter(*filters)

