from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from database import (
    db,
    User,
    Task,
    TimetableItem,
    TaskHistory,
    WeeklyDay
)

from datetime import datetime, timedelta

from sqlalchemy import inspect, text

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
# DATABASE HELPERS
# =========================================================

def get_table_columns(table_name):

    inspector = inspect(db.engine)

    try:

        return {
            column["name"]
            for column in inspector.get_columns(
                table_name
            )
        }

    except Exception:

        return set()


def add_column_if_missing(
    table_name,
    column_name,
    column_definition
):

    columns = get_table_columns(
        table_name
    )

    if column_name not in columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column_name} "
                    f"{column_definition}"
                )
            )


# =========================================================
# DATABASE MIGRATION
# =========================================================

def migrate_database():

    # -----------------------------------------------------
    # CREATE TABLES
    # -----------------------------------------------------

    db.create_all()

    # =====================================================
    # TASKS
    # =====================================================

    task_columns = get_table_columns(
        "tasks"
    )

    if "status" not in task_columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    "ALTER TABLE tasks "
                    "ADD COLUMN status VARCHAR(20) "
                    "DEFAULT 'pending'"
                )
            )

    task_columns = get_table_columns(
        "tasks"
    )

    if "completed_at" not in task_columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    "ALTER TABLE tasks "
                    "ADD COLUMN completed_at DATETIME"
                )
            )

    task_columns = get_table_columns(
        "tasks"
    )

    if "weekday" not in task_columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    "ALTER TABLE tasks "
                    "ADD COLUMN weekday INTEGER"
                )
            )

    task_columns = get_table_columns(
        "tasks"
    )

    if "is_active" not in task_columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    "ALTER TABLE tasks "
                    "ADD COLUMN is_active BOOLEAN "
                    "DEFAULT 1"
                )
            )

    task_columns = get_table_columns(
        "tasks"
    )

    # -----------------------------------------------------
    # FIX OLD TASK DATA
    # -----------------------------------------------------

    with db.engine.begin() as connection:

        if "completed" in task_columns:

            connection.execute(
                text(
                    "UPDATE tasks "
                    "SET status = 'done' "
                    "WHERE completed = 1 "
                    "AND (status IS NULL OR status = '')"
                )
            )

            connection.execute(
                text(
                    "UPDATE tasks "
                    "SET status = 'pending' "
                    "WHERE (completed = 0 "
                    "OR completed IS NULL) "
                    "AND (status IS NULL OR status = '')"
                )
            )

        connection.execute(
            text(
                "UPDATE tasks "
                "SET status = 'pending' "
                "WHERE status IS NULL "
                "OR status = ''"
            )
        )

        # -------------------------------------------------
        # Convert old weekday strings to numbers
        # -------------------------------------------------

        weekday_map = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6
        }

        rows = connection.execute(
            text(
                "SELECT id, weekday, date "
                "FROM tasks"
            )
        ).fetchall()

        for row in rows:

            new_weekday = None

            if row.weekday is not None:

                value = str(
                    row.weekday
                ).strip()

                if value.isdigit():

                    number = int(value)

                    if 0 <= number <= 6:

                        new_weekday = number

                elif value in weekday_map:

                    new_weekday = weekday_map[
                        value
                    ]

            if new_weekday is None and row.date:

                try:

                    if isinstance(
                        row.date,
                        str
                    ):

                        task_date = datetime.strptime(
                            row.date[:10],
                            "%Y-%m-%d"
                        ).date()

                    else:

                        task_date = row.date

                    new_weekday = (
                        task_date.weekday()
                    )

                except Exception:

                    pass

            if new_weekday is not None:

                connection.execute(
                    text(
                        "UPDATE tasks "
                        "SET weekday = :weekday "
                        "WHERE id = :id"
                    ),
                    {
                        "weekday": new_weekday,
                        "id": row.id
                    }
                )

        connection.execute(
            text(
                "UPDATE tasks "
                "SET is_active = 1 "
                "WHERE is_active IS NULL"
            )
        )

    # =====================================================
    # TIMETABLE ITEMS
    # =====================================================

    timetable_columns = get_table_columns(
        "timetable_items"
    )

    if "weekday" not in timetable_columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    "ALTER TABLE timetable_items "
                    "ADD COLUMN weekday INTEGER"
                )
            )

    timetable_columns = get_table_columns(
        "timetable_items"
    )

    if "is_active" not in timetable_columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    "ALTER TABLE timetable_items "
                    "ADD COLUMN is_active BOOLEAN "
                    "DEFAULT 1"
                )
            )

    timetable_columns = get_table_columns(
        "timetable_items"
    )

    if "created_at" not in timetable_columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    "ALTER TABLE timetable_items "
                    "ADD COLUMN created_at DATETIME"
                )
            )

    timetable_columns = get_table_columns(
        "timetable_items"
    )

    # -----------------------------------------------------
    # FIX OLD TIMETABLE DATA
    # -----------------------------------------------------

    with db.engine.begin() as connection:

        weekday_map = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6
        }

        rows = connection.execute(
            text(
                "SELECT id, weekday, date "
                "FROM timetable_items"
            )
        ).fetchall()

        for row in rows:

            new_weekday = None

            if row.weekday is not None:

                value = str(
                    row.weekday
                ).strip()

                if value.isdigit():

                    number = int(value)

                    if 0 <= number <= 6:

                        new_weekday = number

                elif value in weekday_map:

                    new_weekday = weekday_map[
                        value
                    ]

            if new_weekday is None and row.date:

                try:

                    if isinstance(
                        row.date,
                        str
                    ):

                        item_date = datetime.strptime(
                            row.date[:10],
                            "%Y-%m-%d"
                        ).date()

                    else:

                        item_date = row.date

                    new_weekday = (
                        item_date.weekday()
                    )

                except Exception:

                    pass

            if new_weekday is not None:

                connection.execute(
                    text(
                        "UPDATE timetable_items "
                        "SET weekday = :weekday "
                        "WHERE id = :id"
                    ),
                    {
                        "weekday": new_weekday,
                        "id": row.id
                    }
                )

        connection.execute(
            text(
                "UPDATE timetable_items "
                "SET is_active = 1 "
                "WHERE is_active IS NULL"
            )
        )

        connection.execute(
            text(
                "UPDATE timetable_items "
                "SET created_at = CURRENT_TIMESTAMP "
                "WHERE created_at IS NULL"
            )
        )


# =========================================================
# RUN MIGRATION
# =========================================================

with app.app_context():

    migrate_database()


# =========================================================
# CURRENT USER
# =========================================================

def current_user():

    user_id = session.get(
        "user_id"
    )

    if not user_id:

        return None

    return db.session.get(
        User,
        user_id
    )


# =========================================================
# WEEK HELPERS
# =========================================================

def get_current_week():

    today = datetime.now().date()

    monday = (
        today
        - timedelta(
            days=today.weekday()
        )
    )

    sunday = (
        monday
        + timedelta(days=6)
    )

    return monday, sunday


def get_week_dates():

    monday, sunday = (
        get_current_week()
    )

    return [
        monday + timedelta(days=i)
        for i in range(7)
    ]


# =========================================================
# WEEKLY AUTO ARCHIVE
# =========================================================
#
# Every request checks for active tasks belonging to
# previous weeks.
#
# Sunday ends -> Monday arrives -> previous week gets
# archived automatically.
#
# Nothing is hard deleted.
#
# TaskHistory receives a permanent snapshot.
#
# Original Task + TimetableItem become inactive.
#
# =========================================================

def archive_expired_weeks(user):

    if not user:

        return

    current_monday, _ = (
        get_current_week()
    )

    old_tasks = Task.query.filter(
        Task.user_id == user.id,
        Task.is_active == True,
        Task.date < current_monday
    ).all()

    if not old_tasks:

        return

    changed = False

    for task in old_tasks:

        # -------------------------------------------------
        # DUPLICATE PROTECTION
        # -------------------------------------------------

        existing_history = TaskHistory.query.filter_by(
            user_id=user.id,
            original_task_id=task.id
        ).first()

        # -------------------------------------------------
        # FIND TIMETABLE ITEM
        # -------------------------------------------------

        timetable_item = None

        if task.timetable_item_id:

            timetable_item = TimetableItem.query.filter_by(
                id=task.timetable_item_id,
                user_id=user.id
            ).first()

        # -------------------------------------------------
        # CREATE HISTORY SNAPSHOT
        # -------------------------------------------------

        if not existing_history:

            history = TaskHistory(
                user_id=user.id,

                original_task_id=task.id,

                timetable_item_id=(
                    timetable_item.id
                    if timetable_item
                    else task.timetable_item_id
                ),

                date=task.date,

                weekday=(
                    task.weekday
                    if task.weekday is not None
                    else task.date.weekday()
                ),

                subject=task.subject,

                title=task.title,

                start_time=(
                    timetable_item.start_time
                    if timetable_item
                    else None
                ),

                end_time=(
                    timetable_item.end_time
                    if timetable_item
                    else None
                ),

                duration_minutes=(
                    timetable_item.duration_minutes
                    if timetable_item
                    else None
                ),

                status=(
                    task.status
                    if task.status
                    else "pending"
                ),

                completed_at=task.completed_at,

                archived_at=datetime.utcnow(),

                notes=(
                    timetable_item.notes
                    if timetable_item
                    else None
                )
            )

            db.session.add(
                history
            )

        # -------------------------------------------------
        # ARCHIVE ORIGINAL TASK
        # -------------------------------------------------

        task.is_active = False

        # -------------------------------------------------
        # ARCHIVE TIMETABLE ITEM
        # -------------------------------------------------

        if timetable_item:

            timetable_item.is_active = False

        changed = True

    # -----------------------------------------------------
    # REMOVE OLD WEEK DAY MAPS
    # -----------------------------------------------------

    old_week_days = WeeklyDay.query.filter(
        WeeklyDay.user_id == user.id,
        WeeklyDay.week_start < current_monday
    ).all()

    for day in old_week_days:

        db.session.delete(day)

        changed = True

    if changed:

        db.session.commit()


# =========================================================
# AUTO ARCHIVE FOR LOGGED USER
# =========================================================

@app.before_request
def automatic_weekly_archive():

    endpoint = request.endpoint

    # -----------------------------------------------------
    # Skip static / auth pages
    # -----------------------------------------------------

    if endpoint in {
        "login",
        "register",
        "static"
    }:

        return

    user = current_user()

    if user:

        try:

            archive_expired_weeks(
                user
            )

        except Exception:

            db.session.rollback()


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def home():

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    today = datetime.now().date()

    tasks = Task.query.filter_by(
        user_id=user.id,
        date=today,
        is_active=True
    ).order_by(
        Task.id.asc()
    ).all()

    # =====================================================
    # BASIC STATS
    # =====================================================

    total_tasks = len(tasks)

    completed_tasks = sum(
        1
        for task in tasks
        if task.status == "done"
    )

    remaining_tasks = (
        total_tasks
        - completed_tasks
    )

    progress = 0

    if total_tasks > 0:

        progress = round(
            completed_tasks
            / total_tasks
            * 100
        )

    # =====================================================
    # STUDY TIME
    # =====================================================

    study_minutes = 0

    completed_minutes = 0

    for task in tasks:

        if not task.timetable_item_id:

            continue

        item = TimetableItem.query.filter_by(
            id=task.timetable_item_id,
            user_id=user.id
        ).first()

        if not item:

            continue

        study_minutes += (
            item.duration_minutes or 0
        )

        if task.status == "done":

            completed_minutes += (
                item.duration_minutes or 0
            )

    study_hours = round(
        study_minutes / 60,
        1
    )

    completed_hours = round(
        completed_minutes / 60,
        1
    )

    # =====================================================
    # STREAK
    # =====================================================

    completed_dates = set()

    completed_tasks_all = Task.query.filter_by(
        user_id=user.id,
        status="done"
    ).all()

    for task in completed_tasks_all:

        if task.date:

            completed_dates.add(
                task.date
            )

    streak = 0

    check_date = today

    while check_date in completed_dates:

        streak += 1

        check_date -= timedelta(
            days=1
        )

    # =====================================================
    # AURA INTELLIGENCE
    # =====================================================

    if total_tasks == 0:

        intelligence_title = (
            "Your day is ready."
        )

        intelligence_message = (
            "Add your study tasks and start your mission."
        )

    elif progress == 100:

        intelligence_title = (
            "Mission complete! 🏆"
        )

        intelligence_message = (
            "You completed everything planned for today."
        )

    elif progress >= 75:

        intelligence_title = (
            "Almost there! 🔥"
        )

        intelligence_message = (
            f"You've completed {progress}% of today's plan. "
            "Finish the remaining tasks strong."
        )

    elif progress >= 50:

        intelligence_title = (
            "Good progress."
        )

        intelligence_message = (
            f"You've completed {progress}% of today's plan. "
            "Keep your focus and continue."
        )

    else:

        intelligence_title = (
            "Let's get started."
        )

        intelligence_message = (
            f"You have {remaining_tasks} "
            "tasks remaining today."
        )

    # =====================================================
    # SUBJECT PERFORMANCE
    # =====================================================

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

        if task.status == "done":

            subject_data[subject]["completed"] += 1

    for subject, data in subject_data.items():

        if data["total"] > 0:

            data["progress"] = round(
                data["completed"]
                / data["total"]
                * 100
            )

    # =====================================================
    # NEXT UP
    # =====================================================

    now = datetime.now()

    current_time = now.time()

    next_task = None

    current_task = None

    future_tasks = []

    for task in tasks:

        if (
            task.status != "pending"
            or not task.timetable_item_id
        ):

            continue

        item = TimetableItem.query.filter_by(
            id=task.timetable_item_id,
            user_id=user.id
        ).first()

        if not item:

            continue

        try:

            start = datetime.strptime(
                item.start_time,
                "%H:%M"
            ).time()

            end = datetime.strptime(
                item.end_time,
                "%H:%M"
            ).time()

        except (
            ValueError,
            TypeError
        ):

            continue

        if start <= current_time < end:

            current_task = task

        elif current_time < start:

            future_tasks.append(
                (start, task)
            )

    if current_task:

        next_task = current_task

    elif future_tasks:

        future_tasks.sort(
            key=lambda x: x[0]
        )

        next_task = future_tasks[0][1]

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

        user = User(
            name=name,
            username=username,
            email=email,
            password_hash=generate_password_hash(
                password
            ),
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

    # -----------------------------------------------------
    # PRESELECTED DATE
    # -----------------------------------------------------

    preselected_date = request.args.get(
        "date",
        ""
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

        weekday = task_date.weekday()

        timetable_item = TimetableItem(
            user_id=user.id,
            date=task_date,
            subject=subject,
            title=title,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            priority=priority,
            notes=notes,
            weekday=weekday,
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.session.add(
            timetable_item
        )

        db.session.flush()

        task = Task(
            user_id=user.id,
            timetable_item_id=timetable_item.id,
            date=task_date,
            subject=subject,
            title=title,
            completed=False,
            status="pending",
            weekday=weekday,
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.session.add(task)

        db.session.commit()

        flash(
            "Task added successfully!",
            "success"
        )

        # -------------------------------------------------
        # RETURN TO TIMETABLE IF DATE WAS PROVIDED
        # -------------------------------------------------

        return redirect(
            url_for("timetable")
        )

    return render_template(
        "add_task.html",
        preselected_date=preselected_date
    )


# =========================================================
# SET WEEKLY DAY DATE
# =========================================================

@app.route(
    "/set-weekly-date/<int:weekday>",
    methods=["POST"]
)
def set_weekly_date(weekday):

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    if weekday < 0 or weekday > 6:

        flash(
            "Invalid weekday.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    date_string = request.form.get(
        "selected_date",
        ""
    ).strip()

    if not date_string:

        flash(
            "Please select a date.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    try:

        selected_date = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        flash(
            "Invalid date.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    # -----------------------------------------------------
    # DATE MUST MATCH THE SELECTED WEEKDAY
    # -----------------------------------------------------

    if selected_date.weekday() != weekday:

        flash(
            "Please select a date that matches this day.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    week_start, week_end = (
        get_current_week()
    )

    # -----------------------------------------------------
    # KEEP THE DATE INSIDE CURRENT WEEK
    # -----------------------------------------------------

    if not (
        week_start
        <= selected_date
        <= week_end
    ):

        flash(
            "Please select a date inside the current week.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    existing = WeeklyDay.query.filter_by(
        user_id=user.id,
        week_start=week_start,
        weekday=weekday
    ).first()

    if existing:

        existing.selected_date = selected_date

    else:

        weekly_day = WeeklyDay(
            user_id=user.id,
            week_start=week_start,
            weekday=weekday,
            selected_date=selected_date,
            created_at=datetime.utcnow()
        )

        db.session.add(
            weekly_day
        )

    db.session.commit()

    flash(
        f"{selected_date.strftime('%A')} date saved.",
        "success"
    )

    return redirect(
        url_for("timetable")
    )


# =========================================================
# ADD TASK DIRECTLY FROM WEEKLY TIMETABLE
# =========================================================

@app.route(
    "/weekly-add-task",
    methods=["POST"]
)
def weekly_add_task():

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    date_string = request.form.get(
        "date",
        ""
    ).strip()

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
    ).strip()

    end_time = request.form.get(
        "end_time",
        ""
    ).strip()

    priority = request.form.get(
        "priority",
        "normal"
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not date_string:

        flash(
            "Please set the day date first.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    if not subject:

        flash(
            "Please enter a subject.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    if not title:

        flash(
            "Please enter a task title.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    if not start_time or not end_time:

        flash(
            "Please select start and end times.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

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
            url_for("timetable")
        )

    # -----------------------------------------------------
    # VERIFY DATE BELONGS TO CURRENT WEEK
    # -----------------------------------------------------

    week_start, week_end = (
        get_current_week()
    )

    if not (
        week_start
        <= task_date
        <= week_end
    ):

        flash(
            "This date is outside the current week.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    # -----------------------------------------------------
    # VERIFY DATE WAS SET FOR ITS DAY
    # -----------------------------------------------------

    weekly_day = WeeklyDay.query.filter_by(
        user_id=user.id,
        week_start=week_start,
        weekday=task_date.weekday()
    ).first()

    if not weekly_day:

        flash(
            "Please set the date for this day first.",
            "error"
        )

        return redirect(
            url_for("timetable")
        )

    if weekly_day.selected_date != task_date:

        flash(
            "The selected date does not match this day.",
            "error"
        )

        return redirect(
            url_for("timetable")
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
            url_for("timetable")
        )

    weekday = task_date.weekday()

    # =====================================================
    # CREATE TIMETABLE ITEM
    # =====================================================

    timetable_item = TimetableItem(
        user_id=user.id,
        date=task_date,
        subject=subject,
        title=title,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration,
        priority=priority,
        notes=notes,
        weekday=weekday,
        is_active=True,
        created_at=datetime.utcnow()
    )

    db.session.add(
        timetable_item
    )

    db.session.flush()

    # =====================================================
    # CREATE TASK
    # =====================================================

    task = Task(
        user_id=user.id,
        timetable_item_id=timetable_item.id,
        date=task_date,
        subject=subject,
        title=title,
        completed=False,
        status="pending",
        weekday=weekday,
        is_active=True,
        created_at=datetime.utcnow()
    )

    db.session.add(task)

    db.session.commit()

    flash(
        "Study task added to your timetable.",
        "success"
    )

    return redirect(
        url_for("timetable")
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

        weekday = task_date.weekday()

        task.date = task_date
        task.subject = subject
        task.title = title
        task.weekday = weekday
        task.is_active = True

        if timetable_item:

            timetable_item.date = task_date
            timetable_item.subject = subject
            timetable_item.title = title
            timetable_item.start_time = start_time
            timetable_item.end_time = end_time
            timetable_item.duration_minutes = duration
            timetable_item.priority = priority
            timetable_item.notes = notes
            timetable_item.weekday = weekday
            timetable_item.is_active = True

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
                notes=notes,
                weekday=weekday,
                is_active=True,
                created_at=datetime.utcnow()
            )

            db.session.add(
                timetable_item
            )

            db.session.flush()

            task.timetable_item_id = (
                timetable_item.id
            )

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

    task.status = "done"
    task.completed = True
    task.completed_at = datetime.utcnow()
    task.is_active = True

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

    task.status = "pending"
    task.completed = False
    task.completed_at = None
    task.is_active = True

    db.session.commit()

    return redirect(
        url_for("home")
    )


# =========================================================
# MARK TASK AS NOT DONE
# =========================================================

@app.route(
    "/not-done-task/<int:task_id>",
    methods=["POST"]
)
def not_done_task(task_id):

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    task = Task.query.filter_by(
        id=task_id,
        user_id=user.id
    ).first_or_404()

    task.status = "not_done"
    task.completed = False
    task.completed_at = None
    task.is_active = True

    db.session.commit()

    return redirect(
        url_for("home")
    )


# =========================================================
# TIMETABLE — CURRENT WEEK
# =========================================================

@app.route("/timetable")
def timetable():

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    # -----------------------------------------------------
    # CURRENT WEEK
    # -----------------------------------------------------

    monday, sunday = get_current_week()

    week_dates = get_week_dates()

    # -----------------------------------------------------
    # CURRENT WEEK ACTIVE ITEMS
    # -----------------------------------------------------

    timetable_items = TimetableItem.query.filter(
        TimetableItem.user_id == user.id,
        TimetableItem.date >= monday,
        TimetableItem.date <= sunday,
        TimetableItem.is_active == True
    ).order_by(
        TimetableItem.date.asc(),
        TimetableItem.start_time.asc()
    ).all()

    # -----------------------------------------------------
    # SAVED WEEK DAYS
    # -----------------------------------------------------

    saved_days = WeeklyDay.query.filter_by(
        user_id=user.id,
        week_start=monday
    ).all()

    saved_day_map = {
        day.weekday: day
        for day in saved_days
    }

    # -----------------------------------------------------
    # CREATE 7 DAY STRUCTURE
    # -----------------------------------------------------

    weekly_timetable = []

    for weekday in range(7):

        calendar_date = (
            monday
            + timedelta(days=weekday)
        )

        saved_day = saved_day_map.get(
            weekday
        )

        selected_date = (
            saved_day.selected_date
            if saved_day
            else None
        )

        # -------------------------------------------------
        # ONLY SHOW TASKS FOR SELECTED DATE
        # -------------------------------------------------

        day_items = []

        if selected_date:

            day_items = [
                item
                for item in timetable_items
                if item.date == selected_date
            ]

        weekly_timetable.append({

            "weekday": weekday,

            "date": selected_date,

            "calendar_date": calendar_date,

            "day_name": calendar_date.strftime(
                "%A"
            ),

            "items": day_items,

            "is_set": (
                selected_date is not None
            )
        })

    return render_template(
        "timetable.html",

        timetable=timetable_items,

        weekly_timetable=weekly_timetable,

        week_start=monday,

        week_end=sunday
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

    history_data = {}

    # -----------------------------------------------------
    # NEW HISTORY RECORDS
    # -----------------------------------------------------

    history_records = TaskHistory.query.filter_by(
        user_id=user.id
    ).order_by(
        TaskHistory.date.desc(),
        TaskHistory.id.desc()
    ).all()

    for record in history_records:

        date_key = record.date

        if date_key not in history_data:

            history_data[date_key] = {
                "total": 0,
                "completed": 0,
                "not_done": 0,
                "pending": 0
            }

        history_data[date_key]["total"] += 1

        if record.status == "done":

            history_data[date_key]["completed"] += 1

        elif record.status == "not_done":

            history_data[date_key]["not_done"] += 1

        else:

            history_data[date_key]["pending"] += 1

    # -----------------------------------------------------
    # LEGACY TASKS THAT WERE NEVER ARCHIVED
    # -----------------------------------------------------

    legacy_tasks = Task.query.filter_by(
        user_id=user.id
    ).all()

    archived_ids = {
        record.original_task_id
        for record in history_records
        if record.original_task_id is not None
    }

    for task in legacy_tasks:

        if task.id in archived_ids:

            continue

        # Current active tasks should not be counted
        # as history.

        if task.is_active:

            continue

        if not task.date:

            continue

        date_key = task.date

        if date_key not in history_data:

            history_data[date_key] = {
                "total": 0,
                "completed": 0,
                "not_done": 0,
                "pending": 0
            }

        history_data[date_key]["total"] += 1

        if task.status == "done":

            history_data[date_key]["completed"] += 1

        elif task.status == "not_done":

            history_data[date_key]["not_done"] += 1

        else:

            history_data[date_key]["pending"] += 1

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
        if task.status == "done"
    )

    remaining_tasks = (
        total_tasks
        - completed_tasks
    )

    overall_progress = 0

    if total_tasks > 0:

        overall_progress = round(
            completed_tasks
            / total_tasks
            * 100
        )

    # =====================================================
    # SUBJECT DATA
    # =====================================================

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

        if task.status == "done":

            subject_data[subject]["completed"] += 1

    for subject, data in subject_data.items():

        if data["total"] > 0:

            data["progress"] = round(
                data["completed"]
                / data["total"]
                * 100
            )

    # =====================================================
    # BEST SUBJECT
    # =====================================================

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

    # =====================================================
    # WEEKLY DATA
    # =====================================================

    weekly_data = {}

    for task in tasks:

        if not task.date:

            continue

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

        if task.status == "done":

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

    # =====================================================
    # STUDY TIME
    # =====================================================

    study_minutes = 0

    for task in tasks:

        if (
            task.status == "done"
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
        if task.status == "done"
    )

    remaining_tasks = (
        total_tasks
        - completed_tasks
    )

    progress = 0

    if total_tasks > 0:

        progress = round(
            completed_tasks
            / total_tasks
            * 100
        )

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
