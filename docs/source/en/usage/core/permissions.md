# Permissions

The permission system is used to control user access to API endpoints and resources. SRF provides a flexible permission checking mechanism, supporting view-level and object-level permissions.

## Permission Basics

### BasePermission

All permission classes inherit from `BasePermission`, which defines two core methods:

```python
from srf.permission.permission import BasePermission

class BasePermission:
    """Base class for permissions"""
    
    def has_permission(self, request, view):
        """View-level permission check
        
        Args:
            request: Request object
            view: ViewSet instance
        
        Returns:
            bool: True if the user has permission, False otherwise
        """
        return True
    
    def has_object_permission(self, request, view, obj):
        """Object-level permission check
        
        Args:
            request: Request object
            view: ViewSet instance
            obj: The object being accessed
        
        Returns:
            bool: True if the user has permission, False otherwise
        """
        return True
```

### Permission Check Process

1. **View-level permission**: Check if the user has permission to access the endpoint before processing the request.
2. **Object-level permission**: Check if the user has permission to access the specific object after retrieving it.

## Built-in Permission Classes

### IsAuthenticated

Requires the user to be authenticated.

```python
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
```

**Implementation**:

```python
class IsAuthenticated(BasePermission):
    """Requires the user to be authenticated"""
    
    def has_permission(self, request, view):
        user = request.ctx.user if hasattr(request.ctx, 'user') else None
        return user is not None and user.is_active
```

**Use Cases**:
- User profiles
- Shopping carts
- Order management
- Favorites and comments

### IsRoleAdminUser

Requires the user to be in the admin role.

```python
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsRoleAdminUser)
```

**Implementation**:

```python
class IsRoleAdminUser(BasePermission):
    """Requires the user's role to be admin"""
    
    def has_permission(self, request, view):
        user = request.ctx.user if hasattr(request.ctx, 'user') else None
        if not user:
            return False
        
        role = user.role if hasattr(user, 'role') else None
        return role and role.name == 'admin'
```

**Use Cases**:
- Admin panel
- User management
- System configuration
- Data statistics

### IsSafeMethodOnly

Allows only safe HTTP methods (GET, HEAD, OPTIONS).

```python
from srf.permission.permission import IsSafeMethodOnly

class ProductViewSet(BaseViewSet):
    permission_classes = (IsSafeMethodOnly,)
```

**Implementation**:

```python
class IsSafeMethodOnly(BasePermission):
    """Allows only safe methods"""
    
    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
    
    def has_permission(self, request, view):
        return request.method in self.SAFE_METHODS
```

**Use Cases**:
- Public read-only APIs
- Documentation pages
- Product catalog (browse but not modify)

## Custom Permission Classes

### Simple Permissions

Create a custom permission class:

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

Use the custom permission:

```python
from permissions import IsOwner

class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
```

### Complex Permissions

Permissions based on roles and operation types:

```python
class ProductPermission(BasePermission):
    """Product permissions:
    - Everyone can view
    - Authenticated users can create
    - Admins can update and delete
    """
    
    def has_permission(self, request, view):
        # GET requests: accessible by everyone
        if request.method == 'GET':
            return True
        
        # POST requests: require authentication
        if request.method == 'POST':
            user = request.ctx.user if hasattr(request.ctx, 'user') else None
            return user is not None
        
        # PUT, PATCH, DELETE: require admin
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            user = request.ctx.user if hasattr(request.ctx, 'user') else None
            if not user:
                return False
            role = user.role if hasattr(user, 'role') else None
            return role and role.name == 'admin'
        
        return False
```

### Asynchronous Permission Checks

Permission classes support asynchronous methods:

```python
class IsProductOwner(BasePermission):
    """Check if the user is the creator of the product"""
    
    async def has_object_permission(self, request, view, obj):
        # Can perform asynchronous database queries
        creator = await obj.creator
        return creator.id == request.ctx.user.id
```

## Permission Composition

### Using Multiple Permission Classes

Permission classes are checked in order, and all must pass:

```python
class OrderViewSet(BaseViewSet):
    # Must satisfy both: authenticated and owner
    permission_classes = (IsAuthenticated, IsOwner)
```

### Conditional Permissions

Use different permissions based on the action:

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    def get_permissions(self):
        """Return different permission classes based on the action"""
        if self.action in ['update', 'destroy']:
            # Update and delete require admin permissions
            return [IsAuthenticated(), IsRoleAdminUser()]
        elif self.action == 'create':
            # Create requires authentication
            return [IsAuthenticated()]
        else:
            # List and detail don't require permissions
            return []
```

## Object-Level Permissions

Object-level permissions are checked after retrieving a specific object, used for fine-grained access control.

### Basic Usage

```python
class IsOwner(BasePermission):
    """Object-level permission: check if the user is the owner"""
    
    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.ctx.user.id

class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
    
    # Users can only view, modify, or delete their own orders
```

### Custom Object Permission Checks

Override the `check_object_permissions` method:

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    async def check_object_permissions(self, request, obj):
        """Custom object permission check"""
        # First perform the default permission check
        await super().check_object_permissions(request, obj)
        
        # Additional business logic checks
        user = self.get_current_user(request)
        
        # Check if the product is published
        if not obj.is_published and not user.is_staff:
            from sanic.exceptions import Forbidden
            raise Forbidden("Product not published")
        
        # Check regional restrictions
        if obj.region and obj.region != user.region:
            raise Forbidden("This product is not available in your region")
```

### Multi-condition Object Permissions

```python
class CommentPermission(BasePermission):
    """Comment permissions: owners or admins can modify/delete"""
    
    def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # Safe methods: accessible by everyone
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Modify/delete: owner or admin
        is_owner = obj.user_id == user.id
        is_admin = user.role and user.role.name == 'admin'
        
        return is_owner or is_admin
```

## Permission Examples

### Example 1: Blog Article Permissions

```python
class ArticlePermission(BasePermission):
    """Article permissions:
    - Everyone can view published articles
    - Authors can view/edit their own articles
    - Admins can manage all articles
    """
    
    def has_permission(self, request, view):
        # GET list: accessible by everyone
        if request.method == 'GET' and view.action == 'list':
            return True
        
        # Other operations require authentication
        return hasattr(request.ctx, 'user') and request.ctx.user is not None
    
    def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # Admins can manage all articles
        if user.role and user.role.name == 'admin':
            return True
        
        # GET request: published articles or author's own articles
        if request.method == 'GET':
            return obj.is_published or obj.author_id == user.id
        
        # Modify/delete: only the author
        return obj.author_id == user.id

class ArticleViewSet(BaseViewSet):
    permission_classes = (ArticlePermission,)
    
    @property
    def queryset(self):
        user = self.get_current_user(request)
        
        # Admins can see all articles
        if user and user.role and user.role.name == 'admin':
            return Article.all()
        
        # Regular users can only see published articles
        return Article.filter(is_published=True)
```

### Example 2: Order Permissions

```python
class OrderPermission(BasePermission):
    """Order permissions:
    - Users can only access their own orders
    - Admins can access all orders
    """
    
    def has_permission(self, request, view):
        # All operations require authentication
        return hasattr(request.ctx, 'user') and request.ctx.user is not None
    
    async def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # Admins can access all orders
        if user.role and user.role.name == 'admin':
            return True
        
        # Users can only access their own orders
        return obj.user_id == user.id

class OrderViewSet(BaseViewSet):
    permission_classes = (OrderPermission,)
    
    @property
    def queryset(self):
        user = self.get_current_user(request)
        
        # Admins can see all orders
        if user and user.role and user.role.name == 'admin':
            return Order.all()
        
        # Regular users can only see their own orders
        return Order.filter(user_id=user.id)
    
    @action(methods=["post"], detail=True, url_path="cancel")
    async def cancel_order(self, request, pk):
        """Cancel order"""
        order = await self.get_object(request, pk)
        
        # Additional business logic check
        if order.status != 'pending':
            from sanic.response import json
            return json({"error": "Only pending orders can be canceled"}, status=400)
        
        order.status = 'cancelled'
        await order.save()
        
        from sanic.response import json
        return json({"message": "Order canceled"})
```

### Example 3: Team Collaboration Permissions

```python
class TeamMemberPermission(BasePermission):
    """Team member permissions:
    - Team members can view
    - Team owners can modify
    """
    
    async def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # Check if the user is a team member
        is_member = await obj.members.filter(id=user.id).exists()
        
        # GET request: team members can access
        if request.method == 'GET':
            return is_member
        
        # Modify/delete: only team owner
        return obj.owner_id == user.id

class ProjectViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, TeamMemberPermission)
```

## Permission Error Handling

### Automatic Handling

SRF automatically handles failed permission checks:

- Not logged in: returns 401 Unauthorized
- Insufficient permissions: returns 403 Forbidden

### Custom Error Messages

```python
from sanic.exceptions import Forbidden

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.owner_id != request.ctx.user.id:
            raise Forbidden("You do not have permission to access this resource")
        return True
```

### Catching Permission Errors

```python
from sanic.exceptions import Forbidden, Unauthorized

@app.exception(Forbidden)
async def handle_forbidden(request, exception):
    from sanic.response import json
    return json({
        "error": "Insufficient permissions",
        "message": str(exception)
    }, status=403)

@app.exception(Unauthorized)
async def handle_unauthorized(request, exception):
    from sanic.response import json
    return json({
        "error": "Not logged in",
        "message": "Please log in first"
    }, status=401)
```

## Full Example

```python
# permissions.py
from srf.permission.permission import BasePermission

class IsOwnerOrAdmin(BasePermission):
    """Owner or admin permission"""
    
    async def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # Admin
        if user.role and user.role.name == 'admin':
            return True
        
        # Owner
        if hasattr(obj, 'owner_id'):
            return obj.owner_id == user.id
        if hasattr(obj, 'user_id'):
            return obj.user_id == user.id
        
        return False

class IsPublishedOrOwner(BasePermission):
    """Published or owner can access"""
    
    def has_object_permission(self, request, view, obj):
        # Published content is accessible to everyone
        if hasattr(obj, 'is_published') and obj.is_published:
            return True
        
        # Unpublished content is accessible only to the owner
        user = request.ctx.user
        if not user:
            return False
        
        return obj.user_id == user.id

# viewsets.py
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated
from permissions import IsOwnerOrAdmin, IsPublishedOrOwner

class ArticleViewSet(BaseViewSet):
    """Article ViewSet"""
    
    @property
    def queryset(self):
        return Article.all()
    
    def get_schema(self, request, is_safe=False):
        return ArticleSchemaReader if is_safe else ArticleSchemaWriter
    
    def get_permissions(self):
        """Return different permissions based on the action"""
        if self.action in ['list', 'retrieve']:
            # View: published or owner
            return [IsPublishedOrOwner()]
        elif self.action == 'create':
            # Create: requires authentication
            return [IsAuthenticated()]
        else:
            # Update/delete: owner or admin
            return [IsAuthenticated(), IsOwnerOrAdmin()]
```

## Best Practices

1. **Principle of Least Privilege**: Default deny access, explicitly grant necessary permissions.
2. **Separation of Concerns**: Keep permission logic isolated in permission classes.
3. **Compose Permissions**: Use multiple simple permission classes to implement complex permissions.
4. **Object-Level Permissions**: Use object-level permission checks for sensitive resources.
5. **Asynchronous Support**: Use asynchronous methods when performing database queries.
6. **Clear Error Messages**: Provide friendly permission error messages.
7. **Test Permissions**: Write unit tests for permission classes.

## Frequently Asked Questions

### How to skip permission checks for certain actions?

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    @action(methods=["get"], detail=False)
    async def public_list(self, request):
        """Public product list (skip permission checks)"""
        # Manually implemented, no permission check is triggered
        products = await Product.filter(is_public=True)
        # ...
```

### How to add specific permissions for custom actions?

```python
from srf.permission.permission import IsRoleAdminUser

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    @action(methods=["post"], detail=True)
    async def publish(self, request, pk):
        """Publish product (requires admin permissions)"""
        # Manually check admin permissions
        perm = IsRoleAdminUser()
        if not perm.has_permission(request, self):
            from sanic.exceptions import Forbidden
            raise Forbidden("Admin permissions required")
        
        # ...
```

## Next Steps

- Learn [Authentication](authentication.md) to understand user authentication
- Read [Views](viewsets.md) to learn how to use permissions in ViewSet
- View [Authentication Middleware](../advanced/middleware/auth-middleware.md) to understand the underlying mechanisms of permission checks