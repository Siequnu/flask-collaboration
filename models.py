from flask import current_app
from flask_login import current_user
from datetime import datetime
from app import db
from app.models import User, Firepad, Collab
import app.models

def get_user_owned_firepads():
	firepads = Firepad.query.filter_by(owner_id=current_user.id).all()
	firepads_info_array = []
	for firepad in firepads:
		firepad_dict = firepad.__dict__
		firepad_dict['owner'] = app.collaboration.models.get_firepad_owner_user_object(firepad.id)
		firepad_dict['collaborators'] = app.collaboration.models.get_firepad_collaborator_user_objects(firepad.id)
		firepads_info_array.append(firepad_dict)
	return firepads_info_array

def get_user_collaborating_firepads():
	collabs = Collab.query.filter_by(user_id=current_user.id).all()
	collabs_info_array = []
	for collab in collabs:
		collab_dict = collab.__dict__
		collab_dict['owner'] = app.collaboration.models.get_firepad_owner_user_object(collab.firepad_id)
		collab_dict['collaborators'] = app.collaboration.models.get_firepad_collaborator_user_objects(collab.firepad_id)
		collabs_info_array.append(collab_dict)
	return collabs_info_array


# Create a new firepad in the DB and return the object
def create_new_firepad():
	# Create a new firepad in the DB and redirect to the newly created pad
	firepad = Firepad(owner_id=current_user.id, timestamp = datetime.now())
	db.session.add(firepad)
	db.session.flush() # Access the new firepad ID in the redirect
	db.session.commit()
	return firepad


# Returns true if user is admin, owner, or collab in a firepad
def check_if_user_has_access_to_firepad(firepad_id, user_id):
	if app.models.is_admin(
		current_user.username) or Firepad.query.get(
		firepad_id).owner_id == current_user.id:
		return True
	elif check_if_user_is_a_collaborator(firepad_id, user_id):
		return True
	else:
		return False
	
def get_firepad_owner_user_object(firepad_id):
	try:
		return User.query.get(Firepad.query.get(firepad_id).owner_id)
	except: return None


def get_firepad_collaborator_user_objects(firepad_id):
	try:
		return db.session.query(
			Collab, User).join(
			User, Collab.user_id == User.id).filter(
			Collab.firepad_id == firepad_id).all()
	except: return None

# Returns a list of collaborator user IDs 
def check_if_user_is_a_collaborator (firepad_id, user_id):
	collaborators = db.session.query(Collab.user_id).filter_by(firepad_id = firepad_id).all()
	for collaborator in collaborators:
		if user_id in collaborator:
			return True
		else:
			pass
	return False
	
	
	
