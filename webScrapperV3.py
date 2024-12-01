import requests
from bs4 import BeautifulSoup
import pandas as pd
from pymongo import MongoClient

CSV_NAME = 'productos.csv'

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

    for item in soup.find_all('span', class_='itemContainer'):  # Asegúrate de usar la clase correcta
        nombre = item.find('span', class_='itemTitle').text.strip()
        imagen = item.find('img').get('src') if item.find('img') else None

        # Manejo de descuento y precios
        descuento = item.find('span', class_='sav')
        precios = item.find_all('span', attrs={'data-oi-price': True})

        if descuento:
            descuento = descuento.text.replace("Descuento", "").strip()
            precio_sin_descuento = precios[0].text.strip() if len(precios) > 0 else None
            precio_con_descuento = precios[1].text.strip() if len(precios) > 1 else None
        else:
            descuento = None
            precio_sin_descuento = item.find('span', class_='pri').text.strip() if item.find('span', class_='pri') else None
            precio_con_descuento = None

        productos.append({
            'nombre': nombre,
            'precio_sin_descuento': precio_sin_descuento,
            'precio_con_descuento': precio_con_descuento,
            'descuento': descuento,
            'imagen': imagen
        })
    
    return productos

def scrapear_productos(url):
    productos_totales = []
    while url:
        html = obtener_html(url)
        if html:
            productos = parsear_html_jd(html)
            productos_totales.extend(productos)
            
            # Lógica para pasar a la siguiente página
            if 'from' in url:
                current_page_number = int(url.split('=')[-1])
                next_page_number = current_page_number + 72
                url = f'{url.split("?")[0]}?from={next_page_number}'
            else:
                url = f'{url}?from=72'  # URL de la siguiente página (De normal carga 72 productos la pagina de jd)
        else:
            break

    return productos_totales

def guardar_en_csv(productos, nombre_archivo=CSV_NAME):
    df = pd.DataFrame(productos)
    df.to_csv(nombre_archivo, index=False)
    print(f"Datos guardados en {nombre_archivo}")


def cargar_csv_a_mongodb(csv_file, db_name, collection_name, mongo_uri='mongodb+srv://luisnaharroll:OGBGYAaqHpxM0iez@scrapped.l0q8l.mongodb.net/?retryWrites=true&w=majority&appName=Scrapped'):
    """
    Carga los datos de un archivo CSV a una colección de MongoDB.

    Parámetros:
    - csv_file (str): Ruta del archivo CSV que se va a cargar.
    - db_name (str): Nombre de la base de datos de MongoDB.
    - collection_name (str): Nombre de la colección de MongoDB.
    - mongo_uri (str): URI de conexión a MongoDB (por defecto es localhost:27017).

    Retorna:
    - None: Inserta los documentos en MongoDB.
    """
    # Conexión a MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]  # Conectar a la base de datos
    collection = db[collection_name]  # Seleccionar la colección

    # Leer el archivo CSV con pandas
    df = pd.read_csv(csv_file)

    # Convertir el DataFrame a una lista de diccionarios (cada fila como un documento)
    data_dict = df.to_dict(orient='records')

    # Insertar los datos en MongoDB
    try:
        collection.insert_many(data_dict)
        print(f"Datos insertados correctamente en la colección '{collection_name}' de la base de datos '{db_name}'.")
    except Exception as e:
        print(f"Error al insertar los datos: {e}")
    finally:
        # Cerrar la conexión
        client.close()


if __name__ == "__main__":
    url = input("Introduce la URL de la categoría de JD Sports: ") 
    productos = scrapear_productos(url)
    
    if productos:
        guardar_en_csv(productos)
        cargar_csv_a_mongodb(CSV_NAME, 'scrapped', 'products')
    else:
        print("No se encontraron productos.")


"""VERSION CON TODO FUNCIONAL GUARDANDO CSV EN MONGO"""