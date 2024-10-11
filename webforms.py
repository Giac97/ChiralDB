from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError
from wtforms.validators import data_required, equal_to, length, DataRequired
from wtforms.widgets import TextArea
from flask_ckeditor import CKEditorField
from flask_wtf.file import FileField
#login form
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")
    
#post form
class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    content = CKEditorField("Content", validators=[DataRequired()])
    author = StringField("Author")
    slug = StringField("Slug",validators=[DataRequired()])
    submit = SubmitField("Submit")
    
#Create form class
class UserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])

    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    profile_pic = FileField("Profile Picture")
    affiliation = StringField("Affiliation")
    password_hash = PasswordField('Password', validators=[DataRequired(), equal_to('password_hash2', message="Password must match")]) 
    password_hash2 = PasswordField('Confirm Password', validators=[DataRequired(), equal_to('password_hash2', message="Password must match")])
    submit = SubmitField("Submit")

class PasswordForm(FlaskForm):
    email = StringField("What's yer email?", validators=[DataRequired()])
    password_hash = PasswordField("What's yer password?", validators=[DataRequired()])
    submit = SubmitField("Submit")

class MoleculeForm(FlaskForm):
    name = StringField("Molecule name", validators=[DataRequired()])
    composition = StringField("Molecule chemical composition", validators=[DataRequired()])
    raw_data = FileField("Profile Picture")
    publication = StringField("Publications", validators=[DataRequired()], widget=TextArea())
    author = StringField("Author")
 
    submit = SubmitField("Submit")
    
    
#search form
class SearchForm(FlaskForm):
    searched = StringField("Searched", validators=[DataRequired()])
    submit = SubmitField("Submit")
    
class GroupForm(FlaskForm):
    name = StringField("Group name", validators=[DataRequired()])
    affiliation = StringField("Affiliation", validators=[DataRequired()])
    country = StringField("Country", validators=[DataRequired()])

 
    submit = SubmitField("Submit")