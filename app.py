from flask import Flask, render_template, flash, request, redirect, session, url_for, Response, make_response, jsonify
from io import StringIO
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from utilities.polarizability import *
from flask_wtf import FlaskForm
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from datetime import timedelta
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import ARRAY, ENUM
import pandas as pd
from werkzeug.utils import secure_filename
import os
import numpy as np
import plotly.graph_objs as go
from flask_ckeditor import CKEditor, CKEditorField
from webforms import *
from werkzeug.utils import secure_filename
import uuid as uuid
import csv
import io
from sqlalchemy import or_
from utilities.publication import get_metadata_from_doi, get_bibtex_from_doi, get_metadata, get_bibtex
from utilities.units import *
import json
from chiraldb.user import user
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from flask import abort
import secrets
import logging

#Flask instance created below
app = Flask(__name__)
load_dotenv()

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SECURITY_PASSWORD_SALT'] = os.getenv('SECURITY_PASSWORD_SALT')
app.config.update(
    SESSION_COOKIE_SECURE=True,  # Ensures cookies are sent only over HTTPS
    SESSION_COOKIE_HTTPONLY=True,  # Prevents JavaScript access to cookies
    #    SESSION_COOKIE_SAMESITE='Lax'  # Adds protection against CSRF
)
app.register_blueprint(user, url_prefix = "")
#add ckeditor
ckeditor = CKEditor(app)

csrf = CSRFProtect(app)
#add database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')



app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#secret key

app.config['PREFERRED_URL_SCHEME'] = 'https'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['WTF_CSRF_CHECK_REFERRER'] = False

#designate upload foldr
UPLOAD_FOLDER = "static/upload/"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=240)


mail = Mail(app)


app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your email provider's SMTP server
app.config['MAIL_PORT'] = 587                  # Use 465 for SSL or 587 for TLS
app.config['MAIL_USE_TLS'] = True              # Use TLS or SSL as required
app.config['MAIL_USE_SSL'] = False             # Set to True if using SSL
app.config['MAIL_USERNAME'] = os.getenv('MY_EMAIL') 
app.config['MAIL_PASSWORD'] = os.getenv('MY_PASSWOERD')           # Your email password
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@example.com'  # Default sender address


serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
#init db
db = SQLAlchemy(app)

migrate =Migrate(app, db)

#login crap
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


logging.basicConfig(filename='error.log', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
def send_confirmation_email(user):
    """
    Sends a confirmation email to the user with a secure token link.
    """
    token = serializer.dumps(user.email, salt='email-confirmation-salt')
    confirm_url = url_for('confirm_email', token=token, _external=True)
    subject = "Please confirm your email"
    msg = Message(
        subject=subject,
        sender="your-email@example.com",
        recipients=[user.email]
    )
    msg.body = f"Hello {user.first_name},\n\nPlease confirm your email by clicking the link below:\n{confirm_url}\n\nThank you!"
    mail.send(msg)


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get_or_404(user_id)


@app.route("/login/", methods=['GET', 'POST'])
def login():
    session.permanent = True
    form = LoginForm()
    
    if form.validate_on_submit():
        # Strip whitespaces from username or email
        username_or_email = form.username.data.strip()

        # Query by username or email in a single query
        user = Users.query.filter(
            or_(Users.username == username_or_email, Users.email == username_or_email)
        ).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            # Log in the user and redirect to the dashboard
            login_user(user)
            flash("You logged in successfully")
            return redirect(url_for("dashboard"))
        else:
            # Handle incorrect credentials
            flash("Invalid username or password! Please try again.")

    return render_template("login.html", form=form)

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Server Error: {error}")
    return render_template("500.html"), 500


@app.errorhandler(400)
def bad_request(error):
    app.logger.error(f"400 Bad Request: {error}")
    return render_template("400.html"), 400
#dashboard page
@app.route("/dashboard/", methods = ['GET', 'POST'])
@login_required
def dashboard():
    my_mols = Molecule.query.filter(Molecule.poster_id == current_user.id)
    my_mols = my_mols.order_by(Molecule.id).all()
    return render_template("dashboard.html", molecules = my_mols, MeasurementType = MeasurementType)

#logout
@app.route("/logout/", methods = ['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash("You logged out")
    return redirect(url_for("index"))

from flask import flash, redirect, url_for
from flask_login import current_user

@app.route("/admin/dashboard/", methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not any(role.name == 'Admin' for role in current_user.roles):
        return redirect(url_for('index'))

    users = Users.query.order_by(Users.id).all()
    roles = Role.query.all()  # Assuming you have a Role model to get all roles

    # Precompute the role names for each user to avoid using list comprehensions in the template
    users_with_roles = []
    for user in users:
        user_role_names = [role.name for role in user.roles]
        users_with_roles.append({
            'user': user,
            'role_names': user_role_names
        })

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('role')
        user = Users.query.get(user_id)
        role = Role.query.filter_by(name=new_role).first()
        if user and role:
            user.roles = [role]  # Update roles for the user
            db.session.commit()

    return render_template("admin_dash.html", users_with_roles=users_with_roles, roles=roles)


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


@app.route('/user/add/', methods=['GET', 'POST'])
def add_user():
    form = UserForm()
    name = None

    if form.validate_on_submit():
        # Check if email already exists
        existing_user = Users.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('This email is already registered. Please log in or use a different email.')
            return render_template("add_user.html", form=form, name=name)

        # Create new user
        hashed_pw = generate_password_hash(form.password_hash.data)
        user = Users(
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            affiliation=form.affiliation.data,
            password_hash=hashed_pw,
            is_confirmed=False,  # Unconfirmed by default
            confirmed_on=None    # No confirmation timestamp yet
        )
        db.session.add(user)
        db.session.commit()

        # Send confirmation email
        send_confirmation_email(user)
        flash('A confirmation email has been sent. Please check your inbox to complete registration.')

        # Reset form fields
        for field in form:
            field.data = ''

    our_users = Users.query.order_by(Users.date_added)
    return render_template(
        "add_user.html",
        form=form,
        name=name,
        our_users=our_users
    )







@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        # Decode the token to get the email
        email = serializer.loads(token, salt='email-confirmation-salt', max_age=3600)
    except SignatureExpired:
        flash('The confirmation link has expired. Please request a new one.')
        return redirect(url_for('add_user'))
    except BadSignature:
        flash('The confirmation link is invalid.')
        return redirect(url_for('add_user'))

    # Find the user by email
    user = Users.query.filter_by(email=email).first()
    if not user:
        flash('No account found for this email.')
        return redirect(url_for('add_user'))

    if user.is_confirmed:
        flash('Your account is already verified. Please log in.')
    else:
        user.is_confirmed = True
        user.confirmed_on = datetime.utcnow()  # Set confirmation timestamp
        db.session.commit()
        flash('Your email has been confirmed. You can now log in.')

    return redirect(url_for('login'))






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

        return render_template("admin_dash.html", users_with_roles=users_with_roles, roles=roles)

    except:
        flash("Whopso, issue deleting user :(")
        our_users = Users.query.order_by(Users.date_added)
        return render_template("add_user.html",
                        form = form,
                        name = name,
                        our_users = our_users)

#new post 
@app.route("/add-post/", methods=['GET', 'POST'])
@login_required
def add_post():
    form = PostForm()

    # Get molecule_id from URL if provided
    molecule_id = request.args.get("molecule_id", type=int)

    # Filter user's molecules
    form.molecule_id.choices = [(m.id, m.name) for m in Molecule.query.filter_by(poster_id=current_user.id).all()]
    
    # Preselect molecule if molecule_id is provided and valid
    if molecule_id and any(m_id == molecule_id for m_id, _ in form.molecule_id.choices):
        form.molecule_id.data = molecule_id

    if form.validate_on_submit():
        post = Posts(
            title=form.title.data,
            content=form.content.data,
            poster_id=current_user.id,
            slug=form.slug.data,
            molecule_id=form.molecule_id.data
        )
        
        db.session.add(post)
        db.session.commit()
        
        flash("Post submitted successfully!", "success")
        return redirect(url_for("dashboard"))  # Change to appropriate redirect

    return render_template("add_post.html", form=form)

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
from scipy.signal import hilbert
import pubchempy as pcp
@app.route("/molecule/add_molecule", methods=['GET', 'POST'])
@login_required
def add_molecule():
    print("Received a request to add a molecule.")  # Debug line
    form = MoleculeForm()

    if form.validate_on_submit():
        print("Form validated successfully!")  # Debug line
        poster = current_user.id
        file = form.raw_data.data
        twod_file = form.twod_struc.data
        threed_file = form.threed_struc.data
        # Handle PubChem ID if provided
        cid = form.pubchem_id.data
        try:
            if cid:
                c = pcp.Compound.from_cid(cid)
                molecular_weight = c.molecular_weight
                iupac_name = c.iupac_name
            else:
                molecular_weight = form.molecular_weight.data
                iupac_name = None
        except Exception as e:
            print(f"Error fetching from PubChem: {e}")  # Debug line
            molecular_weight = form.molecular_weight.data  # Fallback to user input
            iupac_name = None
        # Handle file upload if present
        raw_data_filename = None
        if file:
            filename = secure_filename(file.filename)
            unique_filename = str(uuid.uuid1()) + "_" + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)  # Save the uploaded file
            raw_data_filename = file_path
            data = open(raw_data_filename, "r")
            for _ in range(17):
                    next(data)
                
                # Read the number of points
            n_points = int(next(data).split(',')[1])
            print(n_points)
                
                # Skip the next 4 lines
            for _ in range(4):
                next(data)
            wvl = np.zeros(n_points)
            ecd = np.zeros(n_points)
            abso = np.zeros(n_points)

        twod_filename = None
        if twod_file:
            filename = secure_filename(twod_file.filename)
            unique_filename = str(uuid.uuid1()) + "_" + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            twod_file.save(file_path)  # Save the uploaded file
            twod_filename = file_path
        threed_filename = None
        if threed_file:
            filename = secure_filename(threed_file.filename)
            unique_filename = str(uuid.uuid1()) + "_" + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            threed_file.save(file_path)  # Save the uploaded file
            threed_filename = file_path 

        #get visibility data
        visible = form.public.data 
        # Initialize the molecule object
        molecule = Molecule(
            name=form.name.data,
            composition=form.composition.data,
            pubchem_id=cid if cid else None,  # Store PubChem ID
            two_d_struc=twod_filename,
            three_d_struc = threed_filename,
            molecular_weight=molecular_weight,
            iupac_name=iupac_name,
            concentration = form.concentration.data,
            poster_id=poster, 
            tool = form.tool.data,
            raw_data=raw_data_filename,  # Store file path in DB
            publication=form.publication.data,
            wavelength = [],
            absortion = [],
            absortion_re = [],
            ecd_re = [],
            ecd = [],
            chir_pol_im = [],
            chir_pol_re = [],
            achir_pol_im = [],
            achir_pol_re = [],
            public=visible
        )
        C = float(form.concentration.data)
        L = 1.0
        M = float(molecular_weight)
        for i in range(n_points):
            line = next(data).strip()
            wv, cd, _, ab, _ = line.split(',')
            """

            if molecule.tool ==MeasurementType.experimental.value:
                if form.abs_units == "ext":
                    ab = float(ab)
                else:
                    ab = float(ab) * M / (C * L)
                if form.ecd_units == "ext":
                    cd = float(cd)
                else:
                    cd = float(cd) * M / (C * L * 32980)
            """
            if (form.abs_units == "abs"):
                ab = abs_to_ext(float(ab), M, C, L)
            if (form.ecd_units == "mdeg"):
                cd = mdeg_to_ext(float(cd), M, C, L)
            if (form.ecd_units == "abs"):
                cd = abs_to_ext(float(cd), M, C, L)
            molecule.wavelength.append(float(wv))
            molecule.absortion.append(float(ab))
            molecule.ecd.append(float(cd))
            abso[i] = ab
            ecd[i] = cd
            wvl[i] = wv
        #re_abs = im2re_reciprocal(abs[1:], wvl[1:])
        #re_ecd = im2re_reciprocal(ecd[1:], wvl[1:])

        # for i in range(n_points):
        #     molecule.absortion_re.append(float(re_abs[i]))
        #     molecule.ecd_re.append(float(re_ecd[i]))
        
        ecd_mdeg = ext_to_mdeg(ecd, M, C, L)
        abs_abs = ext_to_abs(abso, M, C, L) 
        polar = polarisability(wvl, abs_abs, ecd_mdeg , C * 1000 / M, L, 1.0)
        
        im_alphac = np.imag(polar[1])
        re_alphac = np.real(polar[1])

        im_alphaa = np.imag(polar[0])
        re_alphaa = np.real(polar[0])
        for i in range(n_points):
            molecule.chir_pol_im.append(float(im_alphac[i]))
            molecule.chir_pol_re.append(float(re_alphac[i]))
            molecule.achir_pol_im.append(float(im_alphaa[i]))
            molecule.achir_pol_re.append(float(re_alphaa[i]))

        try:
            print(f"Inserting molecule with: {molecule.__dict__}")  # Debug line
            db.session.add(molecule)
            db.session.commit()
            flash("Molecule submitted successfully!")
            return redirect(url_for('add_molecule'))  # Redirect after submission
        except Exception as e:
            db.session.rollback()  # Rollback in case of failure
            print(f"Error adding molecule to database: {e}")  # Debug line
            flash("Error adding molecule to the database.")
    else:
        print("Form validation failed. Errors:", form.errors)  # Debug line

    return render_template("add_molecule.html", form=form)



@app.route("/molecule/<int:id>/", methods=['GET', 'POST'])
def molecule(id):
    
    molecule = Molecule.query.get_or_404(id)
    if molecule.public == False and not current_user.is_authenticated:
        return render_template("404.html")
    if molecule.public == True or (current_user.id == molecule.poster.id or any(role.name == 'Admin' for role in current_user.roles)):

        # Initialize the CSV export form
        form = CSVExportForm()
        L = 1.0
        # Prepare data for Plotly
        wvl = molecule.wavelength
        abs_data = molecule.absortion
        ecd_data = molecule.ecd
        #abs_re_data = molecule.absortion_re
        #ecd_re_data = molecule.ecd_re
        
        ecd_abs = np.array(ecd_data)
        abs_arr = np.array(abs_data)
        #abs_re_arr = np.array(abs_re_data)
        g_fac = np.zeros(len(ecd_abs))
        min_abs = np.max(abs_arr)/1000.0
        for i in range(len(ecd_abs)):
            if abs_arr[i] > min_abs:
                g_fac[i] = ecd_abs[i] / abs_arr[i]
            else:
                g_fac[i] = 0
        C = molecule.concentration
        M = molecule.molecular_weight

        #ecd_mdeg = ext_to_mdeg(ecd_abs, M, C, L)
        
        #polar = polarisability(wvl, ext_to_abs(abs_arr, M=M, C=C, L=L), ecd_mdeg , C * 1000 / M, L, 1.0)
        

        #im_alphac = np.imag(polar[1])
        #re_alphac = np.real(polar[1])

        im_alphac = molecule.chir_pol_im
        re_alphac = molecule.chir_pol_re
        #im_alphaa = np.imag(polar[0])
        #re_alphaa = np.real(polar[0])
        im_alphaa = molecule.achir_pol_im
        re_alphaa = molecule.achir_pol_re

        id_max_g = np.argmax(np.abs(g_fac))
        max_g = g_fac[id_max_g]
        wvl_maxg = wvl[id_max_g]
        

        pad_width = len(ecd_abs) // 2
        padded_ecd_abs = np.pad(ecd_abs, pad_width, mode='reflect')
        padded_abs_arr = np.pad(abs_arr, pad_width, mode='reflect')
        ecd_complex = 1j * hilbert(padded_ecd_abs)[pad_width:-pad_width] 
        abs_complex = 1j * hilbert(padded_abs_arr)[pad_width:-pad_width] 


        ecd_real = ecd_complex.real
        abs_real = abs_complex.real
        # Create Plotly graph data for Absorption, ECD, and g-factor (as you already have)
        absorption_trace = go.Scatter(x=wvl, y=abs_data, mode='lines', name='Absorption', line=dict(color='blue'))
        absorption_trace_re = go.Scatter(x = wvl, y = abs_real, mode = 'lines', name = 'Re(Absorption)', line = dict(color='green'))
        #absorption_trace_re = go.Scatter(x=wvl, y=abs_re_arr, mode='lines', name='Absorption', line=dict(color='red'))
        absorption_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='Absorption [ext]'), hovermode='closest', autosize=True)

        ecd_trace = go.Scatter(x=wvl, y=ecd_data, mode='lines', name='ECD', line=dict(color='orange'))
        ecd_trace_re = go.Scatter(x = wvl, y = ecd_real, mode = 'lines', name = 'Re(ECD)', line = dict(color='green'))
        
        im_alpha_c_trace = go.Scatter(x = wvl, y = im_alphac, mode = 'lines', name = 'Im(Alpha_c)', line = dict(color='magenta'))
        re_alpha_c_trace = go.Scatter(x = wvl, y = re_alphac, mode = 'lines', name = 'Re(Alpha_c)', line = dict(color='green'))

        im_alpha_a_trace = go.Scatter(x = wvl, y = im_alphaa, mode = 'lines', name = 'Im(Alpha_a)', line = dict(color='magenta'))
        re_alpha_a_trace = go.Scatter(x = wvl, y = re_alphaa, mode = 'lines', name = 'Re(Alpha_a)', line = dict(color='green'))

        alpha_c_layout = go.Layout(xaxis = dict(title='Wavelength [nm]'), yaxis=dict(title='Chiral Polarizability [nm^3]'), hovermode='closest', autosize=True)
        alpha_a_layout = go.Layout(xaxis = dict(title='Wavelength [nm]'), yaxis=dict(title='Achiral Polarizability [nm^3]'), hovermode='closest', autosize=True)

        ecd_trace_mirr = go.Scatter(x=wvl, y=-1 * np.array(ecd_data), mode='lines', name='ECD [reflected]', line=dict(color='yellow'))
        ecd_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='ECD [ext]'), hovermode='closest', autosize=True)

        g_fac_trace = go.Scatter(x=wvl, y=g_fac, mode='lines', name='g factor', line=dict(color='orange'))
        g_fac_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='g factor'), hovermode='closest', autosize=True)

        ecd_figure = go.Figure(data=[ecd_trace, ecd_trace_mirr, ecd_trace_re], layout=ecd_layout)
        absorption_figure = go.Figure(data=[absorption_trace,absorption_trace_re], layout=absorption_layout)
        g_fac_figure = go.Figure(data=[g_fac_trace], layout=g_fac_layout)
        alpha_c_figure = go.Figure(data=[im_alpha_c_trace, re_alpha_c_trace], layout=alpha_c_layout)
        alpha_a_figure = go.Figure(data=[im_alpha_a_trace, re_alpha_a_trace], layout=alpha_a_layout)
    
        absorption_plot_div = absorption_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
        ecd_plot_div = ecd_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
        gfac_plot_div = g_fac_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
        alpha_c_plot_div = alpha_c_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
        alpha_a_plot_div = alpha_a_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
        # Replace the existing publication metadata section with this code:
        if hasattr(molecule, 'publication') and molecule.publication:
            publications = molecule.publication.split(",")
            publications = [pub.strip() for pub in publications if pub.strip()]
            
            # Get metadata and BibTeX for each publication using the universal function
            pub_metadata = []
            bibtex_entries = []
            
            for pub_url in publications:
                # Get metadata using the universal function that handles both DOI and arXiv
                metadata = get_metadata(pub_url)
                pub_metadata.append(metadata)
                
                # Get BibTeX citation
                bibtex = get_bibtex(pub_url)
                if bibtex:
                    bibtex_entries.append(bibtex)
            
            # Create context dictionary with all information
            context = {
                "publications": publications,
                "pub_metadata": pub_metadata,
                "bibtex_entries": bibtex_entries,
                "pub_count": len(publications)
            }
        else:
            context = {
                "publications": [],
                "pub_metadata": [],
                "bibtex_entries": [],
                "pub_count": 0
            }
        # Handle CSV export form submission
        if form.validate_on_submit():
            # Create an in-memory CSV
            csv_data = StringIO()
            writer = csv.writer(csv_data)
            
            # Write header
            header = ['Wavelength (nm)']
            if form.absorption.data:
                header.append('Absorption')
            if form.ecd.data:
                header.append('ECD')
            if form.gfactor.data:
                header.append('g Factor')
            if form.abs_re.data:
                header.append('Absorption (Re)')
            if form.alpha_a.data:
                header.append('Achiral Pol (Im)')
            if form.alpha_c.data:
                header.append('Chiral Pol (Im)')

            writer.writerow(header)
            s = 0
            # Write data rows based on user selection
            for i in range(len(wvl)):
                row = [wvl[i]]
                if form.absorption.data:
                    row.append(abs_data[i])
                if form.ecd.data:
                    row.append(ecd_data[i])
                if form.gfactor.data:
                    row.append(g_fac[i])
                if form.alpha_a.data:
                    row.append(im_alphaa[i])
                if form.alpha_c.data:
                    row.append(im_alphac[i])

                writer.writerow(row)

            # Create a downloadable CSV response
            response = make_response(csv_data.getvalue())
            response.headers['Content-Disposition'] = 'attachment; filename=molecule_data.csv'
            response.headers['Content-type'] = 'text/csv'
            return response

        return render_template(
        "molecule.html",
        molecule=molecule,
        absorption_plot_div=absorption_plot_div,
        ecd_plot_div=ecd_plot_div,
        gfac_plot_div=gfac_plot_div,
        alpha_c_plot_div=alpha_c_plot_div,
        alpha_a_plot_div=alpha_a_plot_div,
        max_g=max_g,
        wvl_maxg=wvl_maxg,
        form=form,
        MeasurementType=MeasurementType,
        **context  # Unpack context dictionary
    )
    else:
        return render_template(
            "404.html"
        )



@app.route("/molecule/<int:id>/download")
def download_csv(id):
    molecule = Molecule.query.get_or_404(id)

    # Prepare data for CSV
    wvl = molecule.wavelength
    abs_data = molecule.absortion
    ecd_data = molecule.ecd
    abs_re_data = molecule.absortion_re
    ecd_re_data = molecule.ecd_re
    
    # Create a file-like object in memory
    csv_file = io.StringIO()
    writer = csv.writer(csv_file)

    # Write headers
    writer.writerow(['Wavelength [nm]', 'Absorption', 'ECD', 'Absorption (re)', 'ECD (re)'])
    
    # Write data
    for i in range(len(wvl)):
        writer.writerow([wvl[i], abs_data[i], ecd_data[i]])

    # Move to the beginning of the StringIO object
    csv_file.seek(0)

    # Return the CSV file as a downloadable response
    return Response(
        csv_file,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=molecule_{id}.csv"}
    )

@app.route("/molecule/all_molecules/")
def all_molecules():
    #molecules = Molecule.query.order_by(Molecule.tool).all()  # Use .all() to retrieve results
    #return render_template("molecules.html", molecules=molecules, MeasurementType = MeasurementType)
    page = request.args.get('page', 1, type=int)  # Get page number from query params
    per_page = request.args.get('per_page', 6, type=int)  # Get per-page count, default to 6

    # If "all" is selected, return all molecules without pagination
    if per_page == 0:
        molecules_list = Molecule.query.all()
        pagination = None
    else:
        pagination = Molecule.query.paginate(page=page, per_page=per_page, error_out=False)
        molecules_list = pagination.items

    return render_template(
        'molecules.html',
        molecules=molecules_list,
        pagination=pagination,
        per_page=per_page,
        MeasurementType = MeasurementType
    )
    
    return render_template('molecules.html', molecules=molecules_pagination.items, pagination=molecules_pagination, MeasurementType = MeasurementType)


@app.route("/molecule/delete/<int:id>")
def delete_mol(id):
    mol_to_del = Molecule.query.get_or_404(id)
    try:
        id = current_user.id
    except AttributeError:
        return render_template("not_allowed.html", what = "not_logged")

    
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
            return render_template("molecules.html", molecules = molecules, MeasurementType=MeasurementType)
    else:
        return render_template("not_allowed.html", what = "molecule")

@app.route('/molecule/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update_mol(id):
    mol_to_update = Molecule.query.get_or_404(id)
    
    if current_user.id != mol_to_update.poster.id and not any(role.name == 'Admin' for role in current_user.roles):
        print("Access denied!")  # Debugging
        return render_template("not_allowed.html", what="molecule")

    form = MoleculeForm(obj=mol_to_update)  # Pre-populate form



    if request.method == "POST":
        mol_to_update.name = form.name.data
        mol_to_update.composition = form.composition.data
        mol_to_update.publication = form.publication.data
        mol_to_update.concentration = form.concentration.data
        mol_to_update.public = form.public.data

        twod_file = request.files.get('twod_struc')
        threed_file = request.files.get('threed_struc')

        if twod_file and twod_file.filename:
            filename = secure_filename(twod_file.filename)
            unique_filename = str(uuid.uuid1()) + "_" + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            twod_file.save(file_path)
            mol_to_update.two_d_struc = file_path

        if threed_file and threed_file.filename:
            filename = secure_filename(threed_file.filename)
            unique_filename = str(uuid.uuid1()) + "_" + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            threed_file.save(file_path)
            mol_to_update.three_d_struc = file_path

        try:
            db.session.commit()
            flash("Molecule updated successfully", "success")
            print("Database commit successful!")  # Debugging
            return redirect(url_for('molecule', id=id))
        except:
            flash("Error! Try again!", "danger")
            print("Database commit failed!")  # Debugging

    else:
        print("Form validation failed:", form.errors)  # Debugging

    return render_template("update_mol.html", form=form, mol_to_update=mol_to_update)



#pass stuff to navbar
@app.context_processor
def base():
    form = SearchForm()
    return dict(form = form)



# search

@app.route("/search/", methods=["GET", "POST"])
def search():
    form = SearchForm()
    posts = Posts.query
    molecules = Molecule.query
    searched = request.args.get("searched", "")

    if form.validate_on_submit():
        searched = form.searched.data  # Get search term from form

    if searched:
        posts = posts.filter(Posts.content.ilike(f"%{searched}%")).order_by(Posts.title).all()
        molecules = molecules.filter(
            or_(
                Molecule.name.ilike(f"%{searched}%"),
                Molecule.composition.ilike(f"%{searched}%")
            )
        )
    else:
        posts = []
        molecules = Molecule.query  # If no search term, return all molecules

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 6, type=int)

    if per_page == 0:
        molecules_list = molecules.all()
        pagination = None
    else:
        pagination = molecules.paginate(page=page, per_page=per_page, error_out=False)
        molecules_list = pagination.items

    return render_template(
        "search.html",
        form=form,
        searched=searched,
        posts=posts,
        molecules=molecules_list,
        pagination=pagination,
        per_page=per_page,
        MeasurementType=MeasurementType
    )

@app.route("/compare/<int:id1>-<int:id2>")
def compare_mols(id1, id2):
    mol_1 = Molecule.query.get_or_404(id1)
    mol_2 = Molecule.query.get_or_404(id2)
    wvl = [mol_1.wavelength, mol_2.wavelength]
    abs_data = [mol_1.absortion, mol_2.absortion]
    ecd_data = [mol_1.ecd, mol_2.ecd]
    absorption1_trace = go.Scatter(x=wvl[0], y=abs_data[0], mode='lines', name='Absorption {}'.format(mol_1.name), line=dict(color='blue'))
    absorption2_trace = go.Scatter(x=wvl[1], y=abs_data[1], mode='lines', name='Absorption {}'.format(mol_2.name), line=dict(color='red'))
    chirpol_data = [mol_1.chir_pol_im, mol_2.chir_pol_im]
    achirpol_data = [mol_1.achir_pol_im, mol_2.achir_pol_im]

    ecd1_trace = go.Scatter(x=wvl[0], y=ecd_data[0], mode='lines', name='ECD {}'.format(mol_1.name), line=dict(color='blue'))
    ecd2_trace = go.Scatter(x=wvl[1], y=ecd_data[1], mode='lines', name='ECD {}'.format(mol_2.name), line=dict(color='red'))
    
    absorption_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='Absorption [ext]'), hovermode='closest', autosize=True)
    absorption_figure = go.Figure(data=[absorption1_trace,absorption2_trace ], layout=absorption_layout)

    ecd_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='ECD [ext]'), hovermode='closest', autosize=True)
    ecd_figure = go.Figure(data=[ecd1_trace,ecd2_trace ], layout=ecd_layout)
    
    absorption_plot_div = absorption_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    ecd_plot_div = ecd_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    
    chir_pol1_trace = go.Scatter(x=wvl[0], y=chirpol_data[0], mode='lines', name='Chiral Polarizability {}'.format(mol_1.name), line=dict(color='blue'))
    chir_pol2_trace = go.Scatter(x=wvl[1], y=chirpol_data[1], mode='lines', name='Chiral Polarizability {}'.format(mol_2.name), line=dict(color='red'))
    chir_pol_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='Chiral Polarizability [nm^3]'), hovermode='closest', autosize=True)
    chir_pol_figure = go.Figure(data=[chir_pol1_trace,chir_pol2_trace ], layout=chir_pol_layout)
    chir_pol_div = chir_pol_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    
    achir_pol1_trace = go.Scatter(x=wvl[0], y=achirpol_data[0], mode='lines', name='Achiral Polarizability {}'.format(mol_1.name), line=dict(color='blue'))
    achir_pol2_trace = go.Scatter(x=wvl[1], y=achirpol_data[1], mode='lines', name='Achiral Polarizability {}'.format(mol_2.name), line=dict(color='red'))
    achir_pol_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='Achiral Polarizability [nm^3]'), hovermode='closest', autosize=True)
    achir_pol_figure = go.Figure(data=[achir_pol1_trace,achir_pol2_trace ], layout=achir_pol_layout)
    achir_pol_div = achir_pol_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    
    ecd_arr1 = np.array(ecd_data[0])
    ecd_arr2 = np.array(ecd_data[1])

    abs_arr1 = np.array(abs_data[0])
    abs_arr2 = np.array(abs_data[1])

    g_fac1 = np.zeros(len(ecd_arr1))
    g_fac2 = np.zeros(len(ecd_arr2))

    min_abs1 = np.max(abs_arr1)/1000.0
    min_abs2 = np.max(abs_arr2)/1000.0

    for i in range(len(ecd_arr1)):
        if abs_arr1[i] > min_abs1:
            g_fac1[i] = ecd_arr1[i] / abs_arr1[i]
        else:
            g_fac1[i] = 0   
             
    for i in range(len(ecd_arr2)):
        if abs_arr2[i] > min_abs2:
            g_fac2[i] = ecd_arr2[i] / abs_arr2[i]
        else:
            g_fac2[i] = 0
              
    #max g fac for mol 1
    wvl1 = wvl[0]
    wvl2 = wvl[1]
    id_max_g1 = np.argmax(np.abs(g_fac1))
    max_g1 = g_fac1[id_max_g1]
    wvl_maxg1 = wvl1[id_max_g1]
    
    #max g fac for mol 2
    id_max_g2 = np.argmax(np.abs(g_fac2))
    max_g2 = g_fac2[id_max_g2]
    wvl_maxg2 = wvl2[id_max_g2]
    
    g_fac_trace1 = go.Scatter(x=wvl1, y=g_fac1, mode='lines', name='g factor {}'.format(mol_1.name), line=dict(color='orange'))
    g_fac_trace2 = go.Scatter(x=wvl2, y=g_fac2, mode='lines', name='g factor {}'.format(mol_2.name), line=dict(color='green'))

    g_fac_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='g factor'), hovermode='closest', autosize=True)
    g_fac_figure = go.Figure(data=[g_fac_trace1, g_fac_trace2], layout=g_fac_layout)
    gfac_plot_div = g_fac_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})

    
    return render_template(
        "compare.html",
        molecule1=mol_1,
        molecule2=mol_2,
        absorption_plot_div=absorption_plot_div,
        ecd_plot_div = ecd_plot_div,
        gfac_plot_div=gfac_plot_div,
        chir_pol_div = chir_pol_div,
        achir_pol_div = achir_pol_div,
        max_g1=max_g1,
        wvl_maxg1=wvl_maxg1,
        max_g2=max_g2,
        wvl_maxg2=wvl_maxg2,
        MeasurementType=MeasurementType,

    )


@app.route("/compare/<int:id1>-<int:id2>/data")
def compare_data_json(id1, id2):
    mol_1 = Molecule.query.get_or_404(id1)
    mol_2 = Molecule.query.get_or_404(id2)

    # Prepare JSON data
    data = {
        "molecule1": {
            "name": mol_1.name,
            "wavelength": mol_1.wavelength,
            "ecd": mol_1.ecd
        },
        "molecule2": {
            "name": mol_2.name,
            "wavelength": mol_2.wavelength,
            "ecd": mol_2.ecd
        }
    }
    return jsonify(data)
  
@app.route("/select-molecules", methods=["GET", "POST"])
def select_molecules():
    molecules = Molecule.query.all()  # Fetch all molecules from the database
    if request.method == "POST":
        id1 = request.form.get("molecule1")
        id2 = request.form.get("molecule2")
        if id1 and id2 and id1 != id2:  # Ensure both IDs are selected and different
            return redirect(url_for("compare_mols", id1=id1, id2=id2))
        else:
            flash("Please select two different molecules.", "danger")
    return render_template("select_molecules.html", molecules=molecules)

@app.route("/select-multiple-molecules", methods=["GET", "POST"])
def select_multiple_molecules():
    molecules = Molecule.query.all()  # Fetch all molecules from the database
    
    if request.method == "POST":
        # Get list of selected molecule IDs
        selected_molecule_ids = request.form.getlist("selected_molecules")
        
        # Validate selection
        if len(selected_molecule_ids) < 2:
            flash("Please select at least two molecules.", "danger")
        elif len(set(selected_molecule_ids)) < len(selected_molecule_ids):
            flash("Please select unique molecules.", "danger")
        else:
            # Redirect to comparison route with multiple molecule IDs
            return redirect(url_for("compare_multiple_mols", molecule_ids=selected_molecule_ids))
    
    return render_template("select_multiple_molecules.html", molecules=molecules, MeasurementType=MeasurementType,
)


def get_method_color(method):

    color_map = {
        'Experimental': 'blue',
        'Computational': 'red'
    }
    
    # Use lowercase for case-insensitive matching
    method_lower = method.lower()
    
    # Return mapped color or default to black if method not found
    return color_map.get(method_lower, 'black')

@app.route("/compare-multiple")
def compare_multiple_mols():
    # Get molecule IDs from query parameters
    molecule_ids = request.args.getlist('molecule_ids')
    
    # Validate molecule IDs
    if not molecule_ids or len(molecule_ids) < 2:
        flash("Please select at least two molecules to compare.", "danger")
        return redirect(url_for('select_multiple_molecules'))
    
    # Fetch molecules from database
    molecules = []
    for mol_id in molecule_ids:
        mol = Molecule.query.get_or_404(int(mol_id))
        molecules.append(mol)
    
    # Create Plotly traces
    absorption_traces = []
    ecd_traces = []
    chir_pol_traces = []
    achir_pol_traces = []
    g_fac_traces = []
    
 
    max_g_factors = []
    wvl_max_g_factors = []
    
    for i, mol in enumerate(molecules):
        #color = colors[i % len(colors)]
        if mol.tool == MeasurementType.experimental:
            method = "Experimental"
        else:
            method = "Computational"
        # Absorption trace
        color = "green" if method == "Experimental" else "blue"
        absorption_traces.append(
            go.Scatter(
                x=mol.wavelength, 
                y=mol.absortion, 
                mode='lines', 
                name=f'<span style="color:{color};">{mol.name} ({method})</span>'
            )
        )
        
        # ECD trace
        ecd_traces.append(
            go.Scatter(
                x=mol.wavelength, 
                y=mol.ecd, 
                mode='lines', 
                name=f'<span style="color:{color};">{mol.name} ({method})</span>'
            )
        )
        
        # Chiral Polarizability trace
        chir_pol_traces.append(
            go.Scatter(
                x=mol.wavelength, 
                y=mol.chir_pol_im, 
                mode='lines', 
                name=f'<span style="color:{color};">{mol.name} ({method})</span>'
            )
        )

        # Achiral Polarizability trace
        achir_pol_traces.append(
            go.Scatter(
                x=mol.wavelength, 
                y=mol.achir_pol_im, 
                mode='lines', 
                name=f'<span style="color:{color};">{mol.name} ({method})</span>'
            )
        )
        
        # G-factor calculations
        ecd_arr = np.array(mol.ecd)
        abs_arr = np.array(mol.absortion)
        
        min_abs = np.max(abs_arr) / 1000.0
        
        g_fac = np.zeros(len(ecd_arr))
        for j in range(len(ecd_arr)):
            g_fac[j] = ecd_arr[j] / abs_arr[j] if abs_arr[j] > min_abs else 0
        
        # G-factor trace
        g_fac_traces.append(
            go.Scatter(
                x=mol.wavelength, 
                y=g_fac, 
                mode='lines', 
                name=f'<span style="color:{color};">{mol.name} ({method})</span>'
            )
        )
        
        # Find max g-factor
        id_max_g = np.argmax(np.abs(g_fac))
        max_g_factors.append(g_fac[id_max_g])
        wvl_max_g_factors.append(mol.wavelength[id_max_g])
    
    # Create Plotly figures
    absorption_figure = go.Figure(
        data=absorption_traces, 
        layout=go.Layout(
            xaxis=dict(title='Wavelength [nm]'), 
            yaxis=dict(title='Absorption [ext]'), 
            hovermode='closest', 
            autosize=True
        )
    )
    
    ecd_figure = go.Figure(
        data=ecd_traces, 
        layout=go.Layout(
            xaxis=dict(title='Wavelength [nm]'), 
            yaxis=dict(title='ECD [ext]'), 
            hovermode='closest', 
            autosize=True
        )
    )
    
    chir_pol_figure = go.Figure(
        data=chir_pol_traces, 
        layout=go.Layout(
            xaxis=dict(title='Wavelength [nm]'), 
            yaxis=dict(title='Chiral Polarizability [nm^3]'), 
            hovermode='closest', 
            autosize=True
        )
    )
    
    achir_pol_figure = go.Figure(
        data=achir_pol_traces, 
        layout=go.Layout(
            xaxis=dict(title='Wavelength [nm]'), 
            yaxis=dict(title='Achiral Polarizability [nm^3]'), 
            hovermode='closest', 
            autosize=True
        )
    )
    
    g_fac_figure = go.Figure(
        data=g_fac_traces, 
        layout=go.Layout(
            xaxis=dict(title='Wavelength [nm]'), 
            yaxis=dict(title='g factor'), 
            hovermode='closest', 
            autosize=True
        )
    )
    
    # Convert figures to HTML
    absorption_plot_div = absorption_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    ecd_plot_div = ecd_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    chir_pol_div = chir_pol_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    achir_pol_div = achir_pol_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    gfac_plot_div = g_fac_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    
    return render_template(
        "compare_multiple.html",
        molecules=molecules,
        absorption_plot_div=absorption_plot_div,
        ecd_plot_div=ecd_plot_div,
        gfac_plot_div=gfac_plot_div,
        chir_pol_div=chir_pol_div,
        achir_pol_div=achir_pol_div,
        max_g_factors=max_g_factors,
        wvl_max_g_factors=wvl_max_g_factors,
        MeasurementType=MeasurementType,
    )

@app.route("/compare-multiple/data")
def compare_multiple_data_json():
    # Get molecule IDs from query parameters
    molecule_ids = request.args.getlist('molecule_ids')
    
    # Validate molecule IDs
    if not molecule_ids or len(molecule_ids) < 2:
        return jsonify({"error": "Please select at least two molecules"}), 400
    
    # Fetch molecules from database
    molecules_data = []
    for mol_id in molecule_ids:
        mol = Molecule.query.get_or_404(int(mol_id))
        molecules_data.append({
            "name": mol.name,
            "wavelength": mol.wavelength,
            "ecd": mol.ecd
        })
    
    return jsonify({"molecules": molecules_data})

@app.route("/compare_all/")
def compare_all():
    molecules = Molecule.query.all()
    data_cd = []
    data_abs = []
    data_gfac = []
    data_chir = []
    data_achir = []
    for mol in molecules:
        wvl = mol.wavelength
        abs_data = mol.absortion
        ecd_data = mol.ecd
        chirpol_data = mol.chir_pol_im
        achirpol_data = mol.achir_pol_im
        
        if mol.tool == MeasurementType.experimental:
            method = "Experimental"
        else:
            method = "Computational"
        
        ecd_trace = go.Scatter(x=wvl, y=ecd_data, mode='lines', name='{} ({})'.format(mol.name, method))
        data_cd.append(ecd_trace)
        absorption_trace = go.Scatter(x=wvl, y=abs_data, mode='lines', name='{} ({})'.format(mol.name, method))
        data_abs.append(absorption_trace)    
        
        chir_pol_trace = go.Scatter(x=wvl, y=chirpol_data, mode='lines', name='{} ({})'.format(mol.name, method))
        achir_pol_trace = go.Scatter(x=wvl, y=achirpol_data, mode='lines', name='{} ({})'.format(mol.name, method))

        data_chir.append(chir_pol_trace)
        data_achir.append(achir_pol_trace)


        ecd_arr = np.array(ecd_data)
        g_fac = np.zeros(len(ecd_arr))
        abs_arr = np.array(abs_data)

        min_abs1 = np.max(abs_arr)/1000.0

        for i in range(len(ecd_arr)):
            if abs_arr[i] > min_abs1:
                g_fac[i] = ecd_arr[i] / abs_arr[i]
            else:
                g_fac[i] = 0 
        g_fac_trace = go.Scatter(x=wvl, y=g_fac, mode='lines', name='{} ({})'.format(mol.name, method))
        data_gfac.append(g_fac_trace)

    ecd_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='ECD [ext]'), hovermode='closest', autosize=True)
    ecd_figure = go.Figure(data=data_cd, layout=ecd_layout)
    ecd_plot_div = ecd_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    
    abs_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='Abs [ext]'), hovermode='closest', autosize=True)
    abs_figure = go.Figure(data=data_abs, layout=abs_layout)
    abs_plot_div = abs_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
      
    gfac_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='g-factor'), hovermode='closest', autosize=True)
    gfac_figure = go.Figure(data=data_gfac, layout=gfac_layout)
    gfac_plot_div = gfac_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
      
    chir_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='Chiral Polarizability [ext]'), hovermode='closest', autosize=True)
    chir_figure = go.Figure(data=data_chir, layout=chir_layout)
    chir_plot_div = chir_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
          
    achir_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='Chiral Polarizability [ext]'), hovermode='closest', autosize=True)
    achir_figure = go.Figure(data=data_achir, layout=achir_layout)
    achir_plot_div = achir_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    return render_template(
        "compare_all.html",
        molecule1=mol,
        ecd_plot_div = ecd_plot_div,
        abs_plot_div=abs_plot_div,
        gfac_plot_div = gfac_plot_div,
        chir_plot_div=chir_plot_div,
        achir_plot_div=achir_plot_div,
        MeasurementType=MeasurementType,
    )


@app.route("/search/advanced", methods=["GET", "POST"])
def advanced_search():
    form = AdvancedSearchForm()
    molecules = Molecule.query

    if form.validate_on_submit():
        # Get the search parameters
        name_search = form.name_search.data.strip()
        composition_search = form.composition_search.data.strip()
        method_search = form.method_search.data or None  # Allow None if not selected
        uploader_username = form.uploader_search.data.strip()  # Get username input
        
        # Lookup the user ID based on the username
        uploader_id = None
        if uploader_username:
            user = Users.query.filter_by(username=uploader_username).first()
            if user:
                uploader_id = user.id  # Get the user ID

        # Create filters based on the form input
        filters = []

        if name_search:
            filters.append(Molecule.name.ilike(f'%{name_search}%'))
        
        if composition_search:
            filters.append(Molecule.composition.ilike(f'%{composition_search}%'))

        if method_search:
            filters.append(Molecule.tool == method_search)

        if uploader_id:
            filters.append(Molecule.poster_id == uploader_id)  # Use uploader_id for filtering

        # Combine filters based on 'and'/'or' selection
        if filters:
            if form.and_or.data == "or":
                molecules = molecules.filter(or_(*filters))
            else:
                for filter_condition in filters:
                    molecules = molecules.filter(filter_condition)

        # Fetch the results
        molecules = molecules.all()  # Adjust this based on your pagination logic

        return render_template("search.html", 
                               form = form,
                               molecules = molecules,
                               MeasurementType = MeasurementType)

    return render_template('advanced_search.html', form=form)

@app.route("/molecule/<int:id>/bibtex")
@login_required
def download_bibtex(id):
    molecule = Molecule.query.get_or_404(id)
    
    # Extract DOIs from the molecule
    publications = molecule.publication.split(",")
    bibtex_entries = []
    
    for doi in publications:
        doi = doi.strip()
        if doi:
            bibtex = get_bibtex(doi)
            if bibtex:
                bibtex_entries.append(bibtex)
            else:
                bibtex_entries.append(f"% Error fetching BibTeX for DOI: {doi}")

    # Join all BibTeX entries
    bibtex_content = "\n\n".join(bibtex_entries)

    # Serve the BibTeX content as a file
    response = Response(bibtex_content, mimetype='text/plain')
    response.headers['Content-Disposition'] = 'attachment; filename=publications.bib'
    return response

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

@app.route('/plot_data/<int:molecule_id>', methods=['GET'])
def get_plot_data(molecule_id):
    # Query the molecule from the database
    molecule = Molecule.query.get_or_404(molecule_id)

    # Prepare the data
    data = {
        "wavelength": molecule.wavelength,
        "ecd": molecule.ecd,
        "absorption": molecule.absortion,
        "abs_re": molecule.absortion_re
    }
    return jsonify(data)

@app.route('/plot/<int:molecule_id>', methods=['GET'])
def plot_page(molecule_id):
    return render_template('plot.html', molecule_id=molecule_id)
############################|
###### CLASSESS ORM ########|
############################|




import enum
class MeasurementType(enum.Enum):
    computational = 'computational'
    experimental = 'experimental'


class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    #author = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, default = datetime.utcnow)
    slug = db.Column(db.String(255))
    #foreign key to link user, refer to user primary key
    poster_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    
    #foreign key to molecule being described
    molecule_id = db.Column(db.Integer, db.ForeignKey("molecule.id"), nullable=True)

    
#create user model
class Users(db.Model, UserMixin):
    __tablename__='users'
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
    roles = db.relationship('Role', secondary = 'user_roles')
    

    #user confirmed email???
    is_confirmed = db.Column(db.Boolean, nullable = False, default = False)
    confirmed_on = db.Column(db.DateTime, nullable = True)
    
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

class Role(db.Model):
    __tablename__='roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique = True)

class UserRoles(db.Model):
    __tablename__='user_roles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))


class Molecule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=False)
    composition = db.Column(db.String(100), nullable=False)   
    publication = db.Column(db.Text, nullable=True)
    concentration = db.Column(db.Float, nullable = False)
    #author = db.Column(db.String(100))
    poster_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    
    pubchem_id = db.Column(db.Integer, nullable = True)
    
    molecular_weight = db.Column(db.Float, nullable = False)
    
    iupac_name = db.Column(db.String(150), nullable = True)
    
    two_d_struc = db.Column(db.String(), nullable = True)
    three_d_struc = db.Column(db.String(), nullable = True)
    
    # Using postgresql.ENUM to define the enum type explicitly in PostgreSQL
    tool = db.Column(
        ENUM(MeasurementType, name="measurementtype"), 
        nullable=False
    )
    
    raw_data = db.Column(db.String(), nullable = True)
    wavelength = db.Column(ARRAY(db.Float)) 
    absortion = db.Column(ARRAY(db.Float)) 
    ecd = db.Column(ARRAY(db.Float)) 
    absortion_re = db.Column(ARRAY(db.Float)) 
    ecd_re = db.Column(ARRAY(db.Float))
    chir_pol_im = db.Column(ARRAY(db.FLOAT))  
    chir_pol_re = db.Column(ARRAY(db.FLOAT))  
    achir_pol_im = db.Column(ARRAY(db.FLOAT))  
    achir_pol_re = db.Column(ARRAY(db.FLOAT))  
    
    #public for visibility
    public = db.Column(db.Boolean, nullable = True, default = True)
    #relatiosnhip to post
    posts = db.relationship('Posts', backref="molecule", lazy = True)


    
class ResearchGroup(db.Model):
    __tablename__ = 'researchgroup'
    id  = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    affiliation = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    members = db.relationship('Users', backref = "group")
    def __repr__(self) -> str:
        return '<Name %r>' % self.name


