from flask import Flask, request, jsonify
from flask_compress import Compress

import logging
import sqlite3
from datetime import datetime, timedelta, date

app = Flask(__name__)
Compress(app)
DATABASE = 'data.db'

logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)


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
                timestamp TEXT NOT NULL
            )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_timestamp ON weather(device, timestamp)')
    
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
def get_weather():
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
<div style="max-width:800px; margin: 20px auto;">
    <div style="margin-bottom: 20px;">
        <label for="startDate">Start Date: </label>
        <input type="datetime-local" id="startDate" style="margin-right: 20px;">
        
        <label for="endDate">End Date: </label>
        <input type="datetime-local" id="endDate" style="margin-right: 20px;">
        
        <button onclick="updateChart()" style="padding: 5px 15px;">Update Chart</button>
        <button onclick="resetChart()" style="padding: 5px 15px;">Reset</button>
    </div>
    
    <div id="myChart" style="width:100%; height:500px;"></div>
</div>

<script>
google.charts.load('current',{packages:['corechart']});
google.charts.setOnLoadCallback(initChart);

let fullData;
let chart;

function initChart() {
    // Store full dataset
    fullData = new google.visualization.DataTable();
    fullData.addColumn('datetime', 'Time');
    fullData.addColumn('number', 'Temperature');
    fullData.addRows([
""" + "".join([f"        [new Date('{wdata['timestamp']}'), {wdata['temperature']}],\n" for wdata in weather_data]) + """
    ]);
    
    // Initialize date inputs with data range
    setDefaultDateRange();
    
    // Create chart
    chart = new google.visualization.LineChart(document.getElementById('myChart'));
    
    // Draw initial chart
    drawChart(fullData);
}

function setDefaultDateRange() {
    if (fullData.getNumberOfRows() === 0) return;
    
    // Get min and max dates from data
    let minDate = fullData.getValue(0, 0);
    let maxDate = fullData.getValue(0, 0);
    
    for (let i = 1; i < fullData.getNumberOfRows(); i++) {
        let date = fullData.getValue(i, 0);
        if (date < minDate) minDate = date;
        if (date > maxDate) maxDate = date;
    }
    
    // Set input values
    document.getElementById('startDate').value = formatDateTimeLocal(minDate);
    document.getElementById('endDate').value = formatDateTimeLocal(maxDate);
}

function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function updateChart() {
    const startDateInput = document.getElementById('startDate').value;
    const endDateInput = document.getElementById('endDate').value;
    
    if (!startDateInput || !endDateInput) {
        alert('Please select both start and end dates');
        return;
    }
    
    const startDate = new Date(startDateInput);
    const endDate = new Date(endDateInput);
    
    if (startDate > endDate) {
        alert('Start date must be before end date');
        return;
    }
    
    // Filter data based on date range
    const filteredData = new google.visualization.DataTable();
    filteredData.addColumn('datetime', 'Time');
    filteredData.addColumn('number', 'Temperature');
    
    for (let i = 0; i < fullData.getNumberOfRows(); i++) {
        const date = fullData.getValue(i, 0);
        const temp = fullData.getValue(i, 1);
        
        if (date >= startDate && date <= endDate) {
            filteredData.addRow([date, temp]);
        }
    }
    
    if (filteredData.getNumberOfRows() === 0) {
        alert('No data found in selected date range');
        return;
    }
    
    drawChart(filteredData);
}

function resetChart() {
    setDefaultDateRange();
    drawChart(fullData);
}

function drawChart(data) {
    const options = {
        title: 'Temperature vs Time',
        hAxis: {title: 'Time'},
        vAxis: {title: 'Temperature in Fahrenheit'},
        legend: 'none',
        chartArea: {width: '80%', height: '70%'}
    };
    
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