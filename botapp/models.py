from django.db import models

class TelegramUser(models.Model):
    class Role(models.TextChoices):
        USER = 'USER', 'User'
        ADMIN = 'ADMIN', 'Admin'
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super admin'

    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.telegram_id} ({self.username or self.first_name or 'no name'})"


class Product(models.Model):
    SIZES = [
        ('38-40', '38–40'),
        ('41-43', '41–43'),
        ('44-46', '44–46'),
    ]

    MATERIALS = [
        ('cotton', 'Хлопок'),
        ('wool', 'Шерсть'),
        ('synthetic', 'Синтетика'),
    ]

    name = models.CharField(max_length=255, default='Носки')
    size = models.CharField(max_length=20, choices=SIZES)
    material = models.CharField(max_length=20, choices=MATERIALS)
    color = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} {self.size} {self.material} {self.color}"


class Order(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} for {self.user.telegram_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product} x{self.quantity}"
