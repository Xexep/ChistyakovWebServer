from flask import Blueprint, jsonify, request
from data import db_session, products

blueprint = Blueprint("products_api", __name__, template_folder="templates")


@blueprint.route('/api/products')
def get_products():
    session = db_session.create_session()
    products_ = session.query(products.Product).all()
    return jsonify(
        {
            'users':
                [item.to_dict(
                    only=('name', 'description', 'cost', 'seller', 'category'))
                    for item in products_]
        }
    )


@blueprint.route('/api/products/<int:products_id>', methods=["GET"])
def get_one_product(products_id):
    session = db_session.create_session()
    product = session.query(products.Product).get(products_id)
    if not product:
        return jsonify({"error": "Not found"})
    return jsonify(
        {
            'user':
                product.to_dict(only=('name', 'description', 'cost', 'seller', 'category'))
        }
    )


@blueprint.route('/api/products', methods=["POST"])
def create_product():
    if not request.json:
        return jsonify({"error": "Empty request"})
    elif not all(key in request.json for key in ['name', 'description', 'cost', 'seller', 'category', "id"]):
        return jsonify({"error": "Bad request"})
    session = db_session.create_session()
    ex_product = session.query(products.Product).get(request.json["id"])
    if ex_product:
        return jsonify({"error": "id already exists"})
    product = products.Product(
        id=request.json["id"],
        name=request.json["name"],
        description=request.json["description"],
        cost=request.json["cost"],
        seller=request.json["seller"],
        category=request.json["category"]
    )
    session.add(product)
    session.commit()
    return jsonify({"success": "OK"})


@blueprint.route("/api/products/<int:products_id>", methods=["DELETE"])
def delete_user(products_id):
    session = db_session.create_session()
    product = session.query(products.Product).get(products_id)
    if not product:
        return jsonify({"error": "Not found"})
    session.delete(product)
    session.commit()
    return jsonify({"success": "OK"})


@blueprint.route('/api/products/<int:products_id>', methods=["PUT"])
def edit_product(products_id):
    if not request.json:
        return jsonify({"error": "Empty request"})
    elif not all(key in request.json for key in ['name', 'description', 'cost', 'seller', 'category']):
        return jsonify({"error": "Bad request"})
    session = db_session.create_session()
    product = session.query(products.Product).get(products_id)
    if not product:
        return jsonify({"error": "Id doesn't exist"})
    product.name = request.json["name"]
    product.description = request.json["description"]
    product.cost = request.json["cost"]
    product.seller = request.json["seller"]
    product.category = request.json["category"]
    session.commit()
    return jsonify({"success": "OK"})
