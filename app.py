from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import random
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

DATABASE = 'tickets.db'

# Initialize Database
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            contact TEXT NOT NULL,
            date TEXT NOT NULL,
            category TEXT,
            description TEXT NOT NULL,
            additional_comments TEXT,
            admin_reply TEXT,
            status TEXT DEFAULT 'open',
            agent TEXT DEFAULT 'Unassigned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# Generate unique ticket ID
def generate_ticket_id():
    return f"T{random.randint(10000000, 99999999)}"

# Get database connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Serve HTML files - Default to customer homepage
@app.route('/')
def index():
    if os.path.exists('customer/customer_home.html'):
        return send_from_directory('customer', 'customer_home.html')
    else:
        return "Homepage not found. Try accessing /customer/customer_home.html directly", 404

# Serve customer files
@app.route('/customer/<path:path>')
def serve_customer(path):
    return send_from_directory('customer', path)

# Serve admin files
@app.route('/admin/<path:path>')
def serve_admin(path):
    return send_from_directory('admin', path)

# Serve any file from root directory (images, CSS, etc.)
@app.route('/<path:path>')
def serve_file(path):
    # First check if it's a folder path
    if '/' in path:
        folder, filename = path.split('/', 1)
        if folder == 'customer' and os.path.exists(f'customer/{filename}'):
            return send_from_directory('customer', filename)
        elif folder == 'admin' and os.path.exists(f'admin/{filename}'):
            return send_from_directory('admin', filename)
    
    # Check root directory
    if os.path.exists(path):
        return send_from_directory('.', path)
    
    # Check customer folder
    elif os.path.exists(f'customer/{path}'):
        return send_from_directory('customer', path)
    
    # Check admin folder
    elif os.path.exists(f'admin/{path}'):
        return send_from_directory('admin', path)
    
    else:
        return f"File not found: {path}", 404

# API Routes

# Get all tickets (Admin)
@app.route('/api/tickets', methods=['GET'])
def get_all_tickets():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        status_filter = request.args.get('status')
        agent_filter = request.args.get('agent')
        
        query = "SELECT * FROM tickets WHERE 1=1"
        params = []
        
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        
        if agent_filter:
            query += " AND agent = ?"
            params.append(agent_filter)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        tickets = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'tickets': tickets})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get single ticket
@app.route('/api/tickets/<ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        conn.close()
        
        if ticket:
            return jsonify({'success': True, 'ticket': dict(ticket)})
        else:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Create new ticket
@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    try:
        data = request.json
        
        # Validation
        required_fields = ['name', 'email', 'contact', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        ticket_id = generate_ticket_id()
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tickets (ticket_id, name, email, contact, date, category, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticket_id,
            data['name'],
            data['email'],
            data['contact'],
            data.get('date', ''),
            data.get('category', ''),
            data['description']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'ticket_id': ticket_id})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Update ticket
@app.route('/api/tickets/<ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    try:
        data = request.json
        
        conn = get_db()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if 'additional_comments' in data:
            updates.append("additional_comments = ?")
            params.append(data['additional_comments'])
        
        if 'admin_reply' in data:
            updates.append("admin_reply = ?")
            params.append(data['admin_reply'])
        
        if 'status' in data:
            updates.append("status = ?")
            params.append(data['status'])
        
        if 'agent' in data:
            updates.append("agent = ?")
            params.append(data['agent'])
        
        if not updates:
            return jsonify({'success': False, 'error': 'No fields to update'}), 400
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(ticket_id)
        
        query = f"UPDATE tickets SET {', '.join(updates)} WHERE ticket_id = ?"
        cursor.execute(query, params)
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected == 0:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Close ticket
@app.route('/api/tickets/<ticket_id>/close', methods=['POST'])
def close_ticket(ticket_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tickets 
            SET status = 'closed', updated_at = CURRENT_TIMESTAMP 
            WHERE ticket_id = ?
        ''', (ticket_id,))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected == 0:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Search tickets by email
@app.route('/api/tickets/search', methods=['GET'])
def search_tickets():
    try:
        email = request.args.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email parameter required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE email = ? ORDER BY created_at DESC", (email,))
        tickets = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'tickets': tickets})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
# Ticket Dashboard Endpoint - REAL DATA FROM DATABASE
@app.route('/api/dashboard/tickets', methods=['GET'])
def get_ticket_dashboard():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get basic stats
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE status = 'closed'")
        resolved_result = cursor.fetchone()
        resolved = resolved_result['count'] if resolved_result else 0
        
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE status != 'closed'")
        unresolved_result = cursor.fetchone()
        unresolved = unresolved_result['count'] if unresolved_result else 0
        
        cursor.execute("SELECT COUNT(*) as count FROM tickets")
        total_result = cursor.fetchone()
        total = total_result['count'] if total_result else 0
        
        # Get tickets by category
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM tickets 
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category 
            ORDER BY count DESC
        """)
        category_data = cursor.fetchall()
        
        # Get tickets by status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM tickets 
            GROUP BY status
        """)
        status_data = cursor.fetchall()
        
        # Get top issues (by category)
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM tickets 
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category 
            ORDER BY count DESC 
            LIMIT 4
        """)
        top_issues = cursor.fetchall()
        
        # Get tickets over time (monthly for current year)
        cursor.execute("""
            SELECT strftime('%m', created_at) as month, 
                   COUNT(*) as count 
            FROM tickets 
            WHERE strftime('%Y', created_at) = strftime('%Y', 'now')
            GROUP BY month
            ORDER BY month
        """)
        current_year_tickets = cursor.fetchall()
        
        # Get tickets over time (monthly for previous year)
        cursor.execute("""
            SELECT strftime('%m', created_at) as month, 
                   COUNT(*) as count 
            FROM tickets 
            WHERE strftime('%Y', created_at) = strftime('%Y', 'now', '-1 year')
            GROUP BY month
            ORDER BY month
        """)
        previous_year_tickets = cursor.fetchall()
        
        # Get weekly resolution time data (last 6 weeks)
        cursor.execute("""
            SELECT 
                strftime('%W', created_at) as week,
                AVG(CASE 
                    WHEN status = 'closed' AND updated_at IS NOT NULL 
                    THEN (julianday(updated_at) - julianday(created_at)) * 24 
                    ELSE NULL 
                END) as avg_hours
            FROM tickets
            WHERE created_at >= date('now', '-42 days')
            GROUP BY week
            ORDER BY week DESC
            LIMIT 6
        """)
        resolution_time_current = cursor.fetchall()
        
        # Same for previous period
        cursor.execute("""
            SELECT 
                strftime('%W', created_at) as week,
                AVG(CASE 
                    WHEN status = 'closed' AND updated_at IS NOT NULL 
                    THEN (julianday(updated_at) - julianday(created_at)) * 24 
                    ELSE NULL 
                END) as avg_hours
            FROM tickets
            WHERE created_at >= date('now', '-84 days') AND created_at < date('now', '-42 days')
            GROUP BY week
            ORDER BY week DESC
            LIMIT 6
        """)
        resolution_time_previous = cursor.fetchall()
        
        # Calculate average response time (in hours)
        cursor.execute("""
            SELECT AVG((julianday(updated_at) - julianday(created_at)) * 24) as avg_hours
            FROM tickets
            WHERE status = 'closed' AND updated_at IS NOT NULL
        """)
        avg_time_result = cursor.fetchone()
        avg_response_time = int(avg_time_result['avg_hours']) if avg_time_result and avg_time_result['avg_hours'] else 0
        
        conn.close()
        
        # Helper function to format monthly data
        def format_ticket_monthly(query_results):
            monthly = [0] * 12
            for row in query_results:
                month_index = int(row['month']) - 1
                monthly[month_index] = row['count']
            return monthly
        
        # Helper function to format weekly resolution time
        def format_resolution_time(query_results):
            weeks = [row['avg_hours'] if row['avg_hours'] else 0 for row in query_results]
            weeks.reverse()  # Oldest to newest
            # Pad to 6 weeks if needed
            while len(weeks) < 6:
                weeks.insert(0, 0)
            return weeks[:6]
        
        # Build response data
        data = {
            'stats': {
                'resolved': resolved,
                'unresolved': unresolved,
                'total': total,
                'avgResponseTime': avg_response_time
            },
            'charts': {
                'category': {
                    'labels': [row['category'] if row['category'] else 'Uncategorized' for row in category_data],
                    'data': [row['count'] for row in category_data]
                },
                'resolutionTime': {
                    'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6'],
                    'current': format_resolution_time(resolution_time_current),
                    'previous': format_resolution_time(resolution_time_previous)
                },
                'status': {
                    'labels': [row['status'].title() for row in status_data],
                    'data': [row['count'] for row in status_data]
                },
                'topIssues': {
                    'labels': [row['category'] if row['category'] else 'Uncategorized' for row in top_issues],
                    'data': [row['count'] for row in top_issues]
                },
                'overtime': {
                    'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                    'current': format_ticket_monthly(current_year_tickets),
                    'previous': format_ticket_monthly(previous_year_tickets)
                }
            }
        }
        
        return jsonify(data)
    
    except Exception as e:
        print(f"Error in ticket dashboard: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)