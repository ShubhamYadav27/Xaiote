import os

from gtts import gTTS

# 1. Generate real speech using Google TTS (Hindi)
text = "CNC 2 band ho gayi hai, spindle failure hai aur maintenance wale bol rahe hain aath ghante lagenge."
tts = gTTS(text=text, lang="hi", slow=False)
audio_path = "real_speech.mp3"
tts.save(audio_path)
print(f"Audio generated at {audio_path} ({os.path.getsize(audio_path)} bytes)")

# We will let the integration test upload this and process it.
