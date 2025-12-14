from django.urls import path
from .views import (
    ProductDetailView,
    CartAddView,
    CartDetailView,
    CartClearView,
)

urlpatterns = [
    path("products/<int:id>/", ProductDetailView.as_view(), name="product-detail"),
    path("cart/", CartDetailView.as_view(), name="cart-detail"),
    path("cart/add/<int:product_id>/", CartAddView.as_view(), name="cart-add"),
    path("cart/clear/", CartClearView.as_view(), name="cart-clear"),
]