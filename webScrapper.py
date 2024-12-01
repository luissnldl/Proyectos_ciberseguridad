import requests
from bs4 import BeautifulSoup
import pandas as pd

def obtener_html(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Error al obtener la página. Código de estado: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error al hacer la solicitud: {e}")
        return None

def parsear_html_jd(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    productos = []

    for item in soup.find_all('span', class_='itemContainer'):
        nombre = item.find('span', class_='itemTitle').text.strip()
        
        precios = item.find_all('span', attrs={'data-oi-price': True}) # Estos son los precios (<span> con el atributo data-oi-price.)
        precio_sin_descuento = precios[0].text.strip()
        precio_con_descuento = precios[1].text.strip()

        descuento = item.find('span', class_='sav').text.replace("Descuento", "").strip() # Quito la palabra Descuento

        productos.append({
            'nombre': nombre,
            'precio_sin_descuento': precio_sin_descuento,
            'precio_con_descuento': precio_con_descuento,
            'descuento': descuento
        })
    
    return productos

def scrapear_productos(url):
    html = obtener_html(url)
    if html:
        productos = parsear_html_jd(html)
        return productos
    else:
        return []

def guardar_en_csv(productos, nombre_archivo='productos.csv'):
    df = pd.DataFrame(productos)
    df.to_csv(nombre_archivo, index=False)
    print(f"Datos guardados en {nombre_archivo}")


if __name__ == "__main__":
    # La pagina de jd pagina de 72 en 72 articulos
    url = "https://www.jdsports.es/hombre/ropa-de-hombre/ofertas/" 
    productos = scrapear_productos(url)
    
    
    if productos:
        guardar_en_csv(productos)
    else:
        print("No se encontraron productos.")
