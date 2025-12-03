#!/bin/bash

echo "🚀 INICJALIZACJA SYSTEMU AJNA..."

# 1. Uruchomienie Ollama (w tle)
if pgrep -x "ollama" > /dev/null
then
    echo "✅ Ollama już działa."
else
    echo "🧠 Uruchamianie Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
fi

# 2. Start kontenerów Docker (Qdrant, n8n, Ghost)
# Uwaga: Zakładam, że masz kontenery o takich nazwach. Jeśli nie, stwórz je raz docker-composem.
echo "🐳 Budzenie kontenerów..."
docker start qdrant n8n ghost 2>/dev/null || echo "⚠️ Nie znaleziono niektórych kontenerów (sprawdź docker ps -a)"

# 3. Przejście do projektu i start Dashboardu
echo "📂 Przechodzenie do backendu..."
# Tutaj wpisz ścieżkę do swojego GŁÓWNEGO projektu (tam gdzie jest app.py)
cd /home/ajna/ai-knowledge-orchestrator/

echo "🖥️ Uruchamianie aplikacji..."
# Ustawienie klucza (dla pewności)
export API_KEY="twoje-tajne-haslo" 

# Start aplikacji
python3 app.py
