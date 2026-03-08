import requests

TOKEN = '8757431245:AAHjis0btm24n0Q_WIh4GZYY-b-ToYyZKyU'
url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

try:
    response = requests.get(url).json()
    if response['ok'] and response['result']:
        # Get the chat ID from the last message received
        last_update = response['result'][-1]
        chat_id = last_update['message']['chat']['id']
        username = last_update['message']['chat'].get('username', 'N/A')
        print(f"SUCCESS! Detected Chat ID: {chat_id} (User: @{username})")
    else:
        print("No messages found. Please send a message to your bot on Telegram first!")
except Exception as e:
    print(f"Error: {e}")
