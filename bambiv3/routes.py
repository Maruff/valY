import os
from datetime import datetime
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from bambiv3 import app, db, bcrypt, mail
from bambiv3.forms import RegistrationForm, LoginForm, UpdateAccountForm, MessageForm, PostForm, HomeForm, CommentForm, ProductForm, RequestResetForm, ResetPasswordForm
from bambiv3.models import User, Post, Product, Message as m, Comment
from bambiv3.functions import profile_img, market_img, post_img
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message


@app.before_request
def before_request():
	if current_user.is_authenticated:
		current_user.last_seen = datetime.utcnow()
		db.session.commit()

@app.route('/layout')
def layout():
	users = User.query.all()
	return render_template('layout.html', users=users)


@app.route('/')
@app.route('/home', methods=['GET', 'POST'])
def home():
	form = HomeForm()
	if form.validate_on_submit():
		if form.image.data:
			picture = post_img(form.image.data)
			post = Post(title=form.title.data, content=form.content.data, anonymous=form.anonymous.data, image=picture, author=current_user)
		else:
			post = Post(title=form.title.data, content=form.content.data, anonymous=form.anonymous.data, author=current_user)
		db.session.add(post)
		db.session.commit()
		flash('Your Post Has been Created!', 'success')
		return redirect(url_for('home'))
	page = request.args.get('page', 1, type=int)
	posts = Post.query.order_by(Post.date_posted.desc()).paginate(per_page=50, page=page)
	users = User.query.all()
	suggested_friends = set()
	for user in users:
		if user != current_user and current_user.is_authenticated and not current_user.is_following(user):
			suggested_friends.add(user)
	if current_user.is_authenticated:
		image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
		hour = datetime.now().hour
		greeting = "Good morning" if 5<=hour<12 else "Good afternoon" if hour<18 else "Good evening"
		return render_template('home.html', title="Home", form=form, posts=posts, image_file=image_file, users=users, greeting=greeting, suggested_friends=suggested_friends)
	else:
		#return redirect(url_for('login'))
		return render_template('home.html', title="Home", posts=posts)

@app.route('/friends/posts')
@login_required
def f_posts():
	page = request.args.get('page', 1, type=int)
	posts = current_user.followed_posts().paginate(per_page=50, page=page)
	users = User.query.all()
	suggested_friends = set()
	for user in users:
		if user != current_user and  not current_user.is_following(user):
			suggested_friends.add(user)
	return render_template('friends_posts.html', title="Friend Posts", posts=posts, users=users, suggested_friends=suggested_friends)


@app.route('/blog')
def blog():
	return redirect("https://medium.com/@bambii", code=302)

@app.route('/about')
def about():
	return render_template('about.html', title="About")

@app.route('/me')
def portfolio():
	return redirect("https://harunmohamed.github.io/me/", code=302)

@app.route('/ecc102')
def ecc102():
	return render_template('ecc102.html', title="Programming and Problem Solving")

@app.route('/market', methods=['GET', 'POST'])
def market():
	p = Product.query.order_by(Product.date_posted.desc())
	products = set()
	for product in p:
			products.add(product)
	return render_template('market.html', title="Market", products=products)

@app.route('/inbox')
def inbox():
	return render_template('inbox.html', title="Inbox")

@app.route('/photos')
@login_required
def photos():
	photos = set()
	posts = Post.query.all()
	for post in posts:
		if post.image:
			photos.add(post)
	return render_template('images.html', photos=photos, title="Photos")

@app.route('/anonymous')
@login_required
def anonymous():
	users = User.query.all()
	anonymous = set()
	posts = Post.query.all()
	for post in posts:
		if post.anonymous:
			anonymous.add(post)
	return render_template('anonymous.html', users=users, anonymous=anonymous, title="Anonymous")

@app.route('/m/<recipient>', methods=['GET', 'POST'])
@login_required
def message(recipient):
	current_user.last_message_read_time = datetime.utcnow()
	db.session.commit()
	recipient = recipient.lower()
	user = User.query.filter_by(username=recipient).first_or_404()
	current_user.last_message_read_time = datetime.utcnow()
	db.session.commit()
	#if user == current_user:
		#return redirect(url_for('messages'))
	form = MessageForm()
	if form.validate_on_submit():
		msg = m(author=current_user, recipient=user, body=form.message.data)
		db.session.add(msg)
		db.session.commit()
		flash('Your message has been sent.', 'success')
		return redirect(url_for('message', recipient=recipient))
	sent = current_user.messages_sent.filter_by(recipient_id=user.id)
	received = current_user.messages_received.filter_by(sender_id=user.id)
	messages = sent.union(received).order_by(m.timestamp.asc())

	#adding all names of people who texted me to recent chats
	messages_received = current_user.messages_received.order_by(m.timestamp.desc())
	messages_sent = current_user.messages_sent.order_by(m.timestamp.desc())
	recent_chats = list()
	for message in messages_received:
		recent_chats.append(message.author)
	for message in messages_sent:
		recent_chats.append(message.recipient)
	recent_chats = list(dict.fromkeys(recent_chats))

	return render_template('send_message.html', recipient=recipient, title="Chat with " + recipient.title() , user=user, form=form, messages=messages, recent_chats=recent_chats)


@app.route('/messages')
@login_required
def messages():
	current_user.last_message_read_time = datetime.utcnow()
	db.session.commit()
	messages_received = current_user.messages_received.order_by(m.timestamp.desc())
	messages_sent = current_user.messages_sent.order_by(m.timestamp.desc())

	#recent chats
	recent_chats = list()
	for message in messages_received:
		recent_chats.append(message.author)
	for message in messages_sent:
		recent_chats.append(message.recipient)
	recent_chats = list(dict.fromkeys(recent_chats))

	users = User.query.all()
	hour = datetime.now().hour
	greeting = "Good morning" if 5<=hour<12 else "Good afternoon" if hour<18 else "Good evening"
	return render_template('messages.html', users=users, greeting=greeting, recent_chats=recent_chats, messages_sent=messages_sent, messages_received=messages_received)

@app.route('/inbox/demo')
def chat():
	return render_template('inbox_preview.html', title="Chat")

@app.route('/discover')
@login_required
def discover():
	users = User.query.all()
	suggested_friends = set()
	for user in users:
		if user != current_user and  not current_user.is_following(user):
			suggested_friends.add(user)
	return render_template('discover.html', users=users, title='Discover', suggested_friends=suggested_friends)

@app.route('/swipe')
def swipe():
	users = User.query.all()
	return render_template('swipe.html', users=users)

@app.route('/explore')
def explore():
	return render_template('explore.html', title="Explore")

@app.route('/dating')
def dating():
	return redirect("https://neudating.herokuapp.com/", code=302)
	#return render_template('36.html', title="Dating")

@app.route('/register', methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = RegistrationForm()
	if form.validate_on_submit():
		hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		user = User(username=form.username.data.lower(), email=form.email.data, department=form.department.data,\
			student_number=form.student_number.data, gender=form.gender.data, age=form.age.data, country=form.country.data, hobby=form.hobby.data,\
			password=hashed_password)
		db.session.add(user)
		db.session.commit()
		flash(f'Account Created for {form.username.data}! You can now log in', 'success')
		return redirect(url_for('login'))
	return render_template('register.html', title="Register", form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data.lower()).first()
		if user and bcrypt.check_password_hash(user.password, form.password.data):
			login_user(user, remember=form.remember.data)
			next_page = request.args.get('next')
			return redirect(next_page) if next_page else redirect(url_for('home'))
		else:
			flash(f'Login Unsuccesful! Please try again.', 'danger')
	return render_template('login.html', title="Login", form=form)


@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('login'))

@app.route('/todo')
def todo():
	return render_template('todo.html')

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
	form = UpdateAccountForm()
	if form.validate_on_submit():
		if form.picture.data:
			picture_file = profile_img(form.picture.data)
			current_user.image_file = picture_file
		current_user.username = form.username.data.lower()
		current_user.email = form.email.data
		current_user.department = form.department.data
		current_user.student_number = form.student_number.data
		current_user.country = form.country.data
		current_user.age = form.age.data
		current_user.hobby = form.hobby.data
		db.session.commit()
		flash('Your Account has been updated', 'success')
		return redirect(url_for('account'))
	elif request.method == 'GET':
		form.username.data = current_user.username
		form.email.data = current_user.email
		form.department.data = current_user.department
		form.student_number.data = current_user.student_number
		form.country.data = current_user.country
		form.age.data = current_user.age
		form.hobby.data = current_user.hobby
	image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
	return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
	form = PostForm()
	if form.validate_on_submit():
		if form.image.data:
			picture = post_img(form.image.data)
			post = Post(title=form.title.data, content=form.content.data,anonymous=form.anonymous.data, image=picture, author=current_user)
			db.session.add(post)
			db.session.commit()
			flash('Your Post Has been Created!', 'success')
			return redirect(url_for('home'))
		else:
			post = Post(title=form.title.data, content=form.content.data,anonymous=form.anonymous.data, author=current_user)
			db.session.add(post)
			db.session.commit()
			flash('Your Post Has been Created!', 'success')
			return redirect(url_for('home'))
	return render_template('create_post.html', title='New Post', form=form)

@app.route('/post/<int:post_id>', methods=["GET", "POST"])
@login_required
def post(post_id):
	post = Post.query.get_or_404(post_id)
	users = User.query.all()
	form = CommentForm()
	if form.validate_on_submit():
		comment = Comment(body=form.body.data, post=post, author=current_user)
		db.session.add(comment)
		db.session.commit()
		flash('Your comment has been published.')
		return redirect(url_for('post', post_id=post.id))
	return render_template('post.html',title=post.title, post=post, form=form, users=users)

@app.route('/like/<int:post_id>/<action>')
@login_required
def like_action(post_id, action):
	post = Post.query.filter_by(id=post_id).first_or_404()
	if action == 'like':
		current_user.like_post(post)
		db.session.commit()
	if action == 'unlike':
		current_user.unlike_post(post)
		db.session.commit()
	return redirect(request.referrer)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
	post = Post.query.get_or_404(post_id)
	if post.author != current_user:
		abort(403)
	form = PostForm()
	if form.validate_on_submit():
		post.title = form.title.data
		post.content = form.content.data
		if form.image.data:
			post.image = post_img(form.image.data)
		db.session.commit()
		flash('Your post has been updated!', 'success')
		return redirect(url_for('post', post_id=post.id))
	elif request.method == 'GET':
		form.title.data = post.title
		form.content.data = post.content
		form.image.data = post.image
	return render_template('create_post.html', title='Update Post',
						   form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
	post = Post.query.get_or_404(post_id)
	if post.author != current_user:
		abort(403)
	db.session.delete(post)
	db.session.commit()
	flash('Your post has been deleted!', 'success')
	return redirect(request.referrer)


@app.route('/product/new', methods=['GET', 'POST'])
@login_required
def new_product():
	form = ProductForm()
	if form.validate_on_submit():
			picture1 = market_img(form.image1.data)
			product = Product(title=form.title.data, description=form.description.data, location=form.location.data, price=form.price.data, contact=form.contact.data, image1=picture1, author=current_user)
			db.session.add(product)
			db.session.commit()
			flash('Your Product Has been Posted!', 'success')
			return redirect(url_for('market'))
	return render_template('create_product.html', title='New Product', form=form, legend='New Product')

@app.route("/product/<int:product_id>/delete", methods=['POST'])
@login_required
def delete_product(product_id):
	product = Product.query.get_or_404(product_id)
	if product.author != current_user:
		abort(403)
	db.session.delete(product)
	db.session.commit()
	flash('Your product has been deleted!', 'success')
	return redirect(request.referrer)

@app.route("/<string:username>/likes", methods=['GET', 'POST'])
@login_required
def likes(username):
	username = username.lower()
	user = User.query.filter_by(username=username).first_or_404()
	posts = Post.query.order_by(Post.date_posted.desc())
	users = User.query.all()
	liked_people = set()
	for post in posts:
		if user.has_liked_post(post):
			liked_people.add(post.author)
	return render_template('user_likes.html', user=user, posts=posts, users=users, liked_people=liked_people, title= user.username.title() + "'s Likes")



@app.route("/user/<string:username>", methods=['GET', 'POST'])
def user_posts(username):
	username = username.lower()
	if current_user.is_authenticated:
		form = UpdateAccountForm()
		if form.validate_on_submit():
			if form.picture.data:
				picture_file = profile_img(form.picture.data)
				current_user.image_file = picture_file
			current_user.username = form.username.data.lower()
			current_user.email = form.email.data
			current_user.snapchat = form.snapchat.data
			current_user.instagram = form.instagram.data
			current_user.department = form.department.data
			current_user.student_number = form.student_number.data
			current_user.country = form.country.data
			current_user.age = form.age.data
			current_user.hobby = form.hobby.data
			current_user.bio = form.bio.data
			current_user.private = form.private.data
			current_user.single = form.single.data
			db.session.commit()
			flash('Your Account has been updated', 'success')
			return redirect(url_for('user_posts', username=current_user.username))
		elif request.method == 'GET':
			form.username.data = current_user.username
			form.email.data = current_user.email
			form.snapchat.data = current_user.snapchat
			form.instagram.data = current_user.instagram
			form.department.data = current_user.department
			form.student_number.data = current_user.student_number
			form.country.data = current_user.country
			form.age.data = current_user.age
			form.hobby.data = current_user.hobby
			form.bio.data = current_user.bio
			form.private.data = current_user.private
			form.single.data = current_user.single
		image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
		page = request.args.get('page', 1, type=int)
		user = User.query.filter_by(username=username).first_or_404()
		users = User.query.all()
		posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).paginate(page=page, per_page=10)
		post_images = Post.query.order_by(Post.date_posted.desc())
		return render_template('user_posts.html', posts=posts, post_images=post_images, user=user, users=users, title=user.username.title(),image_file=image_file,form=form)
	page = request.args.get('page', 1, type=int)
	user = User.query.filter_by(username=username).first_or_404()
	posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).paginate(page=page, per_page=10)
	post_images = Post.query.order_by(Post.date_posted.desc())
	return render_template('user_posts.html', posts=posts, post_images=post_images, user=user, title=user.username.title())


@app.route("/<string:username>", methods=['GET', 'POST'])
def user(username):
	return redirect(url_for('user_posts', username=username))

@app.route('/follow/<username>')
@login_required
def follow(username):
	username = username.lower()
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('User {} not found.'.format(username))
		return redirect(url_for('index'))
	if user == current_user:
		flash('You cannot follow yourself!', 'danger')
		return redirect(request.referrer)
	current_user.follow(user)
	db.session.commit()
	flash('💛 You are following {}!'.format(username.title()), 'success')
	return redirect(request.referrer)


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
	username = username.lower()
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('User {} not found.'.format(username))
		return redirect(url_for('index'))
	if user == current_user:
		flash('You cannot unfollow yourself!', 'danger')
		return redirect(url_for('user_posts', username=username))
	current_user.unfollow(user)
	db.session.commit()
	flash('💔 You are not following {}.'.format(username.title()), 'info')
	return redirect(url_for('user_posts', username=username))


def send_reset_email(user):
	token = user.get_reset_token()
	msg = Message('Password Reset Request', sender="BAMBI", recipients=[user.email])
	msg.body = f"""To reset your Bambi Password, visit the following link:

	{url_for('reset_token', token=token, _external=True)}

	If you did not make this request, simply ignore this email and no changes will be made.
	"""
	mail.send(msg)


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = RequestResetForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		send_reset_email(user)
		flash('An email has been set with instructions to reset your password','info')
		return redirect(url_for('login'))
	return render_template('reset_request.html', title='Reset Password', form=form)

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	user = User.verify_reset_token(token)
	if user is None:
		flash('That is an invalid or expired token', 'danger')
		return redirect(url_for('reset_request'))
	form = ResetPasswordForm()
	if form.validate_on_submit():
		hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		user.password = hashed_password
		db.session.commit()
		flash('Your password has been updated! You are now able to log in', 'success')
		return redirect(url_for('login'))
	return render_template('reset_token.html', title='Reset Password', form=form)


#Error Handlers
@app.errorhandler(404)
def not_found_error(error):
	return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden_route_error(error):
	return render_template('403.html'), 403

@app.errorhandler(500)
def internal_error(error):
	db.session.rollback()
	return render_template('500.html'), 500
