from flask import Flask, render_template, url_for, request, redirect, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
import base64
import json
import os

app = Flask(__name__)
app.json.ensure_ascii = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


UPLOAD_FOLDER = r'C:\Users\Zver\PycharmProjects\Flask_Learning\uploads\\'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'exe',
                      'html', 'css', 'pptx', 'docx', "xlsx", 'py', 'zip',
                      'rar'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Article {self.id}>'


class File(db.Model):
    name = db.Column(db.String(50), nullable=False, primary_key=True)
    password = db.Column(db.String(50), nullable=True)
    length = db.Column(db.Float(10), nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)
    comment = db.Column(db.String(300), nullable=True)

    def __repr__(self):
        return f'<File {self.id}>'


with app.app_context():
    db.create_all()


@app.route('/create-article', methods=['POST', 'GET'])
def create_article():
    if request.method == "POST":
        title = request.form['title']
        intro = request.form['intro']
        text = request.form['text']
        if title == "":
            article = Article(title="Без названия", intro=intro, text=text)
        else:
            article = Article(title=title, intro=intro, text=text)

        try:
            db.session.add(article)
            db.session.commit()
            return redirect('/')
        except Exception as e:
            return f"Ошибка при добавлении статьи: {e}"

    elif request.method == "GET":
        return render_template("post_create.html")


@app.route('/')
def posts():
    articles = Article.query.order_by(Article.date.desc()).all()
    return render_template("posts.html", articles=articles)


@app.route('/news/<int:id>')
def post_detail(id):
    article = Article.query.get(id)
    return render_template("post_detail.html", article=article)


@app.route('/news/<int:id>/del')
def post_delete(id):
    article = Article.query.get_or_404(id)

    try:
        db.session.delete(article)
        db.session.commit()
        return redirect('/')
    except Exception as e:
        return f"Ошибка при удалении статьи: {e}"


@app.route('/news/<int:id>/update', methods=['POST', 'GET'])
def post_update(id):
    article = Article.query.get(id)
    if request.method == "POST":
        article.title = request.form['title']
        article.intro = request.form['intro']
        article.text = request.form['text']

        try:
            db.session.commit()
            return redirect('/')
        except Exception as e:
            return f"Ошибка при редактировании статьи: {e}"

    else:
        article = Article.query.get(id)
        return render_template("post_update.html", article=article)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/files', methods=['POST', 'GET'])
def files_page():
    files = File.query.order_by(File.date.desc()).all()
    if request.method == "POST":
        if 'file' not in request.files:
            return "Не найдено файла"
        file = request.files['file']
        filename = file.filename.replace(" ", "_")
        password = hashlib.sha256((request.form['password'] if request.form['password'] else "").encode()).hexdigest()
        comment = request.form['comment'] if request.form['comment'] else ""

        if file and allowed_file(file.filename):
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            length = round((os.path.getsize(app.config['UPLOAD_FOLDER'] + filename) / 1024 / 1024), 2)
            file_db = File(name=filename, password=password, length=length, comment=comment)
            try:
                db.session.add(file_db)
                db.session.commit()
                return redirect('/files')
            except Exception as e:
                return f"Ошибка при добавлении файла: {e}"

        elif not allowed_file(file.filename):
            return render_template("files.html", files=files, message="Недопустимое расширение файла!")
    else:
        return render_template("files.html", files=files)


@app.route("/files/download/<string:file_name>")
def download_file(file_name):
    return send_file(app.config['UPLOAD_FOLDER'] + file_name, as_attachment=True)


@app.route("/files/delete/<string:file_name>", methods=['GET', 'POST'])
def delete_file(file_name):
    if request.method == 'POST':
        password_delete = request.form['password_delete']
        file = File.query.get(file_name)
        if file.password == hashlib.sha256(password_delete.encode()).hexdigest():
            return redirect(f"/files/delete/{file_name}/accept")
        else:
            return render_template("delete_accept.html", file_name=file_name, message="Неверный пароль!")
    elif request.method == 'GET':
        return render_template("delete_accept.html", file_name=file_name)


@app.route("/files/delete/<string:file_name>/accept")
def remove_file(file_name):
    file = File.query.get_or_404(file_name)

    try:
        db.session.delete(file)
        db.session.commit()
        os.remove(app.config['UPLOAD_FOLDER'] + file_name)
        return redirect('/files')
    except Exception as e:
        return f"Ошибка при удалении файла: {e}"


@app.route('/api/files')
def api_print_files():
    if request.method == 'GET':
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        files_size = [(round((os.path.getsize(app.config['UPLOAD_FOLDER'] + i)) / 1024 / 1024, 2)) for i in files]
        files_dict = {'files': []}
        for i in range(len(files)):
            files_dict['files'].append({'name': files[i], 'size': files_size[i]})
        return jsonify(files_dict)


@app.route("/api/files/<string:file_name>")
def api_get_file(file_name):
    return send_file(app.config['UPLOAD_FOLDER'] + file_name, as_attachment=True)


@app.route('/api/posts')
def api_print_posts():
    articles = Article.query.order_by(Article.date.desc()).all()
    articles_dict = {'posts': []}
    for i in range(len(articles)):
        articles_dict['posts'].append({'title': articles[i].title,
                                        'intro': articles[i].intro,
                                        'text': articles[i].text})
    return jsonify(articles_dict)


if __name__ == "__main__":
    app.run(debug=True)
