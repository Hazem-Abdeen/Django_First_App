from django.shortcuts import render, get_object_or_404
from django.views import View
from .models import Product
from decimal import Decimal
from django.shortcuts import redirect
from django.views.generic import DetailView, TemplateView


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

class CartDetailView(TemplateView):
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
