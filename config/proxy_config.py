# --- proxy_config.py ---

# ВАШИ УЧЕТНЫЕ ДАННЫЕ EVOMI (примерный формат)
PROXY_CONFIG = {
    # 1. Шлюз/Хост: IP-адрес или домен  прокси-провайдера (например, gateway.evomi.com)
    "GATEWAY_HOST": "core-residential.evomi.com",  # <-- ЗАМЕНИТЬ
    
    # 2. Порт: Номер порта, предоставленный Evomi (например, 8000)
    "PORT": "1000",  # <-- ЗАМЕНИТЬ
    
    # 3. Логин и Пароль для аутентификации на прокси
    "USERNAME": "yunnamax0",  # <-- ЗАМЕНИТЬ
    "PASSWORD": "JKP4w7x1xrGOCecsmeNw",  # <-- ЗАМЕНИТЬ
}

# Комбинированный формат для передачи в Chrome Options: username:password@host:port
PROXY_ADDRESS = (
    f"http://{PROXY_CONFIG['USERNAME']}:{PROXY_CONFIG['PASSWORD']}@"
    f"{PROXY_CONFIG['GATEWAY_HOST']}:{PROXY_CONFIG['PORT']}"
)