from flask import render_template, redirect, url_for, request,  current_app
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import desc
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
from FotoSite import app, db
from FotoSite.models import User, ImageModel
from FotoSite.InitText import *


@app.route('/index')
def index():
    error = None
    paginated = []
    per_page = 3  # количество записей на странице
    page = request.args.get('page', 1, type=int)  # текущая страница
    total_pages = 0
    has_next = 0
    has_prev = 0

    if current_user.is_authenticated:
        sort_date = {}

        foto_all = ImageModel.query.filter_by(user_id=current_user.id).order_by(desc(ImageModel.date)).all()
        for foto in foto_all:
            # print(foto.image_path)
            date_str = foto.date.strftime('%d.%m.%Y')
            if date_str not in sort_date:
                sort_date[date_str] = []
            sort_date[date_str].append(foto)
        # Преобразование словаря в список
        list_foto = list(sort_date.items())
        total_pages = (len(list_foto) + per_page - 1) // per_page  # общее количество страниц
        paginated = list_foto[(page - 1) * per_page: page * per_page]

        # Флаги для пагинации
        has_next = page < total_pages
        has_prev = page > 1
    else:
        error = Error_NotAuthenticated
    return render_template(
        'index.html',
        TitlePage="Главная страница",
        TextPage="Добро пожаловать в фотоальбом",
        btnHomeVisible=True,
        btnAuthenticatedVisible=True,
        page_obj=paginated,
        page=page,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        AnonymousUser=error
    )


@app.route('/', methods=['GET', 'POST'])
@app.route('/authorization', methods=['GET', 'POST'])
def authorization():
    error = None
    message = None
    if current_user.is_authenticated:
        message = 'Вы авторизованы!'
    #     print('current_user', current_user.username)
    #     return redirect(url_for('index'))

    form_act = request.form.get('form_act', 'login')
    print('form_act ', form_act)
    if request.method == 'POST':
        username = request.form.get('username')
        password1 = request.form.get('password1')
        print('username ', username)
        print('password1 ', password1)

        if form_act == 'login':
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password1):
                login_user(user)
                return redirect(url_for('index'))
            else:
                error = Error_LoginOrPassword
        elif form_act == 'register':
            password2 = request.form.get('password2')
            if not (username or password1 or password2):
                error = Error_AllFieldsRequired
            elif password1 != password2:
                error = Error_PasswordsNotMatch
            elif User.query.filter_by(username=username).first():
                error = Error_UserExists
            elif len(password1) < Min_Password_Length:
                error = Error_Password_Length
            else:
                hashed_password = generate_password_hash(password1)
                new_user = User(username=username, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect(url_for('index'))
    return render_template('authorization.html', TitlePage=AuthTitlePage, btnHomeVisible=True,
                           btnAuthenticatedVisible=False, error=error, message=message)


def user_directory_path(user_id, filename):
    return f'images/{user_id}/{filename}'


def get_random_date():
    import random
    from datetime import datetime
    from datetime import timedelta
    random_days = random.randint(-15, 0)
    return datetime.now() + timedelta(days=random_days)


@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    if 'uploaded_files' not in request.files:
        return redirect(url_for('index'))

    for uploaded_file in request.files.getlist('uploaded_files'):
        if uploaded_file.filename != '':
            filename = secure_filename(uploaded_file.filename)
            filepath = user_directory_path(current_user.id, filename)
            full_path = os.path.join(current_app.root_path, 'static', filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            uploaded_file.save(full_path)
            # Сохранение в базе данных
            new_image = ImageModel(user_id=current_user.id, image_path=filepath, date=get_random_date())
            db.session.add(new_image)
            db.session.commit()
    return redirect(url_for('index'))


@app.route('/delete_image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    image = ImageModel.query.filter_by(id=image_id, user_id=current_user.id).first_or_404()
    # Удаление файла из файловой системы
    full_path = os.path.join(current_app.root_path, 'static', image.image_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    # Удаление записи из базы данных
    db.session.delete(image)
    db.session.commit()
    return redirect(url_for('index'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
