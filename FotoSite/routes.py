import os
from sqlalchemy import desc
from flask import render_template, redirect, url_for, request, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
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

        # Получение всех фотографий текущего пользователя из базы данных, отсортированных по дате в порядке убывания
        foto_all = ImageModel.query.filter_by(user_id=current_user.id).order_by(desc(ImageModel.date)).all()
        for foto in foto_all:
            # Преобразование даты в строку в формате 'дд.мм.гггг'
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
        TitlePage=IndexTitlePage,
        TextPage=IndexTextPage,
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
    """ Авторизация и регистрация """
    error = None
    message = None
    if current_user.is_authenticated:
        message = 'Вы авторизованы!'

    # Получение типа активной формы (вход или регистрация)
    form_act = request.form.get('form_act', 'login')
    if request.method == 'POST':
        # Получаем логин и пароль
        username = request.form.get('username')
        password1 = request.form.get('password1')

        # Обработка действия формы, вход
        if form_act == 'login':
            user = User.query.filter_by(username=username).first()
            # Проверка, что пользователь существует и пароль верен
            if user and check_password_hash(user.password, password1):
                # Вход пользователя в систему
                login_user(user)
                return redirect(url_for('index'))
            else:
                # Сообщение об ошибке при неверном логине или пароле
                error = Error_LoginOrPassword

        # Обработка действия формы, регистрация
        elif form_act == 'register':
            password2 = request.form.get('password2')

            # Проверка на заполнение всех полей
            if not (username or password1 or password2):
                error = Error_AllFieldsRequired
            # Проверка, совпадают ли введенные пароли
            elif password1 != password2:
                error = Error_PasswordsNotMatch
            # Проверка на совпадение логина
            elif User.query.filter_by(username=username).first():
                error = Error_UserExists
            # Проверка длины пароля
            elif len(password1 or password2) <= Min_Password_Length:
                error = Error_Password_Length
            else:
                # Хэширование пароля
                hashed_password = generate_password_hash(password1)
                new_user = User(username=username, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                # Вход пользователя в систему
                login_user(new_user)
                return redirect(url_for('index'))
    return render_template('authorization.html',
                           TitlePage=AuthTitlePage,
                           btnHomeVisible=True,
                           btnAuthenticatedVisible=False,
                           error=error,
                           message=message)


def user_directory_path(user_id, filename):
    return f'images/{user_id}/{filename}'


def get_random_date():
    """Генерируем случайное смещение от текущей даты"""
    import random
    from datetime import datetime
    from datetime import timedelta

    random_days = random.randint(-15, 0)
    return datetime.now() + timedelta(days=random_days)


@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    # Проверка наличия файла в запросе, если его нет, происходит перенаправление
    if 'uploaded_files' not in request.files:
        return redirect(url_for('index'))

    for uploaded_file in request.files.getlist('uploaded_files'):
        if uploaded_file.filename != '':
            filename = secure_filename(uploaded_file.filename)
            filepath = user_directory_path(current_user.id, filename)
            full_path = os.path.join(current_app.root_path, 'static', filepath)
            # Создание всех необходимых промежуточных директорий, если их еще нет
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
    # Получение пути к файлу изображения
    image_path = os.path.join(current_app.root_path, 'static', image.image_path)
    # Удаление записи из базы данных
    db.session.delete(image)
    db.session.commit()
    # Проверка существования файла
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
        except Exception as e:
            print(f"Ошибка при удалении файла: {e}")
    return redirect(url_for('index'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
