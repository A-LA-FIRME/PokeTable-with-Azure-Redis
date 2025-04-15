// main.js - Funcionalidad para la aplicación PokéCache

// Variables globales
let pokemonTable;
let pokemonModal;

// Inicializar la aplicación cuando se cargue el documento
$(document).ready(function() {
    // Inicializar el modal de detalles del Pokémon
    pokemonModal = new bootstrap.Modal(document.getElementById('pokemonModal'));

    // Cargar los datos iniciales
    loadPokemonData();

    // Asignar eventos a los botones
    setupEventListeners();
});

/**
 * Carga los datos de los Pokémon desde el servidor
 */
function loadPokemonData() {
    const startTime = performance.now();

    // Mostrar mensaje de carga
    $('#cacheStatus').text('Cargando datos...');

    // Realizar la solicitud AJAX
    $.ajax({
        url: '/api/pokemon',
        method: 'GET',
        data: {
            limit: 150,  // Cargar los primeros 150 Pokémon
            offset: 0
        },
        success: function(response) {
            const endTime = performance.now();
            const loadTime = (endTime - startTime).toFixed(2);

            // Actualizar información de caché
            $('#cacheStatus').html(`Datos cargados ${response.fromCache ? 'desde la caché' : 'desde la API'}`);
            $('#requestTime').text(`Tiempo de respuesta: ${loadTime} ms`);

            // Inicializar o actualizar la tabla de Pokémon
            initPokemonTable(response.results);
        },
        error: function(error) {
            console.error('Error al cargar los datos:', error);
            $('#cacheStatus').text('Error al cargar los datos');
            $('#cacheInfo').addClass('alert alert-danger');
        }
    });
}

/**
 * Inicializa la tabla de Pokémon con DataTables
 * @param {Array} pokemonData - Los datos de Pokémon para cargar en la tabla
 */
function initPokemonTable(pokemonData) {
    // Si la tabla ya existe, destruirla para recargar los datos
    if (pokemonTable) {
        pokemonTable.destroy();
    }

    // Inicializar DataTable
    pokemonTable = $('#pokemonTable').DataTable({
        data: pokemonData,
        columns: [
            { data: 'id' },
            {
                data: 'image',
                render: function(data) {
                    return `<img src="${data}" class="pokemon-image" alt="Imagen de Pokémon">`;
                }
            },
            {
                data: 'name',
                render: function(data) {
                    return data.charAt(0).toUpperCase() + data.slice(1);
                }
            },
            {
                data: 'height',
                render: function(data) {
                    return `${data / 10} m`;
                }
            },
            {
                data: 'weight',
                render: function(data) {
                    return `${data / 10} kg`;
                }
            },
            {
                data: 'types',
                render: function(data) {
                    return data.map(type =>
                        `<span class="badge badge-type pokemon-type-${type}">${type}</span>`
                    ).join(' ');
                }
            },
            {
                data: 'id',
                render: function(data) {
                    return `<button class="btn btn-sm view-details" data-id="${data}">Ver Detalles</button>`;
                }
            }
        ],
        pageLength: 25,
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json'
        },
        responsive: true,
        order: [[0, 'asc']]
    });
}

/**
 * Configura los escuchadores de eventos para los botones
 */
function setupEventListeners() {
    // Evento para ver detalles de un Pokémon
    $('#pokemonTable').on('click', '.view-details', function() {
        const pokemonId = $(this).data('id');
        loadPokemonDetails(pokemonId);
    });

    // Evento para limpiar la caché
    $('#clearCacheBtn').click(function() {
        clearCache();
    });
}

/**
 * Carga los detalles de un Pokémon específico
 * @param {number} pokemonId - El ID del Pokémon a cargar
 */
function loadPokemonDetails(pokemonId) {
    // Mostrar el modal con indicador de carga
    $('#pokemonModalTitle').text('Cargando...');
    $('#pokemonModalBody').html(`
        <div class="text-center">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
        </div>
    `);
    pokemonModal.show();

    // Cargar los detalles del Pokémon
    $.ajax({
        url: `/api/pokemon/${pokemonId}`,
        method: 'GET',
        success: function(pokemon) {
            // Actualizar el título del modal
            $('#pokemonModalTitle').text(pokemon.name.charAt(0).toUpperCase() + pokemon.name.slice(1));

            // Crear contenido del modal
            const modalContent = `
                <div class="row">
                    <div class="col-md-4 text-center">
                        <img src="${pokemon.image}" class="img-fluid pokemon-detail-img" alt="${pokemon.name}" style="width: 150px;">
                        <div class="mt-3">
                            ${pokemon.types.map(type =>
                                `<span class="badge badge-type pokemon-type-${type}">${type}</span>`
                            ).join(' ')}
                        </div>
                    </div>
                    <div class="col-md-8">
                        <h4>Estadísticas básicas</h4>
                        <table class="table table-sm">
                            <tr>
                                <th>ID:</th>
                                <td>${pokemon.id}</td>
                            </tr>
                            <tr>
                                <th>Altura:</th>
                                <td>${pokemon.height / 10} m</td>
                            </tr>
                            <tr>
                                <th>Peso:</th>
                                <td>${pokemon.weight / 10} kg</td>
                            </tr>
                            <tr>
                                <th>Habilidades:</th>
                                <td>${pokemon.abilities ? pokemon.abilities.join(', ') : 'N/A'}</td>
                            </tr>
                        </table>

                        ${pokemon.stats ? `
                            <h4>Estadísticas</h4>
                            <div class="row">
                                ${Object.entries(pokemon.stats).map(([stat, value]) => `
                                    <div class="col-sm-6 mb-2">
                                        <div class="d-flex justify-content-between">
                                            <span class="stats-label">${stat}:</span>
                                            <span>${value}</span>
                                        </div>
                                        <div class="progress">
                                            <div class="progress-bar stats-bar bg-success" role="progressbar"
                                                style="width: ${Math.min(100, value / 1.5)}%"
                                                aria-valuenow="${value}" aria-valuemin="0" aria-valuemax="100">
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;

            // Actualizar el contenido del modal
            $('#pokemonModalBody').html(modalContent);
        },
        error: function(error) {
            console.error('Error al cargar los detalles:', error);
            $('#pokemonModalBody').html(`
                <div class="alert alert-danger">
                    Error al cargar los detalles del Pokémon.
                </div>
            `);
        }
    });
}

/**
 * Limpia la caché de Redis
 */
function clearCache() {
    $.ajax({
        url: '/clear-cache',
        method: 'GET',
        beforeSend: function() {
            $('#clearCacheBtn').prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Limpiando...');
        },
        success: function(response) {
            if (response.status === 'success') {
                // Mostrar mensaje de éxito
                Toastify({
                    text: "Caché limpiada correctamente",
                    duration: 3000,
                    close: true,
                    gravity: "top",
                    position: "right",
                    backgroundColor: "#4CAF50",
                }).showToast();

                // Recargar los datos
                loadPokemonData();
            } else {
                alert('Error al limpiar la caché: ' + response.message);
            }
        },
        error: function(error) {
            console.error('Error al limpiar la caché:', error);
            alert('Error al limpiar la caché');
        },
        complete: function() {
            $('#clearCacheBtn').prop('disabled', false).text('Limpiar Caché');
        }
    });
}