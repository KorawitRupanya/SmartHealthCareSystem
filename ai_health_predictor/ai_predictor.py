import redis
import json
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.exceptions import NotFittedError

r = redis.Redis(host='redis', port=6379)
p = r.pubsub()
p.subscribe('patient_health_data')

model = LinearRegression()
health_data_history = []
model_fitted = False  # A flag to check if the model is fitted
ALERT_THRESHOLD = 80  # Set the threshold for alerts

def train_model():
    global model_fitted
    if len(health_data_history) > 5:
        X = np.array(range(len(health_data_history))).reshape(-1, 1)  # Use indices as features
        y = np.array([data['heart_rate'] for data in health_data_history])  # Target: heart rate
        model.fit(X, y)
        model_fitted = True  # Mark the model as fitted
        print("AI Model trained.")

def predict_resources():
    if model_fitted:
        prediction = model.predict([[len(health_data_history) + 1]])[0]
        print(f"Predicted healthcare resources demand: {prediction}")

        # Publish the prediction
        r.publish('resource_prediction', prediction)

        # Check if the prediction exceeds the threshold and take action
        if prediction > ALERT_THRESHOLD:
            alert_message = {
                'status': 'high',
                'message': f"High demand predicted: {prediction}. Increase staff and prepare equipment."
            }
        else:
            alert_message = {
                'status': 'low',
                'message': f"Demand predicted: {prediction}. No additional resources needed."
            }

        # Publish alert message to another Redis channel
        r.publish('resource_alert', json.dumps(alert_message))
    else:
        print("Model is not fitted yet. Skipping prediction.")

def listen_for_data():
    for message in p.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'].decode('utf-8'))
                health_data_history.append(data)
                print(f"Received health data: {data}")
                train_model()  # Train the model after receiving data
                predict_resources()  # Try to predict resources
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
            except NotFittedError as e:
                print(f"Model not fitted error: {e}")

if __name__ == "__main__":
    listen_for_data()
