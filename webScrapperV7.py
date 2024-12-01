from selenium import webdriver #Interactuar con Navegador 
from selenium.webdriver.edge.service import Service
from bs4 import BeautifulSoup
import pandas as pd
from pymongo import MongoClient
from selenium.webdriver.common.by import By                     # Para encontrar cosas por nombre de clase por ej con selenium
from selenium.webdriver.support.ui import WebDriverWait         # Esperar que esten listos elementos
from selenium.webdriver.support import expected_conditions as EC #Proporciona condiciones predefinidas que se utilizan con WebDriverWait para esperar eventos

CSV_NAME = 'productos.csv'
JD_GENERIC_URL = 'https://www.jdsports.es/'
MONGO_URI = 'mongodb+srv://luisnaharroll:OGBGYAaqHpxM0iez@scrapped.l0q8l.mongodb.net/?retryWrites=true&w=majority&appName=Scrapped'
cookies_aceptadas = False

def aceptar_cookies(driver):
    global cookies_aceptadas
    try:
        # Esperar a que el botón de aceptar cookies esté presente
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "accept-all-cookies"))  # Cambia esto por el selector adecuado
        )

        # Hacer clic en el botón de aceptar cookies
        cookie_button = driver.find_element(By.CLASS_NAME, "accept-all-cookies")  # Cambia esto por el selector adecuado
        cookie_button.click()
        cookies_aceptadas = True
        print("[*]Cookies aceptadas.")
    except Exception as e:
        print(f"[*]No se pudo aceptar las cookies: {e}")

def create_driver():
    try:
        # Configuración del WebDriver de Microsoft Edge
        edge_driver_path = 'C:/Users/luisn/Desktop/msedgedriver.exe'
        service = Service(executable_path=edge_driver_path)
        
        # Iniciar el navegador Edge
        options = webdriver.EdgeOptions()
        
        # Deshabilitar imágenes
        #prefs = {"profile.managed_default_content_settings.images": 2}
        #options.add_experimental_option("prefs", prefs)
        options.add_argument("--disable-gpu")  # Desactiva la aceleración de hardware (Reducir la carga de gráficos y mejorar el rendimiento.)
        #options.add_argument('--headless')
        options.add_argument("--incognito")  # Activa el modo incógnito
        driver = webdriver.Edge(service=service, options=options)
        return driver
    
    except Exception as e:
        print(f"Error al crear el driver: {e}")
        return None

# Función modificada para usar Selenium en lugar de requests
def obtener_html(url, driver):
    try:
        # Cargar la página y aceptar cookies
        driver.get(url)
        if not cookies_aceptadas:
            aceptar_cookies(driver)
        
        # Asegurarse de que las imágenes se carguen (forzando scroll si es necesario)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Esperar explícitamente a que los elementos clave estén disponibles
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dynamicColoursContainer"))
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "img"))
        )
        
        # Obtener el HTML de la página
        html = driver.page_source
        
        if not html:
            print("[*] No se pudo obtener el HTML, página posiblemente vacía.")
            return None
        
        return html
    
    except Exception as e:
        print(f"Error al obtener la página con Selenium: {e}")
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

        # pillar los colores que se generan de manera dinamica en un div clase dynamicColours que dentro tiene spans en cuya clase estan los colores
        div_colores = item.find('div', class_='dynamicColours')
        colores= []

        if div_colores:
            #print("Hay divColores")
            spans = div_colores.find_all('span')
            for span in spans:
                #print('span en divColores')
                clase_span = ' '.join(span.get('class', []))  # Si el span no tiene ninguna clase, devuelve una lista vacía
                colores.append(clase_span)  # Añadir cada clase a la lista de colores
        #else:
            #print('No hay divColores :(')


        colores_texto = ', '.join(colores).replace('active, ', '') #Los uno con , y quito el atributo active de las clases css

        productos.append({
            'nombre': nombre,
            'precio_sin_descuento': precio_sin_descuento,
            'precio_con_descuento': precio_con_descuento,
            'descuento': descuento,
            'imagen': imagen,
            'colores': colores_texto
        })
    
    return productos

def scrapear_productos(url, driver):
    productos_totales = []
    while url:
        html = obtener_html(url, driver) # Usa selenium
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
    print(f"[*]Datos guardados en {nombre_archivo}")


def verificar_o_crear_coleccion(mongo_client, nombre_bd, nombre_coleccion):
    db = mongo_client[nombre_bd]

    # Listar todas las colecciones en la base de datos
    colecciones = db.list_collection_names()
    
    # Verificar si la colección ya existe
    if nombre_coleccion in colecciones:
        print(f"[*]La colección '{nombre_coleccion}' ya existe en la base de datos '{nombre_bd}', trabajando en ella.")
    else:
        print(f"[*]La colección '{nombre_coleccion}' no existe. Creándola ahora...")
        # Crear la colección insertando un documento inicial
        db[nombre_coleccion].insert_one({"mensaje": "Colección creada"})
        print(f"[*]Colección '{nombre_coleccion}' creada en la base de datos '{nombre_bd}'.")


def cargar_csv_a_mongodb(csv_file, db_name, collection_name, mongo_uri=MONGO_URI):
    """
    Carga los datos de un archivo CSV a una colección de MongoDB,
    verificando si los documentos son nuevos o tienen cambios.

    Parámetros:
    - csv_file (str): Ruta del archivo CSV que se va a cargar.
    - db_name (str): Nombre de la base de datos de MongoDB.
    - collection_name (str): Nombre de la colección de MongoDB.
    - mongo_uri (str): URI de conexión a MongoDB.

    Retorna:
    - None: Inserta o actualiza los documentos en MongoDB.
    """
    # Conexión a MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    
    verificar_o_crear_coleccion(client, db_name, collection_name)

    # Leer el archivo CSV con pandas
    df = pd.read_csv(csv_file)

    # Convertir el DataFrame a una lista de diccionarios (cada fila como un documento)
    data_dict = df.to_dict(orient='records')

    # Iterar sobre cada producto y verificar su estado
    for producto in data_dict:
        resultado = procesar_producto(producto, db[collection_name])

        if resultado["nuevo"]:
            print(f"Producto nuevo añadido: {producto['nombre']}")
        elif resultado["actualizado"]:
            print(f"Producto actualizado: {producto['nombre']}")
            print(f"Cambios detectados: {resultado['cambios']}")
        else:
            print(f"Producto sin cambios: {producto['nombre']}")

    # Cerrar la conexión
    client.close()

def procesar_producto(nuevo_producto, collection):
    """
    Comprueba si un producto es nuevo o tiene cambios en la colección de MongoDB.

    Args:
        nuevo_producto (dict): Diccionario con los datos del nuevo producto.
        collection (pymongo.collection.Collection): La colección de MongoDB.

    Returns:
        dict: Resultado con información sobre si el producto es nuevo o tiene cambios.
    """
    resultado = {
        "nuevo": False,
        "actualizado": False,
        "cambios": {}
    }

    # Buscar el producto por un identificador único (por ejemplo, el nombre o ID)
    producto_existente = collection.find_one({"nombre": nuevo_producto["nombre"]})

    if not producto_existente:
        # Si no existe, insertar el producto
        collection.insert_one(nuevo_producto)
        resultado["nuevo"] = True
    else:
        # Comparar campos para detectar cambios
        for key, value in nuevo_producto.items():
            # Si ambos valores son NaN, ignóralos
            if pd.isna(producto_existente.get(key)) and pd.isna(value):
                continue
            # Si hay diferencias, agrega el cambio
            if producto_existente.get(key) != value:
                resultado["cambios"][key] = {
                    "antes": producto_existente.get(key),
                    "ahora": value
                }

        if resultado["cambios"]:
            # Actualizar el producto en la colección
            collection.update_one(
                {"_id": producto_existente["_id"]},
                {"$set": nuevo_producto}
            )
            resultado["actualizado"] = True

    return resultado



if __name__ == "__main__": #! Ojo que el replace hardcodeado quita a hierro el inicio de la url para formar nombre de bd!
    url = input("[*] Introduce la URL de la categoría de JD Sports: ")
    url_bd_name = url.replace(JD_GENERIC_URL, '')

    driver = create_driver()
    if not driver:
        print("[*] No se pudo iniciar el WebDriver. Saliendo del programa.")
        exit(1)

    productos = scrapear_productos(url, driver)
    driver.quit()
    
    if productos:
        guardar_en_csv(productos)
        cargar_csv_a_mongodb(CSV_NAME, 'scrapped', url_bd_name)
    else:
        print("[*]No se encontraron productos.")
