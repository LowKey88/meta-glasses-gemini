from utils.gemini import *
from utils.whatsapp import send_whatsapp_threaded, download_file

def retrieve_transcript_from_audio(message):
    path = download_file(message['audio'])
    response: str = analyze_audio(path, "Summarize this recording:")
    send_whatsapp_threaded(response)
    return ok


    