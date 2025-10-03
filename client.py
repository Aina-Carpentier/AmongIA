# pylint: disable=invalid-name
# pylint: disable=missing-docstring
# pylint: disable=global-statement
# pylint: disable=redefined-outer-name

import threading
import paho.mqtt.client as mqtt
import uuid
import json
import requests
import random

BROKER_IP = "10.109.111.21"  # ← Remplace par l’IP de la machine qui fait tourner le broker
BROKER_PORT = 1883
API_IP = "10.109.111.21"
API_PORT = 8080

CLIENT_ID = f"machine-{uuid.uuid4()}"

GENERAL_TOPIC = "chat/general"
PRIVATE_TOPIC = f"chat/private/{CLIENT_ID}"
TEMPERATURES_TOPIC = "chat/temperatures"
VOTES_TOPIC = "chat/votes"

ECART_IMPOSTER = [20, 40]

imposter = False
temperatures = {}
coordinates = {}

def reset():
    global imposter, temperatures, coordinates

    imposter = False
    temperatures = {}
    coordinates = {}

def on_message(client, userdata, message):
    
    global imposter, coordinates

    messageContent = message.payload.decode()
    print(messageContent)

    if message.topic == PRIVATE_TOPIC:
        if messageContent == "Vous etes l'imposteur":
            imposter = True

        elif "Vos coordonnees" in messageContent:
            coordinatesValue = messageContent.replace("Vos coordonnees : ", "")
            coordinates = json.loads(coordinatesValue)
            
            client.publish(TEMPERATURES_TOPIC, getTemp(imposter, coordinates))
            


    elif message.topic == GENERAL_TOPIC:
        if "Temperatures" in messageContent:
            temperaturesString = messageContent.replace("Temperatures : ", "")
            lastTemps = json.loads(temperaturesString)

            for key in lastTemps.keys():
                if key in temperatures:
                    temperatures[key].append(lastTemps[key])
                else:
                    temperatures[key] = [lastTemps[key]]

            print(lastTemps)

        elif "Debut de la phase de vote" in messageContent:
            threading.Thread(target=handle_vote, args=(client,), daemon=True).start()

        elif("Fin de la partie" in messageContent or "Debut de la partie" in messageContent):
            reset()


def handle_vote(client):
    suspectedPlayer = findImposter()
    client.publish(VOTES_TOPIC, suspectedPlayer)
    print(f"Vote pour {suspectedPlayer}")

# Quand connecté au broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(GENERAL_TOPIC)
        client.subscribe(PRIVATE_TOPIC)
        print("Connecte au broker MQTT")
    else:
        print(f"Échec de connexion, code : {rc}")

def getTemp(imposter, coordinates):
    response = requests.get(f"http://{API_IP}:{API_PORT}/temp/lat={coordinates['lat']};lon={coordinates['lon']}", timeout=15)
    temp = json.loads(response.text)["tmp"]

    if imposter:
        temp += round(random.choice(list(range(-ECART_IMPOSTER[1],-ECART_IMPOSTER[0]+1)) + list(range(ECART_IMPOSTER[0], ECART_IMPOSTER[1]+1)))/10)

    return temp

def findImposter():
    temperatures.pop(CLIENT_ID)
    url = "http://10.103.1.12:11434/api/generate"  # ou autre IP:PORT si déporté
    headers = {
        "Content-Type": "application/json"
    }

    prompt = f"""
    Tu es un détective chargé d'identifier une machine imposteur parmi plusieurs. Chaque machine envoie une série de températures. Une seule machine est suspecte : elle envoie des températures anormales.

    Analyse uniquement les autres machines et déduis laquelle est l’imposteur.
    Réponds uniquement avec le nom de la machine (clé) qui semble être l'imposteur Aucune autre information ou explication ne doit être ajoutée.

    Voici les données de température à analyser :
    {json.dumps(temperatures, indent=2)}
    """

    payload = {
        "model": "gemma3:4b",  # adapte selon le modèle que tu as chargé
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()["response"].strip()

        return result
    
    except Exception as e:
        print(f"Erreur Ollama : {e}")
        return "inconnu"

def getVotesCount(votes) :
    voteCount = {}

    for voter in votes:
        votedMachine = votes[voter]

        if votedMachine != CLIENT_ID:
            if voteCount[votedMachine]:
                voteCount[votedMachine] += 1

            else:
                voteCount[votedMachine] = 1


    return voteCount

def getMaxVotedClient(voteCount):
    maxVotes = 0
    maxMachine = []

    for machine in voteCount:
        if voteCount[client] > maxVotes:
            maxVotes = voteCount[machine]
            maxMachine = [machine]

        elif voteCount[client] == maxVotes:
            maxMachine.append(client)

    return maxMachine

# Crée le client MQTT
client = mqtt.Client(client_id=CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message

# Connexion au broker
client.connect(BROKER_IP, BROKER_PORT)
client.loop_start()

# Boucle d’envoi de messages
try:
    while True:
        input()

except KeyboardInterrupt:
    print("\nArrêt")
    client.disconnect()
    client.loop_stop()
