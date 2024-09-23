from flask import Flask, render_template, jsonify, Response
from flasgger import Swagger
import redis
import json
from threading import Thread

app = Flask(__name__)
swagger = Swagger(app)

# Redis connection
r = redis.Redis(host='redis', port=6379)

# To store received data
health_data_history = []
predictions_history = []

# Subscribe to Redis channels
p = r.pubsub()
p.subscribe('patient_health_data')
p.subscribe('resource_prediction')

# Background listener to collect data from Redis
def listen_to_redis():
    for message in p.listen():
        if message['type'] == 'message':
            try:
                channel = message['channel'].decode('utf-8')
                if channel == 'patient_health_data':
                    data = json.loads(message['data'].decode('utf-8'))
                    health_data_history.append(data)
                    print(f"Received health data: {data}")  # Debugging line
                elif channel == 'resource_prediction':
                    data = message['data'].decode('utf-8')
                    # Check for numpy float format
                    if 'np.float64(' in data:
                        prediction = float(data.split('np.float64(')[-1].rstrip(')'))
                    else:
                        prediction = float(data)
                    predictions_history.append(prediction)
                    print(f"Received prediction: {prediction}")  # Debugging line
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
            except ValueError as e:
                print(f"Error converting to float: {e}")

# Main dashboard route
@app.route('/')
def dashboard():
    return render_template('dashboard.html', health_data=health_data_history[-10:], predictions=predictions_history[-10:])

# API route to fetch data
@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({
        'health_data': health_data_history[-10:],
        'predictions': predictions_history[-10:]
    })

# Server-sent events route for alerts
def event_stream():
    pubsub = r.pubsub()
    pubsub.subscribe('resource_prediction')
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = message['data'].decode('utf-8')
                # Check for numpy float format
                if 'np.float64(' in data:
                    prediction = float(data.split('np.float64(')[-1].rstrip(')'))
                else:
                    prediction = float(data)
                
                alert_data = {
                    "prediction": prediction,
                    "status": "high" if prediction > 80 else "low",
                    "message": "Increase staff and prepare equipment!" if prediction > 80 else "Patient stable, no additional resources needed."
                }
                yield f"data: {json.dumps(alert_data)}\n\n"
            except ValueError:
                print(f"Error in prediction format: {message['data']}")

@app.route('/api/alerts')
def alerts():
    return Response(event_stream(), content_type='text/event-stream')

if __name__ == "__main__":
    redis_thread = Thread(target=listen_to_redis)
    redis_thread.start()
    app.run(host='0.0.0.0', port=3000)
