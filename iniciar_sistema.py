import os
import sys
import traceback

try:
    import streamlit.web.cli as stcli

    if __name__ == "__main__":
        # Localiza onde o app.py está escondido dentro da pasta compilada
        if getattr(sys, 'frozen', False):
            dirname = sys._MEIPASS
        else:
            dirname = os.path.dirname(os.path.abspath(__file__))
            
        caminho_app = os.path.join(dirname, 'app.py')
        
        # Força a execução do Streamlit pedindo para ele mesmo abrir o navegador
        sys.argv = [
            "streamlit", 
            "run", 
            caminho_app, 
            "--server.headless=false",
            "--global.developmentMode=false"
        ]
        
        sys.exit(stcli.main())

except Exception as e:
    print("🚨 OCORREU UM ERRO FATAL NO SISTEMA:")
    traceback.print_exc()
    input("\nPressione ENTER para fechar a tela...")
