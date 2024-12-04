# ~/project/backend/app/config.py

from pydantic import BaseSettings

class Settings(BaseSettings):
    # Configuraciones generales de la aplicación
    app_name: str = "Trading Platform"
    admin_email: str = "admin@trading-platform.com"
    debug_mode: bool = True

    # Configuración de base de datos
    database_url: str = "sqlite:///./trading.db"

    # Claves de API
    alpha_vantage_api_key: str = "your_alpha_vantage_api_key_here"
    binance_api_key: str = "your_binance_api_key_here"
    binance_api_secret: str = "your_binance_api_secret_here"

    class Config:
        env_file = ".env"

# Instancia de configuraciones
settings = Settings()
