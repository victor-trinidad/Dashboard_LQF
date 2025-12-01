import streamlit as st
import pandas as pd
import numpy as np

# --- 1. PARÁMETROS DE AUDITORÍA (REGLAS DE NEGOCIO LQF) ---

# 🔴 LISTA DE CÓDIGOS CONTROLADOS (MÁXIMO 5% DE DESCUENTO)
codigos_controlados = [
    '3000113', '3000114', '3000080', '3000082', '3000083', '3000084', '3000085',
    '3000098', '3001265', '3001266', '3001267', '3001894', '3001896', '3002906',
    '3003648', '3004041', '3003870', '3004072', '5000002', '3004071', '3003953',
    '3003955', '3003952', '3004074', '3004073', '3003773', '3003775', '3004756'
]

# Topes de Descuento
DESC_MAX_CONTROLADOS = 5.0
DESC_MAX_EMPLEADOS = 0.0
DESC_MAX_NUTRICIA_BEBELAC = 6.0
DESC_MAX_GENERAL = 7.0

# Reglas de Intercompany (CONFIRMADAS)
DESC_INTERCOMPANY_200046 = 11.0 
DESC_INTERCOMPANY_200173 = 10.0
CLIENTE_200046 = '200046'
CLIENTE_200173 = '200173'
ALMACEN_EMPLEADOS_PERMITIDO = 1041
ALMACEN_OFERTAS = 1012
marcas_6_porciento = ['NUTRICIA', 'BEBELAC']
ZONAS_EMPLEADOS = ['EMPLEADOS LQF', 'MEDICOS PARTICULARES']


# --- 2. FUNCIÓN PRINCIPAL DE AUDITORÍA (CON LIMPIEZA DE COLUMNAS) ---
@st.cache_data
def ejecutar_auditoria(df):
    
    # 1. LIMPIEZA AUTOMÁTICA DE ENCABEZADOS (Solución a espacios y formato)
    df.columns = df.columns.str.strip()
    column_mapping = {
        'Fecha factura': 'Fecha factura', 'Almacen': 'Almacen', 'Tipo Venta': 'Tipo Venta',
        'Zona de Venta': 'Zona de Venta', 'Solicitante': 'Solicitante', 'Nombre 1': 'Nombre 1',
        'Codigo': 'Codigo', 'Material': 'Material', 'Jerarquia': 'Jerarquia',
        '% Desc': '% Desc', 'Valor neto': 'Valor neto',
        'Descuento %': '% Desc', 'codigo': 'Codigo', 'jerarquia': 'Jerarquia', 
        'Valor Neto': 'Valor neto', 'VALOR NETO': 'Valor neto'
    }
    df = df.rename(columns=column_mapping)
    
    # 2. Limpieza y Normalización de Datos
    df['% Desc'] = pd.to_numeric(df['% Desc'], errors='coerce')
    df['Almacen'] = pd.to_numeric(df['Almacen'], errors='coerce', downcast='integer')
    df['Solicitante'] = df['Solicitante'].astype(str)
    
    # 3. Lógica de Prioridad de Descuentos (np.select)
    condiciones = [
        ((df['Zona de Venta'] == 'EMPLEADOS LQF') & (df['Almacen'] != ALMACEN_EMPLEADOS_PERMITIDO) & (df['% Desc'] > DESC_MAX_EMPLEADOS)) | \
        ((df['Zona de Venta'] == 'MEDICOS PARTICULARES') & (df['% Desc'] > DESC_MAX_EMPLEADOS)),
        (df['Codigo'].isin(codigos_controlados)) & (df['% Desc'] > DESC_MAX_CONTROLADOS),
        (df['Solicitante'] == CLIENTE_200046) & (df['% Desc'] > DESC_INTERCOMPANY_200046),
        (df['Solicitante'] == CLIENTE_200173) & (df['% Desc'] > DESC_INTERCOMPANY_200173),
        (df['Jerarquia'].isin(marcas_6_porciento)) & (df['% Desc'] > DESC_MAX_NUTRICIA_BEBELAC),
        (df['% Desc'] > DESC_MAX_GENERAL)
    ]
    etiquetas_alerta = [
        '❌ Ilegal (Empleado/Médico)', '⚠️ Controlado (>5%) Excedido',
        '⚠️ Intercompany 200046 (>11%) Excedido', '⚠️ Intercompany 201173 (>10%) Excedido',
        '⚠️ Marca Nutricion (>6%) Excedido', '⚠️ General (>7%) Excedido'
    ]

    df['Alerta_Descuento'] = np.select(condiciones, etiquetas_alerta, default='OK')
    desvios_encontrados = df[df['Alerta_Descuento'] != 'OK']
    
    return desvios_encontrados, df


# --- INTERFAZ STREAMLIT (EL DASHBOARD) ---

st.set_page_config(page_title="Auditoría Continua de Precios LQF", layout="wide")
st.title("🛡️ Dashboard de Auditoría de Desviaciones de Precios - LQF")

# --- Mover el uploader y los filtros a la barra lateral ---
with st.sidebar:
    st.header("⚙️ Configuración y Filtros")
    uploaded_file = st.file_uploader("Subir Reporte de Ventas (CSV/XLSX)", type=['csv', 'xlsx'])
    
    st.markdown("---")
    st.subheader("Opciones de Filtrado")
    
    # FILTRO 1: Ventas a Funcionarios/Médicos (Zona de Venta)
    # Por defecto se excluyen (True) para enfocarse en ventas comerciales
    excluir_empleados = st.checkbox(
        'Excluir Ventas a Empleados/Médicos', 
        value=True, 
        help='Si está tildado, se excluyen las ventas con Zona de Venta: EMPLEADOS LQF y MEDICOS PARTICULARES del análisis.'
    )

    # FILTRO 2: Ventas del Depósito 1012 (Ofertas)
    # Por defecto se excluyen (True) si son ofertas especiales no sujetas a auditoría
    excluir_1012 = st.checkbox(
        'Excluir Ventas del Depósito 1012 (Ofertas)', 
        value=True, 
        help='Si está tildado, se excluyen las ventas provenientes del Almacén 1012 del análisis.'
    )


if uploaded_file is not None:
    try:
        # 1. Carga de datos con corrección de encabezado
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='latin1', header=1) 
        else:
            df = pd.read_excel(uploaded_file, header=1)
        
        # 2. Aplicación de Filtros seleccionados
        df_filtrado = df.copy()

        if excluir_empleados:
            df_filtrado = df_filtrado[~df_filtrado['Zona de Venta'].isin(ZONAS_EMPLEADOS)]

        if excluir_1012:
            df_filtrado = df_filtrado[df_filtrado['Almacen'] != ALMACEN_OFERTAS]

        if df_filtrado.empty:
            st.warning("El archivo cargado no contiene transacciones después de aplicar los filtros seleccionados. Intente destildar alguna opción en la barra lateral.")
            st.stop()
            
        # 3. Ejecutar auditoría sobre el DataFrame filtrado
        desvios, df_completo = ejecutar_auditoria(df_filtrado)
        
        # CÁLCULO DE KPIs (Métricas)
        total_transacciones = len(df_completo)
        transacciones_desviadas = len(desvios)
        porcentaje_cumplimiento = (1 - (transacciones_desviadas / total_transacciones)) * 100 if total_transacciones > 0 else 0
        valor_neto_desviado = pd.to_numeric(desvios['Valor neto'], errors='coerce').sum()
        
        # --- Implementación de 3 Pestañas (Tabs) ---
        tab1, tab2, tab3 = st.tabs(["📊 Resumen Ejecutivo", "⚠️ Análisis Detallado de Riesgo", "📝 Listado Completo Verificado"])

        with tab1:
            st.header("Métricas Clave de Cumplimiento")
            
            # Display de KPIs
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Transacciones Auditadas", f"{total_transacciones:,}")
            col2.metric("Transacciones con Desvío", f"{transacciones_desviadas:,}", delta=f"{transacciones_desviadas} líneas de riesgo")
            col3.metric("Nivel de Cumplimiento", f"{porcentaje_cumplimiento:.2f}%", delta=f"{(100 - porcentaje_cumplimiento):.2f}% de Incumplimiento", delta_color="inverse")
            col4.metric("Valor Neto de Desvíos (Gs.)", f"Gs. {valor_neto_desviado:,.0f}")
            
            st.markdown("---") 
            
            if not desvios.empty:
                st.info(f"Se encontraron **{transacciones_desviadas:,}** transacciones con desvío. Revise la pestaña 'Análisis Detallado de Riesgo'.")
            else:
                st.balloons()
                st.subheader("✅ ¡CUMPLIMIENTO TOTAL!")
                st.info("No se encontraron desviaciones en este reporte según las reglas definidas.")

        with tab2:
            if not desvios.empty:
                st.subheader("Gráfico de Riesgo: Distribución de Alertas por Tipo")
                
                # Gráfico de Barras
                alerta_counts = desvios['Alerta_Descuento'].value_counts().reset_index()
                alerta_counts.columns = ['Tipo de Alerta', 'Cantidad de Desvíos']
                alerta_counts = alerta_counts.set_index('Tipo de Alerta')
                st.bar_chart(alerta_counts, use_container_width=True, color='#f03c3c') 
                
                st.markdown("---")
                
                # DETALLE DE LA TABLA DE AUDITORÍA (Solo desvíos)
                st.subheader("Tabla Detallada de las Desviaciones")
                columnas_auditoria = ['Fecha factura', 'Almacen', 'Nombre 1', 'Codigo', 'Material', 'Jerarquia', '% Desc', 'Valor neto', 'Alerta_Descuento']
                st.dataframe(desvios[columnas_auditoria], use_container_width=True)
                
                # Opción para descargar solo los desvíos
                csv = desvios[columnas_auditoria].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descargar Alertas en CSV", data=csv, file_name='Reporte_Desviaciones_LQF.csv', mime='text/csv',)
                
            else:
                st.info("No hay desvíos que analizar en este reporte.")

        with tab3:
            st.subheader("Listado de Todas las Transacciones Verificadas")
            st.info("Esta tabla muestra todas las líneas del archivo cargado con el resultado de la auditoría (OK o Alerta), luego de aplicar los filtros del sidebar.")

            # Columnas seleccionadas para el listado completo
            columnas_completas = ['Fecha factura', 'Almacen', 'Nombre 1', 'Codigo', 'Material', 'Jerarquia', 'Cant', '% Desc', 'Valor neto', 'Alerta_Descuento']
            
            # Display del DataFrame completo
            st.dataframe(df_completo[columnas_completas], use_container_width=True)

            # Opción para descargar el archivo completo con la columna de alerta
            csv_completo = df_completo[columnas_completas].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Descargar Listado Completo Auditado en CSV", 
                data=csv_completo, 
                file_name='Reporte_Completo_Auditado_LQF.csv', 
                mime='text/csv'
            )
            
    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo. Error: {e}")
