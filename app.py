from flask import Flask, jsonify, render_template, request
import redis
import json
import requests
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()
app = Flask(__name__)

# Configurar sistema de logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, "app.log")

# Configurar el logger
handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Obtener la cadena de conexión Redis completa
REDIS_CONNECTION_STRING = os.environ.get('REDIS_CONNECTION_STRING')

# Verificar la configuración requerida
if not REDIS_CONNECTION_STRING:
    app.logger.warning("Cadena de conexión Redis no encontrada. Verifica tu archivo .env")

# Conexión a Redis usando la cadena de conexión
try:
    # Parsear la cadena de conexión en formato host:port,password=abc,ssl=true
    connection_parts = REDIS_CONNECTION_STRING.split(',')

    # El primer elemento debe contener host:port
    host_port = connection_parts[0].split(':')
    if len(host_port) != 2:
        raise ValueError("El formato de host:port es incorrecto")

    host = host_port[0]
    port = int(host_port[1])

    # Extraer password y ssl de los demás elementos
    password = None
    ssl = False

    for part in connection_parts[1:]:
        if part.startswith('password='):
            password = part.split('=', 1)[1]
        elif part.startswith('ssl='):
            ssl_value = part.split('=', 1)[1].lower()
            ssl = (ssl_value == 'true')

    # Crear conexión con los parámetros extraídos
    redis_client = redis.Redis(
        host=host,
        port=port,
        password=password,
        ssl=ssl,
        socket_timeout=15,
        socket_connect_timeout=15
    )

    redis_client.ping()
    app.logger.info("Conectado a Redis exitosamente!")
except Exception as e:
    app.logger.error(f"Error al conectar a Redis: {e}")
    redis_client = None
@app.route('/')
def index():
    """Renderiza la página principal"""
    app.logger.info("Página principal solicitada")
    return render_template('index.html')

@app.route('/api/pokemon')
def get_pokemon_list():
    """Obtiene una lista de Pokemon, usando la cache cuando sea posible"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)

    # Clave única para este conjunto de resultados
    cache_key = f"pokemon:list:{limit}:{offset}"

    # Verificar si Redis está disponible
    if redis_client:
        # Intentar obtener datos desde Redis
        cached_data = redis_client.get(cache_key)

        if cached_data:
            app.logger.info(f"Datos recuperados de la cache para {cache_key}")
            result = json.loads(cached_data)
            result['fromCache'] = True
            return jsonify(result)

    # Si no hay datos en cache o Redis no está disponible, consultar la API
    app.logger.info(f"Consultando la PokeAPI para {limit} Pokemon con offset {offset}")

    try:
        # Obtener solo la lista básica de la API
        response = requests.get(f"https://pokeapi.co/api/v2/pokemon?limit={limit}&offset={offset}")
        response_data = response.json()

        # Lista para almacenar los detalles de cada Pokemon
        pokemon_details = []

        # Obtener detalles básicos para cada Pokemon de forma optimizada
        for pokemon in response_data['results']:
            name = pokemon['name']
            # Extraer el ID del Pokemon de la URL para evitar una llamada adicional
            # Las URLs tienen el formato: https://pokeapi.co/api/v2/pokemon/{id}/
            url_parts = pokemon['url'].rstrip('/').split('/')
            pokemon_id = url_parts[-1]

            details_cache_key = f"pokemon:basic:{name}"

            # Verificar si los detalles básicos están en cache
            if redis_client:
                cached_details = redis_client.get(details_cache_key)

                if cached_details:
                    pokemon_details.append(json.loads(cached_details))
                    continue

            # Si no está en cache, obtener solo los campos necesarios
            # Usar un endpoint específico para obtener solo la información necesaria
            try:
                # Usar sesión para reutilizar conexiones
                details_url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
                details_response = requests.get(details_url)
                pokemon_data = details_response.json()

                # Crear un objeto con los datos mínimos necesarios
                details = {
                    'id': pokemon_data['id'],
                    'name': pokemon_data['name'],
                    'height': pokemon_data['height'],
                    'weight': pokemon_data['weight'],
                    'types': [t['type']['name'] for t in pokemon_data['types']],
                    'image': pokemon_data['sprites']['front_default']
                }

                # Guardar detalles básicos en cache (24 horas) si Redis está disponible
                if redis_client:
                    redis_client.setex(
                        details_cache_key,
                        timedelta(hours=24),
                        json.dumps(details)
                    )

                pokemon_details.append(details)

            except requests.RequestException as e:
                error_msg = f"Error al obtener detalles básicos para {name}: {e}"
                app.logger.error(error_msg)
                # Continuar con el siguiente Pokemon en caso de error
                continue

        # Preparar el resultado final
        result = {
            'count': response_data['count'],
            'next': response_data['next'],
            'previous': response_data['previous'],
            'results': pokemon_details,
            'fromCache': False
        }

        # Guardar en cache (5 minutos) si Redis está disponible
        if redis_client:
            redis_client.setex(
                cache_key,
                timedelta(minutes=5),
                json.dumps(result)
            )

        return jsonify(result)

    except requests.RequestException as e:
        error_msg = f"Error al obtener datos de la PokeAPI: {e}"
        app.logger.error(error_msg)
        return jsonify({
            'error': 'Error al obtener datos de la PokeAPI',
            'message': str(e)
        }), 500

@app.route('/api/pokemon/<pokemon_id>')
def get_pokemon(pokemon_id):
    """Obtiene detalles de un Pokemon específico"""
    cache_key = f"pokemon:detail:{pokemon_id}"

    # Verificar si Redis está disponible
    if redis_client:
        # Intentar obtener de la cache
        cached_data = redis_client.get(cache_key)

        if cached_data:
            app.logger.info(f"Datos detallados de Pokemon {pokemon_id} recuperados de la cache")
            return jsonify(json.loads(cached_data))

    # Si no está en cache o Redis no está disponible, consultar la API
    app.logger.info(f"Consultando detalles del Pokemon {pokemon_id}...")

    try:
        # Realizar llamada a la API específica para este Pokemon
        response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}")
        pokemon_data = response.json()

        # Extraer solo la información necesaria
        pokemon = {
            'id': pokemon_data['id'],
            'name': pokemon_data['name'],
            'height': pokemon_data['height'],
            'weight': pokemon_data['weight'],
            'types': [t['type']['name'] for t in pokemon_data['types']],
            'image': pokemon_data['sprites']['front_default'],
            'stats': {stat['stat']['name']: stat['base_stat'] for stat in pokemon_data['stats']},
            'abilities': [ability['ability']['name'] for ability in pokemon_data['abilities']]
        }

        # Obtener información de la especie (solo si es necesario)
        try:
            species_url = pokemon_data['species']['url']
            species_response = requests.get(species_url)
            species_data = species_response.json()

            # Extraer solo los datos relevantes de la especie
            pokemon['species'] = {
                'name': species_data['name'],
                'generation': species_data['generation']['name'],
                'habitat': species_data.get('habitat', {}).get('name', None),
                'is_legendary': species_data['is_legendary'],
                'is_mythical': species_data['is_mythical'],
                'flavor_text': next((entry['flavor_text'] for entry in species_data['flavor_text_entries']
                                if entry['language']['name'] == 'es'), None)
            }
        except (requests.RequestException, KeyError) as e:
            app.logger.warning(f"No se pudo obtener datos de la especie para {pokemon_id}: {e}")
            # Continuar sin datos de especie

        # Guardar en cache (24 horas) si Redis está disponible
        if redis_client:
            redis_client.setex(
                cache_key,
                timedelta(hours=24),
                json.dumps(pokemon)
            )

        return jsonify(pokemon)

    except requests.RequestException as e:
        error_msg = f"Error al obtener detalles del Pokemon {pokemon_id}: {e}"
        app.logger.error(error_msg)
        return jsonify({
            'error': f'Error al obtener detalles del Pokemon {pokemon_id}',
            'message': str(e)
        }), 500

@app.route('/clear-cache')
def clear_cache():
    """Endpoint para limpiar la cache """
    if not redis_client:
        app.logger.error("Redis no está disponible al intentar limpiar la cache")
        return jsonify({
            "status": "error",
            "message": "Redis no está disponible"
        }), 500

    try:
        # Encuentra todas las claves con el patrón "pokemon:*"
        pokemon_keys = redis_client.keys("pokemon:*")
        if pokemon_keys:
            redis_client.delete(*pokemon_keys)
            app.logger.info(f"Cache limpiada: {len(pokemon_keys)} claves eliminadas")
        else:
            app.logger.info("No hay claves para limpiar en la cache")

        return jsonify({
            "status": "success",
            "message": "Cache limpiada correctamente",
            "keys_deleted": len(pokemon_keys) if pokemon_keys else 0
        })
    except Exception as e:
        error_msg = f"Error al limpiar la cache: {e}"
        app.logger.error(error_msg)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)