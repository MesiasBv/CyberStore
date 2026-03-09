from app import create_app

# Instanciamos la aplicación llamando a la fábrica
app = create_app()

if __name__ == '__main__':
    # debug=True es vital en VS Code: reinicia el servidor automáticamente 
    # cada vez que guardas un cambio en tus archivos .py
    app.run(debug=True, host='0.0.0.0', port=5000)