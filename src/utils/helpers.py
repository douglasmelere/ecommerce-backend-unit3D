from decimal import Decimal
from src.config import Config

def calculate_payment_fees(amount, payment_method):
    """Calculate payment fees based on method"""
    amount = Decimal(str(amount))
    
    if payment_method not in Config.TAX_RATES:
        raise ValueError(f"Unsupported payment method: {payment_method}")
    
    # Get tax rate and fixed fee
    tax_rate = Decimal(str(Config.TAX_RATES[payment_method]))
    fixed_fee = Decimal(str(Config.FIXED_FEES[payment_method])) / 100  # Convert cents to reais
    
    # Calculate percentage fee
    percentage_fee = amount * tax_rate
    
    # Total fee
    total_fee = percentage_fee + fixed_fee
    
    return {
        'percentage_fee': float(percentage_fee),
        'fixed_fee': float(fixed_fee),
        'total_fee': float(total_fee),
        'amount_with_fee': float(amount + total_fee),
        'tax_rate': float(tax_rate)
    }

def calculate_order_total(subtotal, payment_method, shipping_amount=0):
    """Calculate order total including fees"""
    subtotal = Decimal(str(subtotal))
    shipping_amount = Decimal(str(shipping_amount))
    
    # Calculate payment fees
    fee_info = calculate_payment_fees(subtotal, payment_method)
    
    # Total amount
    total_amount = subtotal + Decimal(str(fee_info['total_fee'])) + shipping_amount
    
    return {
        'subtotal': float(subtotal),
        'shipping_amount': float(shipping_amount),
        'tax_amount': fee_info['total_fee'],
        'total_amount': float(total_amount),
        'fee_breakdown': fee_info
    }

def format_currency(amount):
    """Format amount as Brazilian currency"""
    return f"R$ {amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def validate_cpf(cpf):
    """Validate Brazilian CPF"""
    # Remove non-numeric characters
    cpf = ''.join(filter(str.isdigit, cpf))
    
    # Check if has 11 digits
    if len(cpf) != 11:
        return False
    
    # Check if all digits are the same
    if cpf == cpf[0] * 11:
        return False
    
    # Validate first check digit
    sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digit1 = 11 - (sum1 % 11)
    if digit1 >= 10:
        digit1 = 0
    
    if int(cpf[9]) != digit1:
        return False
    
    # Validate second check digit
    sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digit2 = 11 - (sum2 % 11)
    if digit2 >= 10:
        digit2 = 0
    
    if int(cpf[10]) != digit2:
        return False
    
    return True

def validate_cep(cep):
    """Validate Brazilian CEP (postal code)"""
    # Remove non-numeric characters
    cep = ''.join(filter(str.isdigit, cep))
    
    # Check if has 8 digits
    return len(cep) == 8

def paginate_query(query, page=1, per_page=20):
    """Paginate SQLAlchemy query"""
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': page * per_page < total
    }

def generate_sku(category_name, brand=None, model=None):
    """Generate SKU for product"""
    import uuid
    
    # Create base from category
    base = category_name[:3].upper()
    
    if brand:
        base += f"-{brand[:3].upper()}"
    
    if model:
        base += f"-{model[:3].upper()}"
    
    # Add unique identifier
    unique_id = str(uuid.uuid4())[:8].upper()
    
    return f"{base}-{unique_id}"

