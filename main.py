# -*- coding: utf8 -*-
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask import Flask, redirect, render_template, request, abort, make_response, jsonify
from data import db_session, products, users, categories, purchases
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired
import requests
import sys
import products_api, users_api

app = Flask(__name__)
app.config["SECRET_KEY"] = "yandexlyceum_project"
db_session.global_init("db/trade.sqlite")
login_manager = LoginManager()
login_manager.init_app(app)
app.register_blueprint(products_api.blueprint)
app.register_blueprint(users_api.blueprint)


class LoginForm(FlaskForm):
    email = StringField("Почта", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class RegisterForm(FlaskForm):
    login = StringField("Логин / Email", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    password_again = PasswordField("Повторите пароль", validators=[DataRequired()])
    name = StringField("Имя", validators=[DataRequired()])
    surname = StringField("Фамилия", validators=[DataRequired()])
    city = StringField("Город", validators=[DataRequired()])
    phone = StringField("Телефон", validators=[DataRequired()])
    submit = SubmitField("Зарегистрироваться")


class AddProduct(FlaskForm):
    name = StringField("Имя товара", validators=[DataRequired()])
    description = StringField("Описание", validators=[DataRequired()])
    cost = IntegerField("Цена", validators=[DataRequired()])
    category = StringField("Категория товара", validators=[DataRequired()])
    submit = SubmitField("Добавить товар")


class BuyProduct(FlaskForm):
    name = StringField("Имя", validators=[DataRequired()])
    surname = StringField("Фамилия", validators=[DataRequired()])
    phone = StringField("Телефон", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    address = StringField("Адрес", validators=[DataRequired()])
    submit = SubmitField("Подтвердить")


def set_geocoder_params(toponym_to_find):
    geocoder_params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "geocode": toponym_to_find,
        "format": "json"}
    return geocoder_params


def set_map_params(toponym_coords):
    map_params = {
        "ll": ','.join(toponym_coords.split()),
        "l": "sat",
        "z": 13}
    return map_params


def find_toponym(toponym_to_find):
    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"
    geocoder_params = set_geocoder_params(toponym_to_find)
    response = requests.get(geocoder_api_server, params=geocoder_params)
    if not response:
        print("Ошибка выполнения запроса")
        print("Http status:", response.status_code, '(', response.reason, ')')
        sys.exit(1)

    json_response = response.json()
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    toponym_coords = toponym["Point"]["pos"]
    print("coords", toponym_coords)
    return toponym_coords


def getImage(toponym_coords, purchase_id):
    map_api_server = "http://static-maps.yandex.ru/1.x/"
    map_params = set_map_params(toponym_coords)
    response = requests.get(map_api_server, params=map_params)
    if not response:
        print("Ошибка выполнения запроса:")
        print("Http status:", response.status_code, '(', response.reason, ')')
        sys.exit(1)
    with open(f"static/img/purchase_{str(purchase_id)}.jpg", "wb") as file:
        file.write(response.content)
        print("done")


@login_manager.user_loader
def load_user(users_id):
    session = db_session.create_session()
    return session.query(users.User).get(users_id)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(users.User).filter(users.User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect('/')
        return render_template("login.html", message="Неправильный логин или пароль", form=form)
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template("register.html", form=form, message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(users.User).filter(users.User.email == form.login.data).first():
            return render_template("register.html", form=form, message="Такой пользователь уже есть")
        user = users.User(
            name=form.name.data,
            surname=form.surname.data,
            city=form.city.data,
            email=form.login.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/')
    return render_template("register.html", form=form)


@app.route("/add_product", methods=["GET", "POST"])
@login_required
def add_product():
    form = AddProduct()
    if form.validate_on_submit():
        session = db_session.create_session()
        category = session.query(categories.Category).filter(categories.Category.name == form.category.data).first()
        if not category:
            return render_template("add_product.html", form=form, message="Несуществующая категория товара")
        product = products.Product(
            name=form.name.data,
            description=form.description.data,
            cost=form.cost.data
        )
        product.category = category.id
        product.seller = current_user.id
        session.add(product)
        session.commit()
        return redirect('/')
    return render_template("add_product.html", form=form)


@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    form = AddProduct()
    if request.method == "GET":
        session = db_session.create_session()
        product = session.query(products.Product).filter(products.Product.id == product_id,
                                                         products.Product.user == current_user).first()
        if product:
            form.name.data = product.name
            form.description.data = product.description
            form.cost.data = product.cost
            form.category.data = product.category_rel.name
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        product = session.query(products.Product).filter(products.Product.id == product_id,
                                                         products.Product.user == current_user).first()
        if product:
            category = session.query(categories.Category).filter(categories.Category.name == form.category.data).first()
            product.name = form.name.data
            product.description = form.description.data
            product.cost = form.cost.data
            product.category = category.id
            session.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template("edit_product.html", form=form)


@app.route("/delete_product/<int:product_id>", methods=["GET", "POST"])
@login_required
def delete_product(product_id):
    session = db_session.create_session()
    product = session.query(products.Product).filter(products.Product.id == product_id,
                                                     products.Product.user == current_user).first()
    if product:
        session.delete(product)
        session.commit()
    else:
        abort(404)
    return redirect('/my_products')


@app.route("/view_product/<int:product_id>")
def view_product(product_id):
    session = db_session.create_session()
    product = session.query(products.Product).get(product_id)
    if not product:
        abort(404)
    return render_template("view_product.html", product=product)


@app.route("/buy_product/<int:product_id>", methods=["GET", "POST"])
def buy_product(product_id):
    form = BuyProduct()
    if form.validate_on_submit():
        session = db_session.create_session()
        purchase = purchases.Purchase(
            name=form.name.data,
            surname=form.surname.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data,
            product=product_id
        )
        session.add(purchase)
        session.commit()
        session = db_session.create_session()
        purchase = session.query(purchases.Purchase).filter(purchases.Purchase.name == form.name.data,
                                                            purchases.Purchase.surname == form.surname.data,
                                                            purchases.Purchase.phone == form.phone.data,
                                                            purchases.Purchase.email == form.email.data,
                                                            purchases.Purchase.address == form.address.data,
                                                            purchases.Purchase.product == product_id).first()
        purchase_id = purchase.id
        address_coords = find_toponym(form.address.data)
        getImage(address_coords, purchase_id)

        return redirect('/')
    return render_template("buy_product.html", form=form)


@app.route('/view_purchases')
@login_required
def view_purchases():
    session = db_session.create_session()
    purchases_ = session.query(purchases.Purchase).all()
    return render_template("view_purchases.html", purchases=purchases_)


@app.route('/my_products')
@login_required
def user_products():
    session = db_session.create_session()
    usr_products = session.query(products.Product).filter(products.Product.user == current_user).all()
    return render_template("user_products.html", products=usr_products)


@app.route('/category_products/<int:category_id>')
def category_products(category_id):
    session = db_session.create_session()
    categories_ = session.query(categories.Category).all()
    ctgr = session.query(categories.Category).filter(categories.Category.id == category_id).first()
    ctgr_products = session.query(products.Product).filter(products.Product.category == ctgr.id)
    return render_template("category_products.html", products=ctgr_products, ctgr=ctgr.name, categories=categories_,
                           current_user=current_user)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)


@app.route('/')
def main_page():
    session = db_session.create_session()
    categories_ = session.query(categories.Category).all()
    products_ = session.query(products.Product).all()
    return render_template("all_products.html", categories=categories_, current_user=current_user, products=products_)


if __name__ == "__main__":
    app.run(port=8080, host="127.0.0.1")
