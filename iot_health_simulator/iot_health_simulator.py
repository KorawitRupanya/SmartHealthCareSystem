import time
import redis
import random
import json

r = redis.Redis(host='redis', port=6379)

def simulate_health_data():
    while True:
        heart_rate = random.randint(60, 100)  # Simulated heart rate
        oxygen_level = random.randint(90, 100)  # Simulated oxygen level
        health_data = {
            'heart_rate': heart_rate,
            'oxygen_level': oxygen_level
        }
        r.publish('patient_health_data', json.dumps(health_data))
        print(f"Simulated health data: {health_data}")
        time.sleep(5)

if __name__ == "__main__":
    simulate_health_data()
