import asyncio
from app.bot_advanced import main # Asegúrate que este sea el nombre de tu bot principal

if __name__ == "__main__":
    try:
        # En Python moderno, simplemente usamos run()
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🤖 Bot apagado con éxito.")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")