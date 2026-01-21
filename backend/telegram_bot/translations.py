"""
Translation system for Telegram bot
"""

# Translation dictionaries
TRANSLATIONS = {
    "ru": {
        # Commands and basic messages
        "welcome": (
            "Добро пожаловать в систему учёта контейнеров терминала! 📦\n\n"
            "Используйте кнопки ниже для управления системой:\n"
            "🚛 Въезд - Зарегистрировать въезд контейнера\n"
            "🚚 Выезд - Зарегистрировать выезд контейнера\n"
            "ℹ️ Справка - Показать справку\n"
            "🌍 Язык - Изменить язык интерфейса"
        ),
        "help_text": (
            "📦 Система учёта контейнеров\n\n"
            "Для регистрации въезда нажмите кнопку 🚛 Въезд\n"
            "Для регистрации выезда нажмите кнопку 🚚 Выезд\n\n"
            "При въезде вам нужно будет указать:\n"
            "1️⃣ Номер контейнера (например: MSKU1234567)\n"
            "2️⃣ Тип контейнера ISO (выбрать из списка)\n"
            "3️⃣ Статус (гружёный/порожний)\n"
            "4️⃣ Тип транспорта (авто/вагон)\n"
            "5️⃣ Номер транспорта\n"
            "6️⃣ Фотографии (опционально)\n\n"
            "Во время создания записи используйте кнопку ❌ Отменить для отмены"
        ),
        "choose_language": "Выберите язык / Tilni tanlang:",
        "choose_action": "Выберите действие:",
        "language_changed": "Язык изменён на русский",
        "no_operation": "Нет активных операций для отмены",
        "operation_cancelled": "Операция отменена ❌",
        # Entry creation flow
        "start_entry": "Начинаем создание записи о въезде контейнера.\n\n📝 Введите номер контейнера:",
        "error_text_only": "❌ Пожалуйста, отправьте текстовое сообщение с номером контейнера",
        "invalid_container_format": "❌ Неверный формат номера контейнера!\nФормат: 4 буквы + 7 цифр (например: MSKU1234567)\n\nПопробуйте ещё раз:",
        "container_already_active": "❌ Контейнер {container_number} уже находится на терминале!\n\n📅 Дата въезда: {entry_date}\n🚛 Транспорт: {transport_type}\n\nПожалуйста, сначала зарегистрируйте выезд этого контейнера или введите другой номер контейнера:",
        "error_transport_text": "❌ Пожалуйста, отправьте текстовое сообщение с номером транспорта",
        "error_transport_empty": "❌ Номер транспорта не может быть пустым!\nПожалуйста, введите корректный номер:",
        "photo_loading": "⏳ Получено фото: {count}",
        "photo_received": "✅ Фото получено! Всего: {count}\nОтправьте ещё фото или нажмите 'Готово':",
        "no_photos": "Без фотографий",
        # Summary field labels
        "summary_container": "Контейнер",
        "summary_iso": "ISO тип",
        "summary_owner": "Владелец",
        "summary_status": "Статус",
        "summary_transport": "Транспорт",
        "summary_transport_num": "Номер транспорта",
        "summary_photos": "Фотографий",
        # Step prompts
        "ask_iso_type": "📦 ISO тип контейнера:",
        "ask_owner": "🏢 Выберите владельца контейнера:",
        "ask_status": "📊 Выберите статус контейнера:",
        "ask_transport_type": "🚛 Выберите тип транспорта:",
        "ask_transport_number": "📝 Введите номер транспорта (номер авто или вагона):",
        "ask_truck_plate_photo": "📸 Отправьте фото номерного знака автомобиля для автоматического распознавания:",
        "ask_all_photos_truck": "📸 Отправьте фотографии (авто и контейнер).\nНомер авто будет распознан автоматически.\nКогда закончите, нажмите 'Готово':",
        "plate_recognizing": "🔍 Распознаю номер...",
        "plate_recognized": "✅ Распознан номер: <b>{plate}</b>\n\nУверенность: {confidence}%\n\nВсё верно?",
        "plate_recognition_failed": "❌ Не удалось распознать номер автоматически.\n\nПожалуйста, введите номер вручную:",
        "ask_photos": "📸 Отправьте фотографии контейнера (можно несколько).\nКогда закончите, нажмите 'Готово' или 'Пропустить':",
        # Confirmation
        "confirmation_header": "📋 Проверьте данные:",
        "confirmation_question": "Всё верно?",
        "entry_created": "✅ Запись успешно создана!\n\nID записи: {id}\nКонтейнер: {container}\nВремя въезда: {time}",
        "duplicate_entry": "❌ Этот контейнер уже был зарегистрирован сегодня!\n\nКонтейнер: {container_number}",
        "error_creating": "❌ Ошибка при создании записи:\n{error}",
        "error_missing_data": "Данные отсутствуют. Пожалуйста, начните сначала.",
        "error_unexpected": "Неожиданная ошибка. Пожалуйста, попробуйте снова.",
        "entry_cancelled": "❌ Создание записи отменено",
        # Buttons - Inline keyboards
        "btn_laden": "Гружёный",
        "btn_empty": "Порожний",
        "btn_truck": "Авто",
        "btn_wagon": "Вагон",
        "btn_skip": "Пропустить",
        "btn_skip_owner": "Пропустить",
        "btn_done": "Готово",
        "btn_confirm": "✅ Подтвердить",
        "btn_cancel": "❌ Отменить",
        "btn_confirm_plate": "✅ Подтвердить",
        "btn_edit_plate": "✏️ Ввести вручную",
        # Owner display
        "owner_not_specified": "Не указан",
        "owner_not_found": "Владелец не найден",
        "no_owners_available": 'Нет доступных владельцев. Нажмите "Пропустить" для продолжения.',
        # Buttons - Reply keyboards
        "btn_create_entry": "🚛 Въезд",
        "btn_help": "ℹ️ Справка",
        "btn_change_language": "🌍 Язык",
        "btn_cancel_operation": "❌ Отменить",
        # Status display
        "status_laden": "Гружёный",
        "status_empty": "Порожний",
        "transport_truck": "Авто",
        "transport_wagon": "Вагон",
        # Manager access control
        "not_registered": (
            "❌ <b>Доступ запрещён</b>\n\n"
            "Ваш номер телефона не зарегистрирован в системе.\n"
            "Обратитесь к администратору для регистрации."
        ),
        "account_deactivated": (
            "❌ <b>Аккаунт деактивирован</b>\n\n"
            "Ваш аккаунт был деактивирован.\n"
            "Обратитесь к администратору для восстановления доступа."
        ),
        "access_denied": (
            "❌ <b>Доступ к боту отключён</b>\n\n"
            "У вас нет разрешения на использование бота.\n"
            "Нажмите кнопку ниже, чтобы запросить доступ."
        ),
        "access_request_pending": (
            "⏳ <b>Запрос на рассмотрении</b>\n\n"
            "Ваш запрос на доступ к боту уже отправлен администратору.\n"
            "Ожидайте подтверждения."
        ),
        "telegram_not_linked": (
            "❌ <b>Ошибка связи аккаунта</b>\n\n"
            "Произошла ошибка при связывании вашего Telegram аккаунта.\n"
            "Обратитесь к администратору."
        ),
        "phone_share_request": (
            "📱 <b>Добро пожаловать!</b>\n\n"
            "Для начала работы с ботом, пожалуйста, поделитесь своим номером телефона.\n\n"
            "Нажмите кнопку ниже ⬇️"
        ),
        "phone_verification_success": (
            "✅ <b>Номер подтверждён!</b>\n\n"
            "Доступ к боту активирован.\n"
            "Теперь вы можете использовать все функции бота."
        ),
        "phone_not_registered": (
            "❌ <b>Номер не найден</b>\n\n"
            "Ваш номер телефона <code>{phone_number}</code> не зарегистрирован в системе.\n\n"
            "Обратитесь к администратору для регистрации."
        ),
        "phone_account_deactivated": (
            "❌ <b>Аккаунт деактивирован</b>\n\n"
            "Ваш номер <code>{phone_number}</code> зарегистрирован, но аккаунт деактивирован.\n\n"
            "Обратитесь к администратору для восстановления доступа."
        ),
        "access_request_sent": (
            "✅ <b>Запрос отправлен!</b>\n\n"
            "Ваш запрос на доступ к боту отправлен администратору.\n"
            "Вы получите уведомление, когда доступ будет предоставлен."
        ),
        "btn_request_access": "🔓 Запросить доступ",
        "btn_share_phone": "📱 Поделиться номером",
        "phone_verification_instruction": '❌ Пожалуйста, используйте кнопку "Поделиться номером" для отправки вашего номера телефона.',
        "restart_hint": "💡 Нажмите /start чтобы начать заново.",
        "telegram_already_linked": "❌ Этот номер телефона уже привязан к другому Telegram аккаунту.",
        "generic_error": "❌ <b>Ошибка:</b> {error}",
        "invalid_selection": "❌ Неверный выбор. Попробуйте ещё раз.",
        # Exit container flow
        "btn_exit_container": "🚚 Выезд",
        "btn_train": "Поезд",
        "start_exit": "Начинаем регистрацию выезда контейнера.\n\n📝 Введите номер контейнера:",
        "container_not_found": "❌ Контейнер {container_number} не найден на терминале!\n\nПожалуйста, проверьте номер контейнера и попробуйте ещё раз:",
        "container_already_exited": "❌ Контейнер {container_number} уже выехал с терминала!\n\n📅 Дата выезда: {exit_date}\n\nПожалуйста, введите другой номер контейнера:",
        "ask_exit_date": "📅 Введите дату выезда контейнера (форматы: 2025-10-28 или 28.10.2025 или 28/10/2025 или 28-10-2025).\nЧасы и минуты опциональны (например: 2025-10-28 14:30):",
        "ask_exit_transport_type": "🚛 Выберите тип транспорта для выезда:",
        "ask_exit_transport_number": "📝 Введите номер транспорта для выезда (номер авто или вагона):",
        "ask_exit_train_number": "🚂 Введите номер поезда:",
        "ask_destination_station": "📍 Введите пункт назначения (станцию).\nНажмите 'Пропустить' если не известен пункт назначения:",
        "ask_crane_operations": "🏗️ Введите дату и время дополнительной операции с краном (опционально).\nФормат: 2025-10-28 14:30\n\nНажмите 'Пропустить' если нет дополнительных операций:",
        "ask_exit_photos": "📸 Отправьте фотографии выезда контейнера (опционально).\nКогда закончите, нажмите 'Готово' или 'Пропустить':",
        "invalid_exit_date": "❌ Неверный формат даты!\nПопробуйте ещё раз (2025-10-28 или 28.10.2025):",
        "exit_date_before_entry": "❌ Дата выезда не может быть раньше даты въезда!\n\n📅 Дата въезда: {entry_date}\n\nПожалуйста, введите корректную дату:",
        "error_exit_text": "❌ Пожалуйста, отправьте текстовое сообщение",
        "invalid_crane_date": "❌ Неверный формат даты операции с краном!\nПопробуйте ещё раз (2025-10-28 14:30):",
        "crane_operation_added": "✅ Операция добавлена ({operation_date})\n\nОтправьте ещё дату или нажмите 'Готово':",
        "exit_photos_loading": "⏳ Получено фото: {count}",
        "exit_photos_received": "✅ Фото получено! Всего: {count}\nОтправьте ещё фото или нажмите 'Готово':",
        # Exit summary fields
        "summary_exit_date": "Дата выезда",
        "summary_exit_transport": "Транспорт выезда",
        "summary_exit_transport_num": "Номер транспорта",
        "summary_exit_train_num": "Номер поезда",
        "summary_destination": "Пункт назначения",
        "summary_crane_ops": "Операции с краном",
        "summary_dwell_time": "Время стоянки",
        # Exit entry info labels (for enhanced display)
        "exit_entry_info_header": "Информация при въезде",
        "exit_entry_client": "Клиент",
        "exit_entry_cargo": "Груз",
        "exit_entry_owner": "Владелец контейнера",
        "exit_entry_location": "Местоположение",
        "exit_entry_weight": "Вес груза",
        "exit_entry_notes": "Примечания",
        "exit_photos_header": "Фотографии при выезде",
        "entry_photos_header": "Фотографии при въезде",
        "no_photos_available": "Фото отсутствуют",
        # Confirmation
        "exit_confirmation_header": "📋 Проверьте данные выезда:",
        "exit_confirmation_question": "Всё верно? Подтвердить выезд?",
        "exit_created": "✅ Выезд успешно зарегистрирован!\n\nКонтейнер: {container}\nДата выезда: {exit_date}\n⏱️ Время стоянки: {dwell_time} дней",
        "error_exit_creating": "❌ Ошибка при регистрации выезда:\n{error}",
        "exit_cancelled": "❌ Регистрация выезда отменена",
        # Crane operation flow
        "btn_crane_operation": "🏗️ Кран",
        "start_crane_operation": "Добавление крановой операции.\n\n📝 Введите номер контейнера:",
        "crane_op_container_not_found": "❌ Контейнер {container_number} не найден на терминале!\n\nПожалуйста, проверьте номер и попробуйте ещё раз:",
        "crane_op_added": "✅ Крановая операция добавлена!\n\n📦 Контейнер: {container_number}\n🕐 Время: {operation_time}\n📊 Всего операций: {total_count}\n\nДобавить ещё операцию?",
        "crane_op_error": "❌ Ошибка при добавлении операции:\n{error}",
        "crane_op_completed": "✅ Операции сохранены!\n\n📦 Контейнер: {container_number}\n📊 Всего добавлено: {count} операций",
        "btn_add_more_crane_op": "➕ Добавить ещё",
        "btn_done_crane_op": "✅ Готово",
        # Customer pre-order translations
        "customer_welcome": (
            "Добро пожаловать в систему предзаказов! 📦\n\n"
            "Используйте кнопки ниже для управления:\n"
            "📦 Создать заявку - создать заявку на въезд\n"
            "📋 Мои заявки - посмотреть ваши заявки\n"
            "❌ Отменить заявку - отменить активную заявку"
        ),
        "customer_help": (
            "📦 Система предзаказов для клиентов\n\n"
            "Для создания заявки нажмите 📦 Создать заявку\n\n"
            "При создании заявки:\n"
            "1️⃣ Отправьте фото грузовика\n"
            "2️⃣ Подтвердите номер автомобиля\n"
            "3️⃣ Выберите тип операции\n\n"
            "Когда машина приедет на терминал, охрана найдёт вашу заявку автоматически."
        ),
        "btn_create_order": "📦 Создать заявку",
        "btn_my_orders": "📋 Мои заявки",
        "btn_cancel_order": "❌ Отменить заявку",
        "btn_load": "📥 Погрузка",
        "btn_unload": "📤 Разгрузка",
        "btn_edit": "✏️ Изменить",
        "btn_back": "◀️ Назад",
        "btn_confirm_cancel": "✅ Да, отменить",
        "btn_no": "❌ Нет",
        "operation_load_short": "Погр.",
        "operation_unload_short": "Разгр.",
        # Customer order creation flow (multi-plate)
        "customer_enter_plates": (
            "📝 <b>Введите номера автомобилей</b>\n\n"
            "Можно ввести несколько номеров, каждый с новой строки:\n\n"
            "<code>01A123BC\n"
            "01B456DE\n"
            "01C789FG</code>"
        ),
        "customer_plates_invalid": "❌ Пожалуйста, введите хотя бы один корректный номер (минимум 3 символа)",
        "customer_ask_operation_for_plate": "📊 <b>Авто {index}/{total}</b>\n\n🚛 Номер: <b>{plate}</b>\n\nВыберите тип операции:",
        "customer_summary_header": "📋 Проверьте заявки:",
        "customer_confirm_all": "Подтвердить все заявки?",
        "customer_orders_created": "✅ Успешно создано <b>{count}</b> заявок!\n\nПри въезде на терминал ваши заявки будут найдены автоматически.",
        "customer_orders_partial": (
            "⚠️ Создано {created} из {total} заявок.\n\nОшибки:\n{errors}"
        ),
        "customer_order_error": "❌ Ошибка создания заявки:\n{error}",
        # Legacy keys (for compatibility)
        "customer_ask_truck_photo": "📸 Отправьте фото грузовика:",
        "customer_enter_plate": "📝 Введите номер автомобиля:",
        "customer_plate_text_only": "❌ Пожалуйста, введите номер текстом",
        "customer_ask_operation_type": "📊 Выберите тип операции:",
        "customer_confirm_header": "📋 Проверьте заявку:",
        "customer_confirm_question": "Всё верно?",
        # Customer order viewing
        "customer_no_orders": "📋 У вас нет заявок",
        "customer_orders_header": "📋 Ваши заявки:\n",
        "customer_order_item": "#{id} | {plate} | {operation} | {status}\n",
        "customer_no_pending_orders": "📋 У вас нет активных заявок для отмены",
        "customer_select_order_cancel": "📋 Выберите заявку для отмены:",
        "customer_confirm_cancel_question": "❓ Вы уверены, что хотите отменить эту заявку?",
        "customer_order_cancelled": "✅ Заявка на номер {plate} отменена",
        "customer_cancel_error": "❌ Ошибка отмены: {error}",
        # Customer container cabinet
        "btn_my_containers": "📦 Мои контейнеры",
        "container_list_header": "📦 <b>Контейнеры на терминале</b>\n\nВсего: {count}",
        "container_list_empty": "📋 На терминале нет контейнеров вашей компании",
        "container_no_company": "❌ Вы не привязаны к компании. Обратитесь к администратору.",
        "days_short": "дн.",
        "btn_search_container": "🔍 Поиск",
        "btn_photos": "Фото",
        "btn_back_to_list": "◀️ К списку",
        "btn_cancel_search": "❌ Отмена",
        "container_search_prompt": "🔍 Введите номер контейнера:",
        "container_search_not_found": "❌ Контейнер не найден или уже вывезен с терминала",
        "container_detail": (
            "📦 <b>Контейнер {number}</b>\n\n"
            "📊 Статус: {status}\n"
            "📐 Тип: {iso_type}\n"
            "📅 Въезд: {entry_date}\n"
            "⏱ На терминале: <b>{dwell_days} дн.</b>\n"
        ),
        "container_detail_cargo": "📦 Груз: {cargo}",
        "container_detail_weight": "⚖️ Вес: {weight} кг",
        "container_detail_location": "📍 Место: {location}",
        "container_detail_owner": "🏢 Собственник: {owner}",
        "container_detail_transport": "🚛 Транспорт: {type} ({number})",
        "photos_sending": "📤 Отправляю фото...",
        "photos_sent": "✅ Отправлено {count} фото",
        "photos_none": "📷 Фото не найдены",
        # Customer vehicle notifications
        "customer_vehicle_entered": (
            "✅ Ваш автомобиль въехал на терминал!\n\n"
            "🚛 Номер: <b>{plate}</b>\n"
            "📅 Время: {time}\n\n"
            "Ожидайте дальнейших уведомлений."
        ),
        "customer_vehicle_exited": (
            "🏁 Ваш автомобиль выехал с терминала!\n\n"
            "🚛 Номер: <b>{plate}</b>\n"
            "📅 Время: {time}"
        ),
        "customer_vehicle_cancelled": (
            "❌ Ваша заявка на въезд отменена.\n\n"
            "🚛 Номер: <b>{plate}</b>\n\n"
            "Если это ошибка, создайте новую заявку."
        ),
        # Customer order status display
        "order_status_pending": "Ожидает",
        "order_status_matched": "Найден",
        "order_status_completed": "Выполнен",
        "order_status_cancelled": "Отменён",
        # Summary fields for customer orders
        "summary_plate_number": "Номер авто",
        "summary_operation_type": "Тип операции",
        "operation_load": "Погрузка",
        "operation_unload": "Разгрузка",
        # Customer access messages
        "customer_access_denied": (
            "❌ <b>Доступ запрещён</b>\n\n"
            "У вас нет доступа к системе предзаказов.\n"
            "Обратитесь к администратору для регистрации."
        ),
        "customer_access_pending": (
            "⏳ <b>Ожидание подтверждения</b>\n\n"
            "Ваша заявка на доступ находится на рассмотрении.\n"
            "Ожидайте подтверждения администратора."
        ),
        # Gate matching messages (shown to security when pre-order matched)
        "preorder_match_found": (
            "✅ <b>Найдена заявка клиента!</b>\n\n"
            "👤 Клиент: {customer_name}\n"
            "🚗 Номер авто: {plate_number}\n"
            "📊 Тип операции: {operation_type}\n\n"
            "Заявка будет автоматически привязана к записи."
        ),
        "preorder_match_operation_load": "Погрузка",
        "preorder_match_operation_unload": "Разгрузка",
        "preorder_matched_success": "✅ Заявка клиента #{order_id} успешно привязана к записи",
    },
    "uz": {
        # Commands and basic messages
        "welcome": (
            "Terminal konteyner hisobini yuritish tizimiga xush kelibsiz! 📦\n\n"
            "Tizimni boshqarish uchun quyidagi tugmalardan foydalaning:\n"
            "🚛 Kirish - Konteyner kirishini ro'yxatdan o'tkazish\n"
            "🚚 Chiqish - Konteyner chiqishini ro'yxatdan o'tkazish\n"
            "ℹ️ Ma'lumot - Ma'lumot ko'rsatish\n"
            "🌍 Til - Interfeys tilini o'zgartirish"
        ),
        "help_text": (
            "📦 Konteyner hisobi tizimi\n\n"
            "Kirish ro'yxatdan o'tkazish uchun 🚛 Kirish tugmasini bosing\n"
            "Chiqish ro'yxatdan o'tkazish uchun 🚚 Chiqish tugmasini bosing\n\n"
            "Kirish paytida siz quyidagilarni ko'rsatishingiz kerak:\n"
            "1️⃣ Konteyner raqami (masalan: MSKU1234567)\n"
            "2️⃣ ISO konteyner turi (ro'yxatdan tanlang)\n"
            "3️⃣ Holati (yuklangan/bo'sh)\n"
            "4️⃣ Transport turi (yuk mashinasi/vagon)\n"
            "5️⃣ Transport raqami\n"
            "6️⃣ Fotosuratlar (ixtiyoriy)\n\n"
            "Yozuv yaratish vaqtida bekor qilish uchun ❌ Bekor qilish tugmasidan foydalaning"
        ),
        "choose_language": "Выберите язык / Tilni tanlang:",
        "choose_action": "Amalni tanlang:",
        "language_changed": "Til o'zbek tiliga o'zgartirildi",
        "no_operation": "Bekor qilish uchun faol operatsiya yo'q",
        "operation_cancelled": "Operatsiya bekor qilindi ❌",
        # Entry creation flow
        "start_entry": "Konteyner kirishi haqida yozuv yaratishni boshlaymiz.\n\n📝 Konteyner raqamini kiriting:",
        "error_text_only": "❌ Iltimos, konteyner raqami bilan matnli xabar yuboring",
        "invalid_container_format": "❌ Konteyner raqami formati noto'g'ri!\nFormat: 4 harf + 7 raqam (masalan: MSKU1234567)\n\nQaytadan urinib ko'ring:",
        "container_already_active": "❌ Konteyner {container_number} allaqachon terminalda!\n\n📅 Kirish sanasi: {entry_date}\n🚛 Transport: {transport_type}\n\nIltimos, avval bu konteyner chiqishini ro'yxatdan o'tkazing yoki boshqa konteyner raqamini kiriting:",
        "error_transport_text": "❌ Iltimos, transport raqami bilan matnli xabar yuboring",
        "error_transport_empty": "❌ Transport raqami bo'sh bo'lishi mumkin emas!\nIltimos, to'g'ri raqamni kiriting:",
        "photo_loading": "⏳ Fotosurat qabul qilindi: {count}",
        "photo_received": "✅ Fotosurat qabul qilindi! Jami: {count}\nYana fotosurat yuboring yoki 'Tayyor' tugmasini bosing:",
        "no_photos": "Fotosuratlar yo'q",
        # Summary field labels
        "summary_container": "Konteyner",
        "summary_iso": "ISO turi",
        "summary_owner": "Egasi",
        "summary_status": "Holati",
        "summary_transport": "Transport",
        "summary_transport_num": "Transport raqami",
        "summary_photos": "Fotosuratlar",
        # Step prompts
        "ask_iso_type": "📦 ISO konteyner turi:",
        "ask_owner": "🏢 Konteyner egasini tanlang:",
        "ask_status": "📊 Konteyner holatini tanlang:",
        "ask_transport_type": "🚛 Transport turini tanlang:",
        "ask_transport_number": "📝 Transport raqamini kiriting (yuk mashinasi yoki vagon raqami):",
        "ask_truck_plate_photo": "📸 Avtomobil raqamining rasmini yuboring (avtomatik tanib olish uchun):",
        "ask_all_photos_truck": "📸 Rasmlarni yuboring (avtomobil va konteyner).\nAvtomobil raqami avtomatik tanib olinadi.\nTugagach, 'Tayyor' tugmasini bosing:",
        "plate_recognizing": "🔍 Raqamni taniyapman...",
        "plate_recognized": "✅ Tanilgan raqam: <b>{plate}</b>\n\nIshonch: {confidence}%\n\nTo'g'rimi?",
        "plate_recognition_failed": "❌ Raqamni avtomatik tanib bo'lmadi.\n\nIltimos, raqamni qo'lda kiriting:",
        "ask_photos": "📸 Konteyner fotosuratlarini yuboring (bir nechta bo'lishi mumkin).\nTugagach, 'Tayyor' yoki 'O'tkazib yuborish' tugmasini bosing:",
        # Confirmation
        "confirmation_header": "📋 Ma'lumotlarni tekshiring:",
        "confirmation_question": "Hammasi to'g'rimi?",
        "entry_created": "✅ Yozuv muvaffaqiyatli yaratildi!\n\nYozuv ID: {id}\nKonteyner: {container}\nKirish vaqti: {time}",
        "duplicate_entry": "❌ Bu konteyner bugun allaqachon ro'yxatdan o'tgan!\n\nKonteyner: {container_number}",
        "error_creating": "❌ Yozuv yaratishda xatolik:\n{error}",
        "error_missing_data": "Ma'lumotlar yo'q. Iltimos, boshidan boshlang.",
        "error_unexpected": "Kutilmagan xatolik. Iltimos, qaytadan urinib ko'ring.",
        "entry_cancelled": "❌ Yozuv yaratish bekor qilindi",
        # Buttons - Inline keyboards
        "btn_laden": "Yuklangan",
        "btn_empty": "Bo'sh",
        "btn_truck": "Yuk mashinasi",
        "btn_wagon": "Vagon",
        "btn_skip": "O'tkazib yuborish",
        "btn_skip_owner": "O'tkazib yuborish",
        "btn_done": "Tayyor",
        "btn_confirm": "✅ Tasdiqlash",
        "btn_cancel": "❌ Bekor qilish",
        "btn_confirm_plate": "✅ Tasdiqlash",
        "btn_edit_plate": "✏️ Qo'lda kiritish",
        # Owner display
        "owner_not_specified": "Ko'rsatilmagan",
        "owner_not_found": "Egasi topilmadi",
        "no_owners_available": "Mavjud egalar yo'q. Davom etish uchun \"O'tkazib yuborish\" tugmasini bosing.",
        # Buttons - Reply keyboards
        "btn_create_entry": "🚛 Kirish",
        "btn_help": "ℹ️ Ma'lumot",
        "btn_change_language": "🌍 Til",
        "btn_cancel_operation": "❌ Bekor qilish",
        # Status display
        "status_laden": "Yuklangan",
        "status_empty": "Bo'sh",
        "transport_truck": "Yuk mashinasi",
        "transport_wagon": "Vagon",
        # Manager access control
        "not_registered": (
            "❌ <b>Kirish taqiqlangan</b>\n\n"
            "Sizning telefon raqamingiz tizimda ro'yxatdan o'tmagan.\n"
            "Administrator bilan bog'laning."
        ),
        "account_deactivated": (
            "❌ <b>Hisob deaktivatsiya qilingan</b>\n\n"
            "Sizning hisobingiz deaktivatsiya qilingan.\n"
            "Kirish huquqini tiklash uchun administrator bilan bog'laning."
        ),
        "access_denied": (
            "❌ <b>Botga kirish o'chirilgan</b>\n\n"
            "Sizda botdan foydalanish uchun ruxsat yo'q.\n"
            "Kirish uchun quyidagi tugmani bosing."
        ),
        "access_request_pending": (
            "⏳ <b>So'rov ko'rib chiqilmoqda</b>\n\n"
            "Botga kirish uchun so'rovingiz allaqachon administratorga yuborilgan.\n"
            "Tasdiqlashni kuting."
        ),
        "telegram_not_linked": (
            "❌ <b>Hisob bog'lash xatosi</b>\n\n"
            "Telegram hisobingizni bog'lashda xatolik yuz berdi.\n"
            "Administrator bilan bog'laning."
        ),
        "phone_share_request": (
            "📱 <b>Xush kelibsiz!</b>\n\n"
            "Bot bilan ishlashni boshlash uchun telefon raqamingizni ulashing.\n\n"
            "Quyidagi tugmani bosing ⬇️"
        ),
        "phone_verification_success": (
            "✅ <b>Raqam tasdiqlandi!</b>\n\n"
            "Botga kirish faollashtirildi.\n"
            "Endi siz botning barcha funksiyalaridan foydalanishingiz mumkin."
        ),
        "phone_not_registered": (
            "❌ <b>Raqam topilmadi</b>\n\n"
            "Sizning telefon raqamingiz <code>{phone_number}</code> tizimda ro'yxatdan o'tmagan.\n\n"
            "Ro'yxatdan o'tish uchun administrator bilan bog'laning."
        ),
        "phone_account_deactivated": (
            "❌ <b>Hisob deaktivatsiya qilingan</b>\n\n"
            "Sizning raqamingiz <code>{phone_number}</code> ro'yxatdan o'tgan, lekin hisob deaktivatsiya qilingan.\n\n"
            "Kirish huquqini tiklash uchun administrator bilan bog'laning."
        ),
        "access_request_sent": (
            "✅ <b>So'rov yuborildi!</b>\n\n"
            "Botga kirish uchun so'rovingiz administratorga yuborildi.\n"
            "Kirish berilganda xabar olasiz."
        ),
        "phone_verification_instruction": '❌ Iltimos, telefon raqamingizni yuborish uchun "Raqamni ulashish" tugmasidan foydalaning.',
        "btn_request_access": "🔓 Kirish so'rash",
        "btn_share_phone": "📱 Raqamni ulashish",
        "restart_hint": "💡 Qayta boshlash uchun /start bosing.",
        "telegram_already_linked": "❌ Bu telefon raqami boshqa Telegram hisobiga ulangan.",
        "generic_error": "❌ <b>Xatolik:</b> {error}",
        "invalid_selection": "❌ Noto'g'ri tanlov. Qaytadan urinib ko'ring.",
        # Exit container flow
        "btn_exit_container": "🚚 Chiqish",
        "btn_train": "Poyezd",
        "start_exit": "Konteyner chiqishini ro'yxatdan o'tkkazishni boshlaymiz.\n\n📝 Konteyner raqamini kiriting:",
        "container_not_found": "❌ Konteyner {container_number} terminalda topilmadi!\n\nKonteyner raqamini tekshiring va qaytadan urinib ko'ring:",
        "container_already_exited": "❌ Konteyner {container_number} allaqachon terminaldan chiqgan!\n\n📅 Chiqish sanasi: {exit_date}\n\nBoshqa konteyner raqamini kiriting:",
        "ask_exit_date": "📅 Konteyner chiqish sanasini kiriting (formatlar: 2025-10-28 yoki 28.10.2025 yoki 28/10/2025 yoki 28-10-2025).\nSoatlar va daqiqalar ixtiyoriy (masalan: 2025-10-28 14:30):",
        "ask_exit_transport_type": "🚛 Chiqish uchun transport turini tanlang:",
        "ask_exit_transport_number": "📝 Chiqish uchun transport raqamini kiriting (yuk mashinasi yoki vagon raqami):",
        "ask_exit_train_number": "🚂 Poyezd raqamini kiriting:",
        "ask_destination_station": "📍 Manzilinchi bekatni kiriting (stansiyani).\nAgar manzilinchi bakat noma'lum bo'lsa 'O'tkazib yuborish' tugmasini bosing:",
        "ask_crane_operations": "🏗️ Kran operatsiyasining qo'shimcha sana va vaqtini kiriting (ixtiyoriy).\nFormat: 2025-10-28 14:30\n\nAgar qo'shimcha operatsiya bo'lmasa 'O'tkazib yuborish' tugmasini bosing:",
        "ask_exit_photos": "📸 Konteyner chiqishining fotosuratlarini yuboring (ixtiyoriy).\nTugagach, 'Tayyor' yoki 'O'tkazib yuborish' tugmasini bosing:",
        "invalid_exit_date": "❌ Sana formati noto'g'ri!\nQaytadan urinib ko'ring (2025-10-28 yoki 28.10.2025):",
        "exit_date_before_entry": "❌ Chiqish sanasi kirish sanasidan ilgari bo'lishi mumkin emas!\n\n📅 Kirish sanasi: {entry_date}\n\nTo'g'ri sanani kiriting:",
        "error_exit_text": "❌ Iltimos, matnli xabar yuboring",
        "invalid_crane_date": "❌ Kran operatsiyasi sana formati noto'g'ri!\nQaytadan urinib ko'ring (2025-10-28 14:30):",
        "crane_operation_added": "✅ Operatsiya qo'shildi ({operation_date})\n\nYana sana kiriting yoki 'Tayyor' tugmasini bosing:",
        "exit_photos_loading": "⏳ Fotosurat qabul qilindi: {count}",
        "exit_photos_received": "✅ Fotosurat qabul qilindi! Jami: {count}\nYana fotosurat yuboring yoki 'Tayyor' tugmasini bosing:",
        # Exit summary fields
        "summary_exit_date": "Chiqish sanasi",
        "summary_exit_transport": "Chiqish transporti",
        "summary_exit_transport_num": "Transport raqami",
        "summary_exit_train_num": "Poyezd raqami",
        "summary_destination": "Manzilinchi bakat",
        "summary_crane_ops": "Kran operatsiyalari",
        "summary_dwell_time": "Turish vaqti",
        # Exit entry info labels (for enhanced display)
        "exit_entry_info_header": "Kirish paytidagi ma'lumotlar",
        "exit_entry_client": "Mijoz",
        "exit_entry_cargo": "Yuk",
        "exit_entry_owner": "Konteyner egasi",
        "exit_entry_location": "Joylashuv",
        "exit_entry_weight": "Yuk og'irligi",
        "exit_entry_notes": "Izohlar",
        "exit_photos_header": "Chiqish paytidagi fotosuratlar",
        "entry_photos_header": "Kirish paytidagi fotosuratlar",
        "no_photos_available": "Fotosuratlar mavjud emas",
        # Confirmation
        "exit_confirmation_header": "📋 Chiqish ma'lumotlarini tekshiring:",
        "exit_confirmation_question": "Hammasi to'g'rimi? Chiqishni tasdiqlaysizmi?",
        "exit_created": "✅ Chiqish muvaffaqiyatli ro'yxatdan o'tdi!\n\nKonteyner: {container}\nChiqish sanasi: {exit_date}\n⏱️ Turish vaqti: {dwell_time} kun",
        "error_exit_creating": "❌ Chiqishni ro'yxatdan o'tkazishda xatolik:\n{error}",
        "exit_cancelled": "❌ Chiqishni ro'yxatdan o'tkazish bekor qilindi",
        # Crane operation flow
        "btn_crane_operation": "🏗️ Kran",
        "start_crane_operation": "Kran operatsiyasini qo'shish.\n\n📝 Konteyner raqamini kiriting:",
        "crane_op_container_not_found": "❌ Konteyner {container_number} terminalda topilmadi!\n\nRaqamni tekshiring va qaytadan urinib ko'ring:",
        "crane_op_added": "✅ Kran operatsiyasi qo'shildi!\n\n📦 Konteyner: {container_number}\n🕐 Vaqt: {operation_time}\n📊 Jami operatsiyalar: {total_count}\n\nYana operatsiya qo'shishni xohlaysizmi?",
        "crane_op_error": "❌ Operatsiya qo'shishda xatolik:\n{error}",
        "crane_op_completed": "✅ Operatsiyalar saqlandi!\n\n📦 Konteyner: {container_number}\n📊 Jami qo'shildi: {count} operatsiya",
        "btn_add_more_crane_op": "➕ Yana qo'shish",
        "btn_done_crane_op": "✅ Tayyor",
        # Customer pre-order translations
        "customer_welcome": (
            "Oldindan buyurtma tizimiga xush kelibsiz! 📦\n\n"
            "Boshqarish uchun quyidagi tugmalardan foydalaning:\n"
            "📦 Buyurtma yaratish - kirish uchun buyurtma yaratish\n"
            "📋 Mening buyurtmalarim - buyurtmalaringizni ko'rish\n"
            "❌ Buyurtmani bekor qilish - faol buyurtmani bekor qilish"
        ),
        "customer_help": (
            "📦 Mijozlar uchun oldindan buyurtma tizimi\n\n"
            "Buyurtma yaratish uchun 📦 Buyurtma yaratish tugmasini bosing\n\n"
            "Buyurtma yaratishda:\n"
            "1️⃣ Yuk mashinasi rasmini yuboring\n"
            "2️⃣ Avtomobil raqamini tasdiqlang\n"
            "3️⃣ Operatsiya turini tanlang\n\n"
            "Mashina terminalga kelganda, qo'riqchi buyurtmangizni avtomatik topadi."
        ),
        "btn_create_order": "📦 Buyurtma yaratish",
        "btn_my_orders": "📋 Mening buyurtmalarim",
        "btn_cancel_order": "❌ Buyurtmani bekor qilish",
        "btn_load": "📥 Yuklash",
        "btn_unload": "📤 Tushirish",
        "btn_edit": "✏️ O'zgartirish",
        "btn_back": "◀️ Orqaga",
        "btn_confirm_cancel": "✅ Ha, bekor qilish",
        "btn_no": "❌ Yo'q",
        "operation_load_short": "Yukl.",
        "operation_unload_short": "Tush.",
        # Customer order creation flow (multi-plate)
        "customer_enter_plates": (
            "📝 <b>Avtomobil raqamlarini kiriting</b>\n\n"
            "Bir nechta raqamlarni har biri yangi qatordan kiritish mumkin:\n\n"
            "<code>01A123BC\n"
            "01B456DE\n"
            "01C789FG</code>"
        ),
        "customer_plates_invalid": "❌ Iltimos, kamida bitta to'g'ri raqam kiriting (kamida 3 ta belgi)",
        "customer_ask_operation_for_plate": "📊 <b>Avtomobil {index}/{total}</b>\n\n🚛 Raqam: <b>{plate}</b>\n\nOperatsiya turini tanlang:",
        "customer_summary_header": "📋 Buyurtmalarni tekshiring:",
        "customer_confirm_all": "Barcha buyurtmalarni tasdiqlaysizmi?",
        "customer_orders_created": "✅ <b>{count}</b> ta buyurtma muvaffaqiyatli yaratildi!\n\nTerminalga kirishda buyurtmalaringiz avtomatik topiladi.",
        "customer_orders_partial": (
            "⚠️ {total} tadan {created} ta buyurtma yaratildi.\n\nXatolar:\n{errors}"
        ),
        "customer_order_error": "❌ Buyurtma yaratishda xatolik:\n{error}",
        # Legacy keys (for compatibility)
        "customer_ask_truck_photo": "📸 Yuk mashinasi rasmini yuboring:",
        "customer_enter_plate": "📝 Avtomobil raqamini kiriting:",
        "customer_plate_text_only": "❌ Iltimos, raqamni matn sifatida kiriting",
        "customer_ask_operation_type": "📊 Operatsiya turini tanlang:",
        "customer_confirm_header": "📋 Buyurtmani tekshiring:",
        "customer_confirm_question": "Hammasi to'g'rimi?",
        # Customer order viewing
        "customer_no_orders": "📋 Sizda buyurtmalar yo'q",
        "customer_orders_header": "📋 Sizning buyurtmalaringiz:\n",
        "customer_order_item": "#{id} | {plate} | {operation} | {status}\n",
        "customer_no_pending_orders": "📋 Sizda bekor qilish uchun faol buyurtmalar yo'q",
        "customer_select_order_cancel": "📋 Bekor qilish uchun buyurtmani tanlang:",
        "customer_confirm_cancel_question": "❓ Siz rostdan ham bu buyurtmani bekor qilmoqchimisiz?",
        "customer_order_cancelled": "✅ {plate} raqamli buyurtma bekor qilindi",
        "customer_cancel_error": "❌ Bekor qilishda xatolik: {error}",
        # Customer container cabinet
        "btn_my_containers": "📦 Mening konteynerlarim",
        "container_list_header": "📦 <b>Terminaldagi konteynerlar</b>\n\nJami: {count}",
        "container_list_empty": "📋 Terminalda kompaniyangizning konteynerlari yo'q",
        "container_no_company": "❌ Siz kompaniyaga biriktirilmagansiz. Administratorga murojaat qiling.",
        "days_short": "kun",
        "btn_search_container": "🔍 Qidirish",
        "btn_photos": "Rasmlar",
        "btn_back_to_list": "◀️ Ro'yxatga",
        "btn_cancel_search": "❌ Bekor qilish",
        "container_search_prompt": "🔍 Konteyner raqamini kiriting:",
        "container_search_not_found": "❌ Konteyner topilmadi yoki terminaldan chiqarilgan",
        "container_detail": (
            "📦 <b>Konteyner {number}</b>\n\n"
            "📊 Holat: {status}\n"
            "📐 Turi: {iso_type}\n"
            "📅 Kirish: {entry_date}\n"
            "⏱ Terminalda: <b>{dwell_days} kun</b>\n"
        ),
        "container_detail_cargo": "📦 Yuk: {cargo}",
        "container_detail_weight": "⚖️ Og'irlik: {weight} kg",
        "container_detail_location": "📍 Joylashuv: {location}",
        "container_detail_owner": "🏢 Egasi: {owner}",
        "container_detail_transport": "🚛 Transport: {type} ({number})",
        "photos_sending": "📤 Rasmlar yuborilmoqda...",
        "photos_sent": "✅ {count} ta rasm yuborildi",
        "photos_none": "📷 Rasmlar topilmadi",
        # Customer vehicle notifications
        "customer_vehicle_entered": (
            "✅ Sizning avtomobilingiz terminalga kirdi!\n\n"
            "🚛 Raqam: <b>{plate}</b>\n"
            "📅 Vaqt: {time}\n\n"
            "Keyingi xabarlarni kuting."
        ),
        "customer_vehicle_exited": (
            "🏁 Sizning avtomobilingiz terminaldan chiqdi!\n\n"
            "🚛 Raqam: <b>{plate}</b>\n"
            "📅 Vaqt: {time}"
        ),
        "customer_vehicle_cancelled": (
            "❌ Kirish uchun arizangiz bekor qilindi.\n\n"
            "🚛 Raqam: <b>{plate}</b>\n\n"
            "Agar bu xato bo'lsa, yangi ariza yarating."
        ),
        # Customer order status display
        "order_status_pending": "Kutmoqda",
        "order_status_matched": "Topildi",
        "order_status_completed": "Bajarildi",
        "order_status_cancelled": "Bekor qilindi",
        # Summary fields for customer orders
        "summary_plate_number": "Avtomobil raqami",
        "summary_operation_type": "Operatsiya turi",
        "operation_load": "Yuklash",
        "operation_unload": "Tushirish",
        # Customer access messages
        "customer_access_denied": (
            "❌ <b>Kirish taqiqlangan</b>\n\n"
            "Sizda oldindan buyurtma tizimiga kirish huquqi yo'q.\n"
            "Ro'yxatdan o'tish uchun administrator bilan bog'laning."
        ),
        "customer_access_pending": (
            "⏳ <b>Tasdiqlash kutilmoqda</b>\n\n"
            "Sizning kirish so'rovingiz ko'rib chiqilmoqda.\n"
            "Administrator tasdiqlashini kuting."
        ),
        # Gate matching messages (shown to security when pre-order matched)
        "preorder_match_found": (
            "✅ <b>Mijoz buyurtmasi topildi!</b>\n\n"
            "👤 Mijoz: {customer_name}\n"
            "🚗 Avtomobil raqami: {plate_number}\n"
            "📊 Operatsiya turi: {operation_type}\n\n"
            "Buyurtma avtomatik ravishda yozuvga bog'lanadi."
        ),
        "preorder_match_operation_load": "Yuklash",
        "preorder_match_operation_unload": "Tushirish",
        "preorder_matched_success": "✅ Mijoz buyurtmasi #{order_id} yozuvga muvaffaqiyatli bog'landi",
    },
}


def get_text(key: str, lang: str = "ru", **kwargs) -> str:
    """
    Get translated text by key.

    Args:
        key: Translation key
        lang: Language code ('ru' or 'uz')
        **kwargs: Format parameters for the text

    Returns:
        Translated and formatted text
    """
    text = TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get(
        key, TRANSLATIONS["ru"].get(key, key)
    )
    if kwargs:
        return text.format(**kwargs)
    return text


# Map database values (Russian) to display values by language
STATUS_DISPLAY = {
    "LADEN": {"ru": "Гружёный", "uz": "Yuklangan"},
    "EMPTY": {"ru": "Порожний", "uz": "Bo'sh"},
}

TRANSPORT_DISPLAY = {
    "TRUCK": {"ru": "Авто", "uz": "Yuk mashinasi"},
    "WAGON": {"ru": "Вагон", "uz": "Vagon"},
}


def get_status_display(status: str, lang: str = "ru") -> str:
    """Get status display text in selected language."""
    return STATUS_DISPLAY.get(status, {}).get(lang, status)


def get_transport_display(transport: str, lang: str = "ru") -> str:
    """Get transport type display text in selected language."""
    return TRANSPORT_DISPLAY.get(transport, {}).get(lang, transport)
