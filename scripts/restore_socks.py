#!/usr/bin/env python3
# restore_socks.py - safely create/update sock products with correct Unicode
import os, sys
from decimal import Decimal
sys.path.insert(0, r'E:/tgshop_bot/tgshop')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tgshop.settings')
import django
django.setup()
from botapp.models import Product

products = [
    {'size':'41-43','material':'cotton','color':'black','price':'2000.00','stock':49},
    {'size':'38-40','material':'cotton','color':'white','price':'1500.00','stock':10},
    {'size':'41-43','material':'wool','color':'black','price':'2500.00','stock':5},
]

for it in products:
    p, created = Product.objects.update_or_create(
        size=it['size'], material=it['material'], color=it['color'],
        defaults={'name': 'Носки', 'price': Decimal(it['price']), 'stock': it['stock']}
    )
    print(('CREATED' if created else 'UPDATED'), p.id, p.name, p.size, p.get_material_display(), p.color, p.price, p.stock)

print('--- FINAL LIST ---')
for p in Product.objects.all().order_by('id'):
    print(p.id, p.name, p.size, p.get_material_display(), p.color, p.price, p.stock)
