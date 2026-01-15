import os
from flask import Flask, render_template, request, redirect, url_for, flash
import database

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'espresso-tracker-secret-key-change-in-production')

# Initialize database on startup
database.init_db()


@app.route('/')
def index():
    """Display all entries with coffee filter option."""
    entries = database.get_all_entries()
    coffees = database.get_all_coffees()
    
    # Calculate extraction ratios for each entry
    for entry in entries:
        entry['extraction_ratio'] = database.calculate_extraction_ratio(
            entry['input_weight'], entry['output_weight']
        )
    
    return render_template('index.html', entries=entries, coffees=coffees)


@app.route('/add', methods=['GET', 'POST'])
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
    
    return render_template('entry_detail.html', entry=entry)


@app.route('/coffee/<coffee_name>')
def coffee_view(coffee_name):
    """View all entries for a specific coffee."""
    entries = database.get_entries_by_coffee(coffee_name)
    coffees = database.get_all_coffees()
    
    if not entries:
        flash(f'No entries found for coffee: {coffee_name}', 'info')
        return redirect(url_for('index'))
    
    # Calculate extraction ratios for each entry
    for entry in entries:
        entry['extraction_ratio'] = database.calculate_extraction_ratio(
            entry['input_weight'], entry['output_weight']
        )
    
    return render_template('coffee_view.html', entries=entries, 
                         coffee_name=coffee_name, coffees=coffees)


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
