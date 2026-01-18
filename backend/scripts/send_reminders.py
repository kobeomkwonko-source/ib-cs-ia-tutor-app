import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from server import create_app
from server.db import get_db


WINDOW_MINUTES = 60


def send_email(to_address: str, subject: str, body: str, config):
    if not config["SMTP_USER"] or not config["SMTP_PASSWORD"]:
        raise RuntimeError("SMTP credentials are not configured.")

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = config["SMTP_SENDER"]
    message["To"] = to_address

    with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"]) as server:
        server.starttls()
        server.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
        server.sendmail(config["SMTP_SENDER"], [to_address], message.as_string())


def fetch_due_tasks(conn, now_kst, hours_before):
    cursor = conn.cursor()
    window_start = now_kst + timedelta(hours=hours_before) - timedelta(minutes=WINDOW_MINUTES)
    window_end = now_kst + timedelta(hours=hours_before)
    cursor.execute(
        """
        SELECT id, title, deadline
        FROM tasks
        WHERE deadline BETWEEN %s AND %s
        """,
        (window_start.strftime("%Y-%m-%d %H:%M:%S"), window_end.strftime("%Y-%m-%d %H:%M:%S")),
    )
    tasks = cursor.fetchall()
    cursor.close()
    return tasks


def student_has_submission(conn, task_id, student_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM submissions WHERE task_id = %s AND student_id = %s LIMIT 1",
        (task_id, student_id),
    )
    row = cursor.fetchone()
    cursor.close()
    return row is not None


def reminder_already_sent(conn, task_id, student_id, reminder_type):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM reminder_logs
        WHERE task_id = %s AND student_id = %s AND reminder_type = %s
        """,
        (task_id, student_id, reminder_type),
    )
    row = cursor.fetchone()
    cursor.close()
    return row is not None


def log_reminder(conn, task_id, student_id, reminder_type):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reminder_logs (task_id, student_id, reminder_type)
        VALUES (%s, %s, %s)
        """,
        (task_id, student_id, reminder_type),
    )
    conn.commit()
    cursor.close()


def load_assigned_students(conn, task_id):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.id, u.username, u.email
        FROM task_assignments a
        JOIN users u ON u.id = a.student_id
        WHERE a.task_id = %s AND u.email IS NOT NULL
        """,
        (task_id,),
    )
    students = cursor.fetchall()
    cursor.close()
    return students


def main():
    app = create_app()
    with app.app_context():
        config = app.config
        now_kst = datetime.utcnow() + timedelta(hours=config["KST_OFFSET_HOURS"])
        conn = get_db()

        
        for hours_before, reminder_type in ((24, "24h"), (12, "12h")):
            tasks = fetch_due_tasks(conn, now_kst, hours_before)
            for task in tasks:
                students = load_assigned_students(conn, task["id"])
                for student in students:
                    if student_has_submission(conn, task["id"], student["id"]):
                        continue
                    if reminder_already_sent(conn, task["id"], student["id"], reminder_type):
                        continue

                    subject = f"Homework reminder: {task['title']}"
                    body = (
                        f"Hi {student['username']},\n\n"
                        f"Reminder: '{task['title']}' is due at {task['deadline']} (KST).\n"
                        "Please submit before the deadline.\n"
                    )
                    send_email(student["email"], subject, body, config)
                    log_reminder(conn, task["id"], student["id"], reminder_type)

        conn.close()


if __name__ == "__main__":
    main()
