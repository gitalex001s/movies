import uuid, os, hashlib, pymysql
from flask import Flask, request, render_template, redirect, session, flash, abort, url_for, jsonify
app = Flask(__name__)

# Register the setup page and import create_connection()
from utils import create_connection, setup
app.register_blueprint(setup)


@app.route('/')
def home():
    return render_template("index.html")

@app.before_request
def restrict():
    restricted_pages = [
        'list_students',
        'view_students',
        'edit_students',
        'delete_students'
    ]
    if 'logged_in' not in session and request.endpoint in restricted_pages:
        return redirect('/login')

@app.route('/addsubject', methods=['GET', 'POST'])
def subject_add():
    if request.method == 'POST':

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO subjects
                    (subject_name, subject_code, year)
                    VALUES (%s, %s, %s)
                """
                values = (
                    request.form['subject_name'],
                    request.form['subject_code'],
                    request.form['year']
                )
                try:
                    cursor.execute(sql, values)
                    connection.commit()
                except pymysql.err.IntegrityError:
                    flash('taken')
                    return redirect(url_for('subject_add'))
        return redirect('/')
    return render_template('subject_add.html')

@app.route('/student_add', methods=['GET', 'POST'])
def student_add():
    if request.method == 'POST':

        password = request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO students
                    (first_name, last_name, email, password)
                    VALUES (%s, %s, %s, %s)
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    encrypted_password
                )
                try:
                    cursor.execute(sql, values)
                    connection.commit()
                    sql = "SELECT * FROM students WHERE email=%s AND password=%s"
                    values = (
                        request.form['email'], 
                        encrypted_password
                    )
                    cursor.execute(sql, values)
                    result = cursor.fetchone()
                    session['logged_in'] = True
                    session['first_name'] = result['first_name']
                    session['role'] = result['role']
                    session['id'] = result['id']
                except pymysql.err.IntegrityError:
                    flash('email is taken!')
                    return redirect(url_for('student_add'))
        return redirect('/')
    return render_template('students_add.html')

@app.route('/dashboard')
def list_students():
    if session['role'] != 'admin':
        flash("admin only.")
        return abort(404)
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM students")
            result = cursor.fetchall()
    return render_template('students_list.html', result=result)

@app.route('/subjects')
def list_subjects():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM subjects")
            result = cursor.fetchall()
    return render_template('subject_list.html', result=result)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM students WHERE email=%s AND password=%s"
                values = (
                    request.form['email'], 
                    encrypted_password
                    )
                cursor.execute(sql, values)
            result = cursor.fetchone()
        if result:
            session['logged_in'] = True
            session['first_name'] = result['first_name']
            session['role'] = result['role']
            session['id'] = result['id']
            return redirect("/")
        else:
            flash("wrong!")
            return redirect("/login")
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/view')
def view_students():
    if session['role'] != 'admin' and str(session['id']) != request.args['id']:
        flash("unauthorise!")
        return redirect("/")
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM students WHERE id=%s", request.args['id'])
            result = cursor.fetchone()
    return render_template('students_view.html', result=result)

@app.route('/delete')
def delete_student():
    if session['role'] != 'admin':
        error_message=("NO")
        flash(error_message)
        return redirect('/')
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM students WHERE id=%s", request.args['id'])
            connection.commit()
    return redirect('/dashboard')

@app.route('/removesub')
def delete_subject():
    if session['role'] != 'admin':
        error_message=("NO")
        flash(error_message)
        return redirect('/')
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM subjects WHERE id=%s", request.args['id'])
            connection.commit()
    return redirect('/subjects')


@app.route('/checkemail')
def check_email():
    return jsonify({ status: 'OK'})

@app.route('/select')
def select():

    if session['role'] != 'admin' and str(session['id']) != request.args['students_id']:
        return abort(404)

    with create_connection() as connection:
        with connection.cursor() as cursor:   
            sql = "INSERT INTO student_subjects (idstudent,idsubject) VALUES (%s,%s)"
            values = (
                request.args['students_id'],
                request.args['subjects_id']
            )
            cursor.execute(sql,values)
            connection.commit()
    return redirect(url_for('list_subject_selections',id=request.args['students_id'] ))


# Remove a subject that has been selected
@app.route('/unselect')
def unselect():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "DELETE FROM student_subjects WHERE id = %s"
            values = (
                request.args['id']
            )
            cursor.execute(sql, values)
            connection.commit()
            return redirect(url_for('list_subject_selections', id=session['id']))


#edit a user
@app.route('/edit', methods=['GET', 'POST'])
def edit_student():
    if session['role'] != 'admin' and str(session['id']) != request.args['id']:
        flash("unauthorise!")
        return redirect('/')
    if request.method == 'POST':

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """UPDATE students SET
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    password = %s
                WHERE id = %s"""
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    request.form['password'],
                    request.form['id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/view?id=' + request.form['id'])
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM students WHERE id = %s", request.args['id'])
                result = cursor.fetchone()
        return render_template('students_edit.html', result=result)


@app.route('/edits', methods=['GET', 'POST'])
def edit_subject():
    if session['role'] != 'admin':
        flash("unauthorise!")
        return redirect(url_for('/'))
    if request.method == 'POST':

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """UPDATE subjects SET
                    subject_name = %s,
                    subject_code = %s,
                    year = %s
                WHERE id = %s"""
                values = (
                    request.form['subject_name'],
                    request.form['subject_code'],
                    request.form['year'],
                    request.form['id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/subjects')
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM subjects WHERE id = %s", request.args['id'])
                result = cursor.fetchone()
        return render_template('subject_edit.html', result=result)

# Subject Selection


# View students subject choices
@app.route('/subjectchoices')
def list_subject_selections():
    if 'logged_in' not in session:
        return redirect('/login')
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """
                            SELECT
	                student_subjects.id, 
	                student_subjects.idsubject, 
	                student_subjects.idstudent, 
	                subjects.subject_name, 
	                subjects.subject_code, 
	                subjects.`year`
                FROM
	                student_subjects
	                INNER JOIN
	                subjects
	                ON 
		                student_subjects.idsubject = subjects.id
                WHERE
	                student_subjects.idstudent = %s
            """
    
            cursor.execute(sql, request.args['id'])
            result = cursor.fetchall()
    return render_template('students_subject_selection.html', result=result)

if __name__ == '__main__':
    import os

    # This is required to allow flashing messages. We will cover this later.
    app.secret_key = os.urandom(32)

    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)
