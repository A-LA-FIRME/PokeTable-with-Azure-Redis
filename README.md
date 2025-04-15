# PokéCache - Demo de Azure Cache for Redis con Flask

Esta aplicación muestra cómo implementar Azure Cache for Redis con Python y Flask utilizando la PokeAPI como fuente de datos.

## Características

- Consulta y almacenamiento en caché de datos de la PokeAPI
- Interfaz de usuario con Bootstrap y DataTables
- Gestión eficiente de la caché con control de tiempo de expiración
- Visualización de detalles de Pokémon
- Funcionalidad para limpiar la caché

## Requisitos

- Python 3.7+
- Una instancia de Azure Cache for Redis
- Acceso a Internet (para consultar la PokeAPI)

## Configuración

1. Clonar este repositorio
2. Instalar las dependencias:
   ```
   pip install -r requirements.txt
   ```

3. Crear un archivo `.env` en el directorio raíz del proyecto con las siguientes variables:
   ```
   REDIS_CONNECTION_STRING=your-redis-connection-string
   ```

## Estructura del Proyecto

```
├── app.py                # Aplicación principal de Flask
├── requirements.txt      # Dependencias del proyecto
├── templates/
│   └── index.html        # Plantilla HTML para la interfaz de usuario
├── static/
│   └── css
│       └── style.css     # CSS Personalizado
│   └── js
│       └── main.js       # JS Personalizado
└── .env                  # Archivo de configuración (no incluido en el repositorio)
```

## Cómo Ejecutar

1. Asegúrate de tener configuradas las variables de entorno para la conexión a Redis
2. Ejecuta la aplicación:
   ```
   python app.py
   ```
3. Abre tu navegador en `http://localhost:5000`

## Cómo Funciona

### Flujo de datos

1. Un usuario solicita datos de Pokémon a través de la interfaz web
2. La aplicación Flask verifica si los datos existen en la caché de Redis
3. Si los datos están en caché, se devuelven inmediatamente
4. Si no están en caché, la aplicación consulta la PokeAPI
5. Los datos obtenidos se almacenan en Redis con un tiempo de expiración y se envían al usuario

### Tiempos de expiración

- Lista de Pokémon: 5 minutos
- Detalles de Pokémon individuales: 24 horas

## Despliegue en Azure

Para desplegar esta aplicación en Azure:

1. Crea una instancia de Azure Cache for Redis
2. Crea una App Service para Python
3. Configura las variables de entorno en la App Service
4. Despliega el código mediante Git, GitHub Actions o cualquier otro método de tu elección

## Beneficios de usar Redis Cache

- Reducción significativa en los tiempos de respuesta
- Menos solicitudes a la API externa, lo que evita posibles límites de tasa
- Mejor experiencia del usuario con respuestas más rápidas
- Reducción de la carga en el servidor de la aplicación

## Recursos Adicionales

- [Documentación de Azure Cache for Redis](https://docs.microsoft.com/es-es/azure/azure-cache-for-redis/)
- [Biblioteca redis-py](https://redis-py.readthedocs.io/)
- [PokeAPI](https://pokeapi.co/)
