import pandas as pd
import os
import glob
import csv
from datetime import datetime

def transformar_tejeduria(archivo_origen, carpeta_destino=None):
    """Transforma CSV de tejeduría al formato EXACTO del archivo que funciona."""
    print(f"\n{'='*60}")
    print(f"Procesando: {os.path.basename(archivo_origen)}")
    print(f"{'='*60}")
    
    # 1. Leer CSV origen
    df = pd.read_csv(archivo_origen, skip_blank_lines=True)
    df = df.dropna(how='all')
    df.columns = df.columns.str.strip()
    
    print(f"✓ Columnas origen: {len(df.columns)}")
    print(f"✓ Filas: {len(df)}")
    
    # 2. Transformar fecha: 2026-08-21 → 21/8/2026 (D/M/YYYY)
    def formatear_fecha(fecha_str):
        try:
            fecha = datetime.strptime(str(fecha_str).strip(), '%Y-%m-%d')
            return f"{fecha.day}/{fecha.month}/{fecha.year}"
        except:
            return str(fecha_str)
    
    df['Fecha'] = df['FECHA'].apply(formatear_fecha)
    
    # 3. Mayúsculas
    df['Dia'] = df['DIA'].astype(str).str.upper().str.strip()
    df['Mes'] = df['MES'].astype(str).str.upper().str.strip()
    df['Actividad'] = df['Actividad'].astype(str).str.upper().str.strip()
    
    # 4. Telar con ceros a la izquierda (2 dígitos)
    df['Telar_fmt'] = df['Telar'].astype(str).str.zfill(2)
    
    # 5. Referencia con salto de línea
    def formatear_referencia(ref):
        try:
            ref_str = str(ref).strip()
            if '-' in ref_str:
                partes = ref_str.split('-', 1)
                return f"{partes[0]}-\n{partes[1].strip()}"
            return ref_str
        except:
            return str(ref)
    
    df['Referencia_fmt'] = df['Referencia'].apply(formatear_referencia)
    
    # 6. Limpiar decimales (4.0 → 4)
    columnas_numericas = ['PPP', 'Metros Tejidos', 'Lote', 'Cad.',
                          '% Efic. Máquina', '% Efic. Operador',
                          'RxCMP Trama', 'R Abs. Trama',
                          'RxCMP Urd.', 'R Abs. Urd.',
                          'RxCMP Manual', 'R Abs. Manual',
                          'Tiempo Disponible (H)', 'RPM', '#']
    
    for col in columnas_numericas:
        if col in df.columns:
            def limpiar_decimal(x):
                try:
                    if pd.isna(x) or str(x).strip() == '':
                        return ''
                    num = float(x)
                    if num.is_integer():
                        return str(int(num))
                    return str(num)
                except:
                    return str(x)
            df[col] = df[col].apply(limpiar_decimal)
    
    # 7. ⭐ CABECERAS EXACTAS con saltos de línea (como el archivo que funciona)
    cabeceras_destino = [
        'Dia', 'Mes', 'Fecha', '#', 'Turno', 'Actividad', 'Telar', 'Operador',
        'Referencia', 'Estilo', 'PPP', 'Metros\nTejidos', 'Lote', 'Cad.',
        '% Efic.\nMáquina', '% Efic.\nOperador',
        'RxCMP\nTrama', 'R Abs.\nTrama',
        'RxCMP\nUrd.', 'R Abs.\nUrd.',
        'RxCMP\nManual', 'R Abs.\nManual',
        'Tiempo\nDisponible\n(H)',
        'TELAR', 'RPM', 'TackTime', 'PasadasTack', 'PlegaID'
    ]
    
    # 8. Mapeo de columnas origen → destino
    mapeo = {
        'Dia': 'Dia',
        'Mes': 'Mes',
        'Fecha': 'Fecha',
        '#': '#',
        'Turno': 'turno',
        'Actividad': 'Actividad',
        'Telar': 'Telar_fmt',
        'Operador': 'Operador',
        'Referencia': 'Referencia_fmt',
        'Estilo': 'Estilo',
        'PPP': 'PPP',
        'Metros\nTejidos': 'Metros Tejidos',
        'Lote': 'Lote',
        'Cad.': 'Cad.',
        '% Efic.\nMáquina': '% Efic. Máquina',
        '% Efic.\nOperador': '% Efic. Operador',
        'RxCMP\nTrama': 'RxCMP Trama',
        'R Abs.\nTrama': 'R Abs. Trama',
        'RxCMP\nUrd.': 'RxCMP Urd.',
        'R Abs.\nUrd.': 'R Abs. Urd.',
        'RxCMP\nManual': 'RxCMP Manual',
        'R Abs.\nManual': 'R Abs. Manual',
        'Tiempo\nDisponible\n(H)': 'Tiempo Disponible (H)',
        'TELAR': 'Telar_fmt',
        'RPM': 'RPM',
        'TackTime': None,
        'PasadasTack': None,
        'PlegaID': None,
    }
    
    # 9. Generar nombre de salida
    nombre_base = os.path.basename(archivo_origen)
    match_fecha = None
    for parte in nombre_base.replace('.csv', '').split('_'):
        if parte.isdigit() and len(parte) == 8:
            match_fecha = parte
            break
    
    if match_fecha:
        fecha_obj = datetime.strptime(match_fecha, '%Y%m%d')
        fecha_formateada = fecha_obj.strftime('%d-%m-%Y')
    else:
        fecha_formateada = datetime.now().strftime('%d-%m-%Y')
    
    nombre_salida = f"Sala97_Estilos_Produccion - Tejeduria {fecha_formateada}.csv"
    
    if carpeta_destino is None:
        carpeta_destino = os.path.dirname(archivo_origen) or '.'
    
    ruta_salida = os.path.join(carpeta_destino, nombre_salida)
    
    # 10. Escribir CSV con separador ; y cabeceras con saltos de línea
    with open(ruta_salida, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        
        # Cabecera con saltos de línea
        writer.writerow(cabeceras_destino)
        
        # Filas de datos
        for _, row in df.iterrows():
            fila = []
            for cabecera in cabeceras_destino:
                col_origen = mapeo.get(cabecera)
                if col_origen is None:
                    # Columnas vacías (TackTime, PasadasTack, PlegaID)
                    fila.append('')
                elif col_origen in df.columns:
                    valor = row[col_origen]
                    if pd.isna(valor) or str(valor).strip() == '':
                        fila.append('')
                    else:
                        fila.append(str(valor))
                else:
                    fila.append('')
            writer.writerow(fila)
    
    print(f"\n✓ Archivo generado: {nombre_salida}")
    print(f"  Ruta: {ruta_salida}")
    print(f"  Filas: {len(df)}")
    print(f"  Separador: ; (punto y coma)")
    print(f"  Cabeceras: con saltos de línea (igual al 17-08)")
    print(f"  Fecha: formato D/M/YYYY")
    print(f"  Telar: con ceros a la izquierda")
    print(f"  Referencia: con salto de línea")
    
    return ruta_salida


if __name__ == "__main__":
    carpeta_actual = os.path.dirname(os.path.abspath(__file__))
    
    print(f"\n{'='*60}")
    print(f"TRANSFORMADOR CSV - TEJEDURÍA (VERSIÓN DEFINITIVA)")
    print(f"{'='*60}")
    print(f"Carpeta: {carpeta_actual}")
    
    archivos = glob.glob(os.path.join(carpeta_actual, "tejeduria_*.csv"))
    print(f"\n📊 Archivos encontrados: {len(archivos)}")
    
    if len(archivos) == 0:
        print("❌ No se encontraron archivos tejeduria_*.csv")
    else:
        for archivo in archivos:
            try:
                transformar_tejeduria(archivo)
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n✅ Proceso completado.")
    print("\n📌 IMPORTANTE: Los archivos generados ahora tienen:")
    print("   ✓ Separador ; (punto y coma)")
    print("   ✓ Cabeceras con saltos de línea (igual al 17-08)")
    print("   ✓ Fecha D/M/YYYY")
    print("   ✓ Telar con ceros (01, 02, 03...)")
    print("   ✓ Referencia con salto de línea")
    
    input("\nPresiona Enter para salir...")