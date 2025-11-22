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

# -------------------------------------------------------------------
# --- УНИВЕРСАЛЬНЫЙ СЛОВАРЬ КОНФИГУРАЦИИ ПОРТАЛОВ ---
# -------------------------------------------------------------------

# Выберите, какой профиль использовать для текущего запуска
ACTIVE_PROFILE = "CASA_SAPO" # <-- ИЗМЕНИТЕ ЭТО НА "IMOVIRTUAL" ИЛИ "CUSTOJUSTO" ДЛЯ ТЕСТА

 # --- крупные агрегаторы (высокая защита) ---
PROFILES = {
    "Idealista": {
        # --- ПАРАМЕТРЫ САЙТА  ---
        "BASE_URL": "https://www.idealista.pt/en/comprar-casas/lisboa/",
        "PAGINATION_QUERY": "pagina-", # Разделитель для номера страницы 
        "LINK_CONTAINER_SELECTOR": ".item-info-container", # Контейнер для ссылки
        "LINK_SELECTOR": "a.item-link", # Селектор самой ссылки внутри контейнера
        
        # --- ПАРАМЕТРЫ ЗАПУСКА ---
        "MAX_PAGES_TO_SCRAPE": 5, # Сколько страниц тестировать
        "MIN_DELAY_REQUEST": 5.0, # Этика Cloudflare
    },

    "CASA_SAPO": {
        # --- ПАРАМЕТРЫ САЙТА ---
        "BASE_URL": "https://casa.sapo.pt/en-gb/buy-apartments/sintra/",
        "PAGINATION_QUERY": "?pn=", # Разделитель для номера страницы (pn=2)
        "LINK_CONTAINER_SELECTOR": ".property-info-content", # Контейнер для ссылки
        "LINK_SELECTOR": "a.property-info", # Селектор самой ссылки внутри контейнера
        
        # --- ПАРАМЕТРЫ ЗАПУСКА ---
        "MAX_PAGES_TO_SCRAPE": 5, # Сколько страниц тестировать
        "MIN_DELAY_REQUEST": 5.0, # Этика Cloudflare
    },
    
    "IMOVIRTUAL": {
        "BASE_URL": "https://www.imovirtual.com/pt/resultados/comprar/apartamento/lisboa", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "?page=", 
        "LINK_CONTAINER_SELECTOR": ".ContentContainer", 
        "LINK_SELECTOR": "a.listing-item-link", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },


    # --- международные порталы (высокая / средняя защита) ---
        #cloudflare
        "Kyero": {
        "BASE_URL": "https://www.kyero.com/en/lisbon-district-property-for-sale-0l57088", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "?page=", 
        "LINK_CONTAINER_SELECTOR": ".flex-1 lg:w-3/4 lg:flex-[0_0_75%]", 
        "LINK_SELECTOR": "a.group/tile flex h-auto flex-1", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },
    
    #cloudflare - нужно можифицировать скрипт
    "rightmove": {
        "BASE_URL": "https://www.rightmove.co.uk/overseas-property-for-sale/find.html?searchLocation=Lisbon%2C%20Portugal&useLocationIdentifier=true&locationIdentifier=WORLD_REGION%5E165001&channel=OVERSEAS", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "?page=", 
        "LINK_CONTAINER_SELECTOR": ".flex-1 lg:w-3/4 lg:flex-[0_0_75%]", 
        "LINK_SELECTOR": "a.group/tile flex h-auto flex-1", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },
     

    #cloudflare - нужно можифицировать скрипт 
    "green-acres": {
        "BASE_URL": "https://www.green-acres.pt/property-for-sale/lisbon-municipality", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "?searchQuery=cn-pt-lg-en-city_id-gr_6266&p_n=", 
        "LINK_CONTAINER_SELECTOR": ".flex-1 lg:w-3/4 lg:flex-[0_0_75%]", 
        "LINK_SELECTOR": "a.group/tile flex h-auto flex-1", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },

        #cloudflare
    "propestar": {
        "BASE_URL": "https://www.properstar.pt/portugal/distrito-de-lisboa/venda/apartamento-casas", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "?p=", 
        "LINK_CONTAINER_SELECTOR": ".item-data", 
        "LINK_SELECTOR": "a.listing-title", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },

    # --- региональные специализированные порталы (высокая / средняя защита) ---
            #cloudflare, вернуться позже, проблема с запросами
    "supercasa": {
        "BASE_URL": "https://www.properstar.pt/portugal/distrito-de-lisboa/venda/apartamento-casas", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "?p=", 
        "LINK_CONTAINER_SELECTOR": ".item-data", 
        "LINK_SELECTOR": "a.listing-title", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },
        #cloudflare, вернуться позже,
        "TagusNovo": {
        "BASE_URL": "https://www.properstar.pt/portugal/distrito-de-lisboa/venda/apartamento-casas", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "?p=", 
        "LINK_CONTAINER_SELECTOR": ".item-data", 
        "LINK_SELECTOR": "a.listing-title", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },

     #cloudflare,
        "PortugalHomes": {
        "BASE_URL": "https://www.portugalhomes.com/properties/for/sale/in/lisbon?category=1&search_locations=&location-search-input=&currency-select=EUR&metric-imperial-select=SQM&price-from=min&price-to=max&plot-size-from=min&plot-size-to=max&beds-from=1&beds-to=max&bathrooms-from=1&bathrooms-to=max&order-input=&for-sale-in-location=lisbon&country_code=", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "&page=", 
        "LINK_CONTAINER_SELECTOR": ".property-card-title-container", 
        "LINK_SELECTOR": "a", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },
     
        # --- Люкс сегмент (может быть проще из-за меньшего трафика) ---
         #cloudflare,
        "JamesEdition": {
        "BASE_URL": "https://www.jamesedition.com/real_estate/portugal?real_estate_type[]=apartment&real_estate_type[]=penthouse&real_estate_type[]=condo&real_estate_type[]=co_op", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "&page=", 
        "LINK_CONTAINER_SELECTOR": ".ListingCard", 
        "LINK_SELECTOR": "a", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },   
       # --- Нишевые/информационные порталы (потенциально самые простые) ---
             #cloudflare, вернуться позже, другая пагинация
        "A_Place_in_the_Sun": {
        "BASE_URL": "https://www.aplaceinthesun.com/property/portugal/from/0/to/max/currency/gbp/order-by/datelisteddesc/propperpage/24/page/1?property_types=apartment", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "&page=", 
        "LINK_CONTAINER_SELECTOR": ".ListingCard", 
        "LINK_SELECTOR": "a", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },   

        "Era_Portugal": {
        "BASE_URL": "https://www.era.pt/en/buy?ob=1&tp=1,2&ord=3&ir=1&nr=0&dt=11", # <-- ЗАМЕНИТЬ НА РЕАЛЬНЫЙ АДРЕС
        "PAGINATION_QUERY": "&page=", 
        "LINK_CONTAINER_SELECTOR": ".card", 
        "LINK_SELECTOR": "a.card__gallery", 
        "MAX_PAGES_TO_SCRAPE": 3,
        "MIN_DELAY_REQUEST": 4.0, # Можно попробовать чуть меньшую задержку
    },   

}