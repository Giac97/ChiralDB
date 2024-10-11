from flask import Flask, render_template, flash, request, redirect, url_for
from flask_wtf import FlaskForm
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import ARRAY
import pandas as pd
from werkzeug.utils import secure_filename
import os
import numpy as np
import plotly.graph_objs as go
from flask_ckeditor import CKEditor, CKEditorField
from webforms import *
from werkzeug.utils import secure_filename
import uuid as uuid

from chiraldb.user import user

#Flask instance created below
app = Flask(__name__)

app.register_blueprint(user, url_prefix = "")
#add ckeditor
ckeditor = CKEditor(app)


#add database
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Aeronautica97@localhost/our_users'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Aeronautica97@localhost:5432/our_users'


#postgresql://chiraldb_user:LxOXH6O5iVV3k1ixj2RxIEjh06g3R9KV@dpg-cs3u7bogph6c73c879b0-a/chiraldb

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#secret key
app.config['SECRET_KEY'] = "soldiers of poland second to none"

#designate upload folder
UPLOAD_FOLDER = "static/upload/"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


#init db
db = SQLAlchemy(app)

migrate =Migrate(app, db)

#login crap
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get_or_404(user_id)


#login page
@app.route("/login/", methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username = form.username.data).first()
        if user:
            #check hash
            if check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                flash("Yaldi Yeee!")

                return redirect(url_for("dashboard"))
            else:
                flash("Wrong password! Try again")
        else:
            flash("Wrong Username! Try again")

    return render_template("login.html", form = form)


#logout
@app.route("/logout/", methods = ['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash("You logged out mate, see you later Vader")
    return redirect(url_for("index"))

#dashboard page
@app.route("/dashboard/", methods = ['GET', 'POST'])
@login_required
def dashboard():
    my_mols = Molecule.query.filter(Molecule.poster_id == current_user.id)
    my_mols = my_mols.order_by(Molecule.id).all()
    return render_template("dashboard.html", molecules = my_mols)


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
                username = form.username.data,
                first_name = form.first_name.data,
                last_name = form.last_name.data,
                email = form.email.data,
                affiliation = form.affiliation.data,
                password_hash = hashed_pw
            )
            db.session.add(user)
            db.session.commit()
        name = form.first_name.data
        form.username.data = ''
        form.first_name.data = ''
        form.last_name.data = ''
        form.email.data = ''
        form.affiliation.data = ''
        form.password_hash.data = ''

        flash('User added successfully')
    our_users = Users.query.order_by(Users.date_added)
    return render_template("add_user.html",
                        form = form,
                        name = name,
                        our_users = our_users)

@app.route('/update/<int:id>', methods = ['GET', 'POST'])
@login_required
def update_usr(id):
    form = UserForm()
    name_to_update = Users.query.get_or_404(id)
    if request.method == "POST":
        name_to_update.username = request.form['username']

        name_to_update.first_name = request.form['first_name']
        name_to_update.last_name = request.form['last_name']
        name_to_update.email = request.form['email']
        name_to_update.affiliation = request.form['affiliation']
        name_to_update.profile_pic = request.files['profile_pic']
        pic_filename = secure_filename(name_to_update.profile_pic.filename)
        pic_name = str(uuid.uuid1()) + "_" + pic_filename
        saver = request.files['profile_pic']
        

        name_to_update.profile_pic = pic_name
        
        try:
            db.session.commit()
            saver.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_name))
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
                                    name_to_update = name_to_update,
                                    id = id)

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

        return render_template("index.html")

    except:
        flash("Whopso, issue deleting user :(")
        our_users = Users.query.order_by(Users.date_added)
        return render_template("add_user.html",
                        form = form,
                        name = name,
                        our_users = our_users)

#new post 
@app.route("/add-post/", methods = ['GET', 'POST'])
@login_required
def add_post():
    form = PostForm()
    
    if form.validate_on_submit():
        poster = current_user.id
        post = Posts(
            title = form.title.data,
            content = form.content.data,
            poster_id = poster,
            slug = form.slug.data
        )
        form.title.data = ''
        form.content.data = ''
        form.slug.data = ''
        
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



@app.route("/posts/edit/<int:id>", methods = ['GET', 'POST'])
@login_required
def edit_post(id):
    post = Posts.query.get_or_404(id)
    form = PostForm()
    #you viewing or submitting a change?
    if form.validate_on_submit(): #we clicked and want to validate
        post.title = form.title.data
        post.content = form.content.data
        post.slug = form.slug.data
        #update db
        db.session.add(post)
        db.session.commit()
        flash("Post updated!")
        return redirect(url_for('post', id = post.id))
    #if landing there
    form.title.data = post.title
    #form.author.data = post.author
    form.slug.data = post.slug
    form.content.data = post.content
    return render_template("edit_post.html", form = form)

#delete posts
@app.route("/posts/delete/<int:id>")
@login_required
def delete_post(id):
    post_to_delete = Posts.query.get_or_404(id)
    id = current_user.id
    
    if id == post_to_delete.poster.id:
        
    
        try:
            db.session.delete(post_to_delete)
            db.session.commit()
            flash("Blog post was deleted")
            posts = Posts.query.order_by(Posts.date_posted)
            return render_template("posts.html", posts = posts)
            
        except:
            flash("Whopso, problem deleting post")
            posts = Posts.query.order_by(Posts.date_posted)
            return render_template("posts.html", posts = posts)
    else:
        return render_template("not_allowed.html", what = "post")



###########################################
#######Below Molecule Stuff################
###########################################
from elli.kkr.kkr import im2re_reciprocal
@app.route("/molecule/add_molecule", methods=['GET', 'POST'])
@login_required
def add_molecule():
    form = MoleculeForm()
    if form.validate_on_submit():
        poster = current_user.id
        file = form.raw_data.data
        
        # Initialize file path
        raw_data_filename = None
        
        # Handle file upload if present
        if request.files['raw_data']:
            uploaded_file = request.files['raw_data']
            filename = secure_filename(uploaded_file.filename)
            unique_filename = str(uuid.uuid1()) + "_" + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Save the file and store the file path
            uploaded_file.save(file_path)
            raw_data_filename = file_path

        # Initialize the molecule object
        molecule = Molecule(
            name=form.name.data,
            composition=form.composition.data,
            poster_id=poster,
            raw_data=raw_data_filename,  # Store the file path in DB
            wavelength=[],
            absortion=[],
            absortion_re=[],
            ecd_re=[],
            ecd=[],
            publication=form.publication.data
        )

        # Open and process the uploaded file
        if raw_data_filename:
            with open(raw_data_filename, "r") as data:
                # Skip header lines
                for _ in range(17):
                    next(data)
                
                # Read the number of points
                n_points = int(next(data).split(',')[1])
                print(n_points)
                
                # Skip the next 4 lines
                for _ in range(4):
                    next(data)
                
                # Initialize arrays
                wvl = np.zeros(n_points)
                ecd = np.zeros(n_points)
                abs = np.zeros(n_points)

                # Parse data and populate the molecule object
                for i in range(n_points):
                    line = next(data).strip()
                    wv, cd, _, ab, _ = line.split(',')
                    abs[i] = wv
                    ecd[i] = cd
                    wvl[i] = ab
                    molecule.wavelength.append(float(wv))
                    molecule.absortion.append(float(ab))
                    molecule.ecd.append(float(cd))
                
                # Calculate reciprocal values
                re_abs = im2re_reciprocal(abs[1:], wvl[1:])
                re_ecd = im2re_reciprocal(ecd[1:], wvl[1:])
                
                for i in range(2, n_points - 2):
                    molecule.absortion_re.append(float(re_abs[i]))
                    molecule.ecd_re.append(float(re_ecd[i]))

        try:
            # Add the molecule to the database and commit
            db.session.add(molecule)
            db.session.commit()
            
            flash("Molecule submitted successfully!")
            return redirect(url_for('add_molecule'))  # Redirect after successful submission
        except Exception as e:
            db.session.rollback()  # Rollback in case of failure
            flash(f"Error adding molecule to database: {e}")
            return render_template("add_molecule.html", form=form)

    return render_template("add_molecule.html", form=form)

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
    abs_re_data = molecule.absortion_re
    ecd_re_data = molecule.ecd_re

    # Create Plotly graph data for Absorption
    absorption_trace = go.Scatter(
        x=wvl,
        y=abs_data,
        mode='lines',
        name='Absorption',
        line=dict(color='blue')
    )
    
    absorption_trace_re = go.Scatter(
        x=wvl,
        y=abs_re_data,
        mode='lines',
        name='Absorption',
        line=dict(color='red')
    )

    absorption_layout = go.Layout(
        xaxis=dict(title='Wavelength [nm]'),
        yaxis=dict(title='Absorption [Abs]'),
        hovermode='closest',
        autosize=True
    )


    # Create Plotly graph data for ECD
    ecd_trace = go.Scatter(
        x=wvl,
        y=ecd_data,
        mode='lines',
        name='ECD',
        line=dict(color='orange')
    )
    ecd_trace_re = go.Scatter(
        x=wvl,
        y=ecd_re_data,
        mode='lines',
        name='ECD',
        line=dict(color='green')
    )

    ecd_layout = go.Layout(
        xaxis=dict(title='Wavelength [nm]'),
        yaxis=dict(title='ECD [mdeg]'),
        hovermode='closest',
        autosize=True
    )

    ecd_figure = go.Figure(data=[ecd_trace], layout=ecd_layout)
    absorption_figure = go.Figure(data=[absorption_trace], layout=absorption_layout)

    absorption_plot_div = absorption_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    ecd_plot_div = ecd_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})


    return render_template("molecule.html", molecule=molecule, absorption_plot_div=absorption_plot_div, ecd_plot_div=ecd_plot_div)



@app.route("/molecule/delete/<int:id>")
def delete_mol(id):
    mol_to_del = Molecule.query.get_or_404(id)
    id = current_user.id
    
    if id == mol_to_del.poster.id:
    
        try:
            db.session.delete(mol_to_del)
            db.session.commit()
            flash("Molecule deleted successfully")
            molecules = Molecule.query.order_by(Molecule.id)

            return render_template("molecules.html", molecules = molecules)
        except:
            flash("Whopso, issue deleting molecule :(")
            molecules = Molecule.query.order_by(Molecule.id)
            return render_template("molecules.html", molecules = molecules)
    else:
        return render_template("not_allowed.html", what = "molecule")


#pass stuff to navbar
@app.context_processor
def base():
    form = SearchForm()
    return dict(form = form)


# search
@app.route("/search/", methods = ["POST"])
def search():
    form = SearchForm()
    posts = Posts.query
    molecules = Molecule.query
    if form.validate_on_submit():
        post.searched = form.searched.data
        molecule.searched = form.searched.data
        #query db
        posts = posts.filter(Posts.content.ilike('%' + post.searched +'%'))
        posts = posts.order_by(Posts.title).all()
        
        molecules = molecules.filter(Molecule.name.ilike('%' + molecule.searched +'%'))
        molecules = molecules.order_by(Molecule.name).all()
        return render_template("search.html", 
                               form = form,
                               searched = post.searched,
                               posts = posts,
                               molecules = molecules)


@app.route("/group/add/", methods = ['GET', 'POST'])
@login_required
def create_group():
    form = GroupForm()
    
    if form.validate_on_submit():
        group = ResearchGroup(
            name = form.name.data,
            affiliation = form.affiliation.data,
            country = form.country.data
        )
        form.name.data = ''
        form.affiliation.data = ''
        form.country.data = ''
        
        #add to db
        db.session.add(group)
        db.session.commit()
        
        flash("Post submitted successfully!")
        
    return render_template("create_group.html", form = form)


@app.route("/group/view/")
def view_groups():
    groups = ResearchGroup.query.order_by(ResearchGroup.id).all()
    
    return render_template("groups.html", groups = groups)

    

    
class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    #author = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, default = datetime.utcnow)
    slug = db.Column(db.String(255))
    #foreign key to link user, refer to user primary key
    poster_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    

    
#create user model
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable = False, unique = True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique = True)
    date_added = db.Column(db.DateTime, default = datetime.utcnow)
    affiliation = db.Column(db.String(120))
    resgroup = db.Column(db.Integer, db.ForeignKey("researchgroup.id"))
    profile_pic = db.Column(db.String(), nullable=True)
    #password stuff
    password_hash = db.Column(db.String(200))
    #can have many posts
    posts = db.relationship('Posts', backref = "poster")
    molecules = db.relationship('Molecule', backref = "poster")

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
    #author = db.Column(db.String(100))
    poster_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    raw_data = db.Column(db.String(), nullable = True)
    wavelength = db.Column(ARRAY(db.Float)) 
    absortion = db.Column(ARRAY(db.Float)) 
    ecd = db.Column(ARRAY(db.Float)) 
    absortion_re = db.Column(ARRAY(db.Float)) 
    ecd_re = db.Column(ARRAY(db.Float)) 
    
class ResearchGroup(db.Model):
    __tablename__ = 'researchgroup'
    id  = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    affiliation = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    members = db.relationship('Users', backref = "group")
    def __repr__(self) -> str:
        return '<Name %r>' % self.name