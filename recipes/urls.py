from django.urls import path
from .views import *

urlpatterns = [
    # path('register', register_template),
    path('home/',home),
    path('dashboard/',dashboard),
    path('api/register/', register_user_api, name='api_register'),
    path('api/login/', login_user_api, name='api_login'),
    path('api/login/refresh/', renew_access_token, name='refresh_login'),
    path('api/profile/', profile_view, name='api_profile')
]