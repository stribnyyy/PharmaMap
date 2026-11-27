from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app
)

from flask_login import (
    login_user,
    logout_user,
    current_user
)

from app.services.auth import authenticate


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


@auth_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if current_user.is_authenticated:

        return redirect(
            url_for("main.index")
        )

    if request.method == "POST":

        if not current_app.config["AUTH_PASSWORD_HASH"]:

            flash(
                "Аккаунт ещё не настроен.",
                "error"
            )

            return render_template(
                "auth/login.html"
            ), 503

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        )

        user = authenticate(
            username,
            password
        )

        if user is None:

            flash(
                "Неверный логин или пароль.",
                "error"
            )

            return render_template(
                "auth/login.html"
            ), 401

        session.clear()

        login_user(user)

        return redirect(
            url_for("main.index"),
            code=303
        )

    return render_template(
        "auth/login.html"
    )


@auth_bp.post("/logout")
def logout():

    logout_user()
    session.clear()

    return redirect(
        url_for("auth.login"),
        code=303
    )