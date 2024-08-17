from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from faster_whisper import WhisperModel
import webvtt
from profanity_check import predict_prob
import os
import json

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'static'
app.config['ALLOWED_EXTENSIONS'] = {'mp3'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def numerize_timestamp(timestamp):
    parts = timestamp.split(':')
    seconds = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return seconds

def create_mashup(original_path, vocal_path, music_path, output_path):
    model = WhisperModel("medium.en",device="cpu", compute_type="float32")

    segments, _ = model.transcribe(vocal_path, word_timestamps=True)

    tstamp = []
    tstampn = []
    finishtime = 0
    cfnow = 0

    for segment in segments:
        for word in segment.words:
            print("[%.2fs -> %.2fs] %s" % (word.start, word.end, word.word))
            tstamp.append([word.start, word.end,word.word])
            if (predict_prob([word.word])) >= 0.75:
                tstampn.append([word.start,word.end])
            finishtime=word.end

    music = AudioSegment.from_mp3(music_path)
    original = AudioSegment.from_mp3(original_path)
    fsong = original[:1]
    ftime = 0

    for item in tstampn:
        start_time = int(ftime * 1000)
        end_time = int(item[0] * 1000)
        music_start_time = int(item[0] * 1000)
        music_end_time = int(item[1] * 1000)
        new_part = original[start_time:end_time]
        fsong = fsong + new_part
        new_part = music[music_start_time:music_end_time]
        fsong = fsong + new_part
        ftime = item[1]

    last_section = original[int(ftime * 1000):int(finishtime * 1000)]
    fsong = fsong + last_section

    fsong.export(output_path, format="mp3")

    return tstamp, tstampn, cfnow, finishtime

def fix_errors(original_path, music_path, tstamp, tstampn, cfnow, finishtime, errors, output_path):
    allmissedw = []
    
    for error in errors:
        specific_time = error['time']
        wordatt = []
        for item in tstamp:
            if item[0] > (specific_time - 1) and item[1] < (specific_time + 1):
                wordatt.append([item[0], item[1]])
        
        specific_one = error['index'] - 1
        if 0 <= specific_one < len(wordatt):
            allmissedw.append([wordatt[specific_one][0], wordatt[specific_one][1]])
        else:
            print(f"Invalid index {specific_one + 1} for time {specific_time}. Available range: 1-{len(wordatt)}")

    pfo = 0
    pfn = 0
    tstampn_new = []
    while pfo < len(tstampn) and pfn < len(allmissedw):
        if tstampn[pfo][0] < allmissedw[pfn][0]:
            tstampn_new.append(tstampn[pfo])
            pfo += 1
        else:
            tstampn_new.append(allmissedw[pfn])
            pfn += 1
    tstampn_new.extend(tstampn[pfo:])
    tstampn_new.extend(allmissedw[pfn:])

    music = AudioSegment.from_mp3(music_path)
    original = AudioSegment.from_mp3(original_path)
    fsong = original[:1]
    ftime = 0

    for item in tstampn_new:
        start_time = int(ftime * 1000)
        end_time = int(item[0] * 1000)
        music_start_time = int(item[0] * 1000)
        music_end_time = int(item[1] * 1000)
        new_part = original[start_time:end_time]
        fsong = fsong + new_part
        new_part = music[music_start_time:music_end_time]
        fsong = fsong + new_part
        ftime = item[1]

    last_section = original[int(ftime * 1000):int(finishtime * 1000)]
    fsong = fsong + last_section

    fsong.export(output_path, format="mp3")

    return tstampn_new, allmissedw

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'original' not in request.files or 'vocal' not in request.files or 'music' not in request.files:
        return 'All three files are required'
    
    original = request.files['original']
    vocal = request.files['vocal']
    music = request.files['music']

    if original.filename == '' or vocal.filename == '' or music.filename == '':
        return 'No selected file'

    if original and allowed_file(original.filename) and vocal and allowed_file(vocal.filename) and music and allowed_file(music.filename):
        original_filename = secure_filename(original.filename)
        vocal_filename = secure_filename(vocal.filename)
        music_filename = secure_filename(music.filename)

        original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        vocal_path = os.path.join(app.config['UPLOAD_FOLDER'], vocal_filename)
        music_path = os.path.join(app.config['UPLOAD_FOLDER'], music_filename)

        original.save(original_path)
        vocal.save(vocal_path)
        music.save(music_path)

        tstamp, tstampn, cfnow, finishtime = create_mashup(original_path, vocal_path, music_path, os.path.join(app.config['PROCESSED_FOLDER'], 'mashup1.mp3'))

        return render_template('errors.html', original_path=original_path, music_path=music_path, 
                               tstamp=tstamp, tstampn=json.dumps(tstampn),
                               cfnow=cfnow, finishtime=finishtime)

    return 'Invalid file type'

@app.route('/process', methods=['POST'])
def process_file():
    original_path = request.form['original_path']
    music_path = request.form['music_path']
    tstampn = json.loads(request.form['tstampn'])  # Parse JSON safely
    tstamp = json.loads(request.form['tstamp'])  # Parse JSON safely

    cfnow = int(request.form['cfnow'])
    finishtime = float(request.form['finishtime'])
    
    errors = []
    for i in range(int(request.form['num_errors'])):
        time = float(request.form[f'error_time_{i}'])
        index = int(request.form[f'error_index_{i}'])
        errors.append({'time': time, 'index': index})
    
    tstampn_new, user_added = fix_errors(
        original_path, music_path, tstamp, tstampn, cfnow, finishtime, errors,
        os.path.join(app.config['PROCESSED_FOLDER'], 'mashup1_final.mp3')
    )

    return render_template('result.html', tstampn=tstampn_new, user_added=user_added)

if __name__ == '__main__':
    app.run(port=8000, debug=True)

