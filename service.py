import os
import json
import ast
from pathlib import Path
from dotenv import load_dotenv
import psycopg_pool
import psycopg
from flask import Flask, Response, request, jsonify

load_dotenv(Path(__file__).parent / '.env')

DB_PARAMS = {
    "host": os.getenv('DB_HOST', 'localhost'),
    "port": os.getenv('DB_PORT', '5432'),
    "dbname": os.getenv('DB_NAME', 'postgres'),
    "user": os.getenv('DB_USER', 'postgres'),
    "password": os.getenv('DB_PASSWORD', 'postgres')
}
TABLE_BASE = os.getenv('DB_TABLE', 'covid19')

pool = psycopg_pool.ConnectionPool(kwargs=DB_PARAMS, min_size=1, max_size=10)

app = Flask(__name__)

def get_db():
    return pool.connection()

@app.route("/")
def hello_world():
    return "<p>Hello!</p>"

def _get_table_exists(cursor, table_name):
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

PERSONAS_OFFSET = 0
MUN_OFFSET = 10000

@app.route("/variables/")
def me_api():
    mvars_dict = []
    
    with get_db() as conn:
        with conn.cursor() as cursor:
            # Query personas
            if _get_table_exists(cursor, f"dict_{TABLE_BASE}_personas"):
                cursor.execute(f"""
                    SELECT d.id, d.variable_name, d.description, COUNT(v.id)
                    FROM dict_{TABLE_BASE}_personas d
                    LEFT JOIN values_{TABLE_BASE}_personas v ON d.id = v.dict_id
                    GROUP BY d.id, d.variable_name, d.description
                """)
                for row in cursor.fetchall():
                    id_ = row[0] + PERSONAS_OFFSET
                    section = str(row[2]).split('.') if row[2] else []
                    mvars_dict.append({
                        "id": id_,
                        "name": row[1],
                        "level_size": row[3],
                        "available_grids": [["ensanut"]],
                        "info": {"section": section, "nombre_largo": row[1]}
                    })
                    
            # Query mun
            if _get_table_exists(cursor, f"dict_{TABLE_BASE}_mun"):
                cursor.execute(f"""
                    SELECT d.id, d.variable_name, d.description, COUNT(v.id)
                    FROM dict_{TABLE_BASE}_mun d
                    LEFT JOIN values_{TABLE_BASE}_mun v ON d.id = v.dict_id
                    GROUP BY d.id, d.variable_name, d.description
                """)
                for row in cursor.fetchall():
                    id_ = row[0] + MUN_OFFSET
                    section = str(row[2]).split('.') if row[2] else []
                    mvars_dict.append({
                        "id": id_,
                        "name": row[1],
                        "level_size": row[3],
                        "available_grids": [["mun"]],
                        "info": {"section": section, "nombre_largo": row[1]}
                    })

    return jsonify(mvars_dict)

@app.route("/variables/<id>")
def single_var(id):
    try:
        id = int(id)
    except ValueError:
        return Response(response=json.dumps({"error": "Invalid ID"}), status=400, mimetype="application/json")
        
    datos = []
    with get_db() as conn:
        with conn.cursor() as cursor:
            if id >= MUN_OFFSET:
                dict_id = id - MUN_OFFSET
                if not _get_table_exists(cursor, f"values_{TABLE_BASE}_mun"):
                    return Response(response=json.dumps({"error": "Not found"}), status=404, mimetype="application/json")
                cursor.execute(f"""
                    SELECT bin, interval_mun, alias, valor FROM values_{TABLE_BASE}_mun WHERE dict_id = %s ORDER BY bin
                """, (dict_id,))
                for row in cursor.fetchall():
                    datos.append({
                        "level_id": row[0],
                        "interval": str(row[1]) if row[1] else None,
                        "alias": row[2],
                        "valor": row[3],
                        "id": id
                    })
            else:
                dict_id = id - PERSONAS_OFFSET
                if not _get_table_exists(cursor, f"values_{TABLE_BASE}_personas"):
                    return Response(response=json.dumps({"error": "Not found"}), status=404, mimetype="application/json")
                cursor.execute(f"""
                    SELECT bin, interval_personas, alias, valor FROM values_{TABLE_BASE}_personas WHERE dict_id = %s ORDER BY bin
                """, (dict_id,))
                for row in cursor.fetchall():
                    datos.append({
                        "level_id": row[0],
                        "interval": str(row[1]) if row[1] else None,
                        "alias": row[2],
                        "valor": row[3],
                        "id": id
                    })
                    
    if not datos:
        return Response(response=json.dumps({"error": "Not found"}), status=404, mimetype="application/json")
        
    return Response(response=json.dumps(datos), status=200, mimetype="application/json")

@app.route('/get-data/<id>')
def get_data_id(id):
    try:
        id = int(id)
    except ValueError:
        return Response(response=json.dumps({"error": "Invalid ID"}), status=400, mimetype="application/json")

    levels_id_str = request.args.get('levels_id', "[0]")
    try:
        levels_id = ast.literal_eval(levels_id_str)
        if not isinstance(levels_id, list) or len(levels_id) == 0:
            levels_id = [0]
    except (ValueError, SyntaxError):
        levels_id = [0]

    bin_filter = levels_id[0]

    respuesta = []
    with get_db() as conn:
        with conn.cursor() as cursor:
            if id >= MUN_OFFSET:
                dict_id = id - MUN_OFFSET
                if not _get_table_exists(cursor, f"{TABLE_BASE}_mun"):
                    return Response(response=json.dumps({"error": "Not found"}), status=404, mimetype="application/json")
                cursor.execute(f"""
                    SELECT v.interval_mun, m.cells_mun 
                    FROM values_{TABLE_BASE}_mun v
                    JOIN {TABLE_BASE}_mun m ON v.id = m.values_id
                    WHERE v.dict_id = %s AND v.bin = %s
                """, (dict_id, bin_filter))
                row = cursor.fetchone()
                if row:
                    cells = row[1] if row[1] else []
                    respuesta = [{
                        "id": id, 
                        "grid_id": "mun", 
                        "level_id": [str(row[0]) if row[0] else None],
                        "n": len(cells), 
                        "cells": cells 
                    }]
            else:
                dict_id = id - PERSONAS_OFFSET
                if not _get_table_exists(cursor, f"{TABLE_BASE}_personas"):
                    return Response(response=json.dumps({"error": "Not found"}), status=404, mimetype="application/json")
                cursor.execute(f"""
                    SELECT v.interval_personas, m.cells_personas 
                    FROM values_{TABLE_BASE}_personas v
                    JOIN {TABLE_BASE}_personas m ON v.id = m.values_id
                    WHERE v.dict_id = %s AND v.bin = %s
                """, (dict_id, bin_filter))
                row = cursor.fetchone()
                if row:
                    cells = row[1] if row[1] else []
                    # In python arrays from unnested text queries format from postgres psycopg we might get string formatting,
                    # but since psycopg automatically transforms postgres text arrays to python lists if type matches, it should be a list.
                    respuesta = [{
                        "id": id, 
                        "grid_id": "ensanut", 
                        "level_id": [str(row[0]) if row[0] else None],
                        "n": len(cells), 
                        "cells": cells 
                    }]
                    
    if not respuesta:
        return Response(response=json.dumps({"error": "Not found"}), status=404, mimetype="application/json")
        
    return Response(response=json.dumps(respuesta), mimetype="application/json")

@app.route('/info')
def info():
    informacion = {"name": "ENSANUT Continua 2021",
                    "description": "Datos de la ENSANUT 2021.",
                    "meta": {"url":"https://ensanut.insp.mx/encuestas/ensanutcontinua2021/descargas.php",
                         "info": "Bases de datos y diccionarios originales"}
                   }
    return jsonify(informacion)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4500)