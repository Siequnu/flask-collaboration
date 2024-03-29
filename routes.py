from flask import render_template, flash, redirect, url_for, request, abort, current_app, session, Response, send_from_directory, make_response
from flask_login import current_user, login_required

from . import bp, models
from .models import Firepad, Collab

from app import db
from datetime import datetime
from app.models import User, Enrollment, Turma
import app.models

# Render this blueprint's javascript
@bp.route("/js/<filename>")
@login_required
def js(filename):
	filepath = 'js/' + filename
	response = make_response(render_template(filepath))
	response.headers['Content-type'] = 'text/javascript'
	return response

# Collaboration home page
@bp.route("/")
@login_required
def collaboration_index():
	# Get list of owned pads and pads we are collaborating on
	firepads = models.get_user_owned_firepads()
	collabs = models.get_user_collaborating_firepads()
	return render_template('collaboration_index.html', firepads = firepads, collabs = collabs)


# Create new firepad as owner
@bp.route("/new")
@login_required
def create_new_firepad():
	# Create a new firepad in the DB and redirect to the newly created pad
	firepad = models.create_new_firepad()
	return redirect(url_for('collaboration.collaborate', firepad_id = firepad.id))


# Display a firepad and collaborate online
from flask_talisman import Talisman, ALLOW_FROM
from app import talisman
# Build temporary expanded content security policy
temp_csp = {
        'default-src': [
			'*',
			'\'self\'',
            '\'unsafe-inline\'',
            'cdnjs.cloudflare.com',
            'fonts.googleapis.com',
            'fonts.gstatic.com',
            '*.w3.org',
            'kit-free.fontawesome.com'
        ],
        'img-src': '*',
		'connect-src': '*',
		'font-src': [
			'*',
			'\'self\'',
            'data:',
			'\'unsafe-inline\'',
			'\'unsafe-eval\'',
            'ajax.googleapis.com',
            '*.fontawesome.com'
			'code.jquery.com',
            'cdn.jsdelivr.net',
            'cdnjs.cloudflare.com',
        ],
		'child-src': '*',
        'style-src': [
            '*',
            '\'self\'',
            '\'unsafe-inline\'',
            '\'unsafe-eval\'',
        ],
        'script-src': [
            '*',
			'\'self\'',
            '\'unsafe-inline\'',
			'\'unsafe-eval\'',
            'ajax.googleapis.com',
            'code.jquery.com',
            'cdn.jsdelivr.net',
            'cdnjs.cloudflare.com',
        ]
    }
@talisman(content_security_policy=temp_csp)
@bp.route("/<firepad_id>")
@login_required
def collaborate(firepad_id):
	if models.check_if_user_has_access_to_firepad(firepad_id, current_user.id):
		is_owner = app.models.is_admin(current_user.username) or Firepad.query.get(firepad_id).owner_id == current_user.id
		owner = models.get_firepad_owner_user_object(firepad_id)
		collaborators = db.session.query(
			Collab, User).join(
			User, Collab.user_id == User.id).filter(
			Collab.firepad_id==firepad_id).all()
		
		return render_template(
			'firepad.html',
			api_key = current_app.config['FIREBASE_API_KEY'],
			auth_domain = current_app.config['FIREBASE_AUTH_DOMAIN'],
			database_url = current_app.config['FIREBASE_DATABASE_URL'],
			collaborators = collaborators,
			owner = owner,
			is_owner = is_owner,
			is_admin = app.models.is_admin(current_user.username),
			classes = app.classes.models.get_teacher_classes_from_teacher_id (current_user.id),
			firepad_id = firepad_id)
	else:
		flash ('You do not have permission to access this pad. Please ask the owner to add you as a collaborator', 'info')
		return redirect (url_for('collaboration.collaboration_index'))


# Searchbox and user list to add to firepad collaborator
@bp.route("/find/<firepad_id>")
@login_required
def find_user(firepad_id):
	# If admin, display all students, with shortcut to add entire classes
	if app.models.is_admin(current_user.username):
		classmates = db.session.query(
				User, Enrollment).join(
				Enrollment, User.id == Enrollment.user_id).all()
		classmates = app.classes.models.get_teacher_classes_with_students_from_teacher_id (current_user.id)
	else:
		
		# If student, get list of students from current class
		# Get user list for the current class
		enrollments = db.session.query(Enrollment.turma_id).filter(Enrollment.user_id==current_user.id).all()
		classmates = []
		for turma_id in enrollments[0]:
			class_list = db.session.query(
				User, Enrollment).join(
				Enrollment, User.id == Enrollment.user_id).filter(
				Enrollment.turma_id==turma_id).all()
			for student in class_list: classmates.append(student)
			
		# Display searchable table with username and button to add user
	return render_template(
		'find_user.html', 
		classmates = classmates, 
		classesfirepad_id = firepad_id)

# Method to add new user to a pad
@bp.route("/add/<user_id>/<firepad_id>")
@login_required
def add_user(user_id, firepad_id):
	if app.models.is_admin(current_user.username) or Firepad.query.get(firepad_id).owner_id == current_user.id:
		if int(user_id) == int(current_user.id):
			flash ('You already have access to this pad', 'info')
			return redirect(url_for('collaboration.collaborate', firepad_id = firepad_id))
		else:
			user = User.query.get(user_id)
			collab = Collab (user_id = user_id, firepad_id = firepad_id)
			db.session.add(collab)
			db.session.commit()
			flash ('Successfully added ' + user.username + ' to the pad', 'success')
	else:
		abort (403)
	return redirect(url_for('collaboration.collaborate', firepad_id = firepad_id))

# Method to add an entire class as collaborators in a pad
@bp.route("/add/class/<class_id>/<firepad_id>")
@login_required
def add_class_as_collaborator(class_id, firepad_id):
	if app.models.is_admin(current_user.username):
		# Get class enrollment:
		turma = Turma.query.get(class_id)
		class_enrollment = app.classes.models.get_class_enrollment_from_class_id (class_id)
		for enrollment, turma, user in class_enrollment:
			collab = Collab (user_id = user.id, firepad_id = firepad_id)
			db.session.add(collab)
		db.session.commit()	
		flash ('Successfully created a pad for ' + turma.turma_label + '.', 'success')
	else:
		abort (403)
	return redirect(url_for('collaboration.collaborate', firepad_id = firepad_id))


# Method to remove a user from a pad
@bp.route("/remove/<user_id>/<firepad_id>")
@login_required
def remove_user(user_id, firepad_id):
	if app.models.is_admin(current_user.username) or Firepad.query.get(firepad_id).owner_id == current_user.id:
		user = User.query.get(user_id)
		collab = Collab.query.filter_by(user_id = user_id).filter_by(firepad_id = firepad_id).one()
		db.session.delete(collab)
		db.session.commit()
		flash ('Successfully removed ' + user.username + ' from the pad', 'success')
	else:
		abort (403)
	return redirect(url_for('collaboration.collaborate', firepad_id = firepad_id))


#!# Update user delete method to remove firepads they own
# Method to delete a firepad
@bp.route("/<firepad_id>/remove")
@login_required
def remove_firepad(firepad_id):
	if app.models.is_admin(current_user.username) or Firepad.query.get(firepad_id).owner_id == current_user.id:
		try:
			# Remove all collabs
			collabs = Collab.query.filter_by (firepad_id = firepad_id)
			for collab in collabs:
				db.session.delete(collab)
				
			# Finally, remove the firepad
			firepad = Firepad.query.get (firepad_id)
			db.session.delete (firepad)
			db.session.commit()
			flash ('Successfully removed this pad', 'success')
		except:
			flash ('An error occured while deleting this pad', 'warning')
		return redirect (url_for('collaboration.collaboration_index'))
