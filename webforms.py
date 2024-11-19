from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError, FloatField, IntegerField, SelectField
from wtforms.validators import data_required, equal_to, length, DataRequired
from wtforms.widgets import TextArea
from flask_ckeditor import CKEditorField
from flask_wtf.file import FileField
#login form
class LoginForm(FlaskForm):
    username = StringField("Username (or email)", validators=[DataRequired()])
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
    twod_struc = FileField("2D Structure")
    raw_data = FileField("Spectral Data")
    publication = StringField("Publications, separate with comma", validators=[DataRequired()], widget=TextArea())
    author = StringField("Author")
    pubchem_id = IntegerField("PubChem CID (if available)")
    molecular_weight = FloatField("Molecular Weight (empty if CID given)")
    concentration = FloatField("Concentration [g/L] (1 if ab initio)")
    abs_units = SelectField(
        "Absortion spectrum units",
        choices = [("abs", "Abs"),
                   ("ext", "Ext")],
        validators=[DataRequired()]
    )
    
    ecd_units = SelectField(
        "ECD spectrum units",
        choices = [("abs", "Abs"),
                   ("ext", "Ext"),
                   ("mdeg", "m°")],
        validators=[DataRequired()]
    )
    # Adding the SelectField for choosing the measurement type
    tool = SelectField(
        "Measurement Type", 
        choices=[('computational', 'Computational'), ('experimental', 'Experimental')], 
        validators=[DataRequired()]
    )
    
    submit = SubmitField("Submit")
    
    
#search form
class SearchForm(FlaskForm):
    searched = StringField("Searched", validators=[DataRequired()])
    submit = SubmitField("Submit")
    
class AdvancedSearchForm(FlaskForm):
    name_search = StringField("Molecule Name", default="")
    composition_search = StringField("Molecule Composition", default="")
    method_search = SelectField("Measurement Method",
                                choices=[('', 'Select Method'), ('computational', 'Computational'), ('experimental', 'Experimental')],
                                default='')
    uploader_search = StringField("Uploaded by (Username)", default="")  # Changed to StringField

    and_or = SelectField("Combine search",
                         choices=[("and", "and"), ("or", "or")],
                         default="and")  # Default to "and"
    submit = SubmitField("Search")





class GroupForm(FlaskForm):
    name = StringField("Group name", validators=[DataRequired()])
    affiliation = StringField("Affiliation", validators=[DataRequired()])
    country = StringField("Country", validators=[DataRequired()])

 
    submit = SubmitField("Submit")
    
class CSVExportForm(FlaskForm):
    absorption = BooleanField('Absorption', default=True)
    ecd = BooleanField('ECD', default=True)
    gfactor = BooleanField('g Factor')
    submit = SubmitField('Download CSV')