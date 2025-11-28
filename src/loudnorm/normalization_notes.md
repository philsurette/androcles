# Background.
https://www.izotope.com/en/learn/what-are-lufs.html


First off: the way loudness measurements work is relative to
"decibels full scale" (dBFS). Anything above 0 causes clipping

loudness units (LU): like decibels but taking into account the
subjective loudness to a human based, accounting for tonal balance.

## LUFS -  Loudness Units Full Scale
A human-oriented measure of loudness. The higher the louder,
so -14 is like normal speeh, -1 is very loud.

LUFS is called 'loudness target' in ffmeg and is set with '-i' or '-I'.
The acceptable range is -70 to -5

Spotify recommends a LUFS of -14. Other platforms (apple) recommend -16.

## LRA - Loudness Range
A measure of how much your loudness varies. Too little and the
audio is less interesting, too much and there will be bits
where you seem to be shouting or hard to hear.

loudness range is set with '-lra' or '-LRA'

-9 to -12 is good.

## TP - True Peak
The loudest part of the audio. Max is 0, the digitized
audio can't represent above 0 so you get clippitg.

Set sit '-tp' or '-TP'

TP should be lower than -1 to allow headroom for audio manipulation by the
podcast platform

## Loudness Threshold
parts of the audio below this threshold are ignored for purposes
of measuring LRA and LUFS. This is good because I don't want
my intentional long silent pauses to affect thouse measures.

Confusingly, ffmpeg sets this with 'measured_thresh'

I have silence in my pocast so I may the loudness threshold
to -70 to ignore parts of the podcast that are inserted silence
from the loudness calculation. But it may be that ffmpeg always
measures the threashold to be below that.

valid values ar -99 to 0

# ffmpeg
The ffmpeg [loudnorm](https://ffmpeg.org/ffmpeg-filters.html#loudnorm) 
filter can adjust the LUFS etc. 

First you run it against the file to be normalized to measure the 
current metrics for LUFS, peak, range, and threshold. 

Then you run it again, sending values you want for the
auditory metrics along with the measured values.
You can only tell it the LUFS, peak, and range you want,
the trheshold is not a target metric, it's used as 
an input for the other metrics only.

ffmpeg will fail to normalize certain files...
for instance a silence file.

If it can't normalize the file to good parameters,
trying to normalize the normalized file will only
make things worse... mayb try to normalize a larger file.

