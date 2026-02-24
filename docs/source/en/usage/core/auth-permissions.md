# Interface Permission Verification

This document explains how to use SRF's permission classes to control API access.

## Overview

Permission verification is an essential part of API security. SRF provides a flexible permission system to control who can access which resources.

## Built-in Permission Classes

### IsAuthenticated

Requires the user to be logged in.

```python
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    # All operations require login
```

**Examples**:
- User profile
- Shopping cart
- Order management
- Favorites and comments

**Testing**:

```bash
# Not logged in - returns 401
curl http://localhost:8000/api/products

# Logged in - returns data
curl http://localhost:8000/api/products \
  -H "Authorization: Bearer your-jwt-token"
```

### IsRoleAdminUser

Requires the user to be in an admin role.

```python
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsRoleAdminUser)
    
    # Only administrators can access
```

**Examples**:
- Backend management
- User management
- System configuration
- Data statistics

**Role check logic**:

```python
# Check if the user has an admin role
user = request.ctx.user
if user.role and user.role.name == 'admin':
    # Allow access
    pass
else:
    # Deny access
    raise Forbidden("Requires admin privileges")
```

### IsSafeMethodOnly

Allows only safe HTTP methods (GET, HEAD, OPTIONS).

```python
from srf.permission.permission import IsSafeMethodOnly

class ProductViewSet(BaseViewSet):
    permission_classes = (IsSafeMethodOnly,)
    
    # Can only read, not modify
```

**Examples**:
- Public read-only APIs
- Documentation pages
- Product catalog (browse but not modify)

**Allowed methods**:
- GET - Retrieve a resource
- HEAD - Retrieve resource header information
- OPTIONS - Retrieve supported methods

## Permission Combination

Multiple permission classes can be used simultaneously; all permissions must be passed:

```python
class OrderViewSet(BaseViewSet):
    # Must satisfy both: logged in AND admin
    permission_classes = (IsAuthenticated, IsRoleAdminUser)
```

### Check Order

Permissions are checked in the order they are defined:

1. `IsAuthenticated` - Check if logged in
2. `IsRoleAdminUser` - Check if admin
3. ...

If any permission check fails, it immediately returns 403 Forbidden.

## Different Permissions for Different Operations

### Method 1: Override get_permissions

```python
class ProductViewSet(BaseViewSet):
    def get_permissions(self):
        """Return different permission classes based on the action"""
        if self.action in ['list', 'retrieve']:
            # View: accessible by everyone
            return []
        elif self.action == 'create':
            # Create: requires login
            return [IsAuthenticated()]
        elif self.action in ['update', 'destroy']:
            # Update/Delete: requires admin
            return [IsAuthenticated(), IsRoleAdminUser()]
        else:
            return [IsAuthenticated()]
```

### Method 2: Check in the method

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    async def destroy(self, request, pk):
        """Delete (requires admin)"""
        # Additional permission check
        user = self.get_current_user(request)
        if not user.role or user.role.name != 'admin':
            from sanic.exceptions import Forbidden
            raise Forbidden("Requires admin privileges")
        
        # Execute deletion
        obj = await self.get_object(request, pk)
        await obj.delete()
        
        from sanic.response import json
        return json({}, status=204)
```

### Method 3: Use Decorators

```python
from srf.views.decorators import action
from srf.permission.permission import IsRoleAdminUser
from sanic.exceptions import Forbidden

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    @action(methods=["post"], detail=True, url_path="approve")
    async def approve(self, request, pk):
        """Approve product (only admin)"""
        # Check admin permission
        perm = IsRoleAdminUser()
        if not perm.has_permission(request, self):
            raise Forbidden("Requires admin privileges")
        
        product = await self.get_object(request, pk)
        product.is_approved = True
        await product.save()
        
        from sanic.response import json
        return json({"message": "Approved"})
```

## Custom Permission Classes

### Create a Permission Class

```python
from srf.permission.permission import BasePermission

class IsOwner(BasePermission):
    """Requires the user to be the owner of the resource"""
    
    def has_object_permission(self, request, view, obj):
        # Check if the object has an owner or user attribute
        if hasattr(obj, 'owner'):
            return obj.owner == request.ctx.user
        if hasattr(obj, 'user'):
            return obj.user == request.ctx.user
        return False
```

### Use Custom Permission

```python
from permissions import IsOwner

class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
    
    # Users can only access their own orders
```

### Advanced Permission Class

```python
class IsOwnerOrAdmin(BasePermission):
    """Owners or admins can access"""
    
    def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # Admins can access
        if user.role and user.role.name == 'admin':
            return True
        
        # Owners can access
        if hasattr(obj, 'user_id'):
            return obj.user_id == user.id
        
        return False
```

## Object-Level Permissions

Object-level permissions are checked after retrieving specific objects.

### Basic Usage

```python
class IsOwner(BasePermission):
    """Object-level permission: check if the owner"""
    
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.ctx.user.id

class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
    
    # Users can only view, modify, delete their own orders
```

### Custom Check Logic

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    async def check_object_permissions(self, request, obj):
        """Custom object permission check"""
        # First perform default permission checks
        await super().check_object_permissions(request, obj)
        
        user = self.get_current_user(request)
        
        # Check if the product is published
        if not obj.is_published and not user.is_staff:
            from sanic.exceptions import Forbidden
            raise Forbidden("Product is not published")
        
        # Check regional restrictions
        if obj.region and obj.region != user.region:
            from sanic.exceptions import Forbidden
            raise Forbidden("This product is not available in your region")
```

## Permission Check Process

### View-Level Permissions

Checked before processing the request:

```python
1. Request arrives at ViewSet
   ↓
2. Call check_permissions(request)
   ↓
3. Iterate through permission_classes
   ↓
4. Call has_permission() of each permission class
   ↓
5. All permissions pass → continue processing
   Any permission fails → return 403
```

### Object-Level Permissions

Checked after retrieving the object:

```python
1. Call get_object(request, pk)
   ↓
2. Retrieve the object from the database
   ↓
3. Call check_object_permissions(request, obj)
   ↓
4. Iterate through permission_classes
   ↓
5. Call has_object_permission() of each permission class
   ↓
6. All permissions pass → return the object
   Any permission fails → return 403
```

## Complete Example

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser, BasePermission
from sanic.response import json
from sanic.exceptions import Forbidden
from models import Article
from schemas import ArticleSchemaReader, ArticleSchemaWriter

# Custom permission class
class IsAuthorOrReadOnly(BasePermission):
    """Authors can edit, others can only read"""
    
    def has_permission(self, request, view):
        # GET requests are allowed for everyone
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Other requests require login
        return hasattr(request.ctx, 'user') and request.ctx.user is not None
    
    def has_object_permission(self, request, view, obj):
        # GET requests are allowed for everyone
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Modify and delete require author or admin
        user = request.ctx.user
        is_author = obj.author_id == user.id
        is_admin = user.role and user.role.name == 'admin'
        
        return is_author or is_admin

class ArticleViewSet(BaseViewSet):
    """Article ViewSet - Permission example"""
    
    permission_classes = (IsAuthorOrReadOnly,)
    
    @property
    def queryset(self):
        user = self.get_current_user(request)
        
        # Administrators can see all articles
        if user and user.role and user.role.name == 'admin':
            return Article.all()
        
        # Regular users can only see published articles and their own
        if user:
            from tortoise.expressions import Q
            return Article.filter(
                Q(is_published=True) | Q(author_id=user.id)
            )
        
        # Unauthenticated users can only see published articles
        return Article.filter(is_published=True)
    
    def get_schema(self, request, is_safe=False):
        return ArticleSchemaReader if is_safe else ArticleSchemaWriter
    
    async def perform_create(self, request, schema):
        """Automatically set the author when creating an article"""
        user = self.get_current_user(request)
        data = schema.dict()
        data['author_id'] = user.id
        
        article = await Article.create(**data)
        return article
    
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """Publish an article (author or admin)"""
        article = await self.get_object(request, pk)
        
        # Already checked by IsAuthorOrReadOnly, this is additional logic
        if article.is_published:
            return json({"error": "Article already published"}, status=400)
        
        article.is_published = True
        await article.save()
        
        return json({"message": "Article published"})
    
    @action(methods=["post"], detail=False, url_path="bulk-publish")
    async def bulk_publish(self, request):
        """Bulk publish (only admin)"""
        # Check admin permissions
        user = self.get_current_user(request)
        if not user.role or user.role.name != 'admin':
            raise Forbidden("Requires admin privileges")
        
        ids = request.json.get("ids", [])
        await Article.filter(id__in=ids).update(is_published=True)
        
        return json({"message": f"Successfully published {len(ids)} articles"})
```

## Relationship Between Permissions and Authentication

- **Authentication**: Verifies "Who you are"
- **Permissions**: Verifies "What you can do"

```python
# Authentication: Verify user identity
@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)  # Set request.ctx.user

# Permissions: Verify if the user can access
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)  # Check permissions
```

## Best Practices

1. **Principle of Least Privilege**: Default deny access, grant only necessary permissions explicitly
2. **Separation of Concerns**: Keep permission logic in separate permission classes
3. **Clear Error Messages**: Provide friendly permission error messages
4. **Object-Level Permissions**: Use object-level permission checks for sensitive resources
5. **Test Permissions**: Write unit tests for permission classes
6. **Document**: Document permission requirements in API documentation

## Common Issues

### How to Skip Permission Checks?

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    @action(methods=["get"], detail=False)
    async def public_list(self, request):
        """Public list (skip permission checks)"""
        # Manually implement, does not trigger permission checks
        products = await Product.filter(is_public=True)
        # ...
```

### How to Set Permissions for Specific User Roles?

```python
class HasRole(BasePermission):
    """Check if the user has a specified role"""
    
    def __init__(self, *roles):
        self.roles = roles
    
    def has_permission(self, request, view):
        user = request.ctx.user if hasattr(request.ctx, 'user') else None
        if not user:
            return False
        
        return user.role and user.role.name in self.roles

# Usage
class AdminViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, HasRole('admin', 'moderator'))
```

## Next Steps

- Learn [Authentication](authentication.md) to understand user authentication
- Read [Permission Details](permissions.md) to understand the complete permission system
- View [Authentication Middleware](../advanced/middleware/auth-middleware.md) to understand the underlying mechanism