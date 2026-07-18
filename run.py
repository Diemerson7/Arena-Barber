import webbrowser
from threading import Timer
from app import create_app

app = create_app()

def open_browser():
    # Abre o navegador no endereço padrão do Flask
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    # O Timer espera 1.5 segundos para o servidor ligar e então abre o navegador
    Timer(1.5, open_browser).start()
    app.run(debug=True, use_reloader=False) # use_reloader=False evita abrir 2 vezes