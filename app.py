from flask import Flask, render_template, flash, request, redirect, session, url_for, Response, make_response
from io import StringIO

from flask_wtf import FlaskForm
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from datetime import timedelta

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
from utilities.publication import get_metadata_from_doi, get_bibtex_from_doi
from utilities.units import *

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
app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=50)


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
            flash("Yaldi Yeee!")
            return redirect(url_for("dashboard"))
        else:
            # Handle incorrect credentials
            flash("Invalid username or password! Please try again.")

    return render_template("login.html", form=form)




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
    return render_template("dashboard.html", molecules = my_mols, MeasurementType = MeasurementType)


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
            abs = np.zeros(n_points)

        # Initialize the molecule object
        molecule = Molecule(
            name=form.name.data,
            composition=form.composition.data,
            pubchem_id=cid,  # Store PubChem ID
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
            ecd = []
        )
        C = float(form.concentration.data)
        L = 1.0
        M = float(molecular_weight)
        for i in range(n_points):
            line = next(data).strip()
            wv, cd, _, ab, _ = line.split(',')
            if molecule.tool ==MeasurementType.experimental.value:
                ab = float(ab) * M / (C * L)
                cd = float(cd) * M / (C * L * 32980)
            if (form.abs_units == "abs"):
                ab = abs_to_ext(float(ab), M, C, L)
            if (form.ecd_units == "mdeg"):
                cd = mdeg_to_ext(float(cd), M, C, L)
            molecule.wavelength.append(float(wv))
            molecule.absortion.append(float(ab))
            molecule.ecd.append(float(cd))
        re_abs = im2re_reciprocal(abs[1:], wvl[1:])
        re_ecd = im2re_reciprocal(ecd[1:], wvl[1:])

        for i in range(2,n_points-2):
            molecule.absortion_re.append(float(re_abs[i]))
            molecule.ecd_re.append(float(re_ecd[i]))
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
    
    # Initialize the CSV export form
    form = CSVExportForm()

    # Prepare data for Plotly
    wvl = molecule.wavelength
    abs_data = molecule.absortion
    ecd_data = molecule.ecd
    abs_re_data = molecule.absortion_re
    ecd_re_data = molecule.ecd_re
    
    ecd_abs = np.array(ecd_data)
    abs_arr = np.array(abs_data)
    g_fac = np.zeros(len(ecd_abs))
    min_abs = np.max(abs_arr)/1000.0
    for i in range(len(ecd_abs)):
        if abs_arr[i] > min_abs:
            g_fac[i] = ecd_abs[i] / abs_arr[i]
        else:
            g_fac[i] = 0

    id_max_g = np.argmax(np.abs(g_fac))
    max_g = g_fac[id_max_g]
    wvl_maxg = wvl[id_max_g]
    
    # Create Plotly graph data for Absorption, ECD, and g-factor (as you already have)
    absorption_trace = go.Scatter(x=wvl, y=abs_data, mode='lines', name='Absorption', line=dict(color='blue'))
    absorption_trace_re = go.Scatter(x=wvl, y=abs_re_data, mode='lines', name='Absorption', line=dict(color='red'))
    absorption_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='Absorption [ext]'), hovermode='closest', autosize=True)

    ecd_trace = go.Scatter(x=wvl, y=ecd_data, mode='lines', name='ECD', line=dict(color='orange'))
    ecd_trace_mirr = go.Scatter(x=wvl, y=-1 * np.array(ecd_data), mode='lines', name='ECD [reflected]', line=dict(color='green'))
    ecd_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='ECD [ext]'), hovermode='closest', autosize=True)

    g_fac_trace = go.Scatter(x=wvl, y=g_fac, mode='lines', name='g factor', line=dict(color='orange'))
    g_fac_layout = go.Layout(xaxis=dict(title='Wavelength [nm]'), yaxis=dict(title='g factor'), hovermode='closest', autosize=True)

    ecd_figure = go.Figure(data=[ecd_trace, ecd_trace_mirr], layout=ecd_layout)
    absorption_figure = go.Figure(data=[absorption_trace], layout=absorption_layout)
    g_fac_figure = go.Figure(data=[g_fac_trace], layout=g_fac_layout)

    absorption_plot_div = absorption_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    ecd_plot_div = ecd_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
    gfac_plot_div = g_fac_figure.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})

    publications = molecule.publication
    publications = publications.split(",")
    publications_metadata = [get_metadata_from_doi(doi.strip()) for doi in publications]
    print(publications_metadata)
    context = {"publications": publications,
               "pub_metadata": publications_metadata}
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

        writer.writerow(header)

        # Write data rows based on user selection
        for i in range(len(wvl)):
            row = [wvl[i]]
            if form.absorption.data:
                row.append(abs_data[i])
            if form.ecd.data:
                row.append(ecd_data[i])
            if form.gfactor.data:
                row.append(g_fac[i])
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
    max_g=max_g,
    wvl_maxg=wvl_maxg,
    form=form,
    MeasurementType=MeasurementType,
    **context  # Unpack context dictionary
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
    molecules = Molecule.query.order_by(Molecule.id).all()  # Use .all() to retrieve results
    return render_template("molecules.html", molecules=molecules, MeasurementType = MeasurementType)

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
        
        molecules = molecules.filter(
            or_(Molecule.name.ilike('%' + molecule.searched +'%'),
                Molecule.composition.ilike('%' + molecule.searched + '%'),
                )
        )
        molecules = molecules.order_by(Molecule.name).all()
        return render_template("search.html", 
                               form = form,
                               searched = post.searched,
                               posts = posts,
                               molecules = molecules)


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
                               molecules = molecules)

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
            bibtex = get_bibtex_from_doi(doi)
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
    concentration = db.Column(db.Float, nullable = False)
    #author = db.Column(db.String(100))
    poster_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    
    pubchem_id = db.Column(db.Integer, nullable = True)
    
    molecular_weight = db.Column(db.Float, nullable = False)
    
    iupac_name = db.Column(db.String(150), nullable = True)
    
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
    
class ResearchGroup(db.Model):
    __tablename__ = 'researchgroup'
    id  = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    affiliation = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    members = db.relationship('Users', backref = "group")
    def __repr__(self) -> str:
        return '<Name %r>' % self.name