from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

def get_or_create_wechat_user(openid):
    return User.objects.get_or_create(openid=openid, defaults={'user_type': 'wechat'})

def grant_admin_on_debug_code(code, user, debug):
    granted = False
    if debug and isinstance(code, str) and code.startswith('admin') and not user.is_staff:
        user.is_staff = True
        user.is_superuser = True
        user.user_type = 'admin'
        user.save(update_fields=['is_staff', 'is_superuser'])
        granted = True
    return granted

def update_last_login(user):
    user.last_login_at = timezone.now()
    user.save(update_fields=['last_login_at'])

def create_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh), str(refresh.access_token)

def bootstrap_or_init_admin(username, password):
    admin_qs = User.objects.filter(is_staff=True, is_superuser=True)
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None
    if user is None and not admin_qs.exists():
        user = User.objects.create_user(
            openid=f"bootstrap:{username}",
            username=username,
            password=password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        user.user_type = 'admin'
        user.save(update_fields=['user_type'])
        return user
    if user and (not user.has_usable_password()) and admin_qs.count() == 1:
        user.set_password(password)
        user.username = username
        user.save(update_fields=['password'])
        return user
    return None

def ensure_user_password(user, password):
    if not user.has_usable_password():
        user.set_password(password)
        user.save(update_fields=['password'])
