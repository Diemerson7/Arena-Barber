from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# 1. Modelo de Usuário (Login de Admin)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) # Adicionei email
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) # Padrão é FALSO para clientes

# 2. Modelo de Serviços (Corte, Barba, etc.)
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Integer, default=60) # Tempo em minutos
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointments = db.relationship('Appointment', backref='service', lazy=True) # Relacionamento com Agendamentos

# 3. Modelo de Barbeiros (Os profissionais da Arena)
class Barber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    profile_img = db.Column(db.String(200), default='default_barber.jpg')
    # Relacionamento: Um barbeiro tem vários agendamentos
    appointments = db.relationship('Appointment', backref='barber', lazy=True)

# 4. Modelo de Agendamentos (Onde a mágica acontece)
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    client_phone = db.Column(db.String(20), nullable=False)
    
    # Chaves Estrangeiras (Ligando com as outras tabelas)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    barber_id = db.Column(db.Integer, db.ForeignKey('barber.id'), nullable=False)
    
    status = db.Column(db.String(20), default='Agendado') # Agendado, Cancelado, Concluído
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Feriados (para bloquear datas específicas)
class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    description = db.Column(db.String(100)) # Ex: "Natal", "Folga Coletiva"