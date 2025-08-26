# E-commerce Backend API

Sistema completo de e-commerce para produtos de automação e elétrica, desenvolvido em Flask com integração ao Stripe para pagamentos.

## 🚀 Funcionalidades

- ✅ **Autenticação JWT** com roles (usuário/admin)
- ✅ **CRUD completo de produtos** (apenas admins)
- ✅ **Sistema de categorias** hierárquico
- ✅ **Carrinho de compras** persistente
- ✅ **Gestão de pedidos** com status
- ✅ **Integração com Stripe** (cartão, PIX, boleto)
- ✅ **Cálculo automático de taxas** por método de pagamento
- ✅ **Sistema de estoque** com controle automático
- ✅ **Painel administrativo** com analytics
- ✅ **Rate limiting** e segurança
- ✅ **CORS configurado** para frontend
- ✅ **Pronto para deploy** no Easypanel

## 🛠️ Tecnologias

- **Flask** - Framework web
- **SQLAlchemy** - ORM para banco de dados
- **Flask-JWT-Extended** - Autenticação JWT
- **Stripe** - Gateway de pagamento
- **Marshmallow** - Validação de dados
- **Flask-CORS** - Cross-origin requests
- **Flask-Limiter** - Rate limiting
- **bcrypt** - Hash de senhas

## 📦 Instalação

### Desenvolvimento Local

```bash
# Clone o repositório
git clone <repository-url>
cd ecommerce-backend

# Ative o ambiente virtual
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações

# Execute a aplicação
python src/main.py
```

### Deploy no Easypanel

1. **Conecte seu repositório** no Easypanel
2. **Configure as variáveis de ambiente**:
   ```
   FLASK_ENV=production
   SECRET_KEY=your-super-secret-key
   JWT_SECRET_KEY=your-jwt-secret-key
   STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
   STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
   DATABASE_URL=postgresql://user:password@host:port/database
   ```
3. **Deploy** - O Nixpacks detectará automaticamente o projeto Python

## 🔐 Autenticação

### Usuário Padrão Admin
- **Email**: `admin@ecommerce.com`
- **Senha**: `admin123`

### Endpoints de Autenticação

```http
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
GET  /api/auth/me
POST /api/auth/logout
```

## 📋 API Endpoints

### Produtos (Público)
```http
GET    /api/products              # Listar produtos com filtros
GET    /api/products/{id}         # Detalhes do produto
GET    /api/products/categories   # Listar categorias
```

### Produtos (Admin)
```http
POST   /api/products              # Criar produto
PUT    /api/products/{id}         # Atualizar produto
DELETE /api/products/{id}         # Deletar produto
POST   /api/products/categories   # Criar categoria
```

### Carrinho
```http
GET    /api/cart                  # Ver carrinho
POST   /api/cart/items            # Adicionar item
PUT    /api/cart/items/{id}       # Atualizar quantidade
DELETE /api/cart/items/{id}       # Remover item
DELETE /api/cart                  # Limpar carrinho
```

### Pedidos
```http
GET    /api/orders                # Listar pedidos do usuário
GET    /api/orders/{id}           # Detalhes do pedido
POST   /api/orders                # Criar pedido
POST   /api/orders/{id}/cancel    # Cancelar pedido
```

### Pagamentos
```http
GET    /api/payments/methods      # Métodos de pagamento
POST   /api/payments/create-intent # Criar payment intent
POST   /api/payments/confirm      # Confirmar pagamento
POST   /api/payments/webhook      # Webhook do Stripe
POST   /api/payments/refund       # Criar reembolso
```

### Admin
```http
GET    /api/admin/dashboard       # Estatísticas do dashboard
GET    /api/admin/users           # Listar usuários
POST   /api/admin/users           # Criar usuário
PUT    /api/admin/users/{id}      # Atualizar usuário
DELETE /api/admin/users/{id}      # Desativar usuário
GET    /api/admin/analytics       # Analytics detalhados
GET    /api/admin/orders/all      # Todos os pedidos
PUT    /api/admin/orders/{id}/status # Atualizar status
```

## 💳 Métodos de Pagamento

### Taxas Configuradas (Brasil)
- **Cartão de Crédito**: 3,4% + R$ 0,60
- **Cartão de Débito**: 2,9% + R$ 0,60
- **PIX**: 0,99%
- **Boleto**: R$ 3,49

### Configuração do Stripe

1. **Crie uma conta** no [Stripe](https://stripe.com)
2. **Configure os webhooks** para: `https://seu-dominio.com/api/payments/webhook`
3. **Eventos necessários**:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`

## 🗄️ Banco de Dados

### Modelos Principais

- **User** - Usuários do sistema
- **Product** - Produtos do catálogo
- **Category** - Categorias de produtos
- **Cart/CartItem** - Carrinho de compras
- **Order/OrderItem** - Pedidos
- **Roles** - USER, ADMIN

### Migração para Produção

Para produção, recomenda-se PostgreSQL:

```python
# No arquivo .env
DATABASE_URL=postgresql://user:password@host:port/database
```

## 🔒 Segurança

- **JWT Tokens** com expiração
- **Hash bcrypt** para senhas
- **Rate limiting** configurado
- **CORS** habilitado
- **Validação rigorosa** de dados
- **Logs de segurança**

## 📊 Recursos Administrativos

### Dashboard
- Estatísticas de vendas
- Produtos em baixo estoque
- Distribuição de status de pedidos
- Top produtos mais vendidos

### Analytics
- Vendas por período
- Performance por categoria
- Métodos de pagamento mais usados
- Relatórios personalizados

## 🧪 Testes

```bash
# Executar testes (quando implementados)
python -m pytest tests/

# Testar endpoints manualmente
curl -X GET http://localhost:5000/health
```

## 🚀 Deploy

### Easypanel (Recomendado)
1. Conecte o repositório
2. Configure variáveis de ambiente
3. Deploy automático com Nixpacks

### Docker
```bash
docker build -t ecommerce-backend .
docker run -p 5000:5000 ecommerce-backend
```

### Variáveis de Ambiente Obrigatórias

```env
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
STRIPE_SECRET_KEY=sk_live_your_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
DATABASE_URL=your-database-url
```

## 📝 Exemplos de Uso

### Criar Produto (Admin)
```json
POST /api/products
{
  "name": "Sensor de Proximidade",
  "description": "Sensor indutivo M18",
  "price": 89.90,
  "category_id": 5,
  "brand": "Sick",
  "model": "IM18-3008BPS-ZC1",
  "stock_quantity": 50,
  "sku": "SEN-SICK-001",
  "specifications": {
    "range": "8mm",
    "voltage": "10-30VDC",
    "output": "PNP"
  }
}
```

### Adicionar ao Carrinho
```json
POST /api/cart/items
{
  "product_id": 1,
  "quantity": 2
}
```

### Criar Pedido
```json
POST /api/orders
{
  "shipping_address": {
    "street": "Rua das Flores",
    "number": "123",
    "neighborhood": "Centro",
    "city": "São Paulo",
    "state": "SP",
    "zip_code": "01234567"
  },
  "payment_method": "credit_card"
}
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT.

## 📞 Suporte

Para dúvidas ou suporte, entre em contato através dos issues do GitHub.

---

**Desenvolvido com ❤️ para automação e elétrica**

