from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from backend.app.db import Base


class User(Base):
    """
    Modelo de usuario para la base de datos.
    Representa a los usuarios de la plataforma.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)


class SP500Data(Base):
    """
    Modelo para almacenar datos diarios de las empresas del S&P 500.
    """
    __tablename__ = "sp500_data"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    adj_close = Column(Float, nullable=True)  # Asegúrate de que exista esta columna
    volume = Column(Integer, nullable=False)


class SP500IntradayData(Base):
    """
    Modelo para almacenar datos intradía de las empresas del S&P 500.
    """
    __tablename__ = "sp500_intraday_data"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)  # Símbolo del activo
    datetime = Column(DateTime, nullable=False, index=True)  # Fecha y hora del dato
    open = Column(Float, nullable=False)  # Precio de apertura
    high = Column(Float, nullable=False)  # Precio máximo
    low = Column(Float, nullable=False)  # Precio mínimo
    close = Column(Float, nullable=False)  # Precio de cierre
    volume = Column(Integer, nullable=False)  # Volumen
