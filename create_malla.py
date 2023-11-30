## Creación de la malla de validación de acuerdo al archivo excel como diccionario (JSON)
import pandas as pd
import easygui
import json
import os
from typing import Dict, List, Union


# Función para dejar las condiciones que recibe del Excel de validación en las condiciones como lista de valores o cómo valores únicos según el tipo de dato
def get_list_condiciones(row:pd.Series):
    '''
    Convierte las condiciones en una lista de enteros o cadenas.

    Args:
        row (pd.Series): Fila del DataFrame con columnas 'Condicion' y 'Tipo Validación'.

    Returns:
        Lista de condiciones convertidas.
    '''
    
    # Definimos cómo variables los valores que vamos a verificar
    A = str(row['condicion'])
    B = row['tipo_validacion']
    
    # Si no hay valores por verificar, devuelve un valor Nulo
    if A =='nan':
        val = None
    else:
        # Si el tipo de dato es entero, devuelve la lista de valores en formato entero
        if B == 'int':
            val = [int(i) for i in A.split("|")]
        # Para cualquier otro caso devuelve los datos cómo tipo lista de cadenas de texto
        else:
            val = [str(i) for i in A.split("|")]
    return val


# Función para definir los valores que puede tomar la variable
def get_list_valores(row: pd.Series):
    '''
    Convierte los valores en una lista de enteros o cadenas.

    Args:
        row (pd.Series): Fila del DataFrame con columnas 'Valores' y 'Tipo Validación'.

    Returns:
        Lista de condiciones convertidas.
    '''
    
    # Definimos cómo variables los valores que vamos a verificar
    A = str(row['valores'])
    B = row['tipo_valor']
    
    # Si no hay valores por verificar, devuelve un valor Nulo
    if A =='nan':
        val = None
    else:
        # Si el tipo de validación es entera, devuelve la lista de valores de tipo entero
        if B == 'int':
            val = [int(i) for i in A.split("|")]
        # En el caso que sea de tipo string o listas devuelva la lista de de cadenas de texto
        elif B == 'str' or B=='list' or B == 'listlist':
            val = [str(i) for i in A.split("|")]
        # Los demas casos (TIPO REGEX) devuelva solo la cadena
        else:
            val = A
    return val


def create_malla_dict(condiciones: pd.DataFrame, valores: pd.DataFrame)-> Dict[str, dict]:
    '''
    Crea una malla de validación a partir de DataFrames de condiciones y valores.

    Args:
        condiciones (pd.DataFrame): DataFrame de condiciones.
        valores (pd.DataFrame): DataFrame de valores.

    Returns:
        Dict[str, dict]: Diccionario que representa la malla de validación.
    '''
    
    # Se define un diccionario vacío donde se va a almacenar el resultado
    malla = dict()
    
    # Se aplica la función get_list_condiciones para tener las condiciones y valores corregidos
    try:
        condiciones['condicion'] = condiciones.apply(get_list_condiciones, axis = 1)
        valores['valores'] = valores.apply(get_list_valores, axis = 1)
    except Exception as e:
        raise ValueError("Error al aplicar las funciones get_list_condiciones y get_list_valores") from e
    
    # Se realiza un merge de los dos dataframes para poder iterar sobre un único dataframe
    try:
        result = condiciones.merge(valores, on = 'variable', how = 'left')
    except pd.errors.MergeError as e:
        raise ValueError("Problemas con el archivo Excel de Malla de Validación") from e
        
    # Se itera sobre valor y columna del dataframe
    for index, row in result.iterrows():
        
        # Se guardan como variables cada valor de las variables para un acceso más sencillo
        variable = row['variable']
        dependiente = row['dependiente']
        condicion = row['condicion']
        excluye = row['excluye_pta']
        opcional = row['variable_opcional']
        iand = row['iand']
        valor = row['valores']
        condicion_valor = row['tipo_valor']
        
        """Creación del diccionario Malla de Validación
    
        El proceso de creación de la malla de validación es la creación de un diccionario para cada variable de la siguiente manera: 
        - condicion: Define las condiciones para la variable, en el caso que no haya condición devuelve un dato nulo, caso contrario
        guarda en el diccionario de la variable el diccionario con la variable de la que depende y la condición o valor que debe tomar para 
        que se active la pregunta (Dado que una variable puede tener una o más condiciones, en el caso que tenga más de una condición, esta condición
        se va a añadir en el diccionario de la variable)
        - valores: Ingresa los valores que debe tomar la variable, si no hay valores por validar, devuelve None, caso contrario crea un diccionario donde
        almacena los valores que puede tomar y el tipo de validación que se va a realizar (int, str, regex, list, listlist)
        - iand: Se refiere a la pregunta de si las multiples condiciones a validar son de tipo or o de tipo and, si está vacío significa que es de tipo or por lo que
        devuelve Falso, caso contrario devuelve True.
        - opcional: Se refiere al caso de si la pregunta es opcional, si no es opcional devuelve True, caso contrario devuelve False
        - Excluida_PTA: Se refiere a la pregunta (La variable se excluye de las condiciones, DESEAPARTICIPAR, DISPONETIERRA, DISPONEAGUA), si se excluye devuelve True, 
        caso contrario devuelve False
        """
    
        # Si la variable ya tiene una condición se añade la nueva condición
        if variable in malla.keys():
            malla[variable]['condicion'].update({dependiente : condicion})
        # Creación del diccionario según los parámetros
        else:
            malla[variable] = {
                'condicion': None if pd.isna(dependiente) else {dependiente : condicion},
                'valores': None if pd.isna(condicion_valor) else {'valor':valor, 'Tipo': condicion_valor},
                'iand': False if pd.isna(iand) else True,
                'opcional': False if pd.isna(opcional) else True,
                'excluida_PTA': False if pd.isna(excluye) else True
                }
            
    return malla

# Función para crear el archivo JSON en el caso que no haya sido creado
def create_json_malla(id_encuesta:str):
    """
    Función que crea el archivo JSON para la estructura de la malla de validación a partir de un archivo Excel y lo exporta en la ruta establecida

    Args:
        - name_malla (str): Nombre del archivo excel que contiene la estructura de la malla
        - ruta (str): Ruta de la dirección de la carpeta del proyecto
    returns:
        Crea un archivo JSON en la carpeta `data/validation_json` dentro de la ruta específicada
    """
    ruta_read = easygui.fileopenbox(msg='Seleccione el archivo excel de la malla de validación', title='Cargar archivo excel', default='*.xlsx')   
    ruta_export = easygui.diropenbox(msg='Seleccione la carpeta donde se va a exportar el archivo JSON', title='Exportar archivo JSON')
    ruta_export = os.path.join(ruta_export, id_encuesta + '.json')
    try:
        cond = pd.read_excel(ruta_read, sheet_name='Validaciones')
        val = pd.read_excel(ruta_read, sheet_name='Valores')
        val = val.dropna(subset=['valores'])
    except Exception as e:
        print('Nombre o archivo excel erroneo')
        print(e)
    
    try:
        malla = create_malla_dict(condiciones = cond, valores = val)
    except Exception as e:
        print('Estructura del Archivo excel erroneo')
        print(e)
    
    try:
        with open(ruta_export, 'w', encoding='utf8') as file:
            json.dump(malla, file, ensure_ascii=False, indent = 1)
    except Exception as e:
        print('Error al intentar exportar el archivo json')
        print(e)
        
        
if __name__ == '__main__':
    input = input('Ingrese el id de la encuesta: ')
    create_json_malla(input)