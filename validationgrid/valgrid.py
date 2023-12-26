import pandas as pd
import numpy as np
from typing import List, Union, Optional, Dict, Tuple
import warnings
#from pandas.core.common import SettingWithCopyWarning

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)
#warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)



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


# Creación de la malla de validación de acuerdo al archivo excel como diccionario (JSON)
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


# Crear las condiciones para cada variable o pregunta
def crear_condicion(diccionario: Optional[Dict], data: pd.DataFrame, iand: bool = False,  excluye_pta: bool = False) -> Optional[pd.Series]:
    '''
    Crea las condiciones para cada variable o pregunta según un diccionario y los datos proporcionados.

    Args:
        diccionario (Dict): Un diccionario que especifica las condiciones para cada variable.
        data (pd.DataFrame): El DataFrame de datos que se utilizará para verificar las condiciones.
        iand (bool): Indica si se deben combinar las condiciones con una operación AND (True) o OR (False). Por defecto, es False.
        excluye_pta (bool): Indica si se debe excluir de la validación general (Participar, Tierra y Agua). Por defecto, es False.

    Returns:
        Optional[pd.Series]: Una Serie booleana que representa las condiciones resultantes. Si el diccionario es None y general es False, se devuelve None.
    '''
    # Se define el espacio donde se va a guardar la condición
    condicion_total = None
    
    # Se definen las variables de la verificación general
    # Se crea el filtro dependiendo si las variables se encuentran en el dataframe
    columnas_a_verificar = ['DESEAPARTICIPAR', 'HOGAR_DISPONE_TIERRA', 'HOGAR_DISPONE_AGUA']
    filtros = []
    for columna in columnas_a_verificar:
        if columna in data.columns:
            filtro = data[columna] == ('SI' if columna == 'DESEAPARTICIPAR' else True)
            filtros.append(filtro)
    
    if filtros:
        condicion_general = all(filtros)
    else:
        condicion_general = None
    
    # Se crea la condición
    # Si no hay condicion que validar pero hay condición general devuelva la condición general
    if diccionario is None:
        if excluye_pta == False:
            return condicion_general
        # Si no hay condición ni requiere condición general devuelve None
        else:
            return None
    # Si en el diccionario si hay al menos una condición se dispone a crear la condición
    else:
        # Se itera sobre todas las condiciones existentes en el diccionario
        for col, valores in diccionario.items():
            # En el caso que la condición provenga de la variable Edad no se verifican valores de una lista sino que la Edad sea mayor a la establecida por la condición
            if 'Edad' in col:
                try:
                    condicion_col = data[col] > valores[0]
                except KeyError as e:
                    raise ValueError(f"Error al acceder a la columna '{col}' en el DataFrame de datos") from e
            else: 
                # En el caso que no sea Edad se verifica que el valor se encuentre en la lista específicada
                try:
                    condicion_col = data[col].isin(valores)
                except KeyError as e:
                    raise ValueError(f"Error al acceder a la columna '{col}' en el DataFrame de datos") from e
            # Se almacena la condición creada en el valor condicion_Total
            
            # Si no hay más condiciones la guarda, si hay más condiciones las combina según el tipo de validacion (OR, AND)
            if condicion_total is None:
                condicion_total = condicion_col
            else:
                if iand:
                    condicion_total = condicion_total & condicion_col
                else:
                    condicion_total = condicion_total | condicion_col
            if excluye_pta == False:
                return condicion_total & condicion_general
            else:
                return condicion_total
            
            
            
# Función para retornar verdadero o falso si la validación es de lista
def todos_en_valores_permitidos(row: pd.Series, lista: List, col: str) -> bool:
    '''
    Verifica si todos los valores en una lista están permitidos en la columna de datos.

    Args:
        row (pd.Series): Fila del DataFrame.
        lista (List): Lista de valores permitidos.
        col (str): Nombre de la columna en la que se verifica la condición.

    Returns:
        bool: True si todos los valores en la lista están permitidos en la columna, False en caso contrario.
    '''
    # Intenta verificar que los valores estén en la lista
    # En el caso que el dato se encuentre vacío y no pueda iterar entonces el valor está erroneo y devuelve False
    try:
        return all(valor in lista for valor in row[col])
    except:
        return False
    
    
    

# Función para retornar verdadero o falso en iteración de listas en listas
def validar_listlist(row: pd.Series, lista: List, col: str) -> bool:
    '''
    Verifica si todos los valores en una lista dentro de una lista están permitidos en la columna de datos.

    Args:
        row (pd.Series): Fila del DataFrame.
        lista (List): Lista de valores permitidos.
        col (str): Nombre de la columna en la que se verifica la condición.

    Returns:
        bool: True si todos los valores en la lista están permitidos en la columna, False en caso contrario.
    '''
    # En todas las listas, los valores de cada lista se encuentran dentro de los valores permitidos
    try:
        return all(all(valor in lista for valor in list) for list in row[col]) 
    except:
        return False
    
    
# Función para crear las condiciones en el caso que se deban validar los valores
def verificar_valores(diccionario: Optional[Dict], data: pd.DataFrame, col: str) -> pd.Series:
    '''
    Crea la condición para la variable a verificar según los valores que puede tomar.

    Args:
        diccionario (Optional[Dict]): Diccionario que contiene los valores y el tipo de validación.
        data (pd.DataFrame): DataFrame de datos.
        col (str): Nombre de la columna en la que se verifica la condición.

    Returns:
        pd.Series: Serie booleana que representa las condiciones resultantes.
    '''
    
    # Si no hay valores que revisar devuelve una condición vacía
    if diccionario is None:
        return None
    # Casó contrario crear la validación en la columna según el tipo de validación que se deba realizar
    else:
        valores = diccionario['valor']
        tipo = diccionario['Tipo']
        if tipo == 'regex':
            condicion = data[col].astype(str).str.match(valores)
        elif tipo == 'listlist':
            condicion = data.apply(validar_listlist, args = (valores, col), axis = 1)
        elif tipo == 'list':
            condicion = data.apply(todos_en_valores_permitidos, args = (valores, col), axis = 1)
        else:
            condicion = data[col].isin(valores)
        
    return condicion


# Función que entra a revisar las condiciones y valores de cada variable
def validar_valor(condicion: Optional[pd.Series], values: Optional[pd.Series], col: str, data: pd.DataFrame, file: pd.DataFrame) -> pd.Series:
    '''
    Valida los valores en la columna de datos según las condiciones y los valores a tomar.

    Args:
        condicion (Optional[pd.Series]): Serie booleana que representa las condiciones de validación.
        values (Optional[pd.Series]): Serie booleana que especifica los valores a tomar.
        col (str): Nombre de la columna en la que se valida.
        data (pd.DataFrame): DataFrame de datos original.
        file (pd.DataFrame): DataFrame en el que se actualizan los resultados.

    Returns:
        pd.Series: Serie actualizada con los valores validados.
    '''
    try:
        # En la columna se guardan valores de tipo 0, es decír inicialmente todos los datos están correctos
        file[col] = 0
        
        # Realiza la verificación de la condición o pasa en el caso que no haya condición
        if condicion is None:
            val_data = data
        else:
            val_data = data[condicion]
        
        # Revisa los valores en la variable en el dataframe condicionado por la condición
        # Va a retornar 0 si el valor está correcto y 1 si el valor está erroneo
        if values is None:
            val_series = val_data[col].isnull().astype(int)
        else:
            val_series = val_data.where(values)[col].isnull().astype(int)
            
        # Se actualiza la columna con valores 0, con 1 en los indices donde el dato está erroneo.
        file[col].update(val_series)
        
        return file[col]
    except Exception as e:
        # Manejo de excepciones para identificar y manejar errores específicos
        raise ValueError(f"Error al validar valores en la columna '{col}'") from e
    
    
# Función para convertir las variables numéricas de tipo entero
def restore_type(data: pd.DataFrame, numeric: List[str] or Tuple[str]) -> pd.DataFrame:
    '''
    Convierte las variables numéricas a tipo entero si es posible.

    Args:
        data (pd.DataFrame): DataFrame de datos.
        numeric (List[str] or Tuple[str]): Lista o tupla de nombres de columnas numéricas.

    Returns:
        pd.DataFrame: DataFrame con las variables numéricas convertidas a tipo entero si es posible.
    '''
    
    # Se hace la unión de los valores que el dataframe identifica como numéricas más aquellas que el usuario determina como numéricas
    num_cols = list(set(list(data.select_dtypes(include=np.number).columns))|set(numeric))
    
    # En el caso que la variable no sea latitud o longitud, se convierte el valor de la columna como entero
    for col in num_cols:
        if col not in ['latitud', 'longitud']:
            try:
                data[col]= data[col].astype('float').astype('Int64')
            except:
                data[col] = np.floor(pd.to_numeric(data[col], errors='coerce')).astype('Int64')
    return data


def malla_validacion(data: pd.DataFrame, guia_validacion: dict) -> Tuple[pd.DataFrame, List]:
    """
    Realiza la validación de datos basada en la malla de validación.

    Args:
        - data (pd.DataFrame): DataFrame de datos a validar.
        - guia_validacion (dict): Malla de validación que especifica las condiciones y valores para cada columna.

    Returns:
        Tuple[pd.DataFrame, List]: Tupla con la validación de datos y con la lista de columnas a revisar
    """
    try:
        # Filtrar columnas relevantes según la guía de validación
        columnas = [i for i in data.columns if i in guia_validacion.keys()]
        data = data[columnas]
        
        # Identificar columnas numéricas y convertirlas a tipo entero si es posible
        try:
            numeric = [n for n in [m for m in [i for i in guia_validacion.keys() if guia_validacion[i]['valores'] is not None] if guia_validacion[m]['valores']['Tipo'] == 'int'] if n in columnas]
        except Exception as e:
            print('Problemas con la malla de validación entregada')
            print(e)
        data = restore_type(data, numeric)
        
        # Crear una copia del DataFrame original
        store_file = data.copy()
        
        # Realizar validación para cada columna según la malla de validación
        for col in columnas:
            try:
                # Se crean las condiciones y valores
                condicion = crear_condicion(guia_validacion[col]['condicion'], data, guia_validacion[col]['iand'], guia_validacion[col]['excluida_PTA'])
                values = verificar_valores(guia_validacion[col]['valores'], data, col)
                
                # Se verifica la consistencia de la variable según los valores y condiciones
                store_file[col] = validar_valor(condicion = condicion, values = values, col = col, data = data, file = store_file)
            except Exception as e:
                print("Problema para validar la columna {}".format(col))
                print(e)
            
        # Se identifican las variables obligatorias
        obligatorias = [i for i in guia_validacion.keys() if guia_validacion[i]['opcional']== False]
        obligatorias = [i for i in obligatorias if i in store_file.columns]
        
        # Se añade la validación de número de documento duplicado
        store_file['Documento_Duplicado'] = data['num_documento'].duplicated().astype(int)
        
        # Se agregan variables que permiten identificar los registros que están correctos o erroneos
        id_hogar = data['id']
        num_doc_representante = data['NUMERODOCUMENTOTITULAR']
        num_doc_integrante = data['num_documento']
        store_file.insert(0, 'ID_HOGAR', id_hogar)
        store_file.insert(1,'NUM_TITULAR', num_doc_representante)
        store_file.insert(2,'NUM_DOC_INTEGRANTE', num_doc_integrante)
        
        obligatorias.append('Documento_Duplicado')
        
        # Se realiza la suma de los errores para cada registro del dataframe
        store_file['Validacion'] = store_file[obligatorias].sum(axis = 1)
        
        return store_file, obligatorias
    except Exception as e:
        # Manejo de excepciones para identificar y manejar errores específicos
        print("Error al realizar la validación de datos basada en la malla de validación.")
        print(e)



def concatenate_Errores(row: pd.Series, cols_obligatorias: List[str]) -> str:
    '''
    Concatena los nombres de las columnas que contienen errores en una fila.

    Args:
        row (pd.Series): Fila del DataFrame con información de validación.
        cols_obligatorias (List[str]): Lista de nombres de columnas que debe verificar.

    Returns:
        str: Cadena que contiene los nombres de las columnas con errores, separados por comas.
    '''
    
    errores = []
    # En cada columna a revisar, si se identifica que tiene un error se guarda su nombre en errores para luego devolver la cadena de variables con errores.
    for col in cols_obligatorias:
        if row[col] == 1:
            errores.append(col)
    return ', '.join(errores) if row['Validacion'] > 0 else np.nan


def resultados_malla_de_validacion(data: pd.DataFrame, guia_de_validacion:dict)-> Tuple[pd.DataFrame, pd.DataFrame]:
    """Función que ejecuta la malla de validación y retorna los resultados de la validación.

    Args:
        data (pd.DataFrame): Dataframe sobre el cual se va a realizar la validación.
        guia_de_validacion (dict): Malla de validación que especifica las condiciones y valores para cada columna.

    Returns:
        Validos, No_Validos: Tupla con el dataframe de participantes con valores correctos y el dataframe de participantes con valores erroneos.
    """
    print("MALLA DE VALIDACIÓN")
    dataframe_validado, cols_obligatorias = malla_validacion(data=data, guia_validacion=guia_de_validacion)
    
    dataframe_validado['Errores'] = dataframe_validado.apply(concatenate_Errores, args=(cols_obligatorias,), axis=1)
    
    resultados = dataframe_validado.groupby(by=['ID_HOGAR','NUM_TITULAR','NUM_DOC_INTEGRANTE'], as_index=False).agg({'Validacion':'sum'})
    
    data_con_errores = resultados[resultados['Validacion'] > 0].drop(columns = ['Validacion'])
    data_sin_errores = resultados[resultados['Validacion'] == 0].drop(columns = ['Validacion'])
    
    novalid = data_con_errores.merge(dataframe_validado, 
                                     on=['ID_HOGAR','NUM_TITULAR','NUM_DOC_INTEGRANTE'], 
                                     how='left')[['ID_HOGAR','NUM_TITULAR','NUM_DOC_INTEGRANTE','Validacion','Errores']]
    valid = data_sin_errores.merge(dataframe_validado,
                                   on=['ID_HOGAR','NUM_TITULAR','NUM_DOC_INTEGRANTE'], 
                                   how='left')[['ID_HOGAR','NUM_TITULAR','NUM_DOC_INTEGRANTE','Validacion','Errores']]
    
    # Imprimir resultados
    print("RESULTADOS MALLA DE VALIDACIÓN")
    print("El número total de elementos validados fueron {} participantes que equivale a {} Hogares".format(len(dataframe_validado), dataframe_validado['ID_HOGAR'].nunique()))
    print("="*100)
    print("El número total de participantes con valores correctos es {} que equivale a {} hogares".format(len(valid),valid['ID_HOGAR'].nunique()))
    print("="*100)
    print("El número total de participantes con valores erroneos es {} que equivale a {} hogares".format(len(novalid),novalid['ID_HOGAR'].nunique()))
    
    return valid, novalid
    
    