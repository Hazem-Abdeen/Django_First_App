from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View
from decimal import Decimal
from django.shortcuts import redirect
from django.views.generic import DetailView, TemplateView, UpdateView, ListView

from .forms import ShippingAddressForm
from .models import Product, CartItem, Cart, Customer, Order, OrderItem
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import transaction
from .cart_utils import get_or_create_cart

class HomeView(ListView):
    model = Product
    template_name = "store/home.html"
    context_object_name = "products"

    def get_queryset(self):
        qs = Product.objects.all().order_by("-id")

        q = self.request.GET.get("q", "").strip()

        if q:
            qs = qs.filter(title__icontains=q)

        return qs

class ProductDetailView(DetailView):
    model = Product
    template_name = "store/product_detail.html"
    context_object_name = "product"
    pk_url_kwarg = "id"


class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Product
    pk_url_kwarg = "id"
    fields = ['title', 'description', 'unit_price', 'inventory']
    template_name = 'store/product_edit.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_success_url(self):
        return reverse("product-detail", kwargs={"id": self.object.id})

@method_decorator(require_POST, name="dispatch")
class CartAddView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        qty = request.POST.get("quantity", "1")
        try:
            qty = int(qty)
        except ValueError:
            qty = 1
        qty = max(qty, 1)

        cart = get_or_create_cart(request.user)

        try:
            item = CartItem.objects.get(cart=cart, product=product)
            created = False
        except CartItem.DoesNotExist:
            item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=qty
            )
            created = True

        return redirect("cart-detail")

class CartDetailView(LoginRequiredMixin, TemplateView):
    template_name = "store/cart_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_or_create_cart(self.request.user)
        items = cart.items.select_related("product").all()

        # keep your template variables compatible:
        lines = []
        total = Decimal("0.00")

        for item in items:
            qty = item.quantity
            price = item.product.unit_price
            line_total = price * qty
            total += line_total

            lines.append({
                "product": item.product,
                "quantity": qty,
                "price": price,
                "line_total": line_total,
                "item_id": item.id,  # useful for update/remove
            })

        context["lines"] = lines
        context["total"] = total
        return context

@method_decorator(require_POST, name="dispatch")
class CartClearView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request):
        cart = get_or_create_cart(request.user)
        cart.items.all().delete()
        return redirect("cart-detail")

@method_decorator(require_POST, name="dispatch")
class CartIncrementView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, product_id):
        cart = get_or_create_cart(request.user)
        product = get_object_or_404(Product, id=product_id)

        try:
            item = CartItem.objects.get(cart=cart, product=product)
        except CartItem.DoesNotExist:
            item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=1
            )
        else:
            item.quantity += 1
            item.save()

        return redirect("cart-detail")

@method_decorator(require_POST, name="dispatch")
class CartDecrementView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, product_id):
        cart = get_or_create_cart(request.user)

        item = CartItem.objects.filter(cart=cart, product_id=product_id).first()

        if item is not None:
            item.quantity = item.quantity - 1

            if item.quantity == 0:
                item.delete()
            else:
                item.save()

        return redirect("cart-detail")

@method_decorator(require_POST, name="dispatch")
class CartRemoveItemView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, product_id):
        cart = get_or_create_cart(request.user)
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
        return redirect("cart-detail")

@login_required
def checkout_address(request):
    cart = get_or_create_cart(request.user)

    if cart.status != Cart.Status.OPENED:
        raise Http404("This cart is not editable.")

    address = getattr(cart, "shipping_address", None)

    if request.method == "POST":
        form = ShippingAddressForm(request.POST, instance=address)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.cart = cart
            obj.save()
            return redirect("checkout-review")
    else:
        form = ShippingAddressForm(instance=address)

    return render(request, "store/checkout_address.html", {"form": form, "cart": cart})

@login_required
def checkout_review(request):
    cart = get_or_create_cart(request.user)

    # if cart.status != Cart.Status.OPENED:
    #     raise Http404("Cart is not editable.")

    # Must have shipping address first
    address = getattr(cart, "shipping_address", None)
    if not address:
        return redirect("checkout-address")

    items = cart.items.select_related("product")

    return render(request, "store/checkout_review.html", {
        "cart": cart,
        "items": items,
        "address": address,
    })

@require_POST
@login_required
@transaction.atomic
def place_order(request):
    cart = get_or_create_cart(request.user)

    # if cart.status != Cart.Status.OPENED:
    #     raise Http404("Cart is not editable.")
    #
    # if cart.total_items <= 0:
    #     return redirect("cart-detail")

    address = getattr(cart, "shipping_address", None)
    if not address:
        return redirect("checkout-address")

    # Get/Create Customer profile linked to this user
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={
            "first_name": request.user.first_name or "",
            "last_name": request.user.last_name or "",
            "email": request.user.email or f"user{request.user.id}@example.com",
            "phone": address.phone,
        }
    )

    # Create order
    order = Order.objects.create(customer=customer)

    # Copy items to OrderItem (snapshot unit_price now)
    items = cart.items.select_related("product")
    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.product.unit_price,
        )

    # Freeze cart
    cart.status = Cart.Status.FROZEN
    cart.save(update_fields=["status"])

    return redirect("checkout-success")

@login_required
def checkout_success(request):
    return render(request, "store/checkout_success.html")