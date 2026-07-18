import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-secreta-muito-segura-123'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///arena_barber.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False