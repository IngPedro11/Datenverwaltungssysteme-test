import os

def volcar_archivos(archivo_salida):
    ruta_inicial = os.getcwd()  # Carpeta actual
    with open(archivo_salida, "w", encoding="utf-8") as salida:
        for carpeta, subcarpetas, archivos in os.walk(ruta_inicial):
            for archivo in archivos:
                ruta_completa = os.path.join(carpeta, archivo)
                salida.write(f"=== ARCHIVO: {ruta_completa} ===\n\n")
                try:
                    with open(ruta_completa, "r", encoding="utf-8", errors="ignore") as f:
                        contenido = f.read()
                    salida.write(contenido + "\n\n")
                except Exception as e:
                    salida.write(f"[ERROR AL LEER EL ARCHIVO]: {e}\n\n")
                salida.write("="*80 + "\n\n")

# Genera resultado.txt en la carpeta actual
volcar_archivos("resultado.txt")
