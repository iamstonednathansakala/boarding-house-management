from __future__ import annotations

import os
import sqlite3
import tempfile
import uuid
from datetime import date
from typing import Any

from flask import Flask, current_app, flash, g, redirect, render_template, request, url_for

DATABASE = os.path.join(os.path.dirname(__file__), "boarding_house.db")


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        g._database = db
    return db


def init_db():
    with sqlite3.connect(current_app.config["DATABASE"]) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_number TEXT NOT NULL UNIQUE,
                monthly_rent REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                notes TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS residents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                room_id INTEGER,
                move_in TEXT,
                monthly_rent REAL,
                status TEXT NOT NULL DEFAULT 'active',
                FOREIGN KEY(room_id) REFERENCES rooms(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resident_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_date TEXT NOT NULL,
                month TEXT NOT NULL,
                note TEXT,
                FOREIGN KEY(resident_id) REFERENCES residents(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                expense_date TEXT NOT NULL,
                note TEXT
            )
            """
        )

        room_count = db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
        if room_count == 0:
            db.executemany(
                "INSERT INTO rooms (room_number, monthly_rent, status, notes) VALUES (?, ?, ?, ?)",
                [
                    ("A-1", 600.00, "occupied", "Corner room"),
                    ("A-2", 600.00, "occupied", "Front-facing room"),
                    ("A-3", 600.00, "available", "Recently cleaned"),
                    ("A-4", 600.00, "available", "Front Window"),
                    ("B-5", 600.00, "occupied", "Good for single occupant"),
                    ("C-6", 600.00, "occupied", "Bottom Bunker-Door side"),
                    ("C-7", 600.00, "occupied",  "Double-Bed"),
                    ("C-8", 600.00, "occupied",  "Bottom-Bunker"),
                    ("C-9", 600.00, "occupied", "Top-Bunker"),
                    ("D-10", 600.00, "available", "Top-Bunker"),
                ],
            )

        resident_count = db.execute("SELECT COUNT(*) FROM residents").fetchone()[0]
        if resident_count == 0:
            db.executemany(
                "INSERT INTO residents (name, phone, room_id, move_in, monthly_rent, status) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    ("Aisha Rahman", "01710000001", 1, "2025-01-10", 12000.00, "active"),
                    ("Sajid Hossain", "01710000002", 2, "2025-02-12", 11000.00, "active"),
                ],
            )
            db.execute(
                "UPDATE rooms SET status = 'occupied' WHERE id IN (1, 2)"
            )

        payment_count = db.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        if payment_count == 0:
            db.executemany(
                "INSERT INTO payments (resident_id, amount, payment_date, month, note) VALUES (?, ?, ?, ?, ?)",
                [
                    (1, 12000.00, "2026-09-01", "2026-09", "Monthly rent"),
                    (2, 11000.00, "2026-09-03", "2026-09", "Monthly rent"),
                ],
            )

        expense_count = db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        if expense_count == 0:
            db.executemany(
                "INSERT INTO expenses (title, amount, expense_date, note) VALUES (?, ?, ?, ?)",
                [
                    ("Electricity", 2200.00, "2026-09-05", "Common area usage"),
                    ("Cleaning", 1500.00, "2026-09-08", "Monthly service"),
                ],
            )


app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY="board-house-secret",
    DATABASE=DATABASE,
)


@app.teardown_appcontext
def close_db(_error: Any) -> None:
    db = g.pop("_database", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    db = get_db()
    total_rooms = db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    occupied_rooms = db.execute("SELECT COUNT(*) FROM rooms WHERE status = 'occupied'").fetchone()[0]
    available_rooms = db.execute("SELECT COUNT(*) FROM rooms WHERE status = 'available'").fetchone()[0]
    total_residents = db.execute("SELECT COUNT(*) FROM residents").fetchone()[0]
    monthly_collection = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE month = ?",
        (date.today().strftime("%Y-%m"),),
    ).fetchone()[0]
    total_expenses = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses"
    ).fetchone()[0]
    recent_payments = db.execute(
        """
        SELECT p.*, r.name AS resident_name, room.room_number
        FROM payments p
        INNER JOIN residents r ON r.id = p.resident_id
        INNER JOIN rooms room ON room.id = r.room_id
        ORDER BY p.payment_date DESC, p.id DESC
        LIMIT 5
        """
    ).fetchall()
    room_rows = db.execute(
        """
        SELECT r.*, resident.name AS resident_name
        FROM rooms r
        LEFT JOIN residents resident ON resident.room_id = r.id
        ORDER BY r.room_number
        """
    ).fetchall()

    return render_template(
        "index.html",
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        available_rooms=available_rooms,
        total_residents=total_residents,
        monthly_collection=monthly_collection,
        total_expenses=total_expenses,
        recent_payments=recent_payments,
        rooms=room_rows,
    )


@app.route("/rooms", methods=["GET", "POST"])
def rooms():
    db = get_db()

    if request.method == "POST":
        room_number = request.form.get("room_number", "").strip()
        monthly_rent = float(request.form.get("monthly_rent", 0) or 0)
        status = request.form.get("status", "available")
        notes = request.form.get("notes", "").strip()

        if not room_number:
            flash("Room number is required.", "error")
            return redirect(url_for("rooms"))

        db.execute(
            "INSERT INTO rooms (room_number, monthly_rent, status, notes) VALUES (?, ?, ?, ?)",
            (room_number, monthly_rent, status, notes),
        )
        db.commit()
        flash(f"Room {room_number} added successfully.", "success")
        return redirect(url_for("rooms"))

    room_rows = db.execute(
        """
        SELECT r.*, resident.name AS resident_name
        FROM rooms r
        LEFT JOIN residents resident ON resident.room_id = r.id
        ORDER BY r.room_number
        """
    ).fetchall()
    return render_template("rooms.html", rooms=room_rows)


@app.route("/residents", methods=["GET", "POST"])
def residents():
    db = get_db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        room_id = request.form.get("room_id")
        move_in = request.form.get("move_in") or date.today().isoformat()
        monthly_rent = request.form.get("monthly_rent")
        status = request.form.get("status", "active")

        if not name:
            flash("Resident name is required.", "error")
            return redirect(url_for("residents"))

        db.execute(
            "INSERT INTO residents (name, phone, room_id, move_in, monthly_rent, status) VALUES (?, ?, ?, ?, ?, ?)",
            (name, phone or None, int(room_id) if room_id else None, move_in, float(monthly_rent) if monthly_rent else None, status),
        )
        resident_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()[0]
        if room_id:
            db.execute("UPDATE rooms SET status = 'occupied' WHERE id = ?", (int(room_id),))
            db.execute(
                "UPDATE residents SET monthly_rent = (SELECT monthly_rent FROM rooms WHERE id = ?) WHERE id = ?",
                (int(room_id), resident_id),
            )
        db.commit()
        flash(f"Resident {name} added successfully.", "success")
        return redirect(url_for("residents"))

    room_rows = db.execute("SELECT * FROM rooms ORDER BY room_number").fetchall()
    resident_rows = db.execute(
        """
        SELECT resident.*, room.room_number
        FROM residents resident
        LEFT JOIN rooms room ON room.id = resident.room_id
        ORDER BY resident.name
        """
    ).fetchall()
    return render_template("residents.html", residents=resident_rows, rooms=room_rows)


@app.route("/payments", methods=["GET", "POST"])
def payments():
    db = get_db()

    if request.method == "POST":
        resident_id = request.form.get("resident_id")
        amount = float(request.form.get("amount", 0) or 0)
        payment_date = request.form.get("payment_date") or date.today().isoformat()
        month = request.form.get("month") or payment_date[:7]
        note = request.form.get("note", "").strip()

        if not resident_id:
            flash("Please select a resident.", "error")
            return redirect(url_for("payments"))

        db.execute(
            "INSERT INTO payments (resident_id, amount, payment_date, month, note) VALUES (?, ?, ?, ?, ?)",
            (int(resident_id), amount, payment_date, month, note),
        )
        db.commit()
        flash("Payment recorded successfully.", "success")
        return redirect(url_for("payments"))

    resident_rows = db.execute("SELECT * FROM residents ORDER BY name").fetchall()
    payment_rows = db.execute(
        """
        SELECT p.*, r.name AS resident_name, room.room_number
        FROM payments p
        INNER JOIN residents r ON r.id = p.resident_id
        INNER JOIN rooms room ON room.id = r.room_id
        ORDER BY p.payment_date DESC, p.id DESC
        """
    ).fetchall()
    return render_template("payments.html", residents=resident_rows, payments=payment_rows)


@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    db = get_db()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount = float(request.form.get("amount", 0) or 0)
        expense_date = request.form.get("expense_date") or date.today().isoformat()
        note = request.form.get("note", "").strip()

        if not title:
            flash("Expense title is required.", "error")
            return redirect(url_for("expenses"))

        db.execute(
            "INSERT INTO expenses (title, amount, expense_date, note) VALUES (?, ?, ?, ?)",
            (title, amount, expense_date, note),
        )
        db.commit()
        flash("Expense added successfully.", "success")
        return redirect(url_for("expenses"))

    expense_rows = db.execute(
        "SELECT * FROM expenses ORDER BY expense_date DESC, id DESC"
    ).fetchall()
    return render_template("expenses.html", expenses=expense_rows)


@app.route("/residents/<int:resident_id>/delete", methods=["POST"])
def delete_resident(resident_id: int):
    db = get_db()
    room_assignment = db.execute(
        "SELECT room_id FROM residents WHERE id = ?",
        (resident_id,),
    ).fetchone()

    if room_assignment and room_assignment["room_id"] is not None:
        db.execute(
            "UPDATE rooms SET status = 'available' WHERE id = ?",
            (room_assignment["room_id"],),
        )

    db.execute("DELETE FROM payments WHERE resident_id = ?", (resident_id,))
    db.execute("DELETE FROM residents WHERE id = ?", (resident_id,))
    db.commit()
    flash("Resident deleted successfully.", "success")
    return redirect(url_for("residents"))


@app.route("/payments/<int:payment_id>/delete", methods=["POST"])
def delete_payment(payment_id: int):
    db = get_db()
    db.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    db.commit()
    flash("Payment deleted successfully.", "success")
    return redirect(url_for("payments"))


def create_app(test_config: dict | None = None):
    app.config.from_mapping(
        SECRET_KEY="board-house-secret",
        DATABASE=DATABASE,
    )
    if test_config:
        app.config.update(test_config)
    if app.config.get("TESTING"):
        app.config["DATABASE"] = os.path.join(
            tempfile.gettempdir(),
            f"bhms_test_{uuid.uuid4().hex}.db",
        )
    with app.app_context():
        init_db()
    return app


create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
