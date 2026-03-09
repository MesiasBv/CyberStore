import sys
import os

def leer_archivo(ruta):
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
        print(leer_archivo(ruta))
    else:
        print("Usage: python leer_archivo.py <ruta_archivo>")

