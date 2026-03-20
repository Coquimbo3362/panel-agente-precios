import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y BASE DE DATOS
# ==========================================
st.set_page_config(page_title="Panel de Control - Agente de Precios", layout="wide")

load_dotenv(override=True)
opciones = ClientOptions(schema="agente_precios")
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"), options=opciones)

st.title("⚙️ Backoffice - Agente de Precios")
st.write("Administración de datos maestros para el Bot de Scraping.")

tab_cat, tab_marcas, tab_ret, tab_urls = st.tabs(["📁 Categorías", "🏷️ Marcas", "🏢 Retailers", "🔗 URLs de Navegación"])

# ==========================================
# PESTAÑA 1: CATEGORÍAS
# ==========================================
with tab_cat:
    st.subheader("Gestión de Categorías")
    categorias = supabase.table("categorias").select("*").order("id").execute().data
    st.dataframe(categorias, use_container_width=True)
    
    with st.form("form_cat", clear_on_submit=True):
        st.write("➕ Agregar Nueva Categoría")
        nueva_cat = st.text_input("Nombre de la categoría (ej: Lavarropas)")
        if st.form_submit_button("Guardar Categoría"):
            if nueva_cat:
                supabase.table("categorias").insert({"nombre": nueva_cat}).execute()
                st.success("¡Categoría guardada!")
                st.rerun()

# ==========================================
# PESTAÑA 2: MARCAS
# ==========================================
with tab_marcas:
    st.subheader("Gestión de Marcas")
    marcas = supabase.table("marcas").select("*").order("id").execute().data
    st.dataframe(marcas, use_container_width=True)
    
    col_alta, col_baja = st.columns(2)
    with col_alta:
        with st.form("form_marca", clear_on_submit=True):
            st.write("➕ **Agregar Nueva Marca**")
            nueva_marca = st.text_input("Nombre de la marca (ej: Drean)")
            if st.form_submit_button("Guardar Marca"):
                if nueva_marca:
                    supabase.table("marcas").insert({"nombre": nueva_marca}).execute()
                    st.success("¡Marca guardada!")
                    st.rerun()

    with col_baja:
        st.write("🗑️ **Eliminar Marca**")
        if marcas:
            dicc_marcas_borrar = {f"ID: {m['id']} - {m['nombre']}": m['id'] for m in marcas}
            marca_a_borrar = st.selectbox("Seleccione la marca a eliminar:", options=list(dicc_marcas_borrar.keys()))
            if st.button("🚨 Borrar Marca Seleccionada", type="primary"):
                supabase.table("marcas").delete().eq("id", dicc_marcas_borrar[marca_a_borrar]).execute()
                st.success("¡Marca eliminada correctamente!")
                st.rerun()

# ==========================================
# PESTAÑA 3: RETAILERS
# ==========================================
with tab_ret:
    st.subheader("Configuración de Retailers (Tiendas)")
    retailers = supabase.table("retailers").select("*").order("id").execute().data
    st.dataframe(retailers, use_container_width=True)
    
    tab_alta_ret, tab_edit_ret = st.tabs(["➕ Nuevo Retailer", "✏️ Editar Retailer"])
    
    with tab_alta_ret:
        with st.form("form_retailer", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nombre_ret = col1.text_input("Nombre (ej: Fravega)")
            tipo_pag = col2.selectbox("Tipo Paginación",["PARAMETRO_URL", "CLICK_AJAX", "SCROLL_INFINITO"])
            sel_caja = col1.text_input("Selector Caja Producto (ej: .product-item)")
            sel_sig = col2.text_input("Selector Botón Siguiente (ej: a.next)")
            
            if st.form_submit_button("Guardar Retailer"):
                if nombre_ret and sel_caja:
                    supabase.table("retailers").insert({
                        "nombre": nombre_ret,
                        "selector_caja": sel_caja,
                        "selector_siguiente": sel_sig,
                        "tipo_paginacion": tipo_pag
                    }).execute()
                    st.success("¡Retailer guardado!")
                    st.rerun()

    with tab_edit_ret:
        if retailers:
            dicc_ret_edit = {f"ID: {r['id']} - {r['nombre']}": r for r in retailers}
            ret_seleccionado = st.selectbox("Seleccione el Retailer a editar:", options=list(dicc_ret_edit.keys()))
            datos_ret = dicc_ret_edit[ret_seleccionado]
            
            with st.form("form_edit_retailer"):
                st.info(f"Editando la configuración de: **{datos_ret['nombre']}**")
                col1, col2 = st.columns(2)
                nuevo_nombre = col1.text_input("Nombre", value=datos_ret['nombre'])
                opciones_pag =["PARAMETRO_URL", "CLICK_AJAX", "SCROLL_INFINITO"]
                idx_pag = opciones_pag.index(datos_ret['tipo_paginacion']) if datos_ret['tipo_paginacion'] in opciones_pag else 0
                nuevo_tipo_pag = col2.selectbox("Tipo Paginación", opciones_pag, index=idx_pag)
                nuevo_sel_caja = col1.text_input("Selector Caja Producto", value=datos_ret['selector_caja'])
                nuevo_sel_sig = col2.text_input("Selector Botón Siguiente", value=datos_ret['selector_siguiente'] if datos_ret['selector_siguiente'] else "")
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    supabase.table("retailers").update({
                        "nombre": nuevo_nombre,
                        "selector_caja": nuevo_sel_caja,
                        "selector_siguiente": nuevo_sel_sig,
                        "tipo_paginacion": nuevo_tipo_pag
                    }).eq("id", datos_ret['id']).execute()
                    st.success("¡Retailer actualizado con éxito!")
                    st.rerun()

# ==========================================
# PESTAÑA 4: URLs DE EXTRACCIÓN (NUEVA CON EDICIÓN)
# ==========================================
with tab_urls:
    st.subheader("Mapa de Navegación del Bot")
    urls_data = supabase.table("urls_extraccion").select("id, url_base, activo, categorias(id, nombre), retailers(id, nombre)").order("id").execute().data
    
    # Preparamos los datos para que se vean lindos en la tabla
    if urls_data:
        df_urls = [{"ID": u["id"], "Retailer": u["retailers"]["nombre"], "Categoría": u["categorias"]["nombre"], "URL": u["url_base"], "Activo": u["activo"]} for u in urls_data]
        st.dataframe(df_urls, use_container_width=True)
    else:
        st.info("No hay URLs configuradas.")

    if categorias and retailers:
        dicc_cat = {c['nombre']: c['id'] for c in categorias}
        dicc_ret = {r['nombre']: r['id'] for r in retailers}
        
        # Sub-pestañas para URLs
        tab_alta_url, tab_edit_url, tab_baja_url = st.tabs(["➕ Nueva URL", "✏️ Editar URL", "🗑️ Borrar URL"])
        
        # --- ALTA URL ---
        with tab_alta_url:
            with st.form("form_alta_url", clear_on_submit=True):
                cat_seleccionada = st.selectbox("Seleccione la Categoría", options=list(dicc_cat.keys()))
                ret_seleccionado = st.selectbox("Seleccione el Retailer", options=list(dicc_ret.keys()))
                url_ingresada = st.text_input("Pegue la URL base aquí (use {page} si es necesario)")
                
                if st.form_submit_button("Guardar URL"):
                    if url_ingresada:
                        supabase.table("urls_extraccion").insert({
                            "categoria_id": dicc_cat[cat_seleccionada],
                            "retailer_id": dicc_ret[ret_seleccionado],
                            "url_base": url_ingresada,
                            "activo": True
                        }).execute()
                        st.success("¡Ruta de navegación creada con éxito!")
                        st.rerun()

        # --- EDICIÓN URL ---
        with tab_edit_url:
            if urls_data:
                # Armamos un diccionario fácil de leer para el seleccionador
                dicc_urls_edit = {f"ID: {u['id']} - {u['retailers']['nombre']} ({u['categorias']['nombre']})": u for u in urls_data}
                url_seleccionada = st.selectbox("Seleccione la URL a editar:", options=list(dicc_urls_edit.keys()))
                datos_url = dicc_urls_edit[url_seleccionada]
                
                with st.form("form_edit_url"):
                    st.info(f"Editando URL de **{datos_url['retailers']['nombre']}** para la categoría **{datos_url['categorias']['nombre']}**")
                    
                    # Pre-cargamos la URL actual y el switch de Activo/Inactivo
                    nueva_url = st.text_input("URL base", value=datos_url['url_base'])
                    nuevo_estado = st.checkbox("¿Activar esta URL para el Bot?", value=datos_url['activo'])
                    
                    if st.form_submit_button("💾 Guardar Cambios"):
                        supabase.table("urls_extraccion").update({
                            "url_base": nueva_url,
                            "activo": nuevo_estado
                        }).eq("id", datos_url['id']).execute()
                        st.success("¡URL actualizada con éxito!")
                        st.rerun()
            else:
                st.info("No hay URLs para editar.")

        # --- BAJA URL ---
        with tab_baja_url:
            if urls_data:
                dicc_urls_borrar = {f"ID: {u['id']} - {u['retailers']['nombre']} ({u['categorias']['nombre']})": u['id'] for u in urls_data}
                url_a_borrar = st.selectbox("Seleccione la URL a eliminar:", options=list(dicc_urls_borrar.keys()))
                
                if st.button("🚨 Borrar URL Seleccionada", type="primary"):
                    supabase.table("urls_extraccion").delete().eq("id", dicc_urls_borrar[url_a_borrar]).execute()
                    st.success("¡URL eliminada!")
                    st.rerun()
            else:
                st.info("No hay URLs para borrar.")
    else:
        st.warning("⚠️ Primero debes crear al menos una Categoría y un Retailer para poder vincular URLs.")