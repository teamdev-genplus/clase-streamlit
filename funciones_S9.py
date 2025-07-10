# Importar lirerias
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Datos de la cuenca
Area = 2990.8 # km2
Altura = 2160 # m
Longitud = 83900 # m
c = 0.2 # und

# ! CALCULOS CON LOS DATOS DE LA CUENCA
pendiente = Altura / Longitud # m/m
tc = 0.000325*((Longitud**0.77)/(pendiente**0.385)) # horas

# Datos de la demanda
demanda = pd.DataFrame({
    'MES': ['Thornthwaite', 'Blaney', 'CROPWAT'],
    'ENE': [0.000, 0.000, 0.000],
    'FEB': [0.004, 0.020, 0.01509],
    'MAR': [0.006, 0.081, 0.06154],
    'ABR': [0.008, 0.107, 0.08212],
    'MAY': [0.066, 0.171, 0.14108],
    'JUN': [0.080, 0.178, 0.14324],
    'JUL': [0.081, 0.186, 0.15966],
    'AGO': [0.067, 0.149, 0.13183],
    'SET': [0.073, 0.149, 0.14002],
    'OCT': [0.018, 0.080, 0.06916],
    'NOV': [0.023, 0.080, 0.07414],
    'DIC': [0.000, 0.000, 0.000]
})
demanda

# Extraer los rangos de fechas de los datos de las estaciones
def extraer_rango_fechas(estaciones):
    #fecha_rangos = {}
    for estacion in estaciones:
        df = pd.read_excel(estacion['ruta'])
        df['FECHA'] = pd.to_datetime(df['FECHA'], dayfirst=True)
        fecha_inicio = df['FECHA'].min()
        fecha_fin = df['FECHA'].max()
        estacion['rango'] = (fecha_inicio, fecha_fin)
    return estaciones

# Superponer los rangos de fechas
def superponer_rangos(estaciones):
    inicios = []
    finales = []
    for estacion in estaciones:
        inicios.append(estacion['rango'][0])
        finales.append(estacion['rango'][1])
    # Rango de intersección
    rango_inicio = max(inicios)
    rango_fin = min(finales)
    return [rango_inicio, rango_fin]

# Función para establecer la precipitación anual y el caudal anual
def calcular_precipitacion_caudal(nombre, estaciones, rango, dias_meses):
    for estacion in estaciones:
        if estacion['nombre'] == nombre:
            df = pd.read_excel(estacion['ruta'], sheet_name='Reporte')
            break
    # Agrupar por años y por meses los valors de la tabal, y se vana sumar las precipitaciones correspondientes
    tabla = df.groupby(['AÑO', 'MES'])['VALOR (mm)'].sum().unstack(fill_value=None).round(3)
    anio_inicio = rango[0].year
    anio_fin = rango[1].year
    tabla_filtrada = tabla[(tabla.index >= anio_inicio) & (tabla.index <= anio_fin)]

    # Sacar un promedio para cada mes
    pp_mensual = tabla.mean(axis=0, skipna=True).round(3)
    # Calcular el caudal
    c_mensual = (c*Area*tabla_filtrada*100)/(tc*24*360)
    for col in c_mensual.columns:
        c_mensual[col] = c_mensual[col]/dias_meses[col-1]  # Ajustar el caudal mensual según los días del mes
    c_mensual = c_mensual.mean(axis=0, skipna=True).round(3)  # Rellenar NaN con 0
    #return sum(pp_mensual)
    return sum(pp_mensual), sum(c_mensual)

# Función para establecer la tabla de precipitaciones para todas las estaciones
def tabla_pp_estaciones(estaciones, rango, dias_meses):
    anio_inicio = rango[0].year
    anio_fin = rango[1].year
    tabla_total = pd.DataFrame(np.zeros((anio_fin - anio_inicio + 1, 12)), index=range(anio_inicio, anio_fin + 1), columns=range(1, 13))
    for estacion in estaciones:
        df = pd.read_excel(estacion['ruta'], sheet_name='Reporte')
        tabla = df.groupby(['AÑO', 'MES'])['VALOR (mm)'].sum().unstack(fill_value=0.0).round(3)
        tabla = tabla[(tabla.index >= anio_inicio) & (tabla.index <= anio_fin)]
        tabla_total += tabla
    return tabla_total.fillna(0)/(len(estaciones))

# Funcion para establecer la tabla de PROMEDIOS de precipitaciones y caudales
def tabla_promedios(tabla_pp, dias_meses):
    # Calcular el promedio de precipitaciones
    pp_mensual = tabla_pp.mean(axis=0, skipna=True).round(3)
    # Calcular la velocidad
    velocidad = []
    for i in range(len(pp_mensual)):
        velocidad.append(pp_mensual[i+1] / (1000*dias_meses[i]*24*60*60))
    # calcular caudal
    caudal_s = []
    for i in range(len(velocidad)):
        caudal_s.append(velocidad[i] * Area * 10000)
    # precipitación por hora
    pp_h = []
    for i in range(len(caudal_s)):
        pp_h.append(pp_mensual[i+1]/(24*dias_meses[i]))  # Convertir a m3/h
    # Calculo de la intensidad
    intensidad = [pp/tc for pp in pp_h]
    return pd.DataFrame({'pp (mm/mes)': pp_mensual, 'v (m/s)': velocidad, 'Q (m3/s)': caudal_s, 'pp (mm/h)': pp_h, 'I': intensidad}).round(4).T

# Función para establacer la tabla de las curvas de duración de caudales
def tabla_curvas_duracion_caudales(tabla_pp, rango, dias_meses):
    anio_inicio = rango[0].year
    anio_fin = rango[1].year
    tabla_c_duracion = pd.DataFrame(np.zeros((anio_fin - anio_inicio + 1, 12)), columns=range(1, 13))
    # Calcular el caudal mensual
    caudal_mensual = (c * Area * tabla_pp * 100) / (tc * 24 * 360)
    for col in caudal_mensual.columns:
        caudal_mensual[col] = caudal_mensual[col] / dias_meses[col-1]  # Ajustar el caudal mensual según los días del mes
    # Calcular el caudal diario
    for col in caudal_mensual.columns:
        tabla_c_duracion[col] = caudal_mensual[col].sort_values(ascending=False).reset_index(drop=True)
    # Agregar frecuencias
    n = len(tabla_c_duracion)
    tabla_c_duracion['Frecuencia'] = (tabla_c_duracion.index + 1) / n
    # Hallar los valores interpolados de las frecuencias 0.5, 0.75, y 0.95
    frec = [0.5, 0.75, 0.95]
    resumen_c_duracion = pd.DataFrame(index=frec, columns=tabla_pp.columns)
    for col in tabla_c_duracion.columns[:-1]:  # Excluir la columna de frecuencia
        valores = np.interp(frec, tabla_c_duracion['Frecuencia'], tabla_c_duracion[col])
        resumen_c_duracion[col] = valores
    #resumen_c_duracion.index.name = 'Frecuencia'
    return tabla_c_duracion, resumen_c_duracion

# Función para la grafica de las curvas de duración de caudales

def graficar_curvas_duracion(tabla_duracion):
    import plotly.express as px

    nombres_meses = {
        1: 'ENE', 2: 'FEB', 3: 'MAR', 4: 'ABR', 5: 'MAY', 6: 'JUN',
        7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OCT', 11: 'NOV', 12: 'DIC'
    }

    df_largo = tabla_duracion.melt(id_vars='Frecuencia', var_name='MES', value_name='CAUDAL')
    df_largo['MES'] = df_largo['MES'].astype(int)
    df_largo['Mes_nombre'] = df_largo['MES'].map(nombres_meses)

    fig = px.line(
        df_largo,
        x='Frecuencia',
        y='CAUDAL',
        color='Mes_nombre',
        labels={'Mes_nombre': 'Mes', 'Frecuencia': 'Frecuencia', 'CAUDAL': 'Caudal (m³/s)'},
        title='Curvas de Duración'
    )

    fig.update_layout(legend_title_text='Mes')
    return fig


# Función para la tabla de balance hídrico
def tabla_balance_hidrico(tabla_c_d, tabla_demanda):
    meses_nombres = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN',
                 'JUL', 'AGO', 'SET', 'OCT', 'NOV', 'DIC']
    oferta = tabla_c_d.loc[0.95].values
    # Restar la fila con cada fila del segundo df
    df2_valores = tabla_demanda[meses_nombres]
    diferencia = df2_valores.subtract(oferta, axis=1)
    clasificacion = diferencia.applymap(lambda x: 'DEFICIT' if x > 0 else 'OFERTA')
    return clasificacion

# Funcion para la grafica oferta y demanda
def grafica_oferta_demanda(tabla_resumen, tabla_demanda):
    import plotly.graph_objects as go

    meses_nombres = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN',
                     'JUL', 'AGO', 'SET', 'OCT', 'NOV', 'DIC']
    
    tabla_resumen.columns = meses_nombres
    tabla_resumen.index = ['Q 50%', 'Q 75%', 'Q 95%']
    tabla_demanda.index = tabla_demanda['MES']
    df_concatenado = pd.concat([tabla_resumen, tabla_demanda[meses_nombres]], axis=0)

    fig = go.Figure()
    for nombre in df_concatenado.index:
        fig.add_trace(go.Scatter(
            x=df_concatenado.columns,
            y=df_concatenado.loc[nombre],
            mode='lines+markers',
            name=nombre
        ))

    fig.add_trace(go.Table(
        header=dict(
            values=["<b>Serie</b>"] + list(df_concatenado.columns),
            fill_color='lightblue',
            align='center',
            font=dict(color='black', size=12)
        ),
        cells=dict(
            values=[[i for i in df_concatenado.index]] + [df_concatenado[col].tolist() for col in df_concatenado.columns],
            fill_color='black',
            align='center',
            format=[None] + [".5f"] * 12
        ),
        domain=dict(x=[0, 1], y=[0, 0.3])
    ))

    fig.update_layout(
        title='BALANCE HÍDRICO (OFERTA-DEMANDA)',
        height=800,
        margin=dict(t=80, b=20),
        yaxis=dict(domain=[0.4, 1], title='Caudal (m³/s)'),
        xaxis=dict(title='Mes')
    )
    return fig

    meses_nombres = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN',
                 'JUL', 'AGO', 'SET', 'OCT', 'NOV', 'DIC']
    tabla_resumen.columns = meses_nombres
    tabla_resumen.index = ['Q 50%', 'Q 75%', 'Q 95%']
    tabla_demanda.index = tabla_demanda['MES']
    df_concatenado = pd.concat([tabla_resumen, tabla_demanda[meses_nombres]], axis=0)
    # Crear figura
    fig = go.Figure()
    # Agregar una línea para cada serie (cada fila del df)
    for nombre in df_concatenado.index:
        fig.add_trace(go.Scatter(
            x=df_concatenado.columns,
            y=df_concatenado.loc[nombre],
            mode='lines+markers',
            name=nombre
        ))
    # Agregar la tabla como una traza adicional
    fig.add_trace(go.Table(
        header=dict(
            values=["<b>Serie</b>"] + list(df_concatenado.columns),
            fill_color='lightblue',
            align='center',
            font=dict(color='black', size=12)
        ),
        cells=dict(
            values=[[i for i in df_concatenado.index]] + [df_concatenado[col].tolist() for col in df_concatenado.columns],
            fill_color='white',
            align='center',
            format=[None] + [".5f"] * 12
        ),
        domain=dict(x=[0, 1], y=[0, 0.3])  # Posición de la tabla
    ))
    # Actualizar layout para dejar espacio a la tabla debajo
    fig.update_layout(
        title='BALANCE HÍDRICO (OFERTA-DEMANDA)',
        height=800,  # Alto total para que la tabla no se sobreponga
        margin=dict(t=80, b=20),
        yaxis=dict(domain=[0.4, 1], title='Caudal (m³/s)'),  # Gráfico arriba
        xaxis=dict(title='Mes')
    )
    fig.show()