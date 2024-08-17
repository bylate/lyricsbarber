import stable_whisper
import webvtt #it misses chunks of lyrics sometimes
from pydub import AudioSegment 
from profanity_check import predict, predict_prob

def numerize_timestamp(timestamp):
    parts = timestamp.split(':')
    seconds = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return seconds

#first page
vocal=str(input("Enter filename: \n>> "))
music = AudioSegment.from_mp3("NLUM.mp3")
original = AudioSegment.from_mp3("NLU.mp3")

model = stable_whisper.load_model('small.en')

result = model.transcribe(vocal)

result.to_srt_vtt('audio.vtt', False, True)
tstamp_of_all_words = []
tstamp_of_bad_words = []
finishtime=0
cfnow=0
for caption in webvtt.read('audio.vtt'):
    print(caption.start +" "+caption.text+" "+caption.end)
    a=numerize_timestamp(caption.start)
    b=numerize_timestamp(caption.end)
    tstamp_of_all_words.append([a,b,caption.text])
    if (predict_prob([caption.text])) >= 0.75:
       tstamp_of_bad_words.append([a,b])
    finishtime=caption.end
    

for item in tstamp_of_bad_words:
    print(item) 
    cfnow+=1

#need to have the orinial music
fsong = original[:1]
i=0
ftime=0
for item in tstamp_of_bad_words:
    start_time = int(ftime * 1000)
    end_time = int(item[0] * 1000)
    music_start_time = int(item[0] * 1000)
    music_end_time = int(item[1] * 1000)
    new_part=original[start_time:end_time]
    fsong = fsong + new_part
    new_part=music[music_start_time:music_end_time]
    fsong = fsong + new_part
    ftime = item[1]

finishtime=len(original)
last_section=original[int(ftime*1000):int(finishtime*1000)]

fsong=fsong+last_section


fsong.export("mashup1.mp3", format="mp3") 

#second page where the webpage ask the user to first input the number of erros in a box and for each individual error have a button that expands to 
#include every 
number_of_errors=int(input("Enter the number of erros: \n>> "))

allmissedw = []
for i in range (0,number_of_errors):
    specific_time=float(input("Enter the approximate time in number of seconds: \n>> "))
    wordatt =[]
    cforbd=1
    for item in tstamp_of_all_words:
        if(item[0]>(specific_time-1) and item[1]<(specific_time+1) ): #this is where the code shows the reader all the words within the timestamp provided by the user
            wordatt.append([item[0],item[1]])
            print(f"#{cforbd} {item[0]} - {item[1]} {item[2]}")
            cforbd+=1
    specific_one=int(input("Now select which is the one that program missed: \n"))
    specific_one-=1 #by this one, according to the index provided by the user, the allmissedword list takes the wrong word by index-1 as the user one starts from 1 but code starts from 0
    allmissedw.append([wordatt[specific_one][0],wordatt[specific_one][1]])

pfo=0
pfn=0
tstampn_final_list=[]
for i in range(0,cfnow+number_of_errors):
    if pfo >= len(tstamp_of_bad_words):  
        break
    if pfn >= len(allmissedw):  
        break
    
    if tstamp_of_bad_words[pfo][0] < allmissedw[pfn][0]:
        tstampn_final_list.append([tstamp_of_bad_words[pfo][0], tstamp_of_bad_words[pfo][1]])
        pfo += 1
    else:
        tstampn_final_list.append([allmissedw[pfn][0], allmissedw[pfn][1]])
        pfn += 1
if(pfo<len(tstamp_of_bad_words)):
    for i in range ((pfo+pfn),cfnow+number_of_errors):
        tstampn_final_list.append([tstamp_of_bad_words[pfo][0], tstamp_of_bad_words[pfo][1]])
        pfo+=1
elif (pfn < len(allmissedw)):
    for i in range ((pfo+pfn),cfnow+number_of_errors):
        tstampn_final_list.append([allmissedw[pfn][0], allmissedw[pfn][1]])
        pfn+=1

i=0
ftime=0
fsong = original[:1]
for item in tstampn_final_list:
    start_time = int(ftime * 1000)
    end_time = int(item[0] * 1000)
    music_start_time = int(item[0] * 1000)
    music_end_time = int(item[1] * 1000)
    new_part=original[start_time:end_time]
    fsong = fsong + new_part
    new_part=music[music_start_time:music_end_time]
    fsong = fsong + new_part
    ftime = item[1]

finishtime=len(original)
last_section=original[int(ftime*1000):int(finishtime*1000)]

fsong=fsong+last_section

#this is the third page where the user sees the final output; add the list of tstamp_of_bad_words and allmissedwords to present to the user
fsong.export("mashup1.mp3", format="mp3") 
