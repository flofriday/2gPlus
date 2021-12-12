from datetime import datetime
from traceback import format_exception
import traceback

from flask import session, request, flash
from flask.templating import render_template
from werkzeug.exceptions import InternalServerError

from twogplus import app, db
from twogplus.certificates import verify_test_cert, verify_vaccinated_cert
from twogplus.models import User


@app.get("/")
def home():
    if "username" not in session:
        return render_template("home.html", user=None)

    user = User.query.filter(User.name == session["username"])
    return render_template("home.html", user=user)


@app.post("/")
def upload_cert():

    test_file = request.files["testFile"]
    vaccine_file = request.files["vaccineFile"]
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if vaccine_file.filename == "" and test_file.filename == "":
        flash("You must at least upload one file", "danger")
        return render_template("home.html")

    try:
        vaccine_username = test_username = None
        if vaccine_file.filename != "":
            vaccine_username = verify_vaccinated_cert(vaccine_file)
        if test_file.filename != "":
            test_username = verify_test_cert(test_file)

    except Exception as e:
        traceback.print_exc()

        if hasattr(e, "message"):
            message = e.message
        else:
            message = str(e)
        flash(message, "danger")
        return render_template("home.html")

    is_tested = test_username is not None
    is_vaccinated = vaccine_username is not None

    if is_tested and is_vaccinated and vaccine_username != test_username:
        flash(
            "The name in the test and the vaccine certificate don't match. "
            f"Test name: '{test_username}', "
            f"Vaccine name: '{vaccine_username}'",
            "danger",
        )
        return render_template("home.html")

    # TODO If a user with the name already exist we should only update it
    username = vaccine_username if is_vaccinated else test_username
    user = User(username, is_vaccinated, is_tested)
    db.session.add(user)
    db.session.commit()

    # TODO set some cookies or shit

    # TODO: propper message here
    flash(
        "Successfully uploaded some? certificate(s) 🤷‍♀️ ",
        "success",
    )
    return render_template("home.html", user=user)


# TODO: basic auth
@app.get("/admin")
def admin():
    return render_template(
        "admin.html",
        now=datetime.now(),
    )


@app.errorhandler(InternalServerError)
def handle_bad_request(e):
    return (
        render_template(
            "500.html",
            traceback="".join(
                format_exception(
                    None,
                    e.original_exception,
                    e.original_exception.__traceback__,
                )
            ),
        ),
        500,
    )


@app.get("/crash-now")
def crash_now():
    return f"{4/0}"
