# analyzer/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    # path('api/rag-response/', views.get_rag_response, name='get_rag_response'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
]