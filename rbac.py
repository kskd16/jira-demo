from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def can_see_ticket(ticket, user):
    """Returns True if the user has access to view the ticket"""
    if user.role == 'admin':
        return True  # Admin can see all tickets
    if user.role == 'manager':
        # Managers can see tickets in their projects or public tickets
        if ticket.project and ticket.project.team_lead_id == user.id:
            return True  # Manager's own project
        return ticket.public  # Public tickets are visible to all managers
    if user.role == 'developer':
        return (
            ticket.assignee == user.name or  # assigned to developer
            ticket.public or  # public tickets
            (ticket.project and ticket.project.team_id == user.team_id)  # team's project
        )
    if user.role == 'visitor':
        return ticket.public and ticket.project and ticket.project.team_id == user.team_id
    return False

def can_edit_ticket(ticket, user):
    """Returns True if the user has access to modify the ticket"""
    if user.role == 'admin':
        return True  # Admin can edit all tickets
    if user.role == 'manager' and ticket.project and ticket.project.team_lead_id == user.id:
        return True  # Managers can edit tickets in their projects
    if user.role == 'developer' and ticket.assignee == user.name:
        return True  # Developers can edit tickets assigned to them
    return False

def can_manage_team(team, user):
    """Returns True if the user can manage the team"""
    if user.role == 'admin':
        return True  # Admin can manage all teams
    if user.role == 'manager' and team.manager_id == user.id:
        return True  # Manager can manage their own team
    return False

def can_approve_user(team_id, user):
    """Returns True if the user can approve new users for a team"""
    if user.role == 'admin':
        return True  # Admin can approve any user
    if user.role == 'manager':
        from models import Team
        team = Team.query.get(team_id)
        if team and team.manager_id == user.id:
            return True  # Manager can approve users for their team
    return False

def can_reassign_ticket(ticket, user):
    """Returns True if the user can reassign the ticket"""
    if user.role == 'admin':
        return True  # Admin can reassign any ticket
    if user.role == 'manager' and ticket.project and ticket.project.team_lead_id == user.id:
        return True  # Manager can reassign tickets in their projects
    return False
