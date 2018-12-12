# -*- encoding=UTF-8 -*-

from instagram import app, db
from models import Image, User, Comment
from flask import render_template, redirect, request, flash, get_flashed_messages, send_from_directory
import random, hashlib, json, uuid, os
from flask_login import login_user, logout_user, login_required, current_user
from qiniu import Auth, put_data, etag
import qiniu.config
from qiniusdk import qiniu_upload_file


@app.route('/')
def index():
    images = Image.query.order_by(Image.id.desc()).limit(10).all()
    return render_template('index.html', images=images)


@app.route('/image/<int:image_id>')
@login_required
def image(image_id):
    image = Image.query.get(image_id)
    if image == None:
        return redirect('/')
    return render_template('pageDetail.html', image=image)


@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    user = User.query.get(user_id)
    if user == None:
        return redirect('/')
    paginate = Image.query.filter_by(user_id=user_id).paginate(page=1, per_page=3)
    return render_template('profile.html', user=user, images=paginate.items)


@app.route('/profile/images/<int:user_id>/<int:page>/<int:per_page>/')
def user_images(user_id, page, per_page):
    paginate = Image.query.filter_by(user_id=user_id).paginate(page=page, per_page=per_page)
    map = {'has_next': paginate.has_next}
    images = []
    for image in paginate.items:
        imgvo = {'id': image.id, 'url': image.url, 'comment_count': len(image.comments)}
        images.append(imgvo)
    map['images'] = images
    return json.dumps(map)


@app.route('/index/images/<int:page>/<int:per_page>/')
def index_images(page, per_page):
    paginate = Image.query.order_by('id desc').paginate(page=page, per_page=per_page)
    map = {'has_next': paginate.has_next}
    images = []
    for image in paginate.items:
        imgvo = {'id': image.id, 'url': image.url, 'comment_count': len(image.comments),
                 'created_date': str(image.created_date)}
        user = User.query.get(image.user_id)
        imgvo['user'] = {'username': user.username, 'id': user.id, 'head_url': user.head_url}
        comments = Comment.query.filter_by(image_id=image.id).all()
        commentsvo = []
        for comment in comments:
            commentvo = {'id': comment.id, 'content': comment.content}
            commentsvo.append(commentvo)
        imgvo['comments'] = commentsvo
        images.append(imgvo)
    map['images'] = images
    return json.dumps(map)


@app.route('/regloginpage/')
def regloginpage():
    msg = ''
    for m in get_flashed_messages(with_categories=False, category_filter=['reglogin']):
        msg = msg + m
    return render_template('login.html', msg=msg, next=request.values.get('next'))


def redirect_with_msg(target, msg, category):
    if msg != None:
        flash(msg, category=category)
    return redirect(target)


@app.route('/login/', methods={'get', 'post'})
def login():
    username = request.values.get('username').strip()
    password = request.values.get('password').strip()

    if username == '' or password == '':
        return redirect_with_msg('/regloginpage/', u'用户名或密码为空', 'reglogin')

    user = User.query.filter_by(username=username).first()
    if user == None:
        return redirect_with_msg('/regloginpage/', u'用户不存在', 'reglogin')

    m = hashlib.md5()
    m.update(password + user.salt)
    if (m.hexdigest() != user.password):
        return redirect_with_msg('/regloginpage/', u'密码错误', 'reglogin')

    login_user(user)

    next = request.values.get('next')
    if next != None and next.startswith('/'):
        return redirect(next)
    return redirect('/')


@app.route('/reg/', methods=['post', 'get'])
def reg():
    username = request.values.get('username').strip()
    password = request.values.get('password').strip()
    user = User.query.filter_by(username=username).first()

    if username == '' or password == '':
        return redirect_with_msg('/regloginpage/', u'用户名或密码为空', 'reglogin')

    if user != None:
        return redirect_with_msg('/regloginpage/', u'用户名已经存在', 'reglogin')

    salt = '.'.join(random.sample('0123456789abcdefghijklmn', 10))
    m = hashlib.md5()
    m.update(password + salt)
    password = m.hexdigest()
    user = User(username, password, salt)
    db.session.add(user)
    db.session.commit()

    login_user(user)

    next = request.values.get('next')
    if next != None and next.startswith('/'):
        return redirect(next)

    return redirect('/')


@app.route('/logout/')
def logout():
    logout_user()
    return redirect('/')


def save_to_local(file, file_name):
    save_dir = app.config['UPLOAD_DIR']
    file.save(os.path.join(save_dir, file_name))
    return '/image/' + file_name


def save_to_qiniu(file, file_name):
    access_key = app.config['QINIU_ACCESS_KEY']
    secret_key = app.config['QINIU_SECRET_KEY']

    q = Auth(access_key, secret_key)
    # 要上传的空间
    bucket_name = app.config['QINIU_BUCKET_NAME']
    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, file_name)

    ret, info = put_data(token, file_name, file.stream)

    print(type(info.status_code), info)
    if info.status_code == 200:
        return app.config['QINIU_DOMAIN'] + file_name
    return None


@app.route('/upload/', methods={"post"})
def upload():
    file = request.files['file']
    file_ext = ''
    if file.filename.find('.') > 0:
        file_ext = file.filename.rsplit('.')[1].strip().lower()
    if file_ext in app.config['ALLOWED_EXT']:
        file_name = str(uuid.uuid1()).replace('-', '') + '.' + file_ext
        # url = save_to_local(file, file_name)
        url = save_to_qiniu(file, file_name)
        if url != None:
            db.session.add(Image(url, current_user.id))
            db.session.commit()

    return redirect('/profile/%d' % current_user.id)


@app.route('/image/<image_name>')
def view_image(image_name):
    return send_from_directory(app.config['UPLOAD_DIR'], image_name)


@app.route('/addcomment/', methods={'post'})
@login_required
def add_comment():
    image_id = int(request.values['image_id'])
    content = request.values['content']
    comment = Comment(content, image_id, current_user.id)
    db.session.add(comment)
    db.session.commit()
    return json.dumps({"code": 0, "id": comment.id,
                       "content": comment.content,
                       "username": comment.user.username,
                       "user_id": comment.user_id})
