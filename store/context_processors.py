from .cart_utils import get_or_create_cart

def cart_item_count(request):
    if request.user.is_authenticated:
        cart = get_or_create_cart(request.user)
        return {"cart_count": cart.total_items}
    return {"cart_count": 0}
