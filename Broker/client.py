import paho.mqtt.client as mqtt
import time
import uuid

BROKER_IP = "10.109.111.26"  # ← Remplace par l’IP de la machine qui fait tourner le broker
PORT = 1883
TOPIC_SUB = "chat/general"
TOPIC_PUB = "chat/general"
CLIENT_ID = f"machine-{uuid.uuid4()}"
PRIVATE_SUB = f"chat/private/{CLIENT_ID}"
TEMPERATURE_TOPIC = f"iot/capteurs/"

imposter = False

def on_message(client, userdata, message):
    global imposter
    if (message.topic == PRIVATE_SUB):
        print(message.payload.decode())
        if(message.payload.decode() == "Vous etes l'imposteur"):
            imposter = True

    if (message.topic == TOPIC_SUB): # Changer la condition
        if("Debut de la manche" in message.payload.decode()):
            client.publish(TEMPERATURE_TOPIC, "msg")
            print(f"{message.topic} : {message.payload.decode()}")


# Quand connecté au broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC_SUB)
        client.subscribe(PRIVATE_SUB)
        client.subscribe(TEMPERATURE_TOPIC)
        print("Connecte au broker MQTT")
    else:
        print(f"Échec de connexion, code : {rc}")

# Crée le client MQTT
client = mqtt.Client(client_id=CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message

# Connexion au broker
client.connect(BROKER_IP, PORT)
client.loop_start()

# Boucle d’envoi de messages
try:
    while True:
        input()
        print(imposter)
except KeyboardInterrupt:
    print("\nArrêt")
    client.disconnect()
    client.loop_stop()
