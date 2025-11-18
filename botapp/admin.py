from django.contrib import admin
from .models import TelegramUser, Product, Order, OrderItem


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'email', 'phone', 'role', 'registered_at')
    list_filter = ('role',)
    search_fields = ('telegram_id', 'username', 'first_name', 'email', 'phone')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'size', 'material', 'color', 'price', 'stock')
    list_filter = ('size', 'material', 'color')
    search_fields = ('name', 'color')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    list_filter = ('created_at',)
    inlines = [OrderItemInline]
