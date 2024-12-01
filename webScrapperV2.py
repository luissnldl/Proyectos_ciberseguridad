import requests
from bs4 import BeautifulSoup
import pandas as pd

def obtener_html(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Error al obtener la página {url}. Código de estado: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error al hacer la solicitud: {e}")
        return None

def parsear_html_jd(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    productos = []

    for item in soup.find_all('span', class_='itemContainer'):  # Cambia a 'div' en lugar de 'span'
        
        nombre = item.find('span', class_='itemTitle').text.strip()
        descuento = item.find('span', class_='sav')
        imagen = item.find('img').get('src')

        if descuento:
            descuento = descuento.text.replace("Descuento", "").strip()
            precios = item.find_all('span', attrs={'data-oi-price': True})  # Obtener precios
            precio_sin_descuento = precios[0].text.strip()
            precio_con_descuento = precios[1].text.strip() if len(precios) > 1 else None  # Manejar el caso donde solo hay un precio

        else:
            descuento = None  # Manejar si no hay descuento
            precio_con_descuento = None

            precio_sin_descuento = item.find('span', class_='pri').text.strip()
            
        productos.append({
            'nombre': nombre,
            'precio_sin_descuento': precio_sin_descuento,
            'precio_con_descuento': precio_con_descuento,
            'descuento': descuento,
            'imagen': imagen
            
        })
    
    return productos

def scrapear_productos(url):
    productos_totales = []  # Lista para almacenar todos los productos
    while url:
        html = obtener_html(url)
        if html:
            productos = parsear_html_jd(html)
            productos_totales.extend(productos)  # Agregar los productos de esta página a la lista total
            
            # Lógica para la siguiente página
            if 'from' in url:
                current_page_number = int(url.split('=')[-1])
                next_page_number = current_page_number + 72
                url = f'https://www.jdsports.es/hombre/ropa-de-hombre/ofertas/?from={next_page_number}'
            else:
                url = 'https://www.jdsports.es/hombre/ropa-de-hombre/ofertas/?from=72'  # URL de la siguiente página (De normal carga 72 productos la pagina de jd)
        else:
            break  # Salir del bucle si no se pudo obtener HTML

    return productos_totales

def guardar_en_csv(productos, nombre_archivo='productos.csv'):
    df = pd.DataFrame(productos)
    df.to_csv(nombre_archivo, index=False)
    print(f"Datos guardados en {nombre_archivo}")


if __name__ == "__main__":
    url = "https://www.jdsports.es/hombre/ropa-de-hombre/ofertas/" 
    productos = scrapear_productos(url)
    
    if productos:
        guardar_en_csv(productos)
    else:
        print("No se encontraron productos.")
