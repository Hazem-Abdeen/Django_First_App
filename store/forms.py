from django import forms
from .models import ShippingAddress

class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = [
            "full_name", "phone",
            "country", "city", "area", "street",
            "building", "apartment", "postal_code",
            "notes"
        ]
