from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timedelta, date

app = Flask(__name__)
DATABASE = 'data.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database initialized: {DATABASE}")

@app.route('/')
def hello_world():
    return '<p>Hello, World!</p>'

@app.route('/number', methods=['POST'])
def add_number():
    """Handle POST request with a number in the body"""
    try:
        # Get the data from request body
        data = request.get_json()
        
        # Handle both JSON and plain text
        if data is not None and 'number' in data:
            number = int(data['number'])
        elif request.data:
            number = int(request.data.decode('utf-8'))
        else:
            return jsonify({'error': 'No number provided'}), 400
        
        # Insert into database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO numbers (value) VALUES (?)', (number,))
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'id': record_id,
            'number': number,
            'message': f'Number {number} saved successfully'
        }), 201
        
    except ValueError:
        return jsonify({'error': 'Invalid number format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/numbers', methods=['GET'])
def get_numbers():
    """Get all numbers from the database"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        today = date.today() - timedelta(days=1)
        cursor.execute(f"SELECT * FROM numbers WHERE timestamp > {today.isoformat()} ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        
        numbers = []
        for row in rows:
            if row['value'] > 0:
                numbers.append({
                    'id': row['id'],
                    'value': row['value'],
                    'timestamp': row['timestamp']
                })
        
        # return jsonify({
        #     'count': len(numbers),
        #     'numbers': numbers
        # }), 200
        # return """
        # <h1>Test</h1>
        # <p>This is a test page.</p>
        # <ul>
        # """ + "".join([f"<li>ID: {num['id']}, Value: {num['value']}, Timestamp: {num['timestamp']}</li>" for num in numbers]) + """
        # </ul>

        # """, 200
        return """
        <!DOCTYPE html>
<html>
<script src="https://www.gstatic.com/charts/loader.js"></script>
<body>
<div id="myChart" style="width:100%; max-width:600px; height:500px;"></div>

<script>
google.charts.load('current',{packages:['corechart']});
google.charts.setOnLoadCallback(drawChart);

function drawChart() {

// Set Data
const data = google.visualization.arrayToDataTable([
    ['Time', 'Temperature'],
""" + "".join([f"  [new Date(new Date('{num['timestamp']}').getTime() - 5*60*60*1000), {num['value']}],\n" for num in numbers]) + """
]);

// Set Options
const options = {
  title: 'Temperature vs Time',
  hAxis: {title: 'Time in Seconds'},
  vAxis: {title: 'Temperature in Fahrenheit'},
  legend: 'none'    
};

// Draw
const chart = new google.visualization.LineChart(document.getElementById('myChart'));
chart.draw(data, options);

}
</script>

</body>
</html>
        """, 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/numbers/<int:number_id>', methods=['GET'])
def get_number(number_id):
    """Get a specific number by ID"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM numbers WHERE id = ?', (number_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return jsonify({'error': 'Number not found'}), 404
        
        return jsonify({
            'id': row['id'],
            'value': row['value'],
            'timestamp': row['timestamp']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/numbers/<int:number_id>', methods=['DELETE'])
def delete_number(number_id):
    """Delete a specific number by ID"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM numbers WHERE id = ?', (number_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Number not found'}), 404
        
        conn.close()
        return jsonify({
            'success': True,
            'message': f'Number {number_id} deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
