from flask_wtf import FlaskForm
from govuk_frontend_wtf.wtforms_widgets import GovRadioInput, GovSubmitInput, GovTextInput, GovDateInput, GovSelect
from wtforms.fields import RadioField, SubmitField, StringField, DateField, SelectField
from wtforms.validators import InputRequired, Length
from wtforms.widgets import HiddenInput


class CookiesForm(FlaskForm):
    functional = RadioField(
        "Do you want to accept functional cookies?",
        widget=GovRadioInput(),
        validators=[InputRequired(message="Select yes if you want to accept functional cookies")],
        choices=[("no", "No"), ("yes", "Yes")],
        default="no",
    )
    analytics = RadioField(
        "Do you want to accept analytics cookies?",
        widget=GovRadioInput(),
        validators=[InputRequired(message="Select yes if you want to accept analytics cookies")],
        choices=[("no", "No"), ("yes", "Yes")],
        default="no",
    )
    save = SubmitField("Save cookie settings", widget=GovSubmitInput())


class DiscoForm(FlaskForm):

    desired_url = StringField(
        "Desired URL",
        widget=GovTextInput(),
        validators=[
            InputRequired(message="Enter a desired url"),
            Length(max=256, message="URL must be 256 characters or fewer")
        ],
        description="Must include the / at the start of the URL",
    )

    start_date = DateField(
        "Please enter the start date for the period you need data for",
        widget=GovDateInput(),
        format="%d %m %Y",
        validators=[
            InputRequired()
        ]
    )

    end_date = DateField(
        "Please enter the end date for the period you need data for",
        widget=GovDateInput(),
        format="%d %m %Y",
        validators=[
            InputRequired()
        ]
    )

    ga_toggle = SelectField(
        "Please choose the Google Analytics version you would like to use",
        widget=GovSelect(),
        choices=[("ua", "Universal Analytics"), ("ga4", "Google Analytics 4")]
    )

    submit = SubmitField("Continue", widget=GovSubmitInput())


def hide(self):
    if self.type == "SelectField":
        print("")
    else:
        self.widget = HiddenInput()
