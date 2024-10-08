from flask import Flask, render_template, flash, request, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError, FileField
from wtforms.validators import data_required, equal_to, length
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.widgets import TextArea
from sqlalchemy.dialects.postgresql import ARRAY
import pandas as pd
from werkzeug.utils import secure_filename
import os
import numpy as np
import plotly.graph_objs as go

#Flask instance created below
app = Flask(__name__)

#add database
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Aeronautica97@localhost/our_users'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Aeronautica97@localhost:5432/our_users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#secret key
app.config['SECRET_KEY'] = "soldiers of poland second to none"

#init db
db = SQLAlchemy(app)

migrate =Migrate(app, db)

#blogpost model
class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, default = datetime.utcnow)
    slug = db.Column(db.String(255))

#post form
class PostForm(FlaskForm):
    title = StringField("Title", validators=[data_required()])
    content = StringField("Content", validators=[data_required()], widget=TextArea())
    author = StringField("Author", validators=[data_required()])
    slug = StringField("Slug",validators=[data_required()])
    submit = SubmitField("Submit")
    
#create user model
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

class Molecule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    composition = db.Column(db.String(100), nullable=False)   
    publication = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100))

    
    wavelength = db.Column(ARRAY(db.Float)) 
    absortion = db.Column(ARRAY(db.Float)) 
    ecd = db.Column(ARRAY(db.Float)) 
    
    

    
    


#Create form class
class UserForm(FlaskForm):
    first_name = StringField("First Name", validators=[data_required()])
    last_name = StringField("Last Name", validators=[data_required()])
    email = StringField("Email", validators=[data_required()])
    favourite_color = StringField("Favourite Color")
    password_hash = PasswordField('Password', validators=[data_required(), equal_to('password_hash2', message="Password must match")]) 
    password_hash2 = PasswordField('Confirm Password', validators=[data_required(), equal_to('password_hash2', message="Password must match")])
    submit = SubmitField("Submit")

class PasswordForm(FlaskForm):
    email = StringField("What's yer email?", validators=[data_required()])
    password_hash = PasswordField("What's yer password?", validators=[data_required()])
    submit = SubmitField("Submit")

class MoleculeForm(FlaskForm):
    name = StringField("Molecule name", validators=[data_required()])
    composition = StringField("Molecule chemical composition", validators=[data_required()])
    raw_data = FileField("CSV File with raw data")
    publication = StringField("Publications", validators=[data_required()], widget=TextArea())
    author = StringField("Author", validators=[data_required()])
 
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

@app.route("/test_pw/", methods=['GET','POST'])
def test_pw():
     email = None
     password = None
     pw_to_check = None
     passed = None
     
     form = PasswordForm()
     #validate crap
     if form.validate_on_submit():
        email = form.email.data
        password = form.password_hash.data

        form.email.data = ''
        form.password_hash.data = ''
        
        pw_to_check = Users.query.filter_by(email = email).first()
        passed = check_password_hash(pw_to_check.password_hash, password)
     return render_template("testpw.html",
                            email = email,
                            password = password,
                            pw_to_check = pw_to_check,
                            passed = passed,
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

#new post 
@app.route("/add-post/", methods = ['GET', 'POST'])
def add_post():
    form = PostForm()
    
    if form.validate_on_submit():
        post = Posts(
            title = form.title.data,
            content = form.content.data,
            author = form.author.data,
            slug = form.slug.data
        )
        form.title.data = ''
        form.content.data = ''
        form.slug.data = ''
        form.author.data = ''
        
        #add to db
        db.session.add(post)
        db.session.commit()
        
        flash("Post submitted successfully!")
        
    return render_template("add_post.html", form = form)

@app.route("/date/")
def get_current_date():
    return {"Date" : date.today()}

@app.route("/posts/")
def posts():
    posts = Posts.query.order_by(Posts.date_posted )
    return render_template("posts.html", posts = posts)

@app.route("/posts/<int:id>")
def post(id):
    post = Posts.query.get_or_404(id)
    return render_template("post.html", post= post)

@app.route("/posts/edit/<int:id>")
def edit_post(id):
    post = Posts.query.get_or_404(id)
    form = PostForm()


@app.route("/molecule/add_molecule", methods = ['GET', 'POST'])
def add_molecule():
    form = MoleculeForm()
    if form.validate_on_submit():
        file = form.raw_data.data
        
        data = open(file, "r")
        for i in range(22):
            data.readline()

        wvl = np.zeros(356)
        ecd = np.zeros(356)
        abs = np.zeros(356)
        molecule = Molecule(
            name = form.name.data,
            composition = form.composition.data,
            wavelength = [],
            absortion = [],
            ecd = [],
            author = form.author.data,
            publication = form.publication.data
        )
        for i in range(356):
            wv, cd, u1, ab, u2 = data.readline().split(',')

            molecule.wavelength.append(float(wv))
            molecule.absortion.append(float(ab))
            molecule.ecd.append(float(cd))
        
        
        form.name.data = ''
        form.composition.data = ''
        form.raw_data.data = ''

        
        #add to db
        db.session.add(molecule)
        db.session.commit()
        
        flash("Molecule submitted successfully!")
        
    return render_template("add_molecule.html", form = form)


@app.route("/molecule/all_molecules/")
def all_molecules():
    molecules = Molecule.query.order_by(Molecule.id )
    return render_template("molecules.html", molecules = molecules)


@app.route("/molecule/<int:id>/")
def molecule(id):
    molecule = Molecule.query.get_or_404(id)

    # Prepare data for Plotly
    wvl = molecule.wavelength
    abs_data = molecule.absortion
    ecd_data = molecule.ecd

    # Create Plotly graph data for Absorption
    absorption_trace = go.Scatter(
        x=wvl,
        y=abs_data,
        mode='lines',
        name='Absorption',
        line=dict(color='blue')
    )

    absorption_layout = go.Layout(
        title=f'Absorption Spectrum for {molecule.name}',
        xaxis=dict(title='Wavelength [nm]'),
        yaxis=dict(title='Absorption [Abs]'),
        hovermode='closest'
    )

    absorption_figure = go.Figure(data=[absorption_trace], layout=absorption_layout)
    absorption_plot_div = absorption_figure.to_html(full_html=False, include_plotlyjs='cdn')

    # Create Plotly graph data for ECD
    ecd_trace = go.Scatter(
        x=wvl,
        y=ecd_data,
        mode='lines',
        name='ECD',
        line=dict(color='orange')
    )

    ecd_layout = go.Layout(
        title=f'ECD Spectrum for {molecule.name}',
        xaxis=dict(title='Wavelength [nm]'),
        yaxis=dict(title='ECD [mdeg]'),
        hovermode='closest'
    )

    ecd_figure = go.Figure(data=[ecd_trace], layout=ecd_layout)
    ecd_plot_div = ecd_figure.to_html(full_html=False, include_plotlyjs='cdn')

    return render_template("molecule.html", molecule=molecule, absorption_plot_div=absorption_plot_div, ecd_plot_div=ecd_plot_div)
