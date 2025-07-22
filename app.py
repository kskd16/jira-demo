# --- Imports and app setup ---
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash
from functools import wraps
from flask import abort
from rbac import can_see_ticket, can_edit_ticket
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_required

from models import db, Ticket, User
from auth import auth_bp
from admin import admin_bp

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'  # Needed for session and Flask-Login

db.init_app(app)
migrate = Migrate(app, db)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# --- Registration route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Dummy registration logic: just redirect to login
        flash('Account created! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')


# Route for create_ticket page
@app.route('/create_ticket', methods=['GET', 'POST'])
@login_required
def create_ticket():
    from models import User, Team, Ticket, Project
    # Use Flask-Login's current_user directly
    team_members = []
    if current_user.role not in ['admin', 'manager', 'developer']:
        abort(403)
    if current_user.role == 'developer' and not current_user.team_id:
        flash("You must be in a team to create a ticket.")
        return redirect(url_for('dashboard'))
    if current_user.role == 'manager':
        team_members = User.query.filter_by(team_id=current_user.team_id, approved=True).all()
    elif current_user.role == 'admin':
        team_members = User.query.filter_by(approved=True).all()
    else:
        team_members = [current_user]  # Developer can assign only to self (optional)

    if current_user and current_user.team_id:
        team_members = User.query.filter_by(team_id=current_user.team_id, approved=True).all()
    # Get all projects for project selection dropdown
    projects = Project.query.all()
    if request.method == 'POST':
        from datetime import datetime
        title = request.form['title']
        description = request.form['description']
        type_ = request.form['type']
        priority = request.form['priority']
        assignee_id = request.form['assignee']
        assignee_user = User.query.get(int(assignee_id)) if assignee_id else None
        assignee_name = assignee_user.name if assignee_user else 'Unknown'
        public_flag = 'public' in request.form
        project_id = request.form.get('project')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        ticket = Ticket(
            title=title,
            description=description,
            type=type_,
            priority=priority,
            assignee=assignee_name,
            public=public_flag,
            project_id=project_id if project_id else None,
            start_date=start_date,
            end_date=end_date
        )
        db.session.add(ticket)
        db.session.commit()
        flash('Ticket created successfully!')
        return redirect(url_for('board_page'))
    return render_template('create_ticket.html', team_members=team_members, projects=projects)


# Dummy data for demonstration
people = [
    {"name": "Khushi Dixit", "role": "Developer", "avatar": "https://via.placeholder.com/60"},
    {"name": "Om Verma", "role": "Tester", "avatar": "https://via.placeholder.com/60"}
]
teams = [
    {
        "name": "Team Phoenix",
        "project": "AgriTrek",
        "members": people
    }
]
timeline = [
    {
        "ticket_id": "JIRA-101",
        "title": "Login Page UI",
        "start_date": "2025-07-01",
        "deadline": "2025-07-05",
        "completed_date": "2025-07-04"
    },
    {
        "ticket_id": "JIRA-102",
        "title": "Backend API Setup",
        "start_date": "2025-07-03",
        "deadline": "2025-07-10",
        "completed_date": "2025-07-09"
    }
]
projects = [
    {"name": "AgriTrek", "status": "Active"},
    {"name": "Jira Clone", "status": "Completed"}
]

commits = [
    {"message": "Initial commit", "author": "Khushi", "date": "2025-07-01"},
    {"message": "Add login page", "author": "Om", "date": "2025-07-02"}
]

# --- Auth routes ---
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    from models import User
    from werkzeug.security import check_password_hash
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if not user.approved:
                flash('Your account is pending approval by admin.')
                return redirect(url_for('login'))
            session['logged_in'] = True
            session['user'] = email
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Main app routes (all require login) ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

@app.route('/projects', strict_slashes=False)
@login_required
def projects_page():
    from models import Project, User
    selected_lead_id = request.args.get('team_lead', type=int)
    query = Project.query
    if selected_lead_id:
        query = query.filter(Project.team_lead_id == selected_lead_id)
    projects = query.all()
    # Get distinct team leads assigned to projects
    team_lead_ids = {project.team_lead_id for project in Project.query.all() if project.team_lead_id}
    team_leads = User.query.filter(User.id.in_(team_lead_ids)).all() if team_lead_ids else []
    return render_template('projects.html', projects=projects, team_leads=team_leads, selected_lead_id=selected_lead_id)

@app.route('/teams')
@login_required
def teams_page():
    from models import Team, User
    # Query all teams and their approved users
    teams = Team.query.all()
    teams_dict = {}
    for team in teams:
        teams_dict[team.name] = User.query.filter_by(team_id=team.id, approved=True).all()
    # Flatten people you work with (all approved users)
    people = User.query.filter_by(approved=True).all()
    return render_template('teams.html', teams=teams_dict, people=people)

@app.route('/timeline')
@login_required
def timeline_page():
    from models import Project
    projects = Project.query.all()
    return render_template('timeline.html', projects=projects)

@app.route('/board')
@login_required
def board_page():
    from models import Ticket
    user = current_user
    all_tickets = Ticket.query.all()
    visible_tickets = [ticket for ticket in all_tickets if can_see_ticket(ticket, user)]
    tickets = {'To Do': [], 'In Progress': [], 'In Review': [], 'Done': []}
    for t in visible_tickets:
        tickets.setdefault(t.status, []).append(t)
    return render_template('board.html', tickets=tickets)

@app.route('/all_tickets')
@login_required
def all_tickets():
    from models import Ticket
    # Only admin can see all tickets
    if current_user.role != 'admin':
        abort(403)
    
    tickets = Ticket.query.all()
    return render_template('all_tickets.html', tickets=tickets)

# API endpoint for updating ticket status
@app.route('/api/ticket/<int:ticket_id>/status', methods=['POST'])
@login_required
def api_ticket_status(ticket_id):
    from models import Ticket
    from rbac import can_edit_ticket
    
    data = request.get_json()
    new_status = data.get('status')
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if user has permission to edit this ticket
    if not can_edit_ticket(ticket, current_user):
        return jsonify({"status": "error", "message": "Permission denied"}), 403
    
    if new_status and new_status in ['To Do', 'In Progress', 'In Review', 'Done']:
        ticket.status = new_status
        db.session.commit()
        return jsonify({"status": "success", "message": "Ticket status updated"})
    else:
        return jsonify({"status": "error", "message": "Invalid status"}), 400

@app.route('/summary')
@login_required
def summary_page():
    from models import Ticket, Team, Project, User
    from collections import defaultdict
    from datetime import datetime, timedelta
    
    user = current_user
    tickets = Ticket.query.all()
    filtered = [t for t in tickets if can_see_ticket(t, user)]
    
    # Basic ticket counts
    total_tickets = len(filtered)
    completed_tickets = len([t for t in filtered if t.status == 'Done'])
    
    # Status distribution
    status_data = defaultdict(int)
    for t in filtered:
        status_data[t.status] += 1
    
    # Priority distribution
    priority_data = defaultdict(int)
    for t in filtered:
        priority_data[t.priority] += 1
    
    # Type distribution
    type_data = defaultdict(int)
    for t in filtered:
        type_data[t.type] += 1
    
    # Team data (for admin and managers)
    team_data = {}
    timeline_data = {'labels': [], 'completed': [], 'created': []}
    
    if user.role in ['admin', 'manager']:
        # Team performance data
        teams = Team.query.all()
        for team in teams:
            team_tickets = [t for t in filtered if t.project and t.project.team_id == team.id]
            if team_tickets:
                team_data[team.name] = {
                    'total': len(team_tickets),
                    'completed': len([t for t in team_tickets if t.status == 'Done'])
                }
        
        # Timeline data (last 7 days)
        today = datetime.now().date()
        for i in range(7):
            day = today - timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            timeline_data['labels'].insert(0, day_str)
            
            # This is simplified - in a real app you'd track creation/completion dates
            # For demo purposes, we'll use random data
            import random
            timeline_data['completed'].insert(0, random.randint(0, 5))
            timeline_data['created'].insert(0, random.randint(1, 8))
    
    return render_template('summary.html', 
                           total_tickets=total_tickets, 
                           completed_tickets=completed_tickets,
                           status_data=dict(status_data),
                           priority_data=dict(priority_data),
                           type_data=dict(type_data),
                           team_data=team_data,
                           timeline_data=timeline_data)

@app.route('/code')
@login_required
def code_page():
    return render_template('code.html', github_client_id="your_github_client_id", commits=commits)

# --- API endpoints (optional, not protected) ---
@app.route('/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    from models import User, Team
    from rbac import role_required
    
    # Only admin can create teams
    if current_user.role != 'admin':
        abort(403)
    
    if request.method == 'POST':
        name = request.form.get('name')
        manager_id = request.form.get('manager_id')
        member_ids = request.form.getlist('members[]')
        
        # Create new team
        team = Team(name=name, manager_id=manager_id)
        db.session.add(team)
        db.session.commit()
        
        # Assign members to team
        if member_ids:
            for member_id in member_ids:
                user = User.query.get(int(member_id))
                if user:
                    user.team_id = team.id
            db.session.commit()
        
        flash(f'Team {name} created successfully!')
        return redirect(url_for('teams_page'))
    
    # Get managers and developers for form dropdowns
    managers = User.query.filter_by(role='manager', approved=True).all()
    developers = User.query.filter_by(role='developer', approved=True).all()
    return render_template('create_team.html', managers=managers, developers=developers)

@app.route('/team/<int:team_id>/pending_users')
@login_required
def team_pending_users(team_id):
    from models import User, Team
    from rbac import can_approve_user
    
    team = Team.query.get_or_404(team_id)
    
    # Check if user can approve for this team
    if not can_approve_user(team_id, current_user):
        abort(403)
    
    # Get pending users for this team
    pending_users = User.query.filter_by(team_id=team_id, approved=False).all()
    return render_template('pending_users.html', pending_users=pending_users, team=team)

@app.route('/team/<int:team_id>/approve_user/<int:user_id>', methods=['POST'])
@login_required
def team_approve_user(team_id, user_id):
    from models import User, Team
    from rbac import can_approve_user
    
    if not can_approve_user(team_id, current_user):
        abort(403)
    
    user = User.query.get_or_404(user_id)
    if user.team_id != team_id:
        abort(400)  # Bad request if user is not in this team
    
    user.approved = True
    db.session.commit()
    flash(f'User {user.name} has been approved.')
    return redirect(url_for('team_pending_users', team_id=team_id))

@app.route('/team/<int:team_id>/disapprove_user/<int:user_id>', methods=['POST'])
@login_required
def team_disapprove_user(team_id, user_id):
    from models import User, Team
    from rbac import can_approve_user
    
    if not can_approve_user(team_id, current_user):
        abort(403)
    
    user = User.query.get_or_404(user_id)
    if user.team_id != team_id:
        abort(400)  # Bad request if user is not in this team
    
    # Remove user from DB to hide request
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} registration request has been disapproved and removed.')
    return redirect(url_for('team_pending_users', team_id=team_id))

@app.route('/ticket/<int:ticket_id>/reassign', methods=['GET', 'POST'])
@login_required
def reassign_ticket(ticket_id):
    from models import Ticket, User
    from rbac import can_reassign_ticket
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_reassign_ticket(ticket, current_user):
        abort(403)
    
    if request.method == 'POST':
        new_assignee_id = request.form.get('assignee_id')
        if not new_assignee_id:
            flash('No assignee selected')
            return redirect(url_for('board_page'))
        
        new_assignee = User.query.get(int(new_assignee_id))
        if not new_assignee:
            flash('Invalid assignee')
            return redirect(url_for('board_page'))
        
        ticket.assignee = new_assignee.name
        db.session.commit()
        flash(f'Ticket reassigned to {new_assignee.name}')
        return redirect(url_for('board_page'))
    
    # GET request - show reassign form
    # Get team members who can be assigned
    team_members = []
    if ticket.project and ticket.project.team_id:
        team_members = User.query.filter_by(team_id=ticket.project.team_id, approved=True).all()
    elif current_user.role == 'admin':
        team_members = User.query.filter_by(approved=True).all()
    
    return render_template('reassign_ticket.html', ticket=ticket, team_members=team_members)

@app.route('/api/people', methods=['GET', 'POST'])
def api_people():
    from models import User
    if request.method == 'GET':
        users = User.query.filter_by(approved=True).all()
        people = []
        for user in users:
            people.append({
                "name": user.name,
                "role": user.role,
                "avatar": "https://via.placeholder.com/60"
            })
        return jsonify(people)
    elif request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        # Create new user with default role and pending approval
        new_user = User(
            name=email.split('@')[0].capitalize(),
            email=email,
            role='visitor',
            approved=False,
            password=''  # No password set yet
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success", "person": {"name": new_user.name, "role": new_user.role}}), 201

@app.route('/api/teams', methods=['GET', 'POST'])
def api_teams():
    from models import Team, User
    if request.method == 'GET':
        teams = Team.query.all()
        teams_list = []
        for team in teams:
            members = User.query.filter_by(team_id=team.id, approved=True).all()
            members_list = []
            for m in members:
                members_list.append({
                    "name": m.name,
                    "role": m.role,
                    "avatar": "https://via.placeholder.com/60"
                })
            teams_list.append({
                "name": team.name,
                "project": team.project if hasattr(team, 'project') else '',
                "members": members_list
            })
        return jsonify(teams_list)
    elif request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        project = data.get('project')
        member_emails = data.get('members')
        members = []
        for email in member_emails:
            user = User.query.filter_by(email=email).first()
            if user:
                members.append(user)
        new_team = Team(name=name, project=project)
        db.session.add(new_team)
        db.session.commit()
        # Assign members to the new team
        for member in members:
            member.team_id = new_team.id
        db.session.commit()
        return jsonify({"status": "created", "team": {"name": new_team.name, "project": new_team.project, "members": member_emails}})

@app.route('/api/timeline')
def api_timeline():
    from models import Project
    projects = Project.query.all()
    projects_list = []
    for project in projects:
        projects_list.append({
            "id": project.id,
            "name": project.name,
            "start_date": project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
            "deadline": project.deadline.strftime('%Y-%m-%d') if project.deadline else '',
            "status": project.status
        })
    return jsonify(projects_list)

@app.errorhandler(Exception)
def handle_exception(e):
    return f"<pre>{e}</pre>", 500

@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    from models import Project, User
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        team_lead_id = request.form.get('team_lead')
        start_date = request.form.get('start_date')
        deadline = request.form.get('deadline')
        if name and team_lead_id and start_date and deadline:
            from datetime import datetime
            existing_project = Project.query.filter_by(name=name).first()
            if existing_project:
                flash('Project with this name already exists.')
            else:
                status = request.form.get('status', 'Active')
                new_project = Project(
                    name=name,
                    description=description,
                    team_lead_id=team_lead_id,
                    start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
                    deadline=datetime.strptime(deadline, '%Y-%m-%d').date(),
                    status=status
                )
                db.session.add(new_project)
                db.session.commit()
                flash('Project created successfully!')
                return redirect(url_for('projects_page'))
        else:
            flash('Please fill in all required fields.')
    team_leads = User.query.filter_by(role='manager', approved=True).all()
    return render_template('create_project.html', team_leads=team_leads)

@app.route('/project/<int:project_id>/board')
@login_required
def project_board(project_id):
    from models import Project, Ticket
    project = Project.query.get_or_404(project_id)
    tickets = {'To Do': [], 'In Progress': [], 'In Review': [], 'Done': []}
    for ticket in Ticket.query.filter_by(project_id=project_id).all():
        tickets.setdefault(ticket.status, []).append(ticket)
    return render_template('board.html', tickets=tickets, project=project)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from models import User, Team
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            from werkzeug.security import generate_password_hash
            admin_user = User(
                name='Default Admin',
                email='admin@example.com',
                password=generate_password_hash('adminpassword'),
                role='admin',
                approved=True
            )
            db.session.add(admin_user)
            db.session.commit()
        # Initialize default teams alpha, beta, gamma with managers
        default_teams = ['alpha', 'beta', 'gamma']
        for team_name in default_teams:
            team = Team.query.filter_by(name=team_name).first()
            if not team:
                # Assign manager for each team (for now assign admin as manager)
                team = Team(name=team_name, manager_id=admin_user.id)
                db.session.add(team)
        db.session.commit()
        # Ensure teams are visible on teams.html by querying them
        teams = Team.query.all()
        print(f"Teams in DB: {[team.name for team in teams]}")
    app.run(debug=True)