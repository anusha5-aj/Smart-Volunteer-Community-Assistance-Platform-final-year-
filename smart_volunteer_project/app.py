from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import random
from aimatching import calculate_match, calculate_skill_match
from datetime import datetime


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'smart_volunteer_secret_key'

# MySQL Configuration - Update these credentials for your environment
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '4321', 
    'database': 'smart_volunteer_db'
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def get_relative_time(dt):
    if not dt or not isinstance(dt, datetime):
        return "N/A"
    now = datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)} mins ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)} hours ago"
    if seconds < 604800:
        return f"{int(seconds // 86400)} days ago"
    return dt.strftime('%d %b %Y')

def time12(t):
    if not t: return t
    if isinstance(t, str):
        try:
            from datetime import datetime as dt_mod
            return dt_mod.strptime(t.strip()[:5], '%H:%M').strftime('%I:%M %p').lstrip('0')
        except: return t
    try:
        # Assuming timedelta from MySQL
        seconds = t.total_seconds()
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        import datetime as dt_lib
        return dt_lib.time(hours, minutes).strftime('%I:%M %p').lstrip('0')
    except: return t

app.jinja_env.filters['time12'] = time12

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['role'])
    return None

def add_notification(user_id, message, n_type='info', link=None):
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notifications (user_id, message, type, link) VALUES (%s, %s, %s, %s)", 
                       (user_id, message, n_type, link))
        conn.commit()
    except Exception as e:
        print(f"Error adding notification: {e}")
    finally:
        cursor.close()
        conn.close()

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

def generate_captcha():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' # Removed confusing chars like 0, O, 1, I
    captcha = ''.join(random.choice(chars) for _ in range(4))
    session['captcha_answer'] = captcha
    return captcha

@app.route('/refresh_captcha')
def refresh_captcha():
    return jsonify({'captcha': generate_captcha()})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        if not conn:
            flash("Database connection failed.", "error")
            return redirect(url_for('register'))
        
        cursor = conn.cursor()
        try:
            # Check if username exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash("Username already exists.", "error")
                return redirect(url_for('register'))

            # Insert into users table
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                           (username, hashed_password, role))
            user_id = cursor.lastrowid

            if role == 'volunteer':
                cursor.execute("""
                    INSERT INTO volunteers (user_id, first_name, last_name, email, gender, location, skills)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, request.form.get('first_name'), request.form.get('last_name'), 
                     request.form.get('email'), request.form.get('gender'), 
                     request.form.get('location'), request.form.get('skills')))
            elif role == 'ngo':
                cursor.execute("""
                    INSERT INTO ngos (user_id, organization_name, trust_id, website, location)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, request.form.get('organization_name'), request.form.get('trust_id'), 
                     request.form.get('website'), request.form.get('location')))
            
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash(f"Error during registration: {e}", "error")
        finally:
            cursor.close()
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_captcha = request.form.get('captcha')
        
        # Verify Captcha
        if not user_captcha or user_captcha.upper() != session.get('captcha_answer'):
            flash("Incorrect CAPTCHA answer.", "error")
            return redirect(url_for('login'))

        conn = get_db_connection()
        if not conn:
            flash("Database connection failed.", "error")
            return redirect(url_for('login'))
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data['id'], user_data['username'], user_data['role'])
            login_user(user)
            if user.role == 'admin': return redirect(url_for('admin_dashboard'))
            if user.role == 'ngo': return redirect(url_for('ngo_dashboard'))
            if user.role == 'volunteer': return redirect(url_for('volunteer_dashboard'))
        else:
            flash("Invalid username or password.", "error")
            
    captcha_text = generate_captcha()
    return render_template('login.html', captcha_text=captcha_text)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- Role Based Dashboards ---

@app.route('/dashboard/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Summary Stats
    cursor.execute("SELECT COUNT(*) as total FROM ngos")
    total_ngos = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM volunteers")
    total_volunteers = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM events")
    total_events = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM applications")
    total_apps = cursor.fetchone()['total']
    
    stats = {
        'total_ngos': total_ngos,
        'total_volunteers': total_volunteers,
        'total_events': total_events,
        'total_applications': total_apps
    }
    
    # Management Data
    cursor.execute("SELECT * FROM ngos")
    ngos = cursor.fetchall()
    
    cursor.execute("""
        SELECT u.id, u.username, u.role, u.created_at, v.email, v.id as vol_id,
               COALESCE(v.first_name, n.organization_name) as name,
               COALESCE(v.location, n.location) as location,
               v.skills
        FROM users u 
        LEFT JOIN volunteers v ON u.id = v.user_id 
        LEFT JOIN ngos n ON u.id = n.user_id
    """)
    users = cursor.fetchall()
    
    cursor.execute("""
        SELECT e.*, n.organization_name, (SELECT COUNT(*) FROM applications WHERE event_id = e.id) as app_count 
        FROM events e 
        JOIN ngos n ON e.ngo_id = n.id
    """)
    events = cursor.fetchall()
    
    # Analytics
    cursor.execute("SELECT status, COUNT(*) as count FROM applications GROUP BY status")
    app_status = cursor.fetchall()
    
    cursor.execute("""
        SELECT n.organization_name, COUNT(e.id) as event_count 
        FROM ngos n 
        LEFT JOIN events e ON n.id = e.ngo_id 
        GROUP BY n.id
    """)
    ngo_events_dist = cursor.fetchall()
    
    # Registration Trend (Dynamic)
    cursor.execute("""
        SELECT DATE_FORMAT(created_at, '%b') as month,
        COUNT(CASE WHEN role='volunteer' THEN 1 END) as volunteers,
        COUNT(CASE WHEN role='ngo' THEN 1 END) as ngos
        FROM users
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY month
        ORDER BY MIN(created_at)
    """)
    trend_raw = cursor.fetchall()
    reg_trend = {
        'labels': [r['month'] for r in trend_raw],
        'volunteers': [r['volunteers'] for r in trend_raw],
        'ngos': [r['ngos'] for r in trend_raw]
    }

    # Recent Activity Feed (Dynamic)
    cursor.execute("""
        (SELECT 'volunteer_reg' as type, u.username as name, u.created_at as time_at FROM users u WHERE role='volunteer')
        UNION ALL
        (SELECT 'ngo_reg' as type, COALESCE(n.organization_name, u.username) as name, u.created_at as time_at FROM users u LEFT JOIN ngos n ON u.id = n.user_id WHERE u.role='ngo')
        UNION ALL
        (SELECT 'app_submitted' as type, v.first_name as name, a.applied_at as time_at FROM applications a JOIN volunteers v ON a.volunteer_id = v.id)
        UNION ALL
        (SELECT 'event_created' as type, e.event_title as name, e.created_at as time_at FROM events e)
        ORDER BY time_at DESC
        LIMIT 5
    """)
    activities_raw = cursor.fetchall()
    activities = []
    for act in activities_raw:
        desc = ""
        icon = ""
        color = ""
        if act['type'] == 'volunteer_reg':
            desc = f"Volunteer {act['name']} registered"
            icon = "user-plus"
            color = "blue"
        elif act['type'] == 'ngo_reg':
            desc = f"NGO {act['name']} registered"
            icon = "building"
            color = "amber"
        elif act['type'] == 'app_submitted':
            desc = f"Volunteer {act['name']} applied for event"
            icon = "file-text"
            color = "purple"
        elif act['type'] == 'event_created':
            desc = f"New event: {act['name']} created"
            icon = "calendar-plus"
            color = "green"
        
        activities.append({
            'description': desc,
            'relative_time': get_relative_time(act['time_at']),
            'icon': icon,
            'color': color
        })

    analytics = {
        'user_ratio': {'Volunteers': total_volunteers, 'NGOs': total_ngos},
        'app_status_dist': {row['status']: row['count'] for row in app_status},
        'ngo_events_dist': {row['organization_name']: row['event_count'] for row in ngo_events_dist},
        'reg_trend': reg_trend
    }
    
    cursor.close()
    conn.close()
    return render_template('admin_dashboard.html', stats=stats, ngos=ngos, users=users, events=events, analytics=analytics, activities=activities)

@app.route('/admin/verify_ngo/<int:ngo_id>/<string:status>')
@login_required
def verify_ngo(ngo_id, status):
    if current_user.role != 'admin': return redirect(url_for('index'))
    if status not in ['Verified', 'Rejected']: status = 'Pending'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE ngos SET status = %s WHERE id = %s", (status, ngo_id))
    conn.commit()
    
    # Notify NGO admin
    cursor.execute("SELECT user_id FROM ngos WHERE id = %s", (ngo_id,))
    ngo_user = cursor.fetchone()
    if ngo_user:
        add_notification(ngo_user[0], f"Your NGO account status has been updated to: {status}.", "info")
        
    cursor.close()
    conn.close()
    flash(f"NGO status updated to {status}.")
    return redirect(url_for('admin_dashboard') + "#ngos")

@app.route('/admin/delete_event/<int:event_id>')
@login_required
def admin_delete_event(event_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Event deleted by administrator.")
    return redirect(url_for('admin_dashboard') + "#events")

@app.route('/admin/volunteer_profile/<int:vol_id>')
@login_required
def admin_volunteer_profile(vol_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT v.*, u.created_at, u.username
        FROM volunteers v
        JOIN users u ON v.user_id = u.id
        WHERE v.id = %s
    """, (vol_id,))
    volunteer = cursor.fetchone()
    cursor.close()
    conn.close()
    if not volunteer:
        flash("Volunteer not found.")
        return redirect(url_for('admin_dashboard'))
    return render_template('volunteer_profile.html', vol=volunteer)

@app.route('/admin/delete_volunteer/<int:user_id>')
@login_required
def admin_delete_volunteer(user_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Delete user (cascades to volunteers and applications)
        cursor.execute("DELETE FROM users WHERE id = %s AND role = 'volunteer'", (user_id,))
        if cursor.rowcount > 0:
            conn.commit()
            flash("Volunteer deleted successfully.")
        else:
            flash("User not found or not a volunteer.")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting volunteer: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_dashboard') + "#users")

@app.route('/dashboard/ngo')
@login_required
def ngo_dashboard():
    if current_user.role != 'ngo': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM ngos WHERE user_id = %s", (current_user.id,))
    ngo = cursor.fetchone()
    ngo_id = ngo['id']
    
    # 1. Dashboard Stats
    cursor.execute("SELECT COUNT(*) as total FROM events WHERE ngo_id = %s", (ngo_id,))
    total_events = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM applications a JOIN events e ON a.event_id = e.id WHERE e.ngo_id = %s", (ngo_id,))
    total_applications = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM applications a JOIN events e ON a.event_id = e.id WHERE e.ngo_id = %s AND a.status = 'Accepted'", (ngo_id,))
    accepted_volunteers = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM applications a JOIN events e ON a.event_id = e.id WHERE e.ngo_id = %s AND a.status = 'Pending'", (ngo_id,))
    pending_applications = cursor.fetchone()['total']
    stats = {'total_events': total_events, 'total_applications': total_applications, 'accepted_volunteers': accepted_volunteers, 'pending_applications': pending_applications}

    # 2. Events (All)
    cursor.execute("""
        SELECT e.*, (SELECT COUNT(*) FROM applications WHERE event_id = e.id) as app_count 
        FROM events e 
        WHERE e.ngo_id = %s 
        ORDER BY e.event_date DESC
    """, (ngo_id,))
    events = cursor.fetchall()

    # 3. Volunteers (Directory)
    cursor.execute("SELECT * FROM volunteers")
    all_volunteers = cursor.fetchall()
    
    # Pre-calculate AI Match scores for all volunteers against current NGO events 
    # to ensure consistency in the interactive directory
    match_data = {}
    for ev in events:
        match_data[str(ev['id'])] = {}
        for vol in all_volunteers:
            # Use the centralized AI function
            score = calculate_skill_match(vol['skills'], ev['required_skills'])
            match_data[str(ev['id'])][str(vol['id'])] = score

    # 4. Applications (Reviews)
    cursor.execute("""
        SELECT a.*, v.first_name, v.last_name, v.email as v_email, v.location as v_location, 
               v.skills as v_skills, v.impact_bio as v_impact_bio, v.availability as v_availability,
               v.avatar_url, e.event_title, e.required_skills as e_skills, e.status as event_status
        FROM applications a 
        JOIN volunteers v ON a.volunteer_id = v.id 
        JOIN events e ON a.event_id = e.id
        WHERE e.ngo_id = %s
    """, (ngo_id,))
    applications_list = cursor.fetchall()
    for app_item in applications_list:
        match_info = calculate_match(app_item['v_skills'], app_item['e_skills'])
        app_item['match_percentage'] = match_info['match_percentage']
        app_item['matched_skills'] = ", ".join(match_info['matched_skills'])
        app_item['missing_skills'] = ", ".join(match_info['missing_skills'])

    # 5. Notifications
    cursor.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC", (current_user.id,))
    notifications = cursor.fetchall()

    # 6. Analytics
    cursor.execute("SELECT a.status, COUNT(*) as count FROM applications a JOIN events e ON a.event_id = e.id WHERE e.ngo_id = %s GROUP BY a.status", (ngo_id,))
    status_data = cursor.fetchall()
    cursor.execute("SELECT e.event_title, COUNT(a.id) as count FROM events e LEFT JOIN applications a ON e.id = a.event_id WHERE e.ngo_id = %s GROUP BY e.id", (ngo_id,))
    event_counts = cursor.fetchall()
    
    # Skill Distribution for Analytics
    cursor.execute("SELECT skills FROM volunteers")
    all_v_skills = cursor.fetchall()
    skill_counts = {}
    for row in all_v_skills:
        if row['skills']:
            for s in row['skills'].split(','):
                s = s.strip().title()
                if s: skill_counts[s] = skill_counts.get(s, 0) + 1
    
    # Sort and take top 5
    top_skills = dict(sorted(skill_counts.items(), key=lambda item: item[1], reverse=True)[:5])

    analytics = {
        "status_distribution": {row['status']: row['count'] for row in status_data},
        "event_distribution": {row['event_title']: row['count'] for row in event_counts},
        "skill_distribution": top_skills
    }

    cursor.close()
    conn.close()
    return render_template('ngo_dashboard.html', stats=stats, ngo=ngo, events=events, volunteers=all_volunteers, applications=applications_list, notifications=notifications, analytics=analytics, match_data=match_data)

# Redundant individual routes removed (now part of /dashboard/ngo)

# Legacy NGO Analytics route removed (now handled by /api/analytics_data and ngo_dashboard.html)

@app.route('/dashboard/volunteer')
@login_required
def volunteer_dashboard():
    if current_user.role != 'volunteer': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get Volunteer profile
    cursor.execute("SELECT * FROM volunteers WHERE user_id = %s", (current_user.id,))
    volunteer = cursor.fetchone()
    vol_id = volunteer['id']
    vol_skills = volunteer['skills'] or ""
    
    # 1. Quick Activity Stats
    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE volunteer_id = %s", (vol_id,))
    apps_sent = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE volunteer_id = %s AND status = 'Accepted'", (vol_id,))
    invites_accepted = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE volunteer_id = %s AND status = 'Pending'", (vol_id,))
    invites_pending = cursor.fetchone()['count']
    
    quick_stats = {
        'sent': apps_sent,
        'accepted': invites_accepted,
        'pending': invites_pending
    }

    # 2. Top Community Heroes (Leaderboard)
    cursor.execute("""
        SELECT v.first_name, (COUNT(a.id) * 5) as total_hours
        FROM volunteers v
        JOIN applications a ON v.id = a.volunteer_id
        WHERE a.status = 'Accepted'
        GROUP BY v.id
        ORDER BY total_hours DESC
        LIMIT 5
    """)
    top_heroes = cursor.fetchall()

    # 3. Opportunities (Available events)
    cursor.execute("SELECT e.*, n.organization_name FROM events e JOIN ngos n ON e.ngo_id = n.id WHERE e.status = 'Open'")
    events = cursor.fetchall()
    
    # Apply Search Filters
    search_skill = request.args.get('search_skill', '').lower().strip()
    city_filter = request.args.get('city_filter', '').lower().strip()
    date_filter = request.args.get('date_filter', '').strip()
    
    if search_skill or city_filter or date_filter:
        filtered_events = []
        for event in events:
            match = True
            if search_skill and search_skill not in (event['required_skills'] or "").lower():
                match = False
            if city_filter and city_filter not in (event['location'] or "").lower():
                match = False
            if date_filter and str(event['event_date']) < date_filter:
                match = False
            if match:
                filtered_events.append(event)
        events = filtered_events
    
    # 4. Enhanced Recommendations (Rule-based: 70% Skill, 30% Location)
    match_skills = request.args.get('match_skills') == 'true'
    scored_events = []
    top_matches = [] # For Home section legacy logic
    for event in events:
        # Skill matching using centralized AI function
        score = calculate_skill_match(vol_skills, event['required_skills'])
            
        event['match_score'] = score
        scored_events.append(event)
            
        # Legacy populate top_matches for the Home section
        match_info = calculate_match(vol_skills, event['required_skills'])
        event['match_percentage'] = match_info['match_percentage']
        if event['match_percentage'] >= 80:
            top_matches.append(event)
            
    # Sort by score
    scored_events = sorted(scored_events, key=lambda x: x['match_score'], reverse=True)
    
    recommended_events = None
    other_events = scored_events
    if match_skills:
        recommended_events = [e for e in scored_events if e['match_score'] > 0][:3]
        # For others, if they are already in recommendations, exclude them to avoid duplicates
        recommended_ids = {e['id'] for e in recommended_events}
        other_events = [e for e in scored_events if e['id'] not in recommended_ids]

    # 4. My Applications (Status tracker)
    cursor.execute("""
        SELECT a.*, e.event_title, e.event_date, e.status as event_status, n.organization_name 
        FROM applications a 
        JOIN events e ON a.event_id = e.id 
        JOIN ngos n ON e.ngo_id = n.id
        WHERE a.volunteer_id = %s
    """, (vol_id,))
    my_applications = cursor.fetchall()
    
    # 3. Impact Stats
    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE volunteer_id = %s", (vol_id,))
    total_apps = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE volunteer_id = %s AND status = 'Accepted'", (vol_id,))
    accepted_apps = cursor.fetchone()['count']
    volunteer_hours = accepted_apps * 5 # Simulated
    cursor.execute("""
        SELECT COUNT(DISTINCT e.ngo_id) as count 
        FROM applications a 
        JOIN events e ON a.event_id = e.id 
        WHERE a.volunteer_id = %s AND a.status = 'Accepted'
    """, (vol_id,))
    ngos_worked = cursor.fetchone()['count']

    stats = {
        'total_applications': total_apps,
        'accepted_events': accepted_apps,
        'volunteer_hours': volunteer_hours,
        'ngos_worked': ngos_worked
    }
    
    # 4. Notifications
    cursor.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC", (current_user.id,))
    notifications = cursor.fetchall()
    
    # 5. Completed Events for Impact Section
    cursor.execute("""
        SELECT e.*, n.organization_name
        FROM applications a
        JOIN events e ON a.event_id = e.id
        JOIN ngos n ON e.ngo_id = n.id
        WHERE a.volunteer_id = %s
        AND a.status = 'Accepted'
        AND e.status = 'Completed'
    """, (vol_id,))
    completed_events = cursor.fetchall()

    from datetime import datetime
    for e in completed_events:
        if e['start_time'] and e['end_time']:
            # Calculate service hours
            # e['start_time'] and e['end_time'] are timedeltas or time objects
            # Let's handle them as strings or timedeltas
            try:
                # If they are timedeltas, find total seconds / 3600
                td = e['end_time'] - e['start_time']
                e['service_hours'] = round(td.total_seconds() / 3600, 1)
            except:
                e['service_hours'] = 5 # Fallback
        else:
            e['service_hours'] = 5 # Default fallback

    # 6. Upcoming Accepted Events for Schedule Section
    cursor.execute("""
        SELECT e.id, e.event_title, e.event_date, e.location, n.organization_name
        FROM applications a
        JOIN events e ON a.event_id = e.id
        JOIN ngos n ON e.ngo_id = n.id
        WHERE a.volunteer_id = %s
        AND a.status = 'Accepted'
        AND e.event_date >= CURDATE()
        ORDER BY e.event_date ASC
    """, (vol_id,))
    upcoming_events = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('volunteer_dashboard.html', events=other_events, top_matches=top_matches, my_applications=my_applications, stats=stats, volunteer=volunteer, notifications=notifications, completed_events=completed_events, quick_stats=quick_stats, top_heroes=top_heroes, upcoming_events=upcoming_events, recommended_events=recommended_events)

@app.route('/api/ngo_profile/<int:ngo_id>')
@login_required
def api_ngo_profile(ngo_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT organization_name, trust_id, website, location, description FROM ngos WHERE id = %s", (ngo_id,))
    ngo = cursor.fetchone()
    cursor.close()
    conn.close()
    if ngo: return jsonify(ngo)
    return jsonify({"error": "NGO not found"}), 404

@app.route('/ngo_profile/<int:ngo_id>')
def ngo_profile(ngo_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get NGO Details
    cursor.execute("SELECT id, organization_name, trust_id, website, location, description FROM ngos WHERE id = %s", (ngo_id,))
    ngo = cursor.fetchone()
    
    if not ngo:
        cursor.close()
        conn.close()
        flash("NGO not found", "error")
        return redirect(url_for('index'))
        
    # Get active events for this NGO
    cursor.execute("SELECT * FROM events WHERE ngo_id = %s AND status = 'Open' ORDER BY event_date ASC", (ngo_id,))
    events = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('ngo_profile.html', ngo=ngo, events=events)

@app.route('/download_certificate/<int:event_id>')
@login_required
def download_certificate(event_id):
    if current_user.role != 'volunteer': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Verify participation and fetch name
    cursor.execute("SELECT id, first_name, last_name FROM volunteers WHERE user_id = %s", (current_user.id,))
    vol_data = cursor.fetchone()
    if not vol_data:
        cursor.close()
        conn.close()
        return redirect(url_for('volunteer_dashboard'))
    vol_id = vol_data['id']
    volunteer_name = f"{vol_data['first_name']} {vol_data['last_name']}"
    
    cursor.execute("SELECT a.*, e.event_title, n.organization_name FROM applications a JOIN events e ON a.event_id = e.id JOIN ngos n ON e.ngo_id = n.id WHERE a.volunteer_id = %s AND a.event_id = %s AND a.status = 'Accepted' AND e.status = 'Completed'", (vol_id, event_id))
    participation = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not participation:
        flash("Certificate only available for completed events you participated in.")
        return redirect(url_for('volunteer_dashboard'))
    
    import pdfkit
    from flask import Response
    html_content = render_template('certificate.html',
                                   volunteer_name=volunteer_name,
                                   event_title=participation['event_title'],
                                   ngo_name=participation['organization_name'])
    
    try:
        config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
        pdf = pdfkit.from_string(html_content, False, configuration=config)
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment;filename=certificate.pdf"}
        )
    except Exception as e:
        print(f"PDFKit Error: {e}")
        flash("Failed to generate PDF certificate.", "error")
        return redirect(url_for('volunteer_dashboard'))

@app.route('/certificate/<int:event_id>')
@login_required
def certificate(event_id):
    return download_certificate(event_id)

# --- Feature Routes ---

@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if current_user.role != 'ngo': return redirect(url_for('index'))
    if request.method == 'POST':
        conn = get_db_connection()
        if not conn:
            flash("Database connection error.")
            return redirect(url_for('ngo_dashboard'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM ngos WHERE user_id = %s", (current_user.id,))
        res = cursor.fetchone()
        if not res:
            cursor.close()
            conn.close()
            flash("NGO profile not found.")
            return redirect(url_for('ngo_dashboard'))
        ngo_id = res['id']
        
        cursor.execute("""
            INSERT INTO events (ngo_id, event_title, description, required_skills, location, event_date, start_time, end_time, volunteer_limit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (ngo_id, request.form.get('event_title'), request.form.get('description'), 
             request.form.get('required_skills'), request.form.get('location'), request.form.get('event_date'),
             request.form.get('start_time'), request.form.get('end_time'), request.form.get('volunteer_limit')))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Event created successfully!")
        return redirect(url_for('ngo_dashboard'))
    return render_template('create_event.html')

@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    if current_user.role != 'ngo': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Verify ownership
    cursor.execute("SELECT n.id FROM ngos n WHERE n.user_id = %s", (current_user.id,))
    ngo_id = cursor.fetchone()['id']
    
    cursor.execute("SELECT * FROM events WHERE id = %s AND ngo_id = %s", (event_id, ngo_id))
    event = cursor.fetchone()
    if not event:
        cursor.close()
        conn.close()
        flash("Event not found or unauthorized access.")
        return redirect(url_for('ngo_dashboard'))
    
    if request.method == 'POST':
        cursor.execute("""
            UPDATE events 
            SET event_title = %s, description = %s, required_skills = %s, location = %s, event_date = %s, start_time = %s, end_time = %s, volunteer_limit = %s
            WHERE id = %s
        """, (request.form.get('event_title'), request.form.get('description'), 
             request.form.get('required_skills'), request.form.get('location'), 
             request.form.get('event_date'), request.form.get('start_time'), 
             request.form.get('end_time'), request.form.get('volunteer_limit'), event_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Event updated successfully!")
        return redirect(url_for('ngo_dashboard'))
        
    cursor.close()
    conn.close()
    return render_template('edit_event.html', event=event)

@app.route('/delete_event/<int:event_id>')
@login_required
def delete_event(event_id):
    if current_user.role != 'ngo': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Verify ownership
    cursor.execute("SELECT n.id FROM ngos n WHERE n.user_id = %s", (current_user.id,))
    ngo_id = cursor.fetchone()['id']
    
    cursor.execute("DELETE FROM events WHERE id = %s AND ngo_id = %s", (event_id, ngo_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Event deleted successfully.")
    return redirect(url_for('ngo_dashboard'))

@app.route('/my_impact')
@login_required
def my_impact():
    if current_user.role != 'volunteer': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get Volunteer profile id
    cursor.execute("SELECT id FROM volunteers WHERE user_id = %s", (current_user.id,))
    vol_id = cursor.fetchone()['id']
    
    # Impact Stats
    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE volunteer_id = %s AND status = 'Accepted'", (vol_id,))
    accepted_apps = cursor.fetchone()['count']
    
    # Simulate hours: 5 hours per accepted event
    volunteer_hours = accepted_apps * 5
    
    # Count unique NGOs worked with
    cursor.execute("""
        SELECT COUNT(DISTINCT e.ngo_id) as count 
        FROM applications a 
        JOIN events e ON a.event_id = e.id 
        WHERE a.volunteer_id = %s AND a.status = 'Accepted'
    """, (vol_id,))
    ngos_worked = cursor.fetchone()['count']

    stats = {
        'accepted_events': accepted_apps,
        'volunteer_hours': volunteer_hours,
        'ngos_worked': ngos_worked
    }
    
    cursor.close()
    conn.close()
    return render_template('my_impact.html', stats=stats)

@app.route('/apply/<int:event_id>')
@login_required
def apply_event(event_id):
    if current_user.role != 'volunteer': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM volunteers WHERE user_id = %s", (current_user.id,))
    volunteer_id = cursor.fetchone()['id']
    
    # Check if already applied
    cursor.execute("SELECT id FROM applications WHERE event_id = %s AND volunteer_id = %s", (event_id, volunteer_id))
    if cursor.fetchone():
        flash("You have already applied for this event.")
    else:
        # Conflict Detection: check if any accepted event exists on the same date
        cursor.execute("""
            SELECT e.event_title, e.event_date 
            FROM applications a 
            JOIN events e ON a.event_id = e.id 
            WHERE a.volunteer_id = %s AND a.status = 'Accepted' 
            AND e.event_date = (SELECT event_date FROM events WHERE id = %s)
        """, (volunteer_id, event_id))
        conflict = cursor.fetchone()
        
        if conflict:
            flash(f"Conflict: You already have an accepted event ('{conflict['event_title']}') on {conflict['event_date']}.")
        else:
            cursor.execute("INSERT INTO applications (event_id, volunteer_id) VALUES (%s, %s)", (event_id, volunteer_id))
            conn.commit()
            
            # Notify NGO
            cursor.execute("SELECT ngo_id FROM events WHERE id = %s", (event_id,))
            ngo_row = cursor.fetchone()
            if ngo_row:
                cursor.execute("SELECT user_id FROM ngos WHERE id = %s", (ngo_row['ngo_id'],))
                ngo_user = cursor.fetchone()
                if ngo_user:
                    add_notification(ngo_user['user_id'], f"A new volunteer has applied for your event.", "info")
                    
            flash("Application sent successfully!")
        
    cursor.close()
    conn.close()
    return redirect(url_for('volunteer_dashboard'))

@app.route('/notifications')
@login_required
def notifications():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch notifications
    cursor.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC", (current_user.id,))
    notifications_list = cursor.fetchall()
    
    # Mark as read
    cursor.execute("UPDATE notifications SET is_read = TRUE WHERE user_id = %s", (current_user.id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    # Determine where to redirect based on user role (volunteer defaults to dashboard)
    if current_user.role == 'volunteer':
        return render_template('notifications.html', notifications=notifications_list)
    return redirect(url_for('ngo_dashboard'))

@app.route('/application/<int:app_id>/<string:status>')
@login_required
def update_application_status(app_id, status):
    if current_user.role != 'ngo': return redirect(url_for('index'))
    if status not in ['Accepted', 'Rejected']: return redirect(url_for('ngo_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET status = %s WHERE id = %s", (status, app_id))
    conn.commit()
    
    # Notify Volunteer
    cursor.execute("""
        SELECT a.volunteer_id, e.event_title 
        FROM applications a 
        JOIN events e ON a.event_id = e.id 
        WHERE a.id = %s
    """, (app_id,))
    app_data = cursor.fetchone()
    if app_data:
        vol_id_val, event_title = app_data
        cursor.execute("SELECT user_id FROM volunteers WHERE id = %s", (vol_id_val,))
        vol_user = cursor.fetchone()
        if vol_user:
            # Add link to #my-impact section for volunteer
            link = "/dashboard/volunteer#impact-section" if status == 'Accepted' else None
            add_notification(vol_user[0], f"Your application for '{event_title}' has been {status}.", 
                             "success" if status == 'Accepted' else 'error', link=link)
            
    cursor.close()
    conn.close()
    flash(f"Application status updated to {status}.")
    return redirect(url_for('ngo_dashboard'))

@app.route('/update_event_status/<int:event_id>/<string:status>')
@login_required
def update_event_status(event_id, status):
    if current_user.role != 'ngo': return redirect(url_for('index'))
    if status not in ['Open', 'Closed', 'Completed']: return redirect(url_for('ngo_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET status = %s WHERE id = %s", (status, event_id))
    
    if status == 'Completed':
        # Update certificate eligibility for all accepted and present volunteers
        cursor.execute("""
            UPDATE applications
            SET certificate_status = 'eligible'
            WHERE event_id = %s AND status = 'Accepted' AND attendance = 'present'
        """, (event_id,))
        
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Event status updated to {status}.")
    return redirect(url_for('ngo_dashboard'))

@app.route('/mark_attendance/<int:app_id>/<string:attendance>')
@login_required
def mark_attendance(app_id, attendance):
    if current_user.role != 'ngo': return redirect(url_for('index'))
    if attendance not in ['present', 'absent']: return redirect(url_for('ngo_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Update attendance
    cursor.execute("UPDATE applications SET attendance = %s WHERE id = %s", (attendance, app_id))
    
    # Check eligibility for certificate
    cursor.execute("""
        SELECT a.status, e.status as event_status 
        FROM applications a 
        JOIN events e ON a.event_id = e.id 
        WHERE a.id = %s
    """, (app_id,))
    app_data = cursor.fetchone()
    
    if app_data and app_data['status'] == 'Accepted' and attendance == 'present' and app_data['event_status'] == 'Completed':
        cursor.execute("UPDATE applications SET certificate_status = 'eligible' WHERE id = %s", (app_id,))
    else:
        cursor.execute("UPDATE applications SET certificate_status = 'not_eligible' WHERE id = %s", (app_id,))
        
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Attendance marked as {attendance}.")
    return redirect(url_for('ngo_dashboard'))

@app.route('/ngo/download_certificate/<int:app_id>')
@login_required
def ngo_download_certificate(app_id):
    if current_user.role != 'ngo': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Verify participation and fetch required info
    cursor.execute("""
        SELECT a.*, v.first_name, v.last_name, e.event_title, n.organization_name 
        FROM applications a 
        JOIN volunteers v ON a.volunteer_id = v.id
        JOIN events e ON a.event_id = e.id 
        JOIN ngos n ON e.ngo_id = n.id 
        WHERE a.id = %s AND e.ngo_id = (SELECT id FROM ngos WHERE user_id = %s)
    """, (app_id, current_user.id))
    participation = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not participation or participation['certificate_status'] != 'eligible':
        flash("Certificate is not available or not eligible.")
        return redirect(url_for('ngo_dashboard'))
    
    import pdfkit
    from flask import Response
    volunteer_name = f"{participation['first_name']} {participation['last_name']}"
    html_content = render_template('certificate.html',
                                   volunteer_name=volunteer_name,
                                   event_title=participation['event_title'],
                                   ngo_name=participation['organization_name'])
    
    try:
        config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
        pdf = pdfkit.from_string(html_content, False, configuration=config)
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment;filename=certificate_{participation['first_name']}.pdf"}
        )
    except Exception as e:
        print(f"PDFKit Error: {e}")
        flash("Failed to generate PDF certificate.", "error")
        return redirect(url_for('ngo_dashboard'))


@app.route('/invite_volunteer/<int:volunteer_id>/<int:event_id>')
@login_required
def invite_volunteer(volunteer_id, event_id):
    if current_user.role != 'ngo': return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if exists
        cursor.execute("SELECT id FROM applications WHERE event_id = %s AND volunteer_id = %s", (event_id, volunteer_id))
        if cursor.fetchone():
            flash("Volunteer is already part of this event.")
        else:
            cursor.execute("INSERT INTO applications (event_id, volunteer_id, status) VALUES (%s, %s, 'Invited')", (event_id, volunteer_id))
            conn.commit()
            
            # Notify Volunteer
            cursor.execute("SELECT user_id FROM volunteers WHERE id = %s", (volunteer_id,))
            vol_user = cursor.fetchone()
            if vol_user:
                add_notification(vol_user[0], "You have been invited to a new event!", "info")
                
            flash("Invitation sent successfully!")
    except Exception as e:
        conn.rollback()
        flash(f"Error inviting volunteer: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('ngo_dashboard'))

@app.route('/api/analytics_data')
@login_required
def get_analytics_data():
    if current_user.role != 'ngo': return {"error": "Unauthorized"}, 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id FROM ngos WHERE user_id = %s", (current_user.id,))
    ngo = cursor.fetchone()
    
    # Applications per status
    cursor.execute("""
        SELECT a.status, COUNT(*) as count 
        FROM applications a 
        JOIN events e ON a.event_id = e.id 
        WHERE e.ngo_id = %s 
        GROUP BY a.status
    """, (ngo['id'],))
    status_data = cursor.fetchall()
    
    # Applications per event
    cursor.execute("""
        SELECT e.event_title, COUNT(a.id) as count 
        FROM events e 
        LEFT JOIN applications a ON e.id = a.event_id 
        WHERE e.ngo_id = %s 
        GROUP BY e.id
    """, (ngo['id'],))
    event_counts = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {
        "status_distribution": {row['status']: row['count'] for row in status_data},
        "event_distribution": {row['event_title']: row['count'] for row in event_counts}
    }

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if current_user.role != 'volunteer': return redirect(url_for('index'))
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    location = request.form.get('location')
    skills = request.form.get('skills')
    impact_bio = request.form.get('impact_bio')
    
    avatar_url = None
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"avatar_{current_user.id}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            avatar_url = url_for('static', filename=f'uploads/{filename}')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if avatar_url:
            cursor.execute("""
                UPDATE volunteers 
                SET first_name = %s, last_name = %s, email = %s, location = %s, skills = %s, impact_bio = %s, avatar_url = %s
                WHERE user_id = %s
            """, (first_name, last_name, email, location, skills, impact_bio, avatar_url, current_user.id))
        else:
            cursor.execute("""
                UPDATE volunteers 
                SET first_name = %s, last_name = %s, email = %s, location = %s, skills = %s, impact_bio = %s
                WHERE user_id = %s
            """, (first_name, last_name, email, location, skills, impact_bio, current_user.id))
        conn.commit()
        flash("Profile updated successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating profile: {e}", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('volunteer_dashboard'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    if current_user.role != 'volunteer': return redirect(url_for('index'))
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not new_password or new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for('volunteer_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password FROM users WHERE id = %s", (current_user.id,))
    user = cursor.fetchone()
    
    if not user or not check_password_hash(user['password'], current_password):
        cursor.close()
        conn.close()
        flash("Incorrect current password.", "error")
        return redirect(url_for('volunteer_dashboard'))
    
    hashed_password = generate_password_hash(new_password)
    try:
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, current_user.id))
        conn.commit()
        flash("Password changed successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error changing password: {e}", "error")
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('volunteer_dashboard'))

@app.route('/ngo_settings', methods=['GET'])
@login_required
def ngo_settings_page(): # Renamed to avoid conflict with POST route
    if current_user.role != 'ngo': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM ngos WHERE user_id = %s", (current_user.id,))
    ngo = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('settings.html', ngo=ngo)

@app.route('/ngo_settings', methods=['POST'])
@login_required
def ngo_settings():
    if current_user.role != 'ngo': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    
    organization_name = request.form.get('organization_name')
    trust_id = request.form.get('trust_id')
    website = request.form.get('website')
    location = request.form.get('location')
    description = request.form.get('description')
    
    try:
        cursor.execute("""
            UPDATE ngos 
            SET organization_name = %s, trust_id = %s, website = %s, location = %s, description = %s
            WHERE user_id = %s
        """, (organization_name, trust_id, website, location, description, current_user.id))
        conn.commit()
        flash("Profile updated successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating profile: {e}", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('ngo_dashboard') + "#settings")

@app.route('/ngo_change_password', methods=['POST'])
@login_required
def ngo_change_password():
    if current_user.role != 'ngo': return redirect(url_for('index'))
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not new_password or new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for('ngo_dashboard') + "#settings")
    
    hashed_password = generate_password_hash(new_password)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, current_user.id))
        conn.commit()
        flash("Password changed successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error changing password: {e}", "error")
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ngo_dashboard') + "#settings")

if __name__ == '__main__':
    app.run(debug=True)
