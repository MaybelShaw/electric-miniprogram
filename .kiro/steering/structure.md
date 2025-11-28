# Project Structure & Conventions

## Repository Layout

```
electric-miniprogram/
├── backend/           # Django REST API
├── frontend/          # Taro mini-program (user-facing)
├── merchant/          # React admin dashboard
└── docs/             # Documentation files
```

## Backend Structure (`backend/`)

**Django App Organization**
- `users/` - User authentication, profiles, addresses
- `catalog/` - Products, categories, brands, search
- `orders/` - Orders, cart, payments, discounts
- `integrations/` - Third-party APIs (Haier, YLH)
- `common/` - Shared utilities, permissions, pagination

**Key Patterns**
- Models in `models.py` - Database schema with Django ORM
- Views in `views.py` - DRF ViewSets for API endpoints
- Serializers in `serializers.py` - Data validation and transformation
- Services in `services.py` - Business logic layer
- URLs in `urls.py` - Route configuration

**Settings Structure**
```
backend/settings/
├── base.py          # Shared settings
├── development.py   # Dev overrides
├── production.py    # Production overrides
└── env_config.py    # Environment detection
```

**Naming Conventions**
- Models: PascalCase (e.g., `Product`, `OrderStatusHistory`)
- Functions/methods: snake_case (e.g., `get_queryset`, `create_order`)
- Constants: UPPER_SNAKE_CASE (e.g., `STATUS_CHOICES`)
- Files: snake_case (e.g., `state_machine.py`)

## Frontend Structure (`frontend/src/`)

**Directory Organization**
- `pages/` - Page components (one folder per page)
- `components/` - Reusable UI components
- `services/` - API service layer
- `utils/` - Helper functions (request, storage, format)
- `types/` - TypeScript type definitions
- `config/` - Environment configuration

**Page Structure Pattern**
```
pages/product-detail/
├── index.tsx        # Component logic
├── index.scss       # Styles
└── index.config.ts  # Page config (optional)
```

**Naming Conventions**
- Components: PascalCase (e.g., `ProductCard`)
- Files: kebab-case (e.g., `product-detail/`)
- Functions: camelCase (e.g., `getProducts`)
- Types/Interfaces: PascalCase (e.g., `Product`, `ProductListResponse`)

**API Service Pattern**
```typescript
export const productService = {
  async getProducts(params) {
    return http.get('/products/', params, false)
  }
}
```

## Merchant Admin Structure (`merchant/src/`)

**Directory Organization**
- `pages/` - Page components (Products, Orders, Users, etc.)
- `components/` - Shared components (Layout, ImageUpload)
- `services/` - API service layer (`api.ts`)
- `utils/` - Utilities (request, auth, image)

**Component Pattern**
- Use Ant Design Pro Components (`ProTable`, `ModalForm`, etc.)
- Functional components with hooks
- TypeScript for type safety

**Naming Conventions**
- Components: PascalCase (e.g., `Products`, `ImageUpload`)
- Files: PascalCase for components (e.g., `Products/index.tsx`)
- Functions: camelCase (e.g., `getProducts`, `handleEdit`)

## Code Style Guidelines

### Python (Backend)

**Imports Order**
1. Standard library
2. Third-party packages
3. Django imports
4. Local app imports

**Docstrings**
```python
def create_order(user, product, quantity):
    """
    Create a new order for the user.
    
    Args:
        user: User instance
        product: Product instance
        quantity: Order quantity
        
    Returns:
        Order: Created order instance
    """
```

**Type Hints** - Use where helpful but not required

### TypeScript (Frontend/Admin)

**Imports Order**
1. React/framework imports
2. Third-party libraries
3. Local components
4. Services/utils
5. Types
6. Styles

**Type Definitions**
```typescript
interface Product {
  id: number
  name: string
  price: number
  // ...
}
```

## API Conventions

**URL Patterns**
- List: `GET /api/products/`
- Detail: `GET /api/products/{id}/`
- Create: `POST /api/products/`
- Update: `PUT/PATCH /api/products/{id}/`
- Delete: `DELETE /api/products/{id}/`
- Custom actions: `POST /api/products/{id}/sync_haier_stock/`

**Response Format**
```json
// List responses
{
  "results": [...],
  "total": 100,
  "page": 1,
  "total_pages": 10,
  "has_next": true,
  "has_previous": false
}

// Detail/Create responses
{
  "id": 1,
  "name": "Product Name",
  ...
}

// Error responses
{
  "detail": "Error message",
  "code": "error_code"
}
```

**Authentication**
- JWT Bearer tokens in `Authorization` header
- Format: `Bearer <access_token>`

## Database Conventions

**Model Fields**
- Primary keys: `id = models.BigAutoField(primary_key=True)`
- Timestamps: `created_at`, `updated_at` (auto_now_add, auto_now)
- Foreign keys: Use `related_name` for reverse relations
- Choices: Define as class constants with `_CHOICES` suffix

**Indexes**
- Add indexes for frequently queried fields
- Use composite indexes for common filter combinations
- Example: `models.Index(fields=['category', 'is_active'])`

**Migrations**
- Always create migrations after model changes
- Review migration files before committing
- Use descriptive migration names when possible

## File Upload Handling

**Backend**
- Store in `media/images/YYYY/MM/DD/` structure
- Use UUID-based filenames for security
- Validate file types and sizes
- Store URLs in JSONField for multiple images

**Frontend**
- Use `ImageUpload` component in admin
- Immediate upload on selection (edit mode)
- Store URLs in form state

## Permission Patterns

**Backend Permission Classes**
- `IsAdminOrReadOnly` - Public read, admin write
- `IsOwnerOrAdmin` - Owner or admin access
- `IsAdmin` - Admin only
- `IsAuthenticated` - Requires login

**Usage**
```python
class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
```

## State Management

**Backend (Orders)**
- Use state machine pattern (`orders/state_machine.py`)
- Track state transitions in `OrderStatusHistory`
- Validate state changes before applying

**Frontend**
- Use Taro's built-in state (useState, useEffect)
- Store auth tokens in local storage
- No global state library needed for current scope

## Testing Approach

**Backend**
- Unit tests for models and services
- API tests for endpoints
- Run with `python manage.py test`

**Frontend**
- Manual testing via mini-program dev tools
- Focus on user flows and edge cases

## Common Patterns

**Pagination**
- Backend: Use DRF pagination classes
- Frontend: Handle `page` and `page_size` params
- Response includes metadata (total, has_next, etc.)

**Search & Filtering**
- Use query parameters for filters
- Backend: `ProductSearchService` for complex search
- Support multiple filter combinations

**Error Handling**
- Backend: Use DRF exception handlers
- Frontend: Show user-friendly toast messages
- Log errors for debugging

## Integration Points

**Haier API**
- Located in `backend/integrations/haierapi.py`
- Products marked with `source='haier'`
- Sync methods on Product model
- Track sync in `HaierSyncLog`

**WeChat Mini-Program**
- Auth flow: code → openid → JWT
- Payment integration via WeChat Pay API
- Store openid in User model
