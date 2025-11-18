# botapp/telegram_bot.py

from decimal import Decimal, InvalidOperation

from django.conf import settings

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)

from .models import TelegramUser, Product, Order, OrderItem

ASK_EMAIL, ASK_PHONE = range(2)


def get_or_create_telegram_user(update: Update) -> TelegramUser:
    tg_user = update.effective_user

    user, _ = TelegramUser.objects.get_or_create(
        telegram_id=tg_user.id,
        defaults={
            'username': tg_user.username,
            'first_name': tg_user.first_name,
        }
    )

    changed = False
    if user.username != tg_user.username:
        user.username = tg_user.username
        changed = True
    if user.first_name != tg_user.first_name:
        user.first_name = tg_user.first_name
        changed = True
    if changed:
        user.save()

    return user


def is_admin(user: TelegramUser) -> bool:
    return user.role in (TelegramUser.Role.ADMIN, TelegramUser.Role.SUPER_ADMIN)


def is_super_admin(user: TelegramUser) -> bool:
    return user.role == TelegramUser.Role.SUPER_ADMIN


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton('/catalog')],
        [KeyboardButton('/my_orders')],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton('/catalog')],
        [KeyboardButton('/my_orders')],
        [KeyboardButton('/add_socks'), KeyboardButton('/list_orders')],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def start(update: Update, context: CallbackContext):
    user = get_or_create_telegram_user(update)

    if not user.email:
        update.message.reply_text('Привет! Давай зарегистрируемся.\nОтправь, пожалуйста, свой email.')
        return ASK_EMAIL

    if not user.phone:
        update.message.reply_text('Спасибо! Теперь отправь номер телефона.')
        return ASK_PHONE

    keyboard = admin_menu_keyboard() if is_admin(user) else main_menu_keyboard()
    update.message.reply_text('С возвращением! Вот меню:', reply_markup=keyboard)
    return ConversationHandler.END


def ask_email(update: Update, context: CallbackContext):
    email = update.message.text.strip()
    user = get_or_create_telegram_user(update)
    user.email = email
    user.save()

    update.message.reply_text('Отлично, теперь отправь номер телефона.')
    return ASK_PHONE


def ask_phone(update: Update, context: CallbackContext):
    phone = update.message.text.strip()
    user = get_or_create_telegram_user(update)
    user.phone = phone
    user.save()

    keyboard = admin_menu_keyboard() if is_admin(user) else main_menu_keyboard()
    update.message.reply_text('Регистрация завершена! Пользуйся меню ниже.', reply_markup=keyboard)
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Регистрация отменена.')
    return ConversationHandler.END


def help_command(update: Update, context: CallbackContext):
    user = get_or_create_telegram_user(update)

    text = [
        'Доступные команды:',
        '/start - начать заново',
        '/catalog - каталог носков',
        '/buy <id> - добавить носки в корзину',
        '/my_orders - мои заказы',
        '/help - помощь',
    ]

    if is_admin(user):
        text += [
            '',
            'Команды админа:',
            '/add_socks <size> <material> <color> <price> <stock>',
            '/list_orders - список всех заказов',
        ]

    if is_super_admin(user):
        text += [
            '',
            'Команды супер-админа:',
            '/promote_user <telegram_id> <role>',
        ]

    update.message.reply_text('\n'.join(text))


def catalog(update: Update, context: CallbackContext):
    get_or_create_telegram_user(update)

    args = context.args
    products = Product.objects.filter(stock__gt=0)

    if len(args) >= 1:
        size = args[0]
        products = products.filter(size=size)

    if len(args) >= 2:
        material = args[1]
        products = products.filter(material=material)

    if not products.exists():
        update.message.reply_text('Подходящих носков не найдено 😢')
        return

    lines = ['Каталог носков:\n']
    for p in products:
        lines.append(
            f'ID: {p.id}\n'
            f'{p.name}, размер {p.size}, {p.get_material_display()}, цвет {p.color}\n'
            f'Цена: {p.price} ₸, на складе: {p.stock}\n'
            f'Добавить в корзину: /buy {p.id}\n'
        )

    update.message.reply_text('\n'.join(lines))


def buy(update: Update, context: CallbackContext):
    user = get_or_create_telegram_user(update)

    if not user.email or not user.phone:
        update.message.reply_text('Сначала нужно завершить регистрацию. Нажми /start.')
        return

    if not context.args:
        update.message.reply_text('Использование: /buy <ID_товара>, например: /buy 1')
        return

    try:
        product_id = int(context.args[0])
    except ValueError:
        update.message.reply_text('ID товара должен быть числом.')
        return

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        update.message.reply_text('Товар с таким ID не найден.')
        return

    if product.stock <= 0:
        update.message.reply_text('Эти носки закончились на складе.')
        return

    order = Order.objects.create(user=user)
    OrderItem.objects.create(order=order, product=product, quantity=1)

    product.stock -= 1
    product.save()

    update.message.reply_text(
        f'Носки добавлены в корзину (заказ #{order.id}).'
    )


def my_orders(update: Update, context: CallbackContext):
    user = get_or_create_telegram_user(update)
    orders = user.orders.all().order_by('-created_at')

    if not orders.exists():
        update.message.reply_text('У тебя пока нет заказов.')
        return

    lines = ['Твои заказы:\n']
    for order in orders:
        lines.append(f'Заказ #{order.id}:')
        for item in order.items.all():
            lines.append(f'  - {item.product} x{item.quantity}')
        lines.append('')

    update.message.reply_text('\n'.join(lines))


def add_socks(update: Update, context: CallbackContext):
    user = get_or_create_telegram_user(update)

    if not is_admin(user):
        update.message.reply_text('У тебя нет прав для этой команды.')
        return

    args = context.args
    if len(args) < 5:
        update.message.reply_text(
            'Использование: /add_socks <size> <material> <color> <price> <stock>\n'
            'Например: /add_socks 41-43 cotton black 2000 50'
        )
        return

    size, material, color, price_str, stock_str = args[:5]

    try:
        price = Decimal(price_str)
        stock = int(stock_str)
    except (ValueError, InvalidOperation):
        update.message.reply_text('Цена должна быть числом, количество — целым числом.')
        return

    product = Product.objects.create(
        name='Носки',
        size=size,
        material=material,
        color=color,
        price=price,
        stock=stock,
    )

    update.message.reply_text(f'Товар создан: ID {product.id} — {product}')


def list_orders(update: Update, context: CallbackContext):
    user = get_or_create_telegram_user(update)

    if not is_admin(user):
        update.message.reply_text('У тебя нет прав для этой команды.')
        return

    orders = Order.objects.all().order_by('-created_at')

    if not orders.exists():
        update.message.reply_text('Заказов пока нет.')
        return

    lines = ['Список заказов:\n']
    for order in orders:
        lines.append(f'Заказ #{order.id} от {order.user.telegram_id}:')
        for item in order.items.all():
            lines.append(f'  - {item.product} x{item.quantity}')
        lines.append('')

    update.message.reply_text('\n'.join(lines))


def promote_user(update: Update, context: CallbackContext):
    caller = get_or_create_telegram_user(update)

    if not is_super_admin(caller):
        update.message.reply_text('Только SUPER_ADMIN может менять роли.')
        return

    args = context.args
    if len(args) < 2:
        update.message.reply_text('Использование: /promote_user <telegram_id> <role>')
        return

    try:
        tg_id = int(args[0])
    except ValueError:
        update.message.reply_text('telegram_id должен быть числом.')
        return

    role = args[1]

    if role not in TelegramUser.Role.values:
        update.message.reply_text('Роль должна быть одной из: USER, ADMIN, SUPER_ADMIN.')
        return

    try:
        target = TelegramUser.objects.get(telegram_id=tg_id)
    except TelegramUser.DoesNotExist:
        update.message.reply_text('Пользователь с таким telegram_id не найден.')
        return

    target.role = role
    target.save()

    update.message.reply_text(f'Роль пользователя {target.telegram_id} изменена на {role}.')


def create_user(update: Update, context: CallbackContext):
    """Usage: /create_user <telegram_id> <username> <first_name> [email] [phone] [role]
    Minimal: /create_user 123456 Имя
    """
    args = context.args
    if len(args) < 2:
        update.message.reply_text('Использование: /create_user <telegram_id> <username> <first_name> [email] [phone] [role]')
        return

    try:
        tg_id = int(args[0])
    except ValueError:
        update.message.reply_text('telegram_id должен быть числом.')
        return

    username = args[1]
    first_name = args[2] if len(args) >= 3 else ''
    email = args[3] if len(args) >= 4 else ''
    phone = args[4] if len(args) >= 5 else ''
    role = args[5] if len(args) >= 6 else TelegramUser.Role.USER

    user, created = TelegramUser.objects.get_or_create(
        telegram_id=tg_id,
        defaults={'username': username, 'first_name': first_name, 'email': email, 'phone': phone, 'role': role}
    )

    if not created:
        update.message.reply_text(f'Пользователь с telegram_id {tg_id} уже существует (id={user.id}).')
        return

    update.message.reply_text(f'Пользователь создан: id={user.id}, telegram_id={user.telegram_id}.')


def list_users(update: Update, context: CallbackContext):
    users = TelegramUser.objects.all().order_by('id')
    if not users.exists():
        update.message.reply_text('Пользователей пока нет.')
        return

    lines = []
    for u in users:
        username_part = f"(@{u.username})" if u.username else ''
        first_name = u.first_name or ''
        lines.append(f'id={u.id} tg={u.telegram_id} {first_name} {username_part} role={u.role}')

    update.message.reply_text('\n'.join(lines))


def view_user(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text('Использование: /view_user <telegram_id>')
        return

    try:
        tg_id = int(context.args[0])
    except ValueError:
        update.message.reply_text('telegram_id должен быть числом.')
        return

    try:
        u = TelegramUser.objects.get(telegram_id=tg_id)
    except TelegramUser.DoesNotExist:
        update.message.reply_text('Пользователь не найден.')
        return

    update.message.reply_text(
        f'id={u.id}\ntelegram_id={u.telegram_id}\nusername={u.username}\nfirst_name={u.first_name}\nemail={u.email}\nphone={u.phone}\nrole={u.role}'
    )


def update_user(update: Update, context: CallbackContext):
    """Usage: /update_user <telegram_id> <field> <value>
    Fields: username, first_name, email, phone, role
    """
    if len(context.args) < 3:
        update.message.reply_text('Использование: /update_user <telegram_id> <field> <value>')
        return

    try:
        tg_id = int(context.args[0])
    except ValueError:
        update.message.reply_text('telegram_id должен быть числом.')
        return

    field = context.args[1]
    value = ' '.join(context.args[2:])

    allowed = {'username', 'first_name', 'email', 'phone', 'role'}
    if field not in allowed:
        update.message.reply_text(f'Поле должно быть одним из: {", ".join(allowed)}')
        return

    try:
        u = TelegramUser.objects.get(telegram_id=tg_id)
    except TelegramUser.DoesNotExist:
        update.message.reply_text('Пользователь не найден.')
        return

    setattr(u, field, value)
    u.save()
    update.message.reply_text(f'Пользователь {tg_id} обновлён: {field}={value}')


def delete_user(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text('Использование: /delete_user <telegram_id>')
        return

    try:
        tg_id = int(context.args[0])
    except ValueError:
        update.message.reply_text('telegram_id должен быть числом.')
        return

    try:
        u = TelegramUser.objects.get(telegram_id=tg_id)
    except TelegramUser.DoesNotExist:
        update.message.reply_text('Пользователь не найден.')
        return

    u.delete()
    update.message.reply_text(f'Пользователь с telegram_id {tg_id} удалён.')


def run_bot():
    updater = Updater(token=settings.TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_EMAIL: [MessageHandler(Filters.text & ~Filters.command, ask_email)],
            ASK_PHONE: [MessageHandler(Filters.text & ~Filters.command, ask_phone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('help', help_command))
    dp.add_handler(CommandHandler('catalog', catalog))
    dp.add_handler(CommandHandler('buy', buy))
    dp.add_handler(CommandHandler('my_orders', my_orders))
    dp.add_handler(CommandHandler('add_socks', add_socks))
    dp.add_handler(CommandHandler('list_orders', list_orders))
    dp.add_handler(CommandHandler('promote_user', promote_user))
    # Simple Telegram CRUD handlers for TelegramUser
    dp.add_handler(CommandHandler('create_user', create_user))
    dp.add_handler(CommandHandler('list_users', list_users))
    dp.add_handler(CommandHandler('view_user', view_user))
    dp.add_handler(CommandHandler('update_user', update_user))
    dp.add_handler(CommandHandler('delete_user', delete_user))

    updater.start_polling()
    updater.idle()
