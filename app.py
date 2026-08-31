from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from database import db, User, Task, TimetableItem

from datetime import datetime, timedelta

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import os


# =========================================================
# APP
# =========================================================

app = Flask(__name__)

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

app.config["SECRET_KEY"] = "aura-secret-key-2028"

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(BASE_DIR, "aura.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# =========================================================
# DATABASE
# =========================================================

with app.app_context():
    db.create_all()


# =========================================================
# CURRENT USER
# =========================================================

def current_user():

    user_id = session.get("user_id")

    if not user_id:
        return None

    return User.query.get(user_id)


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def home():

    user = current_user()

    if not user:
        return redirect(url_for("login"))

    today = datetime.now().date()

    tasks = Task.query.filter_by(
        user_id=user.id,
        date=today
    ).order_by(
        Task.completed.asc(),
        Task.id.asc()
    ).all()

    # -----------------------------------------------------
    # BASIC TASK STATS
    # -----------------------------------------------------

    total_tasks = len(tasks)

    completed_tasks = sum(
        1
        for task in tasks
        if task.completed
    )

    remaining_tasks = total_tasks - completed_tasks

    progress = 0

    if total_tasks > 0:

        progress = round(
            completed_tasks / total_tasks * 100
        )

    # -----------------------------------------------------
    # TODAY'S PLANNED STUDY TIME
    # -----------------------------------------------------

    study_minutes = 0

    for task in tasks:

        if task.timetable_item_id:

            item = TimetableItem.query.filter_by(
                id=task.timetable_item_id,
                user_id=user.id
            ).first()

            if item:

                study_minutes += (
                    item.duration_minutes or 0
                )

    study_hours = round(
        study_minutes / 60,
        1
    )

    # -----------------------------------------------------
    # COMPLETED STUDY TIME
    # -----------------------------------------------------

    completed_minutes = 0

    for task in tasks:

        if (
            task.completed
            and task.timetable_item_id
        ):

            item = TimetableItem.query.filter_by(
                id=task.timetable_item_id,
                user_id=user.id
            ).first()

            if item:

                completed_minutes += (
                    item.duration_minutes or 0
                )

    completed_hours = round(
        completed_minutes / 60,
        1
    )

    # -----------------------------------------------------
    # CURRENT STREAK
    # -----------------------------------------------------

    completed_dates = set()

    completed_tasks_all = Task.query.filter_by(
        user_id=user.id,
        completed=True
    ).all()

    for task in completed_tasks_all:

        completed_dates.add(task.date)

    streak = 0

    check_date = today

    while check_date in completed_dates:

        streak += 1

        check_date = (
            check_date - timedelta(days=1)
        )

    # -----------------------------------------------------
    # AURA INTELLIGENCE
    # -----------------------------------------------------

    if total_tasks == 0:

        intelligence_title = "Your day is ready."

        intelligence_message = (
            "Add your study tasks and start your mission."
        )

    elif progress == 100:

        intelligence_title = "Mission complete! 🏆"

        intelligence_message = (
            "You completed everything planned for today."
        )

    elif progress >= 75:

        intelligence_title = "Almost there! 🔥"

        intelligence_message = (
            f"You've completed {progress}% of today's plan. "
            "Finish the remaining tasks strong."
        )

    elif progress >= 50:

        intelligence_title = "Good progress."

        intelligence_message = (
            f"You've completed {progress}% of today's plan. "
            "Keep your focus and continue."
        )

    else:

        intelligence_title = "Let's get started."

        intelligence_message = (
            f"You have {remaining_tasks} tasks remaining today."
        )

    # -----------------------------------------------------
    # SUBJECT PERFORMANCE
    # -----------------------------------------------------

    subject_data = {}

    all_user_tasks = Task.query.filter_by(
        user_id=user.id
    ).all()

    for task in all_user_tasks:

        subject = (
            task.subject.strip()
            if task.subject
            else "Other"
        )

        if subject not in subject_data:

            subject_data[subject] = {
                "total": 0,
                "completed": 0,
                "progress": 0
            }

        subject_data[subject]["total"] += 1

        if task.completed:

            subject_data[subject]["completed"] += 1

    for subject, data in subject_data.items():

        if data["total"] > 0:

            data["progress"] = round(
                data["completed"]
                / data["total"]
                * 100
            )

    # -----------------------------------------------------
    # NEXT TASK
    # -----------------------------------------------------

    next_task = None

    for task in tasks:

        if not task.completed:

            next_task = task

            break

    # -----------------------------------------------------
    # RENDER DASHBOARD
    # -----------------------------------------------------

    return render_template(
        "dashboard.html",
        user=user,
        tasks=tasks,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        remaining_tasks=remaining_tasks,
        progress=progress,
        study_hours=study_hours,
        completed_hours=completed_hours,
        streak=streak,
        intelligence_title=intelligence_title,
        intelligence_message=intelligence_message,
        next_task=next_task,
        subject_data=subject_data
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if "user_id" in session:

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not name:

            flash(
                "Please enter your name.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if not username:

            flash(
                "Please enter a username.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if not email:

            flash(
                "Please enter your email.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # -------------------------------------------------
        # DUPLICATE USERNAME
        # -------------------------------------------------

        existing_username = User.query.filter_by(
            username=username
        ).first()

        if existing_username:

            flash(
                "Username is already taken.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # -------------------------------------------------
        # DUPLICATE EMAIL
        # -------------------------------------------------

        existing_email = User.query.filter_by(
            email=email
        ).first()

        if existing_email:

            flash(
                "An account already exists with this email.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # -------------------------------------------------
        # CREATE USER
        # -------------------------------------------------

        password_hash = generate_password_hash(
            password
        )

        user = User(
            name=name,
            username=username,
            email=email,
            password_hash=password_hash,
            email_verified=True
        )

        db.session.add(user)

        db.session.commit()

        flash(
            "Account created successfully!",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if "user_id" in session:

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        login_value = request.form.get(
            "login",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter(
            (User.username == login_value)
            |
            (User.email == login_value.lower())
        ).first()

        if not user:

            flash(
                "Invalid username/email or password.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        if not check_password_hash(
            user.password_hash,
            password
        ):

            flash(
                "Invalid username/email or password.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        session.clear()

        session["user_id"] = user.id

        return redirect(
            url_for("home")
        )

    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# ADD TASK
# =========================================================

@app.route(
    "/add-task",
    methods=["GET", "POST"]
)
def add_task():

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        date_string = request.form.get(
            "date",
            ""
        )

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        title = request.form.get(
            "title",
            ""
        ).strip()

        start_time = request.form.get(
            "start_time",
            ""
        )

        end_time = request.form.get(
            "end_time",
            ""
        )

        priority = request.form.get(
            "priority",
            "normal"
        )

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not date_string:

            flash(
                "Please select a date.",
                "error"
            )

            return redirect(
                url_for("add_task")
            )

        if not subject:

            flash(
                "Please enter a subject.",
                "error"
            )

            return redirect(
                url_for("add_task")
            )

        if not title:

            flash(
                "Please enter a task title.",
                "error"
            )

            return redirect(
                url_for("add_task")
            )

        if not start_time or not end_time:

            flash(
                "Please select start and end times.",
                "error"
            )

            return redirect(
                url_for("add_task")
            )

        # -------------------------------------------------
        # DATE / TIME
        # -------------------------------------------------

        try:

            task_date = datetime.strptime(
                date_string,
                "%Y-%m-%d"
            ).date()

            start = datetime.strptime(
                start_time,
                "%H:%M"
            )

            end = datetime.strptime(
                end_time,
                "%H:%M"
            )

        except ValueError:

            flash(
                "Invalid date or time.",
                "error"
            )

            return redirect(
                url_for("add_task")
            )

        duration = int(
            (
                end - start
            ).total_seconds()
            / 60
        )

        if duration <= 0:

            flash(
                "End time must be after start time.",
                "error"
            )

            return redirect(
                url_for("add_task")
            )

        # -------------------------------------------------
        # TIMETABLE ITEM
        # -------------------------------------------------

        timetable_item = TimetableItem(
            user_id=user.id,
            date=task_date,
            subject=subject,
            title=title,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            priority=priority,
            notes=notes
        )

        db.session.add(
            timetable_item
        )

        db.session.flush()



        # -------------------------------------------------
        # TASK
        # -------------------------------------------------

        task = Task(
            user_id=user.id,
            timetable_item_id=timetable_item.id,
            date=task_date,
            subject=subject,
            title=title,
            completed=False
        )

        db.session.add(task)

        db.session.commit()

        flash(
            "Task added successfully!",
            "success"
        )

        return redirect(
            url_for("home")
        )

    return render_template(
        "add_task.html"
    )


# =========================================================
# EDIT TASK
# =========================================================

@app.route(
    "/edit-task/<int:task_id>",
    methods=["GET", "POST"]
)
def edit_task(task_id):

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    task = Task.query.filter_by(
        id=task_id,
        user_id=user.id
    ).first_or_404()

    timetable_item = None

    if task.timetable_item_id:

        timetable_item = TimetableItem.query.filter_by(
            id=task.timetable_item_id,
            user_id=user.id
        ).first()

    if request.method == "POST":

        date_string = request.form.get(
            "date",
            ""
        )

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        title = request.form.get(
            "title",
            ""
        ).strip()

        start_time = request.form.get(
            "start_time",
            ""
        )

        end_time = request.form.get(
            "end_time",
            ""
        )

        priority = request.form.get(
            "priority",
            "normal"
        )

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not date_string:

            flash(
                "Please select a date.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_task",
                    task_id=task.id
                )
            )

        if not subject:

            flash(
                "Please enter a subject.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_task",
                    task_id=task.id
                )
            )

        if not title:

            flash(
                "Please enter a task title.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_task",
                    task_id=task.id
                )
            )

        if not start_time or not end_time:

            flash(
                "Please select start and end times.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_task",
                    task_id=task.id
                )
            )

        # -------------------------------------------------
        # DATE / TIME
        # -------------------------------------------------

        try:

            task_date = datetime.strptime(
                date_string,
                "%Y-%m-%d"
            ).date()

            start = datetime.strptime(
                start_time,
                "%H:%M"
            )

            end = datetime.strptime(
                end_time,
                "%H:%M"
            )

        except ValueError:

            flash(
                "Invalid date or time.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_task",
                    task_id=task.id
                )
            )

        duration = int(
            (
                end - start
            ).total_seconds()
            / 60
        )

        if duration <= 0:

            flash(
                "End time must be after start time.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_task",
                    task_id=task.id
                )
            )

        # -------------------------------------------------
        # UPDATE TASK
        # -------------------------------------------------

        task.date = task_date
        task.subject = subject
        task.title = title

        # -------------------------------------------------
        # UPDATE TIMETABLE ITEM
        # -------------------------------------------------

        if timetable_item:

            timetable_item.date = task_date
            timetable_item.subject = subject
            timetable_item.title = title
            timetable_item.start_time = start_time
            timetable_item.end_time = end_time
            timetable_item.duration_minutes = duration
            timetable_item.priority = priority
            timetable_item.notes = notes

        else:

            timetable_item = TimetableItem(
                user_id=user.id,
                date=task_date,
                subject=subject,
                title=title,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration,
                priority=priority,
                notes=notes
            )

            db.session.add(
                timetable_item
            )

            db.session.flush()

            task.timetable_item_id = timetable_item.id

        db.session.commit()

        flash(
            "Task updated successfully!",
            "success"
        )

        return redirect(
            url_for("home")
        )

    return render_template(
        "edit_task.html",
        task=task,
        timetable_item=timetable_item
    )


# =========================================================
# DELETE TASK
# =========================================================

@app.route(
    "/delete-task/<int:task_id>",
    methods=["POST"]
)
def delete_task(task_id):

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    task = Task.query.filter_by(
        id=task_id,
        user_id=user.id
    ).first_or_404()

    timetable_item = None

    if task.timetable_item_id:

        timetable_item = TimetableItem.query.filter_by(
            id=task.timetable_item_id,
            user_id=user.id
        ).first()

    db.session.delete(task)

    if timetable_item:

        db.session.delete(
            timetable_item
        )

    db.session.commit()

    flash(
        "Task deleted successfully.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# COMPLETE TASK
# =========================================================

@app.route(
    "/complete-task/<int:task_id>",
    methods=["POST"]
)
def complete_task(task_id):

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    task = Task.query.filter_by(
        id=task_id,
        user_id=user.id
    ).first_or_404()

    if task.completed:

        return redirect(
            url_for("home")
        )

    task.completed = True

    task.completed_at = datetime.utcnow()

    db.session.commit()

    return redirect(
        url_for("home")
    )


# =========================================================
# UNCOMPLETE TASK
# =========================================================

@app.route(
    "/uncomplete-task/<int:task_id>",
    methods=["POST"]
)
def uncomplete_task(task_id):

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    task = Task.query.filter_by(
        id=task_id,
        user_id=user.id
    ).first_or_404()

    task.completed = False

    task.completed_at = None

    db.session.commit()

    return redirect(
        url_for("home")
    )


# =========================================================
# TIMETABLE
# =========================================================

@app.route("/timetable")
def timetable():

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    timetable_items = TimetableItem.query.filter_by(
        user_id=user.id
    ).order_by(
        TimetableItem.date.asc(),
        TimetableItem.start_time.asc()
    ).all()

    return render_template(
        "timetable.html",
        timetable=timetable_items
    )

# =========================================================
# DELETE TIMETABLE SESSION
# =========================================================

@app.route(
    "/delete-timetable/<int:item_id>",
    methods=["POST"]
)
def delete_timetable(item_id):

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    item = TimetableItem.query.filter_by(
        id=item_id,
        user_id=user.id
    ).first_or_404()

    task = Task.query.filter_by(
        timetable_item_id=item.id,
        user_id=user.id
    ).first()

    if task:

        db.session.delete(task)

    db.session.delete(item)

    db.session.commit()

    flash(
        "Study session deleted successfully.",
        "success"
    )

    return redirect(
        url_for("timetable")
    )

# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    tasks = Task.query.filter_by(
        user_id=user.id
    ).order_by(
        Task.date.desc(),
        Task.id.desc()
    ).all()

    history_data = {}

    for task in tasks:

        date_key = task.date

        if date_key not in history_data:

            history_data[date_key] = {
                "total": 0,
                "completed": 0
            }

        history_data[date_key]["total"] += 1

        if task.completed:

            history_data[date_key]["completed"] += 1

    return render_template(
        "history.html",
        history=history_data
    )


# =========================================================
# ANALYTICS
# =========================================================

@app.route("/analytics")
def analytics():

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    # -----------------------------------------------------
    # ALL USER TASKS
    # -----------------------------------------------------

    tasks = Task.query.filter_by(
        user_id=user.id
    ).order_by(
        Task.date.asc(),
        Task.id.asc()
    ).all()

    total_tasks = len(tasks)

    completed_tasks = sum(
        1
        for task in tasks
        if task.completed
    )

    remaining_tasks = (
        total_tasks - completed_tasks
    )

    overall_progress = 0

    if total_tasks > 0:

        overall_progress = round(
            completed_tasks
            / total_tasks
            * 100
        )

    # -----------------------------------------------------
    # SUBJECT DATA
    # -----------------------------------------------------

    subject_data = {}

    for task in tasks:

        subject = (
            task.subject.strip()
            if task.subject
            else "Other"
        )

        if subject not in subject_data:

            subject_data[subject] = {
                "total": 0,
                "completed": 0,
                "progress": 0
            }

        subject_data[subject]["total"] += 1

        if task.completed:

            subject_data[subject]["completed"] += 1

    for subject, data in subject_data.items():

        total = data["total"]

        completed = data["completed"]

        if total > 0:

            data["progress"] = round(
                completed
                / total
                * 100
            )

    # -----------------------------------------------------
    # BEST SUBJECT
    # -----------------------------------------------------

    best_subject = None

    best_progress = 0

    if subject_data:

        best_subject = max(
            subject_data,
            key=lambda subject:
                subject_data[subject]["progress"]
        )

        best_progress = subject_data[
            best_subject
        ]["progress"]

    # -----------------------------------------------------
    # WEEKLY DATA
    # -----------------------------------------------------

    weekly_data = {}

    for task in tasks:

        week_key = task.date.strftime(
            "%Y-%W"
        )

        if week_key not in weekly_data:

            weekly_data[week_key] = {
                "total": 0,
                "completed": 0,
                "progress": 0
            }

        weekly_data[week_key]["total"] += 1

        if task.completed:

            weekly_data[week_key]["completed"] += 1

    for week, data in weekly_data.items():

        total = data["total"]

        completed = data["completed"]

        if total > 0:

            data["progress"] = round(
                completed
                / total
                * 100
            )

    # -----------------------------------------------------
    # STUDY TIME
    # -----------------------------------------------------

    study_minutes = 0

    for task in tasks:

        if (
            task.completed
            and task.timetable_item_id
        ):

            item = TimetableItem.query.filter_by(
                id=task.timetable_item_id,
                user_id=user.id
            ).first()

            if item:

                study_minutes += (
                    item.duration_minutes or 0
                )

    study_hours = round(
        study_minutes / 60,
        1
    )

    # -----------------------------------------------------
    # RENDER ANALYTICS
    # -----------------------------------------------------

    return render_template(
        "analytics.html",
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        remaining_tasks=remaining_tasks,
        overall_progress=overall_progress,
        subject_data=subject_data,
        best_subject=best_subject,
        best_progress=best_progress,
        weekly_data=weekly_data,
        study_hours=study_hours
    )


# =========================================================
# SUBJECT DETAIL
# =========================================================

@app.route(
    "/subject/<path:subject_name>"
)
def subject_detail(subject_name):

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    subject_name = subject_name.strip()

    tasks = Task.query.filter(
        Task.user_id == user.id,
        Task.subject == subject_name
    ).order_by(
        Task.date.desc(),
        Task.id.desc()
    ).all()

    total_tasks = len(tasks)

    completed_tasks = sum(
        1
        for task in tasks
        if task.completed
    )

    remaining_tasks = (
        total_tasks - completed_tasks
    )

    progress = 0

    if total_tasks > 0:

        progress = round(
            completed_tasks
            / total_tasks
            * 100
        )

    # -----------------------------------------------------
    # STUDY TIME
    # -----------------------------------------------------

    study_minutes = 0

    for task in tasks:

        if task.timetable_item_id:

            item = TimetableItem.query.filter_by(
                id=task.timetable_item_id,
                user_id=user.id
            ).first()

            if item:

                study_minutes += (
                    item.duration_minutes or 0
                )

    study_hours = round(
        study_minutes / 60,
        1
    )

    return render_template(
        "subject_detail.html",
        subject=subject_name,
        tasks=tasks,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        remaining_tasks=remaining_tasks,
        progress=progress,
        study_hours=study_hours
    )


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
