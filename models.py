from flask import current_app
from flask_login import current_user

from app import db
from app.models import User, Firepad, Collab
import app.models

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

# Returns a list of collaborator user IDs 
def check_if_user_is_a_collaborator (firepad_id, user_id):
	collaborators = db.session.query(Collab.user_id).filter_by(firepad_id = firepad_id).all()
	for collaborator in collaborators:
		if user_id in collaborator:
			return True
		else:
			pass
	return False
	
	
	