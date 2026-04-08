import streamlit as st
import pandas as pd
import datetime
import os
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

st.set_page_config(page_title="Dashboard - Agente de Precios", layout="wide")

load_dotenv(override=True)
opciones = ClientOptions(schema="agente_precios")
supabase_url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY")
supabase = create_client(supabase_url, supabase_key, options=opciones)

@st.cache_data(ttl=600)
def cargar_datos():
    todos_los_datos =[]
    inicio = 0
    tamano_bloque = 1000
    
    while True:
        # AHORA PEDIMOS TAMBIÉN CUOTAS Y SEMANA_ANIO
        respuesta = supabase.table("historico_precios").select(
            "id, precio_lista, cuotas, semana_anio, fecha_extraccion, marca_detectada, nombre_modelo_completo, retailers(nombre), categorias(nombre)"
        ).range(inicio, inicio + tamano_bloque - 1).execute()
        
        datos = respuesta.data
        if not datos: break
        todos_los_datos.extend(datos)
        if len(datos) < tamano_bloque: break
        inicio += tamano_bloque
        
    if not todos_los_datos: return pd.DataFrame()
        
    df = pd.DataFrame(todos_los_datos)
    df['Retailer'] = df['retailers'].apply(lambda x: x['nombre'] if x else 'Desconocido')
    df['Categoría'] = df['categorias'].apply(lambda x: x['nombre'] if x else 'Desconocido')
    df['fecha_extraccion'] = pd.to_datetime(df['fecha_extraccion']).dt.date
    
    # Rellenamos nulos por si hay registros viejos sin semana o cuotas
    df['semana_anio'] = df['semana_anio'].fillna(0).astype(int)
    df['cuotas'] = df['cuotas'].fillna(0).astype(int)
    
    df = df.rename(columns={
        'precio_lista': 'Precio',
        'marca_detectada': 'Marca',
        'nombre_modelo_completo': 'Modelo',
        'fecha_extraccion': 'Fecha',
        'semana_anio': 'Semana',
        'cuotas': 'Cuotas'
    })
    
    df['Marca'] = df['Marca'].str.title()
    return df[['Fecha', 'Semana', 'Categoría', 'Retailer', 'Marca', 'Modelo', 'Precio', 'Cuotas']]

df_precios = cargar_datos()

# ==========================================
# 4. INTERFAZ: BARRA LATERAL (FILTROS)
# ==========================================
st.sidebar.header("🔍 Filtros de Búsqueda")

if not df_precios.empty:
    # NUEVO: BÚSQUEDA POR TEXTO LIBRE
    busqueda_texto = st.sidebar.text_input("🔎 Buscar en descripción (ej: No Frost, 8kg):")
    st.sidebar.markdown("---")

    # NUEVO: SELECTOR DE TIPO DE TIEMPO
    tipo_tiempo = st.sidebar.radio("⏱️ Filtrar tiempo por:",["Rango de Fechas", "Semanas del Año"])
    
    fecha_inicio, fecha_fin = None, None
    semanas_seleccionadas =[]
    
    if tipo_tiempo == "Rango de Fechas":
        hoy = datetime.date.today()
        hace_un_mes = hoy - datetime.timedelta(days=30)
        rango_fechas = st.sidebar.date_input("📅 Seleccione Fechas", value=(hace_un_mes, hoy), max_value=hoy)
        if len(rango_fechas) == 2:
            fecha_inicio, fecha_fin = rango_fechas
    else:
        semanas_disponibles = sorted(df_precios[df_precios['Semana'] > 0]['Semana'].unique().tolist())
        semanas_seleccionadas = st.sidebar.multiselect("📆 Seleccione Semanas", semanas_disponibles, default=semanas_disponibles)
    
    st.sidebar.markdown("---")
    
    # Filtros en Cascada (Categoría primero)
    categorias_unicas = sorted(df_precios['Categoría'].unique().tolist())
    cat_default = ["Heladeras"] if "Heladeras" in categorias_unicas else categorias_unicas
    filtro_categoria = st.sidebar.multiselect("📁 Categoría", categorias_unicas, default=cat_default)
    
    df_temp_cat = df_precios[df_precios['Categoría'].isin(filtro_categoria)] if filtro_categoria else df_precios
    retailers_unicos = sorted(df_temp_cat['Retailer'].unique().tolist())
    filtro_retailer = st.sidebar.multiselect("🏪 Retailer", retailers_unicos, default=retailers_unicos)
    
    df_temp_ret = df_temp_cat[df_temp_cat['Retailer'].isin(filtro_retailer)] if filtro_retailer else df_temp_cat
    marcas_unicas = sorted(df_temp_ret['Marca'].unique().tolist())
    filtro_marca = st.sidebar.multiselect("🏷️ Marca", marcas_unicas, default=marcas_unicas)

    # ==========================================
    # 5. APLICAR FILTROS
    # ==========================================
    df_filtrado = df_precios.copy()
    
    # Aplicar filtro de tiempo
    if tipo_tiempo == "Rango de Fechas" and fecha_inicio and fecha_fin:
        df_filtrado = df_filtrado[(df_filtrado['Fecha'] >= fecha_inicio) & (df_filtrado['Fecha'] <= fecha_fin)]
    elif tipo_tiempo == "Semanas del Año" and semanas_seleccionadas:
        df_filtrado = df_filtrado[df_filtrado['Semana'].isin(semanas_seleccionadas)]
        
    # Aplicar filtro de cascada
    df_filtrado = df_filtrado[
        (df_filtrado['Categoría'].isin(filtro_categoria)) &
        (df_filtrado['Retailer'].isin(filtro_retailer)) &
        (df_filtrado['Marca'].isin(filtro_marca))
    ]
    
    # Aplicar búsqueda de texto libre
    if busqueda_texto:
        df_filtrado = df_filtrado[df_filtrado['Modelo'].str.contains(busqueda_texto, case=False, na=False)]

    st.sidebar.markdown("---")
    st.sidebar.write(f"**Registros listados: {len(df_filtrado)}**")

    # ==========================================
    # 6. DASHBOARD
    # ==========================================
    st.title("📊 Tablero de Control de Precios")
    
    if len(df_filtrado) > 0:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Productos", len(df_filtrado))
        col2.metric("Precio Promedio", f"${int(df_filtrado['Precio'].mean()):,}")
        col3.metric("Marcas Encontradas", df_filtrado['Marca'].nunique())
        
        # Métrica Nueva: Promedio de cuotas (ignorando los ceros)
        promedio_cuotas = df_filtrado[df_filtrado['Cuotas'] > 0]['Cuotas'].mean()
        col4.metric("Promedio Cuotas", f"{int(promedio_cuotas)} cuotas" if pd.notna(promedio_cuotas) else "N/A")
        
        st.write("---")
        
        if df_filtrado['Marca'].nunique() > 1:
            if st.checkbox("📈 Mostrar gráfico comparativo de precio promedio", value=False):
                st.subheader("Precio Promedio por Marca")
                st.bar_chart(df_filtrado.groupby('Marca')['Precio'].mean().sort_values(ascending=False))
                st.write("---")
                
        st.subheader("Base de Datos Detallada")
        st.dataframe(
            df_filtrado.style.format({'Precio': '${:,.0f}'}), 
            use_container_width=True,
            height=600
        )
    else:
        st.warning("⚠️ No hay datos que coincidan con los filtros.")
else:
    st.title("📊 Tablero de Control de Precios")
    st.info("Aún no hay datos en la base de datos.")