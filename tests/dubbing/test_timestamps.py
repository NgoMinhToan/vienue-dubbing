import threading
import numpy as np
import pytest
import soundfile as sf
from apps.dubbing_web.media import run, inspect_video, mux_mkv, probe, encode_mp3
from test_media import media_tools


@pytest.mark.parametrize('extension', ['mp4', 'mkv'])
@pytest.mark.parametrize('audio_delay', [0, .4])
def test_nonzero_source_origin_dub_stays_relative_to_video(tmp_path, media_tools, extension, audio_delay):
    source = tmp_path / ('offset.' + extension)
    run('ffmpeg', ['-v','error','-f','lavfi','-i','color=s=160x90:r=25:d=2',
                  '-itsoffset',str(audio_delay),'-f','lavfi','-i','sine=frequency=300:duration=2','-c:v','libx264','-c:a','aac',
                  '-output_ts_offset','5', source])
    metadata = inspect_video(source)
    assert 1.95 <= metadata['duration'] <= 2.45
    signal = np.zeros(96000)
    signal[24000:28800] = .5
    sf.write(tmp_path/'dub.wav', signal, 48000)
    encode_mp3(tmp_path/'dub.wav', tmp_path/'dub.mp3', threading.Event())
    project = {'video_file':source.name,'media':metadata,'audio_index':metadata['audio_tracks'][0]['index']}
    output = tmp_path/'output.mkv'
    mux_mkv(project,tmp_path,tmp_path/'dub.mp3',output,threading.Event())
    streams = probe(output)['streams']
    video = next(s for s in streams if s['codec_type']=='video')
    audio = [s for s in streams if s['codec_type']=='audio'][-1]
    assert abs(float(audio.get('start_time',0)) - float(video.get('start_time',0))) < .06
    original = [s for s in streams if s['codec_type']=='audio'][0]
    expected = metadata['audio_tracks'][0]['start'] - metadata['video_start']
    assert abs(float(original.get('start_time',0)) - float(video.get('start_time',0)) - expected) < .06
    decoded = tmp_path/'decoded.wav'
    run('ffmpeg',['-v','error','-i',output,'-map','0:a:1',decoded])
    samples, rate = sf.read(decoded)
    onset = np.flatnonzero(abs(samples) > .2)[0] / rate
    assert abs(onset - .5) < .05


def test_vfr_remux_keeps_frame_timestamps(tmp_path, media_tools):
    source=tmp_path/'vfr.mp4'
    run('ffmpeg',['-v','error','-f','lavfi','-i','color=s=160x90:r=25:d=2',
                  '-f','lavfi','-i','sine=duration=3','-vf',"setpts='if(lt(N,25),N,25+(N-25)*2)/(25*TB)'",
                  '-fps_mode','vfr','-c:v','libx264','-c:a','aac',source])
    metadata=inspect_video(source)
    sf.write(tmp_path/'dub.wav',np.zeros(144000),48000)
    encode_mp3(tmp_path/'dub.wav',tmp_path/'dub.mp3',threading.Event())
    p={'video_file':source.name,'media':metadata,'audio_index':metadata['audio_tracks'][0]['index']}
    output=tmp_path/'output.mkv'
    mux_mkv(p,tmp_path,tmp_path/'dub.mp3',output,threading.Event())
    def stamps(path):
        import json
        frames=json.loads(run('ffprobe',['-v','error','-select_streams','v:0','-show_frames',
                                        '-show_entries','frame=best_effort_timestamp_time','-of','json',path]))['frames']
        values=np.array([float(f['best_effort_timestamp_time']) for f in frames])
        return values-values[0]
    before,after=stamps(source),stamps(output)
    assert len(set(np.round(np.diff(before),3))) > 1
    assert after == pytest.approx(before,abs=.002)
