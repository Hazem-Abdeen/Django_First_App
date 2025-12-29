from store.models import Cart

def get_or_create_cart(user):
    try:
        cart = Cart.objects.get(user=user)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=user)

    return cart
