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
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                device INTEGER NOT NULL,
                timestamp TEXT
            )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS device (
                id	INTEGER PRIMARY KEY AUTOINCREMENT,
         	    name	TEXT NOT NULL
            );
    ''')

    cursor.execute('''
            INSERT INTO device (name)
                   SELECT 'Office'
                   WHERE NOT EXISTS(
                   SELECT 1 FROM device WHERE name = 'Office')
    ''')
    conn.commit()
    conn.close()
    app.logger.info(f"Database initialized: {DATABASE}")

# Ensure DB/table exist when module is imported (e.g. under gunicorn/systemd)
try:
    init_db()
except Exception as _e:
    app.logger.error("init_db on import failed: %s", _e)

@app.route('/')
def hello_world():
    return '<p>Hello, World!</p>'

@app.route('/weather', methods=['POST'])
def add_weather_data():
    """Handle POST request with a number in the body"""
    try:
        # Get the data from request body (expect JSON with temperature & humidity)
        data = request.get_json(silent=True)

        if data is None or 'temperature' not in data or 'humidity' not in data:
            return jsonify({'error': 'Missing temperature or humidity in JSON body'}), 400

        try:
            temperature = float(data['temperature'])
            humidity = float(data['humidity'])
            device = int(data['device'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid temperature or humidity format'}), 400

        timestamp = datetime.now().isoformat()
        app.logger.info(timestamp)
        
        # Insert into database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO weather (temperature, humidity, device, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (temperature, humidity, device, timestamp))
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'id': record_id,
            'temperature': temperature,
            'humidity': humidity,
            'device': device,
            'timestamp': timestamp,
        }), 201
        
    except ValueError:
        return jsonify({'error': 'Invalid number format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/weather', methods=['GET'])
def get_numbers():
    """Get all numbers from the database"""

    query = request.args.get('details')
    try:
        conn = get_db()
        cursor = conn.cursor()
        today = datetime.now() - timedelta(days=1)
        cursor.execute('''
                       SELECT
                            w.id,
                            w.temperature,
                            w.humidity,
                            d.name,
                            w.timestamp
                       FROM 
                            weather as w
                       JOIN 
                            device as d
                       ON 
                            d.id = w.device
                       WHERE 
                            w.timestamp > ? 
                       ORDER BY w.timestamp DESC
                       ''', (today.isoformat(),))
        rows = cursor.fetchall()
        conn.close()
        
        weather_data = []
        for row in rows:
            weather_data.append({
                'id': row['id'],
                'temperature': row['temperature'],
                'humidity': row['humidity'],
                'device': row['name'],
                'timestamp': row['timestamp']
            })
        
        # return jsonify({
        #     'count': len(weather_data),
        #     'weather_data': weather_data
        # }), 200
        if query != None:
            return """
                <h1>Weather Data</h1>
                <p>Temperature and Humidity data:</p>
                <ul>
                """ + "".join([f"<li>ID: {data['id']}, Temperature: {data['temperature']}, Humidity: {data['humidity']}, Device: {data['device']}, Timestamp: {data['timestamp']}</li>" for data in weather_data]) + """
                </ul>

                """, 200
        else:
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
        // Create typed DataTable so first column is Date and second is Number
        const data = new google.visualization.DataTable();
        data.addColumn('datetime', 'Time');
        data.addColumn('number', 'Temperature');
        data.addRows([
    """ + "".join([f"  [new Date('{wdata['timestamp']}'), {wdata['temperature']}],\n" for wdata in weather_data]) + """
        ]);

    // Set Options
    const options = {
    title: 'Temperature vs Time',
    hAxis: {title: 'Time in minutes'},
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

    # Ensure DB/table exist when module is imported (e.g. under gunicorn/systemd)
    try:
        init_db()
    except Exception as _e:
        app.logger.error("init_db on import failed:", _e)