from app import create_app, db, bcrypt
from app.models import User

app = create_app()
with app.app_context():
    # Limpa admins antigos para evitar erros
    User.query.filter_by(username='admin').delete()
    db.session.commit()

    # Cria o novo Admin oficial
    hashed_password = bcrypt.generate_password_hash('arena123').decode('utf-8')
    
    novo_admin = User(
        username='admin',
        email='contato@arenabarber.com',
        password_hash=hashed_password,
        is_admin=True # Isso garante que ele veja o Painel
    )
    
    db.session.add(novo_admin)
    db.session.commit()
    
    print("\n" + "="*30)
    print("ADMIN CRIADO COM SUCESSO!")
    print("Usuário: admin")
    print("Senha: arena123")
    print("="*30 + "\n")    