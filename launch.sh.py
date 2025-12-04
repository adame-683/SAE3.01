#!/bin/bash

echo "=== Démarrage du système de routage en oignon ==="

# Démarrer le Master
echo "Démarrage du Master..."
python3 master_gui.py &
MASTER_PID=$!
sleep 2

# Démarrer 3 routeurs
echo "Démarrage des routeurs..."
python3 router.py 1 9001 &
python3 router.py 2 9002 &
python3 router.py 3 9003 &
sleep 2

# Démarrer 2 clients
echo "Démarrage des clients..."
python3 client_gui.py ClientA &
python3 client_gui.py ClientB &

echo "=== Système démarré ==="
echo "Pour arrêter: killall python3"
