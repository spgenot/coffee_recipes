import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import database
from models import User

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'espresso-tracker-secret-key-change-in-production')

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user from database for Flask-Login."""
    user_dict = database.get_user_by_id(int(user_id))
    return User.from_dict(user_dict) if user_dict else None

# Configure Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

# Password reset token serializer
serializer = URLSafeTimedSerializer(app.secret_key)

# Initialize database on startup
database.init_db()


def send_password_reset_email(user, token):
    """Send password reset email."""
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = Message(
        subject='Reset Your Password - Espresso Tracker',
        recipients=[user.email],
        body=f'''To reset your password, visit the following link:
{reset_url}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email.
'''
    )
    try:
        mail.send(msg)
    except Exception as e:
        app.logger.error(f'Failed to send email: {e}')


@app.route('/')
def index():
    """Display all entries with coffee filter option."""
    user_id = current_user.id if current_user.is_authenticated else None
    entries = database.get_all_entries(user_id)
    coffees = database.get_all_coffees()
    
    # Separate user entries from community entries
    user_entries = []
    community_entries = []
    
    for entry in entries:
        entry['extraction_ratio'] = database.calculate_extraction_ratio(
            entry['input_weight'], entry['output_weight']
        )
        if user_id and entry.get('user_id') == user_id:
            user_entries.append(entry)
        else:
            community_entries.append(entry)
    
    return render_template('index.html', 
                         user_entries=user_entries, 
                         community_entries=community_entries,
                         coffees=coffees)


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_entry():
    """Add a new espresso entry."""
    if request.method == 'POST':
        coffee = request.form.get('coffee', '').strip()
        grinder_setting = request.form.get('grinder_setting', '').strip()
        input_weight = request.form.get('input_weight', '').strip()
        output_weight = request.form.get('output_weight', '').strip()
        taste_comment = request.form.get('taste_comment', '').strip()
        
        # Validation
        errors = []
        if not coffee:
            errors.append('Coffee name is required')
        if not grinder_setting:
            errors.append('Grinder setting is required')
        if not input_weight:
            errors.append('Input weight is required')
        elif not _is_valid_number(input_weight):
            errors.append('Input weight must be a valid number')
        if not output_weight:
            errors.append('Output weight is required')
        elif not _is_valid_number(output_weight):
            errors.append('Output weight must be a valid number')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            coffees = database.get_all_coffees()
            return render_template('add_entry.html', coffees=coffees,
                                 coffee=coffee, grinder_setting=grinder_setting,
                                 input_weight=input_weight, output_weight=output_weight,
                                 taste_comment=taste_comment)
        
        # Add entry to database
        try:
            entry_id = database.add_entry(
                user_id=current_user.id,
                coffee=coffee,
                grinder_setting=grinder_setting,
                input_weight=float(input_weight),
                output_weight=float(output_weight),
                taste_comment=taste_comment
            )
            flash('Entry added successfully!', 'success')
            return redirect(url_for('view_entry', entry_id=entry_id))
        except Exception as e:
            flash(f'Error adding entry: {str(e)}', 'error')
            coffees = database.get_all_coffees()
            return render_template('add_entry.html', coffees=coffees)
    
    # GET request - show form
    coffees = database.get_all_coffees()
    return render_template('add_entry.html', coffees=coffees)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        if not email:
            errors.append('Email is required')
        elif '@' not in email:
            errors.append('Invalid email format')
        if not password:
            errors.append('Password is required')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters')
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html', email=email)
        
        # Create user
        try:
            user_id = database.create_user(email, password)
            user_dict = database.get_user_by_id(user_id)
            user = User.from_dict(user_dict)
            login_user(user)
            flash('Registration successful! Welcome!', 'success')
            return redirect(url_for('index'))
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('register.html', email=email)
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            return render_template('register.html', email=email)
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return render_template('login.html', email=email)
        
        user_dict = database.get_user_by_email(email)
        if user_dict and database.verify_password(user_dict, password):
            user = User.from_dict(user_dict)
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
            return render_template('login.html', email=email)
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address', 'error')
            return render_template('forgot_password.html')
        
        user_dict = database.get_user_by_email(email)
        if user_dict:
            user = User.from_dict(user_dict)
            # Generate reset token (expires in 1 hour)
            token = serializer.dumps(user.email, salt='password-reset-salt')
            try:
                send_password_reset_email(user, token)
                flash('Password reset email sent! Check your inbox.', 'success')
            except Exception as e:
                flash('Failed to send email. Please try again later.', 'error')
                app.logger.error(f'Email send error: {e}')
        else:
            # Don't reveal if email exists for security
            flash('If that email exists, a password reset link has been sent.', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception:
        flash('Invalid or expired reset token', 'error')
        return redirect(url_for('forgot_password'))
    
    user_dict = database.get_user_by_email(email)
    if not user_dict:
        flash('User not found', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        if not password:
            errors.append('Password is required')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters')
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('reset_password.html', token=token)
        
        try:
            database.update_user_password(user_dict['id'], password)
            flash('Password reset successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Password reset failed: {str(e)}', 'error')
            return render_template('reset_password.html', token=token)
    
    return render_template('reset_password.html', token=token)


@app.route('/entry/<int:entry_id>')
def view_entry(entry_id):
    """View a single entry."""
    entry = database.get_entry_by_id(entry_id)
    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('index'))
    
    entry['extraction_ratio'] = database.calculate_extraction_ratio(
        entry['input_weight'], entry['output_weight']
    )
    
    # Check if user owns this entry
    is_owner = current_user.is_authenticated and entry.get('user_id') == current_user.id
    
    return render_template('entry_detail.html', entry=entry, is_owner=is_owner)


@app.route('/coffee/<coffee_name>')
def coffee_view(coffee_name):
    """View all entries for a specific coffee."""
    user_id = current_user.id if current_user.is_authenticated else None
    
    if user_id:
        user_entries, anonymous_entries = database.get_user_and_anonymous_entries_by_coffee(
            coffee_name, user_id
        )
        
        # Calculate extraction ratios
        for entry in user_entries:
            entry['extraction_ratio'] = database.calculate_extraction_ratio(
                entry['input_weight'], entry['output_weight']
            )
        for entry in anonymous_entries:
            entry['extraction_ratio'] = database.calculate_extraction_ratio(
                entry['input_weight'], entry['output_weight']
            )
        
        if not user_entries and not anonymous_entries:
            flash(f'No entries found for coffee: {coffee_name}', 'info')
            return redirect(url_for('index'))
        
        coffees = database.get_all_coffees()
        return render_template('coffee_view.html', 
                             user_entries=user_entries,
                             anonymous_entries=anonymous_entries,
                             coffee_name=coffee_name, 
                             coffees=coffees)
    else:
        entries = database.get_entries_by_coffee(coffee_name, None)
        coffees = database.get_all_coffees()
        
        if not entries:
            flash(f'No entries found for coffee: {coffee_name}', 'info')
            return redirect(url_for('index'))
        
        # Calculate extraction ratios for each entry
        for entry in entries:
            entry['extraction_ratio'] = database.calculate_extraction_ratio(
                entry['input_weight'], entry['output_weight']
            )
        
        return render_template('coffee_view.html', 
                             user_entries=[],
                             anonymous_entries=entries,
                             coffee_name=coffee_name, 
                             coffees=coffees)


@app.route('/entry/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    """Edit an espresso entry."""
    entry = database.get_entry_by_id(entry_id)
    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('index'))
    
    # Check ownership
    if entry.get('user_id') != current_user.id:
        flash('You can only edit your own entries', 'error')
        return redirect(url_for('view_entry', entry_id=entry_id))
    
    if request.method == 'POST':
        coffee = request.form.get('coffee', '').strip()
        grinder_setting = request.form.get('grinder_setting', '').strip()
        input_weight = request.form.get('input_weight', '').strip()
        output_weight = request.form.get('output_weight', '').strip()
        taste_comment = request.form.get('taste_comment', '').strip()
        
        # Validation
        errors = []
        if not coffee:
            errors.append('Coffee name is required')
        if not grinder_setting:
            errors.append('Grinder setting is required')
        if not input_weight:
            errors.append('Input weight is required')
        elif not _is_valid_number(input_weight):
            errors.append('Input weight must be a valid number')
        if not output_weight:
            errors.append('Output weight is required')
        elif not _is_valid_number(output_weight):
            errors.append('Output weight must be a valid number')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('edit_entry.html', entry=entry, 
                                 coffee=coffee, grinder_setting=grinder_setting,
                                 input_weight=input_weight, output_weight=output_weight,
                                 taste_comment=taste_comment)
        
        # Update entry
        try:
            database.update_entry(
                entry_id=entry_id,
                user_id=current_user.id,
                coffee=coffee,
                grinder_setting=grinder_setting,
                input_weight=float(input_weight),
                output_weight=float(output_weight),
                taste_comment=taste_comment
            )
            flash('Entry updated successfully!', 'success')
            return redirect(url_for('view_entry', entry_id=entry_id))
        except PermissionError as e:
            flash(str(e), 'error')
            return redirect(url_for('view_entry', entry_id=entry_id))
        except Exception as e:
            flash(f'Error updating entry: {str(e)}', 'error')
            return render_template('edit_entry.html', entry=entry)
    
    # GET request - show form
    return render_template('edit_entry.html', entry=entry)


@app.route('/entry/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(entry_id):
    """Delete an espresso entry."""
    entry = database.get_entry_by_id(entry_id)
    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('index'))
    
    # Check ownership
    if entry.get('user_id') != current_user.id:
        flash('You can only delete your own entries', 'error')
        return redirect(url_for('view_entry', entry_id=entry_id))
    
    try:
        database.delete_entry(entry_id, current_user.id)
        flash('Entry deleted successfully!', 'success')
        return redirect(url_for('index'))
    except PermissionError as e:
        flash(str(e), 'error')
        return redirect(url_for('view_entry', entry_id=entry_id))
    except Exception as e:
        flash(f'Error deleting entry: {str(e)}', 'error')
        return redirect(url_for('view_entry', entry_id=entry_id))


def _is_valid_number(value):
    """Check if a string is a valid number."""
    try:
        float(value)
        return True
    except ValueError:
        return False


if __name__ == '__main__':
    # Development server only - production uses gunicorn
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
