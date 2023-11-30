import requests
from typing import List, Dict
import pandas as pd
import numpy as np
import os
import json


def get_response(id_encuesta: str, header = Dict[str, str])-> List[dict]:
    """Función que ingresa al API determinado y obtiene la información de tipo JSON

    Args:
        id_encuesta (str): Id de la encuesta sobre la que se va a tomar la informacion 

    Returns:
        list: Lista de respuestas o registros obtenidos desde el API
    """
    
    url = f"https://as-rit-api-prod.azurewebsites.net/api/Sincronizador/resultados?id={id_encuesta}"
    try:
        response = requests.get(url = url, headers = header)
        response.raise_for_status()
        json_data = response.json()
        return json_data
    
    except requests.exceptions.RequestException as req_ex:
        print(f"Error en la solicitud: {req_ex}")
        return []
    
    except ValueError as val_err:
        print(f"Error al analizar JSON: {val_err}")
        return []
    
    except Exception as ex:
        print(f"Error inesperado: {ex}")
        return []
    
    
    
def explode_integrantes(dataframe : pd.DataFrame)-> pd.DataFrame:
    """Función que expande los resultados de la variable integrantes

    Args:
        dataframe (pd.DataFrame): Dataframe a expandir

    Returns:
        pd.DataFrame: Dataframe expandido
    """
    try:
        data =  dataframe.explode('respuestas.integrante').reset_index(drop=True)
        df_resp_integrante = pd.json_normalize(data['respuestas.integrante'])
        df_resp_integrante = df_resp_integrante.rename(columns={'identificacion':'identificacion_integrante'})
        data = pd.concat([data, df_resp_integrante], axis=1)
        data = data.rename(columns = lambda x: x.replace('respuestas.', ''))
        
        return data
    except:
        print("Normalización del DataFrame Cancelada.")
        return pd.DataFrame()
    
def read__dataframe(id_encuesta: str, header = Dict[str,str])-> pd.DataFrame:
    """Función que realiza el request al API en la encuesta determinada por el id_enciesta y lo convierte en un dataframe

    Args:
        id_encuesta (str): Id de la encuesta sobre la que se van a revisar los datos

    Returns:
        pd.DataFrame: Dataframe resultante
    """
    response = get_response(id_encuesta = id_encuesta, header=header)
    try:
        data = pd.json_normalize(response)
        data = explode_integrantes(dataframe = data)
        return data
    except Exception as e:
        raise e
    
    
    
def cargar_malla_validacion(id_encuesta:str, ruta_folder:str)-> dict:
    """Función encargada de leer archivo JSON que contiene la malla de validación

    Args:
        id_encuesta (str): Número identificador de la encuesta a validar

    Returns:
        dict: Diccionario que almacena la malla de validacion
    """
    try:
        ruta_malla = os.path.join(ruta_folder,'data','json', f"{id_encuesta}.json")
        with open(ruta_malla, 'r', encoding='utf-8') as file:
            malla = json.load(file)
            return malla
    except FileNotFoundError as e:
        raise e
        
    except json.JSONDecodeError as e:
        raise e
    
    

# Elimina listas que contengan valores nulos
def remove_datos_vacios_de_lista(row: pd.Series, col: str):
    '''
    Reemplaza los valores NaN en una columna con NaN en una fila de un DataFrame.

    Args:
        row (pd.Series): Fila de un DataFrame.
        col (str): Nombre de la columna a procesar.

    Returns:
        Union[float, pd.Series]: Retorna un valor NaN si todos los valores en la columna son NaN, o la columna original sin cambios si contiene al menos un valor no NaN.
    '''
    # Se verifica que valores son nulos, dado que son listas, la validación devuelve un Array
    A = row[col]
    valor = pd.isna(A).squeeze()
    forma = len(valor.shape)
    
    # Se hace la validación según la dimensión de la validación de errores nulos
    if forma == 0:
        if valor == True:
            return np.nan
        else:
            return A
    elif forma == 1:
        if all(i for i in valor):
            return np.nan
        else:
            return A
    else:
        if all(all(m for m in i) for i in valor):
            return np.nan
        else:
            return A




def expand_data_frame(col: str, data: pd.DataFrame) -> pd.DataFrame:
    '''
    Expande una columna que contiene listas o diccionarios en un DataFrame.

    Args:
        col (str): Nombre de la columna a expandir.
        data (pd.DataFrame): DataFrame de entrada.

    Returns:
        pd.DataFrame: DataFrame expandido con las listas o diccionarios desglosados en filas separadas.
    '''
    # Se expande la columna como un dataframe y se guarda el index para poder concatenar más adelante
    expansion = pd.json_normalize(data[col].explode())
    relacion_filas = data[col].explode().index
    
    # Si la expansión dió como resultado una única columna se deja el nombre original
    if len(list(expansion.columns)) == 1:
        expansion = expansion.rename(columns={list(expansion.columns)[0]:col})
        
    expansion['id'] = relacion_filas
    
    # Se identifica si aún con la expansión hay variables con datos de tipo lista
    is_list = expansion.applymap(lambda x: isinstance(x, list)).any()
    a_expandir = list(is_list[is_list == True].index)
    
    columnas = list(expansion.columns)
    columnas.remove("id")
    
    # Se crea un diccionario que va a definir como se van a agrupar los datos de la expansión
    aggregation_dict = {
    columna: (lambda x: [i for i in x]) if columna in a_expandir else (lambda x: [i for i in x] if not all(pd.isna(i) for i in x) else np.nan)
    for columna in columnas
    }
    
    # Se agrupa la expansión por el id según las condiciones definidas en el diccionario
    result = expansion.groupby('id', as_index=False).agg(aggregation_dict)
    
    # Si tenemos columnas que aún contenian listas se remueven las listas agrupadas que quedaron con datos nulos
    for columna in a_expandir:
        result[columna] = result.apply(remove_datos_vacios_de_lista, args=(columna,), axis = 1)
    
    # Se elimina la columna id que ya no es necesaria
    result = result.drop(columns='id')
    return result




def expandir_columnas_adicionales(dataframe: pd.DataFrame, malla: dict)-> pd.DataFrame:
    """Función que tomas aquellas columnas que se deben expandir pero que no están entre Respuestas e Integrantes y las expande

    Args:
        data (pd.DataFrame): Dataframe Original

    Returns:
        pd.DataFrame: Dataframe Expandido
    """
    
    data = dataframe.copy()
    
    # Se identifican las variables que se pueden expandir
    is_list = data.applymap(lambda x: isinstance(x, list)).any()
    posible_expandir = list(is_list[is_list == True].index)
    try:
        # Se seleccionan las variables que se deben expandir según la malla
        Expandir = [i for i in posible_expandir if malla[i]['valores'] is None]
    except Exception as e:
        print("Error en la malla de validación")
        print(e)
        
    # Se expande cada columna seleccionada
    for columna in Expandir:
        try:
            result = expand_data_frame(columna, data)
            # Si el resultado de la expansión da una única columna, se elimina la original y se mantiene la expandida
            if len(result.columns) == 1:
                data = data.drop(columns = columna)
            # Se concatenan la expansión con el dataframe
            data = pd.concat([data, result], axis = 1)
        except Exception as e:
            print("Problemas con la expansión de la columna {}".format(columna))
            print(e)
    
    return data