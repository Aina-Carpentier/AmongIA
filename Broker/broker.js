const aedes = require('aedes')();
const net = require('net');
const mqtt = require('mqtt');

const PORT = 1883;
const PLAYERS = 17
const MAX_ROUNDS = 10

// --- Lancer le broker ---
const server = net.createServer(aedes.handle);
const clients = []

let temperatures = {}
let votes = {}
let imposterClient = ""
let gameState = "stop"
let currentRound = 1
let baseCoordinates = {
  "lat" : 0,
  "lon" : 0
}

server.listen(PORT, () => {
  console.log(`✅ Broker MQTT en écoute sur le port ${PORT}`);

  // --- Une fois le broker démarré, créer un client MQTT interne ---
  const publisher = mqtt.connect(`mqtt://localhost:${PORT}`);

  publisher.on('connect', () => {
    console.log('🧠 Client MQTT interne connecté au broker');
  });

  
  aedes.on('client', (client) => {
      setTimeout(() => {
        if (client.id.includes("machine") && gameState === "stop"){
          clients.push(client.id)

          console.log(`${client.id} a rejoint la partie`)
          publisher.publish("chat/general", `${client.id} a rejoint la partie`)


          if(clients.length >= PLAYERS){
            publisher.publish('chat/general', `Debut de la partie, selection de l'imposteur en cours...`)

            imposterClient = pickImposter(clients, publisher)
            console.log(imposterClient, "imposter")
            
            gameState = "temperatures"
            baseCoordinates = randomCoordinates()

            publisher.publish('chat/general', `Debut de la manche ${currentRound}, coordonnees de base : ${JSON.stringify(baseCoordinates)}`)

            clients.map((cli) => {
              let clientCoordinates = customedCoordinates(baseCoordinates)
              publisher.publish(`chat/private/${cli}`, `Vos coordonnees : ${JSON.stringify(clientCoordinates)}`)
              console.log(`coordinates pour ${cli}: ${JSON.stringify(clientCoordinates)}`)
            })
          }
      }

      else if(client.id !== publisher.options.clientId){
        client.close()
      }
    }, 1000)
  });

  aedes.on('publish', (packet, client) => {
    if (client && client.id !== publisher.options.clientId) {
      if(gameState === "temperatures" && packet.topic.includes("chat/temperatures")){
        temperatures[client.id] = packet.payload.toString()
        
        if (Object.keys(temperatures).length === clients.length){
          publisher.publish('chat/general', `Fin de la manche ${currentRound}`)
          publisher.publish('chat/general', `Temperatures : ${JSON.stringify(temperatures)}`)
          console.log(temperatures)
          
          currentRound++
          temperatures = {}
          
          setTimeout(() => {
            if (currentRound <= MAX_ROUNDS){
                baseCoordinates = randomCoordinates()

                publisher.publish('chat/general', `Debut de la manche ${currentRound}, coordonnees de base : ${JSON.stringify(baseCoordinates)}`)

                clients.map((cli) => {
                  let clientCoordinates = customedCoordinates(baseCoordinates)
                  publisher.publish(`chat/private/${cli}`, `Vos coordonnees : ${JSON.stringify(clientCoordinates)}`)
                  console.log(`coordinates pour ${cli}: ${JSON.stringify(clientCoordinates)}`)
                })
            } else {
              publisher.publish("chat/general", "Debut de la phase de vote, veuillez indiquer pour qui vous souhaitez voter")
              console.log("Debut de la phase de vote, veuillez indiquer pour qui vous souhaitez voter")
              gameState = "votes"
            } 
          }, 1000)
        }
      }

      else if(gameState === "votes" && packet.topic.includes("chat/votes")){
        votes[client.id] = packet.payload.toString()
        console.log(votes)

        if (Object.keys(votes).length === clients.length){
          let voteResult = getVotesCount(votes);
          let maxClient = getMaxVotedClient(voteResult);

          
          publisher.publish("chat/general", `Machine(s) ayant recu le plus de votes : ${maxClient.toString()}`)
          console.log(`Machine(s) ayant recu le plus de votes : ${maxClient.toString()}`)
          
          setTimeout(() => {
            let result
            publisher.publish("chat/general", `L'imposteur était : ${imposterClient}`)
            console.log(`L'imposteur était : ${imposterClient}`)
  
            if (!maxClient.includes(imposterClient)){
              result = "L'imposteur n'ayant pas ete le plus vote, il remporte la partie."
            }
  
            else if (maxClient.length !== 1){
              result = "L'imposteur n'ayant pas ete le seul avec le plus de votes, il remporte la partie."
            }
  
            else{
              result = "L'imposteur ayant été le seul avec le plus de votes, il perd la partie."
            }

            publisher.publish("chat/general", result)
            console.log(result)
            
            gameState = "stop"
            
          }, 2000)
        }
      }
    }
  });

  aedes.on('clientDisconnect', (client) => {
    const index = clients.indexOf(client.id);
    if (index !== -1) {
      clients.splice(index, 1);
      
      console.log(`${client.id} a quitté la partie`)
      publisher.publish("chat/general", `Fin de la partie, ${client.id} a quitte la partie`)
      
      reset()
    }
  });
});


const randomCoordinates = () => {
  return {
    "lat": Math.random() * 180 - 90,
    "lon": Math.random() * 360 - 180
  }
}

const customedCoordinates = (coordinates) => {
  const movedCoordinates = {
    "lat": coordinates["lat"] + Math.random() * 3 - 1.5,
    "lon": coordinates["lon"] + Math.random() * 3 - 1.5
  }

  if (movedCoordinates["lat"] > 90)
    movedCoordinates["lat"] = 180 - movedCoordinates["lat"]

  else if (movedCoordinates["lat"] < -90)
    movedCoordinates["lat"] = -180 - movedCoordinates["lat"]

  if (movedCoordinates["lon"] > 180)
    movedCoordinates["lon"] = movedCoordinates["lon"] - 360

  else if (movedCoordinates["lon"] < - 180)
    movedCoordinates["lon"] = movedCoordinates["lon"] + 360

  return movedCoordinates
}

const pickImposter = (clients, publisher) => {
  const imposterClient = clients[Math.floor(Math.random() * clients.length)]
  publisher.publish(`chat/private/${imposterClient}`, "Vous etes l'imposteur")
  return imposterClient
}

const getVotesCount = (votes) => {
  let voteCount = {};

  for (let voter in votes) {
    let votedMachine = votes[voter];
    
    if (voteCount[votedMachine]) {
      voteCount[votedMachine] += 1;
    } else {
      voteCount[votedMachine] = 1;
    }
  }

  return voteCount;
}

const getMaxVotedClient = (voteCount) => {
  let maxVotes = 0;
  let maxClient = [];

  for (let client in voteCount) {
    if (voteCount[client] > maxVotes) {
      maxVotes = voteCount[client];
      maxClient = [client];
    } else if (voteCount[client] === maxVotes) {
      maxClient.push(client);
    }
  }

  return maxClient;
}

const reset = () => {
    temperatures = {}
    votes = {}
    imposterClient = ""
    gameState = "stop"
    currentRound = 1
}