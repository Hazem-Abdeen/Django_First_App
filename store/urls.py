from django.urls import path
from . import views
from .views import (
    ProductDetailView,
    CartAddView,
    CartDetailView,
    CartClearView, HomeView, ProductUpdateView, CartDecrementView, CartIncrementView, CartRemoveItemView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("products/<int:id>/", ProductDetailView.as_view(), name="product-detail"),
    path("cart/", CartDetailView.as_view(), name="cart-detail"),
    path("cart/add/<int:product_id>/", CartAddView.as_view(), name="cart-add"),
    path("cart/increment/<int:product_id>/", CartIncrementView.as_view(), name="cart-increment"),
    path("cart/decrement/<int:product_id>/", CartDecrementView.as_view(), name="cart-decrement"),
    path("cart/remove/<int:product_id>/", CartRemoveItemView.as_view(), name="cart-remove"),
    path("cart/clear/", CartClearView.as_view(), name="cart-clear"),
    path("products/<int:id>/edit/", ProductUpdateView.as_view(), name="product-edit"),
    path("checkout/address/", views.checkout_address, name="checkout-address"),
    path("checkout/review/", views.checkout_review, name="checkout-review"),
    path("checkout/place-order/", views.place_order, name="place-order"),
    path("checkout/success/", views.checkout_success, name="checkout-success"),

]