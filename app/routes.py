from flask import render_template, url_for, flash, redirect, request, jsonify
from flask import current_app as app
from app import db, bcrypt
from app.models import User, Service, Barber, Appointment, Holiday
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime, time, timedelta

# --- FUNÇÃO AUXILIAR: REGRAS DE HORÁRIO ---
def get_operating_hours(date_obj):
    """Define o horário de funcionamento exato da Arena Barber"""
    # Férias até 26/07. Dia 27/07 já é horário normal.
    vacation_limit = datetime(2026, 7, 27).date()
    
    if date_obj < vacation_limit:
        return "10:00", "19:30" # Horário de Férias
    
    weekday = date_obj.weekday() # 0=Segunda, 5=Sábado, 6=Domingo
    if weekday == 6: return None, None # Domingo fechado
    if weekday == 5: return "09:30", "19:00" # Sábado
    return "13:30", "19:30" # Dias Úteis Normal

# --- ROTA DA HOME ---
@app.route('/')
def index():
    servicos = Service.query.all()
    return render_template('index.html', servicos=servicos)

# --- API DE HORÁRIOS LIVRES ---
@app.route('/api/get-available-times')
def get_available_times():
    barber_id = request.args.get('barber_id')
    date_str = request.args.get('date')
    if not barber_id or not date_str: return jsonify({'is_holiday': False, 'slots': []})

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # 1. VERIFICA FERIADO
        holiday = Holiday.query.filter_by(date=selected_date).first()
        if holiday:
            friendly_reason = holiday.description if (holiday.description and len(holiday.description) > 1) else "Recesso Administrativo"

            return jsonify({
                'is_holiday': True, 
                'reason': friendly_reason
            })

        # 2. VERIFICA DOMINGO
        start_str, end_str = get_operating_hours(selected_date)
        if not start_str: 
            return jsonify({
                'is_holiday': True, 
                'reason': "A Arena fecha aos domingos"
            })

        # 3. LÓGICA NORMAL DE SLOTS (Almoço, Ocupado, Passado)
        lunch_start = time(12, 0)
        lunch_end = time(14, 0)
        existing_appts = Appointment.query.filter_by(barber_id=barber_id, date=selected_date).all()

        available_slots = []
        current_dt = datetime.combine(selected_date, datetime.strptime(start_str, '%H:%M').time())
        end_dt = datetime.combine(selected_date, datetime.strptime(end_str, '%H:%M').time())

        while current_dt < end_dt:
            slot_time = current_dt.time()
            is_lunch = slot_time >= lunch_start and slot_time < lunch_end
            
            is_busy = False
            for appt in existing_appts:
                duration = appt.service.duration if appt.service else 40
                appt_start = datetime.combine(selected_date, appt.time)
                appt_end = appt_start + timedelta(minutes=duration)
                if current_dt >= appt_start and current_dt < appt_end:
                    is_busy = True
                    break
            
            is_past = False
            if selected_date == datetime.now().date() and slot_time <= datetime.now().time():
                is_past = True

            if not is_lunch and not is_busy and not is_past:
                available_slots.append(slot_time.strftime('%H:%M'))
            
            current_dt += timedelta(minutes=30)

        return jsonify({'is_holiday': False, 'slots': available_slots})
    
    except Exception as e:
        return jsonify({'is_holiday': False, 'slots': [], 'error': str(e)})

# --- ROTA DE AGENDAMENTO (POST) ---
@app.route('/agendar', methods=['GET', 'POST'])
@login_required
def booking():
    services = Service.query.all()
    barbers = Barber.query.all()

    if request.method == 'POST':
        service_id = request.form.get('service_id')
        barber_id = request.form.get('barber_id')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        
        if not all([service_id, barber_id, date_str, time_str]):
            flash('Por favor, preencha todos os campos.', 'danger')
            return redirect(url_for('booking'))

        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        selected_time = datetime.strptime(time_str, '%H:%M').time()
        
        # Bloqueia 2 agendamentos no mesmo dia
        check_user = Appointment.query.filter_by(client_name=current_user.username, date=selected_date).first()
        if check_user:
            flash('Você já tem um horário neste dia!', 'danger')
            return redirect(url_for('booking'))

        new_appt = Appointment(
            date=selected_date, time=selected_time,
            service_id=service_id, barber_id=barber_id,
            client_name=current_user.username, client_phone=current_user.email
        )
        db.session.add(new_appt)
        db.session.commit()
        flash('Agendado com sucesso!', 'success')
        return redirect(url_for('index'))

    return render_template('booking.html', services=services, barbers=barbers)

# --- LOGIN / CADASTRO / LOGOUT ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            flash('Bem-vindo à Arena Barber!', 'success')
            return redirect(url_for('index'))
        flash('Login inválido.', 'danger')
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Verifica se já existe
        if User.query.filter_by(email=request.form.get('email')).first():
            flash('Este e-mail já tem conta.', 'danger')
            return redirect(url_for('register'))
        
        hashed = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        new_u = User(username=request.form.get('username'), email=request.form.get('email'), password_hash=hashed)
        db.session.add(new_u)
        db.session.commit()
        flash('Conta criada! Bem-vindo.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- ADMIN PANEL ---
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin: return redirect(url_for('index'))
    return render_template('admin.html', 
                           servicos=Service.query.all(), 
                           barbeiros=Barber.query.all(), 
                           agendamentos=Appointment.query.all(),
                           usuarios=User.query.all(),
                           feriados=Holiday.query.all())

# --- ACTIONS ADMIN (ADICIONAR / EDITAR / DELETAR) ---

@app.route('/admin/add-service', methods=['POST'])
@login_required
def add_service():
    new_s = Service(name=request.form.get('name'), price=float(request.form.get('price')), duration=int(request.form.get('duration')))
    db.session.add(new_s)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/edit-service/<int:id>', methods=['POST'])
@login_required
def edit_service(id):
    s = Service.query.get(id)
    s.name = request.form.get('name'); s.price = float(request.form.get('price')); s.duration = int(request.form.get('duration'))
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete-service/<int:id>', methods=['POST'])
@login_required
def delete_service(id):
    s = Service.query.get(id); db.session.delete(s); db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/add-barber', methods=['POST'])
@login_required
def add_barber():
    new_b = Barber(name=request.form.get('name'))
    db.session.add(new_b)
    db.session.commit()
    return redirect(url_for('admin_panel', section='barbeiros'))

@app.route('/admin/delete-barber/<int:id>', methods=['POST'])
@login_required
def delete_barber(id):
    b = Barber.query.get(id); db.session.delete(b); db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/delete-appointment/<int:id>', methods=['POST'])
@login_required
def delete_appointment(id):
    a = Appointment.query.get(id); db.session.delete(a); db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/delete-user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    u = User.query.get(id)
    if u.id != current_user.id:
        db.session.delete(u); db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Não pode se deletar'})

@app.route('/meus-horarios')
@login_required
def my_appointments():
    apps = Appointment.query.filter_by(client_name=current_user.username).all()
    return render_template('my_appointments.html', agendamentos=apps)

@app.route('/cancelar-agendamento/<int:id>', methods=['POST'])
@login_required
def cancel_appointment(id):
    a = Appointment.query.get(id)
    if a.client_name == current_user.username:
        db.session.delete(a); db.session.commit()
        flash('Cancelado.', 'success')
    return redirect(url_for('my_appointments'))

@app.route('/admin/add-holiday', methods=['POST'])
@login_required
def add_holiday():
    if not current_user.is_admin: return redirect(url_for('index'))
    date_str = request.form.get('date')
    desc = request.form.get('description')
    
    new_h = Holiday(date=datetime.strptime(date_str, '%Y-%m-%d').date(), description=desc)
    db.session.add(new_h)
    db.session.commit()
    # MUDANÇA: Agora redireciona para a seção de feriados
    return redirect(url_for('admin_panel', section='feriados'))

@app.route('/admin/delete-holiday/<int:id>', methods=['POST'])
@login_required
def delete_holiday(id):
    h = Holiday.query.get(id); db.session.delete(h); db.session.commit()
    return jsonify({'success': True})