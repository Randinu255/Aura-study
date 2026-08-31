from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()


# =========================================================
# USER
# =========================================================

class User(db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    email_verified = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    verification_code = db.Column(
        db.String(10),
        nullable=True
    )

    verification_expires_at = db.Column(
        db.DateTime,
        nullable=True
    )

    verification_sent_at = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # -----------------------------------------------------
    # RELATIONSHIPS
    # -----------------------------------------------------

    timetable_items = db.relationship(
        "TimetableItem",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    tasks = db.relationship(
        "Task",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    history_records = db.relationship(
        "TaskHistory",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    weekly_days = db.relationship(
        "WeeklyDay",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


# =========================================================
# WEEKLY DAY
# =========================================================
#
# Current week's 7-day planner.
#
# weekday:
# Monday    = 0
# Tuesday   = 1
# Wednesday = 2
# Thursday  = 3
# Friday    = 4
# Saturday  = 5
# Sunday    = 6
#
# Each user can set a date once for each weekday.
#
# Example:
#
# Monday
# 2026-08-31
#
# Then all tasks added from Monday automatically
# receive that date.
#
# =========================================================

class WeeklyDay(db.Model):

    __tablename__ = "weekly_days"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # -----------------------------------------------------
    # WEEK IDENTIFIER
    # -----------------------------------------------------

    week_start = db.Column(
        db.Date,
        nullable=False
    )

    # -----------------------------------------------------
    # WEEKDAY NUMBER
    # -----------------------------------------------------

    weekday = db.Column(
        db.Integer,
        nullable=False
    )

    # -----------------------------------------------------
    # SELECTED DATE
    # -----------------------------------------------------

    selected_date = db.Column(
        db.Date,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# TIMETABLE ITEM
# =========================================================

class TimetableItem(db.Model):

    __tablename__ = "timetable_items"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    date = db.Column(
        db.Date,
        nullable=False
    )

    # -----------------------------------------------------
    # STUDY INFORMATION
    # -----------------------------------------------------

    subject = db.Column(
        db.String(100),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    # -----------------------------------------------------
    # TIME
    # -----------------------------------------------------

    start_time = db.Column(
        db.String(10),
        nullable=False
    )

    end_time = db.Column(
        db.String(10),
        nullable=False
    )

    duration_minutes = db.Column(
        db.Integer,
        nullable=True
    )

    # -----------------------------------------------------
    # EXTRA INFORMATION
    # -----------------------------------------------------

    priority = db.Column(
        db.String(20),
        default="normal"
    )

    notes = db.Column(
        db.Text,
        nullable=True
    )

    # -----------------------------------------------------
    # WEEKDAY
    # -----------------------------------------------------

    weekday = db.Column(
        db.Integer,
        nullable=True
    )

    # -----------------------------------------------------
    # ACTIVE / ARCHIVED
    # -----------------------------------------------------

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# TASK
# =========================================================

class Task(db.Model):

    __tablename__ = "tasks"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # -----------------------------------------------------
    # CONNECTION TO TIMETABLE
    # -----------------------------------------------------

    timetable_item_id = db.Column(
        db.Integer,
        db.ForeignKey("timetable_items.id"),
        nullable=True
    )

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    date = db.Column(
        db.Date,
        nullable=False
    )

    # -----------------------------------------------------
    # TASK INFORMATION
    # -----------------------------------------------------

    subject = db.Column(
        db.String(100),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    # -----------------------------------------------------
    # OLD COMPATIBILITY FIELD
    # -----------------------------------------------------

    completed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    status = db.Column(
        db.String(20),
        default="pending",
        nullable=False
    )

    # -----------------------------------------------------
    # COMPLETION
    # -----------------------------------------------------

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # -----------------------------------------------------
    # WEEKDAY
    # -----------------------------------------------------

    weekday = db.Column(
        db.Integer,
        nullable=True
    )

    # -----------------------------------------------------
    # ACTIVE TASK
    # -----------------------------------------------------

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# TASK HISTORY
# =========================================================

class TaskHistory(db.Model):

    __tablename__ = "task_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # -----------------------------------------------------
    # USER
    # -----------------------------------------------------

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # -----------------------------------------------------
    # ORIGINAL TASK
    # -----------------------------------------------------

    original_task_id = db.Column(
        db.Integer,
        nullable=True
    )

    # -----------------------------------------------------
    # ORIGINAL TIMETABLE ITEM
    # -----------------------------------------------------

    timetable_item_id = db.Column(
        db.Integer,
        nullable=True
    )

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    date = db.Column(
        db.Date,
        nullable=False
    )

    # -----------------------------------------------------
    # WEEKDAY
    # -----------------------------------------------------

    weekday = db.Column(
        db.Integer,
        nullable=True
    )

    # -----------------------------------------------------
    # TASK INFORMATION
    # -----------------------------------------------------

    subject = db.Column(
        db.String(100),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    # -----------------------------------------------------
    # TIME
    # -----------------------------------------------------

    start_time = db.Column(
        db.String(10),
        nullable=True
    )

    end_time = db.Column(
        db.String(10),
        nullable=True
    )

    duration_minutes = db.Column(
        db.Integer,
        nullable=True
    )

    # -----------------------------------------------------
    # FINAL STATUS
    # -----------------------------------------------------

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
    )

    # -----------------------------------------------------
    # COMPLETION
    # -----------------------------------------------------

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # -----------------------------------------------------
    # ARCHIVED TIME
    # -----------------------------------------------------

    archived_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # -----------------------------------------------------
    # NOTES
    # -----------------------------------------------------

    notes = db.Column(
        db.Text,
        nullable=True
    )
