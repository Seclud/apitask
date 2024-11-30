import requests
from bs4 import BeautifulSoup


# Основной метод парсинга
def parse_page(url):
    response = requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')

    product_containers = soup.find_all('article', class_='l-product')

    products = []
    for container in product_containers:
        name = container.find('div', class_='l-product__name').find('span').text
        price = container.find('div', class_='l-product__price-base').text if container.find('div', class_='l-product__price-base') else 'N/A'
        price = price.strip()
        products.append({'name': name, 'price': price})

    return products, soup

# Метод, чтобы получить ссылку на следующую страницу
def get_next_page_url(soup):
    next_page = soup.find('a', id='navigation_2_next_page')
    return next_page['href'] if next_page else None


# Метод, который перебирает все страницы категории
def scrape_category(base_url, start_url):
    url = start_url
    all_products = []

    while url:
        products, soup = parse_page(url)
        all_products.extend(products)

        next_page_url = get_next_page_url(soup)
        if next_page_url:
            url = base_url + next_page_url
        else:
            url = None

    return all_products



def get_price():
    base_url = 'https://www.maxidom.ru'
    start_url = 'https://www.maxidom.ru/catalog/vanny/'

    all_products = scrape_category(base_url, start_url)
    return all_products

# all_products = get_price()
# print(all_products)
# for product in all_products:
#     print(f"Название товара: {product['name']}, Цена: {product['price']}")