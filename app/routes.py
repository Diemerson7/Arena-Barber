from flask import render_template, url_for, flash, redirect, request
from flask import current_app as app
from app import db, bcrypt
from app.models import User, Service, Barber, Appointment
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
from flask import jsonify, request, current_app
import os
from werkzeug.utils import secure_filename

# --- ROTA DA LANDING PAGE (HOME) ---
@app.route('/')
def index():
    # Busca todos os serviços para mostrar no "Menu de Especialidades"
    servicos = Service.query.all()
    return render_template('index.html', servicos=servicos)

# --- ROTA DE LOGIN (ÍCONE DO BONEQUINHO) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Se o cara já estiver logado, manda ele de volta pra Home
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Procura o usuário pelo username ou email
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        # Verifica a senha criptografada (BCrypt)
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Bem-vindo à Arena Barber!', 'success')
            
            # Se for Admin, pode mandar direto pro painel se quiser, 
            # mas o padrão é ir pra home e o botão "Admin" aparecer lá.
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
            
    return render_template('login.html')

# --- ROTA DE CADASTRO DE CLIENTES ---
@app.route('/cadastro', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        hashed_password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        
        # Verifica se o usuário já existe
        user_exists = User.query.filter_by(username=request.form.get('username')).first()
        if user_exists:
            flash('Este nome de usuário já está em uso.', 'danger')
            return redirect(url_for('register'))

        new_user = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            password_hash=hashed_password,
            is_admin=False # Clientes novos nunca são admins
        )
        db.session.add(new_user)
        db.session.commit()

        # Mensagem de Boas-vindas
        flash('Bem-vindo à Arena Barber! Sua conta foi criada.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

# --- ROTA DE LOGOUT ---
@app.route('/logout')
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('index'))

# --- PAINEL ADMINISTRATIVO (PROTEGIDO) ---
@app.route('/admin')
@login_required
def admin_panel():
    # Segurança de elite: Mesmo logado, se não for o dono, é expulso
    if not current_user.is_admin:
        flash('Acesso proibido! Apenas para administradores.', 'danger')
        return redirect(url_for('index'))
    
    # Carrega os dados para o Admin gerenciar
    servicos = Service.query.all()
    barbeiros = Barber.query.all()
    usuarios = User.query.all()
    agendamentos = Appointment.query.all()
    return render_template('admin.html', servicos=servicos, barbeiros=barbeiros, agendamentos=agendamentos, usuarios=usuarios)


# --- ADICIONAR SERVIÇO ---
@app.route('/admin/add-service', methods=['POST'])
@login_required
def add_service():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    new_service = Service(
        name=request.form.get('name'),
        price=float(request.form.get('price')),
        description=request.form.get('description')
    )
    db.session.add(new_service)
    db.session.commit()
    flash('Serviço adicionado com sucesso!', 'success')
    return redirect(url_for('admin_panel'))

# --- EXCLUIR SERVIÇO ---
@app.route('/admin/delete-service/<int:id>', methods=['DELETE', 'POST'])
@login_required
def delete_service(id):
    if not current_user.is_admin: return jsonify({'error': 'Acesso negado'}), 403
    service = Service.query.get(id)
    if service:
        try:
            db.session.delete(service)
            db.session.commit()
            return jsonify({'success': True})
        except:
            db.session.rollback()
            return jsonify({'error': 'Não é possível excluir um serviço que possui agendamentos vinculados.'}), 400
    return jsonify({'error': 'Serviço não encontrado'}), 404

# --- ADICIONAR BARBEIRO ---
@app.route('/admin/add-barber', methods=['POST'])
@login_required
def add_barber():
    if not current_user.is_admin: return redirect(url_for('index'))
    new_barber = Barber(name=request.form.get('name'))
    db.session.add(new_barber)
    db.session.commit()
    flash('Barbeiro adicionado!', 'success')
    return redirect(url_for('admin_panel', section='barbeiros'))

# --- EXCLUIR BARBEIRO ---
@app.route('/admin/delete-barber/<int:id>', methods=['DELETE', 'POST'])
@login_required
def delete_barber(id):
    if not current_user.is_admin: return jsonify({'error': 'Acesso negado'}), 403
    barber = Barber.query.get(id)
    if barber:
        try:
            db.session.delete(barber)
            db.session.commit()
            return jsonify({'success': True})
        except:
            db.session.rollback()
            return jsonify({'error': 'Não é possível excluir um barbeiro que possui agendamentos vinculados.'}), 400
    return jsonify({'error': 'Barbeiro não encontrado'}), 404

# --- LISTAR USUÁRIOS NO ADMIN ---
@app.route('/admin/users')
@login_required
def manage_users():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    usuarios = User.query.all()
    return render_template('admin_users.html', usuarios=usuarios)

# --- EDITAR SERVIÇO ---
@app.route('/admin/edit-service/<int:id>', methods=['POST'])
@login_required
def edit_service(id):
    if not current_user.is_admin: return redirect(url_for('index'))
    service = Service.query.get(id)
    service.name = request.form.get('name')
    service.price = float(request.form.get('price'))
    service.description = request.form.get('description')
    db.session.commit()
    flash('Serviço atualizado!', 'success')
    return redirect(url_for('admin_panel'))

# --- EDITAR BARBEIRO + UPLOAD DE FOTO ---
@app.route('/admin/edit-barber/<int:id>', methods=['POST'])
@login_required
def edit_barber(id):
    if not current_user.is_admin: return redirect(url_for('index'))
    barber = Barber.query.get(id)
    barber.name = request.form.get('name')
    
    file = request.files.get('profile_img')
    if file and file.filename != '':
        filename = secure_filename(f"barber_{barber.id}.jpg")
        # Caminho onde a foto será salva
        upload_path = os.path.join(app.root_path, 'static/img/barbers', filename)
        file.save(upload_path)
        barber.profile_img = filename # Salva o nome da foto no banco

    db.session.commit()
    flash('Barbeiro atualizado!', 'success')
    return redirect(url_for('admin_panel', section='barbeiros'))

# --- EXCLUIR USUÁRIO ---
@app.route('/admin/delete-user/<int:id>', methods=['DELETE', 'POST'])
@login_required
def delete_user(id):
    if not current_user.is_admin: return jsonify({'error': 'Acesso negado'}), 403
    user = User.query.get(id)
    if user.id == current_user.id: return jsonify({'error': 'Você não pode se deletar'}), 400
    if user:
        try:
            db.session.delete(user)
            db.session.commit()
            return jsonify({'success': True})
        except:
            db.session.rollback()
            return jsonify({'error': 'Erro ao deletar usuário.'}), 400
    return jsonify({'error': 'Usuário não encontrado'}), 404

# --- ROTA DE AGENDAMENTO (CLIENTE) ---
@app.route('/agendar', methods=['GET', 'POST'])
@login_required
def booking():
    services = Service.query.all()
    barbers = Barber.query.all()
    
    # Lista completa de horários da Arena Barber
    all_times = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

    if request.method == 'POST':
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        barber_id = request.form.get('barber_id')
        service_id = request.form.get('service_id')

        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_obj = datetime.strptime(time_str, '%H:%M').time()

        # VALIDAÇÃO REALISTA: Verifica se o barbeiro já está ocupado
        conflict = Appointment.query.filter_by(
            date=date_obj, 
            time=time_obj, 
            barber_id=barber_id
        ).first()

        if conflict:
            flash('Desculpe, este barbeiro já possui um cliente neste horário.', 'danger')
            return redirect(url_for('booking'))

        # Se não há conflito, salva
        new_appointment = Appointment(
            date=date_obj,
            time=time_obj,
            service_id=service_id,
            barber_id=barber_id,
            client_name=current_user.username,
            client_phone=current_user.email
        )
        db.session.add(new_appointment)
        db.session.commit()
        
        flash(f'Agendado com sucesso para as {time_str}!', 'success')
        return redirect(url_for('index'))

    return render_template('booking.html', services=services, barbers=barbers, times=all_times)

# --- PÁGINA: MEUS HORÁRIOS (PORTAL DO CLIENTE) ---
@app.route('/meus-horarios')
@login_required
def my_appointments():
    # Buscamos apenas os agendamentos onde o client_name é igual ao username do logado
    # Ordenamos pela data e hora mais próxima
    agendamentos = Appointment.query.filter_by(client_name=current_user.username).order_by(Appointment.date.asc(), Appointment.time.asc()).all()
    return render_template('my_appointments.html', agendamentos=agendamentos)

# --- CANCELAR AGENDAMENTO ---
@app.route('/cancelar-agendamento/<int:id>', methods=['POST'])
@login_required
def cancel_appointment(id):
    agendamento = Appointment.query.get_or_404(id)
    
    # SEGURANÇA SÊNIOR: Verifica se o agendamento pertence ao usuário logado
    if agendamento.client_name != current_user.username:
        flash('Você não tem permissão para cancelar este horário.', 'danger')
        return redirect(url_for('my_appointments'))
    
    db.session.delete(agendamento)
    db.session.commit()
    
    flash('Agendamento cancelado com sucesso.', 'success')
    return redirect(url_for('my_appointments'))