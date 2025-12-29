from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from decimal import Decimal
from django.shortcuts import redirect
from django.views.generic import DetailView, TemplateView, UpdateView, ListView
from .models import Product, CartItem
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

        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart, product=product,
            defaults={"quantity": qty}
        )
        if not created:
            item.quantity += qty
            item.save(update_fields=["quantity"])

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

        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart, product=product,
            defaults={"quantity": 1}
        )
        if not created:
            item.quantity += 1
            item.save(update_fields=["quantity"])

        return redirect("cart-detail")

@method_decorator(require_POST, name="dispatch")
class CartDecrementView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, product_id):
        cart = get_or_create_cart(request.user)

        item = CartItem.objects.select_for_update().filter(
            cart=cart, product_id=product_id
        ).first()

        if item:
            item.quantity -= 1
            if item.quantity <= 0:
                item.delete()
            else:
                item.save(update_fields=["quantity"])

        return redirect("cart-detail")

@method_decorator(require_POST, name="dispatch")
class CartRemoveItemView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, product_id):
        cart = get_or_create_cart(request.user)
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
        return redirect("cart-detail")