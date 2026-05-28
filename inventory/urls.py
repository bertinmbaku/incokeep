from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('product/new/', views.ProductCreateView.as_view(), name='product-create'),
    path('product/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product-edit'),
    path('product/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction-list'),
    path('transactions/new/', views.TransactionCreateView.as_view(), name='transaction-create'),
    path('manage/users/', views.UserListView.as_view(), name='user-list'),
    path('manage/users/<int:pk>/edit/', views.UserEditView.as_view(), name='user-edit'),
    path('manage/users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user-delete'),
]