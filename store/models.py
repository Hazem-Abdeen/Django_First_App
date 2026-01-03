from django.db import models
from django.conf import settings
from django.db.models import Q

class Product(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField()
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    inventory = models.IntegerField()
    last_update = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)


class Customer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
        null=True,
        blank=True,
    )

    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=255)
    birthday = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'store_customers'
        indexes = [models.Index(fields=['last_name', 'first_name'])]


class Order(models.Model):
    PENDING = 'p'
    COMPLETE = 'c'
    FAILED = 'f'

    PAYMENT_STATUS_CHOICES = [
        (PENDING, 'pending'),
        (COMPLETE, 'complete'),
        (FAILED, 'failed'),
    ]

    payment_status = models.CharField(
        max_length=1,
        choices=PAYMENT_STATUS_CHOICES,
        default=PENDING
    )
    placed_at = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Status(models.TextChoices):
        OPENED = "OPENED", "Opened"
        FROZEN = "FROZEN", "Frozen"

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPENED,
        db_index=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="OPENED"),
                name="unique_opened_cart_per_user",
            )
        ]

    def __str__(self):
        return f"Cart({self.user})"

    @property
    def total_items(self):
        total = 0

        for item in self.items.all():
            total = total + item.quantity

        return total

    @property
    def subtotal(self):
        total = 0

        for item in self.items.select_related("product"):
            price = item.product.unit_price
            quantity = item.quantity
            total = total + (price * quantity)

        return total

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey("Product", on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_product")
        ]

    @property
    def line_total(self):
        return self.product.unit_price * self.quantity

class ShippingAddress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shipping_addresses"
    )

    cart = models.OneToOneField(   # one shipping address per cart
        Cart,
        on_delete=models.CASCADE,
        related_name="shipping_address"
    )

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)

    country = models.CharField(max_length=100, default="Jordan")
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100, blank=True)
    street = models.CharField(max_length=255)
    building = models.CharField(max_length=50, blank=True)
    apartment = models.CharField(max_length=50, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ShippingAddress({self.user}) for Cart({self.cart_id})"
