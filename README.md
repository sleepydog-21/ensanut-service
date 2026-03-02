# C3 Service API

Este repositorio contiene la API del servicio para consultar los datos procesados de ENSANUT, separada del proyecto original `C3_Procesador_de_datos`. 

La API está construida con **Flask** y se conecta a una base de datos **PostgreSQL** para exponer los datos a través de diferentes endpoints.

## Requisitos

- Python 3.8+
- PostgreSQL
- pip (gestor de paquetes de Python)

## Instalación

1. **Clona este repositorio:**
   ```bash
   git clone https://github.com/chinchibul/ensanut-service.git
   cd ensanut-service
   ```

2. **Crea un entorno virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # En Windows usa: venv\Scripts\activate
   ```

3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura las variables de entorno:**
   Copia el archivo de ejemplo para las variables de entorno y ajusta las credenciales de tu base de datos si es necesario:
   ```bash
   cp .env.example .env
   ```
   Edita `.env` con tus propios valores de:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_TABLE=covid19
   ```

## Ejecución Lócal

Para iniciar la API en tu entorno local, ejecuta:

```bash
python service.py
```

El servidor estará disponible en `http://localhost:4500`.

## Endpoints de la API

- `GET /` : Endpoint de prueba, responde "Hello!".
- `GET /info` : Retorna información general sobre los datos de la ENSANUT Continua 2021.
- `GET /variables/` : Devuelve un diccionario con las variables disponibles, tanto para el nivel "personas" como para el nivel municipal ("mun").
- `GET /variables/<id>` : Devuelve los valores de distribución (bins) y alias asociados al ID de una variable específica.
- `GET /get-data/<id>?levels_id=[<bin_id>]` : Devuelve las celdas H3 asociadas a una variable para un bin en específico (para su visualización en mapas).

## Origen

El archivo `service.py` fue abstraido del proyecto original [C3_Procesador_de_datos](https://github.com/chilam-lab/C3_Procesador_de_datos) para funcionar de manera autónoma como un microservicio.
