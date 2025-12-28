from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import View
from .models import Product
from decimal import Decimal
from django.shortcuts import redirect
from django.views.generic import DetailView, TemplateView, UpdateView, ListView

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

class CartAddView(View):
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.POST.get("quantity", 1))

        cart = request.session.get("cart", {})
        pid = str(product.id)

        if pid in cart:
            cart[pid]["quantity"] += quantity
        else:
            cart[pid] = {
                "quantity": quantity,
                "price": str(product.unit_price),
            }

        request.session["cart"] = cart
        request.session.modified = True
        return redirect("cart-detail")

class CartDetailView(LoginRequiredMixin , TemplateView):
    template_name = "store/cart_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cart = self.request.session.get("cart", {})
        products = Product.objects.filter(id__in=cart.keys())

        lines = []
        total = Decimal("0.00")

        for product in products:
            item = cart[str(product.id)]
            qty = item["quantity"]
            price = Decimal(item["price"])
            line_total = qty * price
            total += line_total

            lines.append({
                "product": product,
                "quantity": qty,
                "price": price,
                "line_total": line_total,
            })

        context["lines"] = lines
        context["total"] = total
        return context

class CartClearView(View):
    def post(self, request):
        request.session.pop("cart", None)
        return redirect("cart-detail")


class CartIncrementView(View):
    def post(self, request, product_id):
        cart = request.session.get("cart", {})
        pid = str(product_id)

        # if item not in cart, treat it like add 1 (optional safety)
        if pid not in cart:
            product = get_object_or_404(Product, id=product_id)
            cart[pid] = {"quantity": 1, "price": str(product.unit_price)}
        else:
            cart[pid]["quantity"] += 1

        request.session["cart"] = cart
        request.session.modified = True
        return redirect("cart-detail")


class CartDecrementView(View):
    def post(self, request, product_id):
        cart = request.session.get("cart", {})
        pid = str(product_id)

        if pid in cart:
            cart[pid]["quantity"] -= 1

            # if quantity becomes 0 or less -> remove item
            if cart[pid]["quantity"] <= 0:
                del cart[pid]

        request.session["cart"] = cart
        request.session.modified = True
        return redirect("cart-detail")


class CartRemoveItemView(View):
    def post(self, request, product_id):
        cart = request.session.get("cart", {})
        pid = str(product_id)

        if pid in cart:
            del cart[pid]

        request.session["cart"] = cart
        request.session.modified = True
        return redirect("cart-detail")

class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Product
    pk_url_kwarg = "id"
    fields = ['title', 'description', 'unit_price', 'inventory']
    template_name = 'store/product_edit.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_success_url(self):
        return reverse("product-detail", kwargs={"id": self.object.id})

