import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

# --------- CONFIG ---------#
app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


# --------- HOME PAGE  --------- #
@app.route("/")
def index():
    recipes = list(mongo.db.recipes.find())
    return render_template("index.html", recipes=recipes)


# --------- USERS  --------- #
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})
    
        if existing_user:
            flash("Username already exists")
            return redirect(url_for("signup"))
    
        signup = {
            "email": request.form.get("email").lower(),
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(signup)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("You are succesfully signed up.")
        return redirect(url_for("profile", username=session["user"]))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                        session["user"] = request.form.get("username").lower()
                        flash("Welcome, {}".format(
                            request.form.get("username")))
                        return redirect(url_for(
                            "profile", username=session["user"]))
            else:
                # invalid password match
                flash("unfortunately, your username and/or password is incorrect.")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("unfortunately, your username and/or password is incorrect.")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # grab the session user's username from db 
    username = mongo.db.users.find_one(
        {"username": session["user"]}) ["username"]
    
    if session["user"]:
        # Admin has acces to all recipes
        if session["user"] == "admin":
            user_recipes = list(mongo.db.recipes.find())
        else:
            # user sees own recipes
            user_recipes = list(
                mongo.db.recipes.find({"created_by": session["user"]}))
        return render_template(
            "profile.html", username=username, user_recipes=user_recipes)
    
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    #remove user from session cookies 
    flash("You have been succesfully logged out!")
    session.pop("user")
    return redirect(url_for("login"))


# --------- RECIPES  --------- #
@app.route("/recipes/<category>")
def recipes(category):
    if category == "all":
        recipes = list(mongo.db.recipes.find())
    elif category == "smoothie":
        recipes = list(mongo.db.recipes.find({"category_name": "Smoothie"}))
    
    return render_template("recipes.html", recipes=recipes, category=category)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    return render_template("recipes.html", recipes=recipes)


# --------- Recipe description --------- #
@app.route("/recipe/<recipe_id>")
def recipe(recipe_id):
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    return render_template("recipe.html", recipe=recipe)


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        recipe = {
            "recipe_name": request.form.get("recipe_name"),
            "category_name": request.form.get("category_name"),
            "img_url": request.form.get("img_url"),
            "serves": request.form.get("serves"),
            "prep_time": request.form.get("prep_time"),
            "ingredients": request.form.get("ingredients"),
            "instructions": request.form.getlist("instructions"),
            "tips": request.form.get("tips"),
            "created_by": session["user"] 
        }
        mongo.db.recipes.insert_one(recipe)
        flash("Recipe is successfully added")
        return redirect(url_for("profile", username=session['user']))

    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("add_recipe.html", categories=categories)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if request.method == "POST":
        edited = {
            "recipe_name": request.form.get("recipe_name"),
            "category_name": request.form.get("category_name"),
            "img_url": request.form.get("img_url"),
            "serves": request.form.get("serves"),
            "prep_time": request.form.get("prep_time"),
            "ingredients": request.form.get("ingredients"),
            "instructions": request.form.getlist("instructions"),
            "tips": request.form.get("tips"),
            "created_by": session["user"] 
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, edited)
        flash("Recipe is successfully edited")
        return redirect(url_for("profile", username=session['user']))

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template(
        "edit_recipe.html", recipe=recipe, categories=categories)


@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    flash("Recipe is succesfully deleted")
    return redirect(url_for("profile", username=session['user']))


# --------- CATEGORIES --------- #
@app.route("/categories")
def categories():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("categories.html", categories=categories)


@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    if request.method == "POST":
        category = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.insert_one(category)
        flash("New category is succesfully added")
        return redirect(url_for("categories"))

    return render_template("add_category.html")


@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    if request.method == "POST":
        edited = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.update({"_id": ObjectId(category_id)}, edited)
        flash("Category is succesfully edited")
        return redirect(url_for("categories"))

    category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
    return render_template("edit_category.html", category=category)


@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    mongo.db.categories.remove({"_id": ObjectId(category_id)})
    flash("Category is succesfully deleted")
    return redirect(url_for("categories"))


# --------- SUBSCRIBE NEWSLETTER  --------- #
@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if request.method == "POST":
        # check if email already exists in db 
        existing_email = mongo.db.subscribers.find_one(
            {"email": request.form.get("email").lower()})

        if existing_email:
            flash("You are already subscribed to the newsletter")
            return redirect(url_for('index'))

        subscribe = {
            "email": request.form.get("email").lower()
        }
        mongo.db.subscribers.insert_one(subscribe)

    flash("You are succesfully subscribed")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)