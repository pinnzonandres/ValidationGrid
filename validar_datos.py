from typing import List, Dict, Tuple, Union
import pandas as pd
from validationgrid.read import read__dataframe, cargar_malla_validacion, expandir_columnas_adicionales
from validationgrid.valgrid import resultados_malla_de_validacion


def validar_datos(id_encuesta: str, token:str, ruta: str)-> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Función que realiza la validación de los datos de la encuesta seleccionada

    Args:
        id_encuesta (str): Id de la encuesta sobre la que se van a revisar los datos
        token (str): Token de Acceso al API
        ruta (str): Ruta al folder donde esta el proyecto

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: Dataframe resultante, datos validos y datos no validos
    """
    # Se define el token de Acceso al API
    headers = {"Authorization": f"Bearer {token}"}
    
    # Se carga y modifica el dataframe
    dataframe = read__dataframe(id_encuesta, headers)
    malla = cargar_malla_validacion(id_encuesta, ruta_folder=ruta)
    dataframe = expandir_columnas_adicionales(dataframe, malla = malla)
    
    # Se valida la información
    validos, novalidos= resultados_malla_de_validacion(dataframe, malla)
    
    return dataframe, validos, novalidos