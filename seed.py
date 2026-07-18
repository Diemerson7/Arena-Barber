from app import create_app
from app.models import db, Service

app = create_app()
with app.app_context():
    # Adicionando serviços de exemplo
    s1 = Service(name="Corte Masculino", price=60.0, description="Corte clássico ou moderno com acabamento premium.")
    s2 = Service(name="Barba Terapia", price=45.0, description="Toalha quente, óleos essenciais e navalha.")
    s3 = Service(name="Combo Arena", price=90.0, description="Corte + Barba com desconto exclusivo.")
    
    db.session.add_all([s1, s2, s3])
    db.session.commit()
    print("Banco de dados populado com sucesso!")