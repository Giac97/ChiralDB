from flask import Flask, render_template, flash, request, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError
from wtforms.validators import data_required, equal_to, length
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash

#Flask instance created below
app = Flask(__name__)

#add database
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Aeronautica97@localhost/our_users'

#secret key
app.config['SECRET_KEY'] = "soldiers of poland second to none"

#init db
db = SQLAlchemy(app)

migrate =Migrate(app, db)
#create model
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique = True)
    date_added = db.Column(db.DateTime, default = datetime.utcnow)
    favourite_color = db.Column(db.String(120))
    
    #password stuff
    password_hash = db.Column(db.String(200))
    
    @property
    def password(self):
        raise AttributeError('Password not a readable atribute!')
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    def __repr__(self) -> str:
        return '<Name %r>' % self.first_name

#Create form class
class UserForm(FlaskForm):
    first_name = StringField("First Name", validators=[data_required()])
    last_name = StringField("Last Name", validators=[data_required()])
    email = StringField("Email", validators=[data_required()])
    favourite_color = StringField("Favourite Color")
    password_hash = PasswordField('Password', validators=[data_required(), equal_to('password_hash2', message="Password must match")]) 
    password_hash2 = PasswordField('Confirm Password', validators=[data_required(), equal_to('password_hash2', message="Password must match")])
    submit = SubmitField("Submit")

#route decorator
@app.route("/")
@app.route("/home/")
def index():
    return render_template("index.html")

@app.route("/user/<name>/")
def user(name):
     return render_template("user.html", name = name)

@app.errorhandler(404)
def page_not_found(e):
     return render_template("404.html"), 404

@app.errorhandler(500)
def page_not_found(e):
     return render_template("500.html"), 500 

@app.route("/name/", methods=['GET','POST'])
def name():
     name = None
     form = UserForm()
     #validate crap
     if form.validate_on_submit():
          name = form.name.data
          form.name.data = ''
          flash("Form suss-essfully submitted!!!")
     return render_template("name.html",
                            name = name,
                            form = form)

@app.route('/user/add/', methods = ['GET', 'POST'])
def add_user():
    name = None
    form = UserForm()

    if form.validate_on_submit():
        user = Users.query.filter_by(email = form.email.data).first()
        if user is None:
            hashed_pw = generate_password_hash(form.password_hash.data)
            user = Users(
                first_name = form.first_name.data,
                last_name = form.last_name.data,
                email = form.email.data,
                favourite_color = form.favourite_color.data,
                password_hash = hashed_pw
            )
            db.session.add(user)
            db.session.commit()
        name = form.first_name.data
        form.first_name.data = ''
        form.last_name.data = ''
        form.email.data = ''
        form.favourite_color.data = ''
        form.password_hash.data = ''

        flash('User added successfully')
    our_users = Users.query.order_by(Users.date_added)
    return render_template("add_user.html",
                        form = form,
                        name = name,
                        our_users = our_users)

@app.route('/update/<int:id>', methods = ['GET', 'POST'])
def update_usr(id):
    form = UserForm()
    name_to_update = Users.query.get_or_404(id)
    if request.method == "POST":
        name_to_update.first_name = request.form['first_name']
        name_to_update.last_name = request.form['last_name']
        name_to_update.email = request.form['email']
        name_to_update.favourite_color = request.form['favourite_color']

        try:
            db.session.commit()
            flash("User updated successfully!")
            return render_template("update.html",
                                    form = form,
                                    name_to_update = name_to_update)
        except:
            flash("Error! Try again!")
            return render_template("update.html",
                                    form = form,
                                    name_to_update = name_to_update)
    else:
        return render_template("update.html",
                                    form = form,
                                    name_to_update = name_to_update)

@app.route("/delete/<int:id>")
def delete(id):
    usr_to_del = Users.query.get_or_404(id)
    name = None
    form = UserForm()
    try:
        db.session.delete(usr_to_del)
        db.session.commit()
        flash("User deleted successfully")
        our_users = Users.query.order_by(Users.date_added)

        return redirect("/user/add")

    except:
        flash("Whopso, issue deleting user :(")
        our_users = Users.query.order_by(Users.date_added)
        return render_template("add_user.html",
                        form = form,
                        name = name,
                        our_users = our_users)

        