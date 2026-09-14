import threading
import shutil
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf


def test_unrecognized_container_uses_stream_copy_fallback(tmp_path, monkeypatch):
    from apps.dubbing_web import media
    source = tmp_path / 'nguồn thử.mov'
    media.run('ffmpeg', ['-v','error','-y','-f','lavfi','-i','color=s=64x64:d=1',
        '-f','lavfi','-i','sine=duration=1','-c:v','libx264','-c:a','aac',source])
    project = {'media':media.inspect_video(source), 'video_file':source.name, 'audio_index':1}
    dub = tmp_path/'dub.wav'
    sf.write(dub, np.zeros(48000), 48000)
    identify = media.identify
    def reject_source(path):
        if Path(path) == source:
            raise RuntimeError('Simulated unsupported container')
        return identify(path)
    monkeypatch.setattr(media, 'identify', reject_source)
    output = tmp_path/'result.mkv'
    media.mux_mkv(project, tmp_path, dub, output, threading.Event())
    tracks = identify(output)['tracks']
    assert [t['type'] for t in tracks] == ['video','audio','audio']
    assert tracks[0]['properties']['codec_id'] == 'V_MPEG4/ISO/AVC'
from apps.dubbing_web.config import executable
from apps.dubbing_web.media import run, inspect_video, mux_mkv, identify, mix, encode_mp3


@pytest.fixture
def media_tools():
    for name in ('ffmpeg', 'ffprobe', 'mkvmerge'):
        try:
            executable(name)
        except RuntimeError:
            pytest.skip(f'{name} missing')


@pytest.mark.parametrize('suffix', ['mp4', 'mkv'])
def test_export_exactly_two_tracks_from_multi_audio(tmp_path, media_tools, suffix):
    cancel = threading.Event()
    source = tmp_path / ('source.' + suffix)
    run('ffmpeg', ['-v','error','-f','lavfi','-i','color=c=blue:s=160x90:r=25:d=2',
        '-f','lavfi','-i','sine=frequency=300:duration=2','-f','lavfi','-i','sine=frequency=600:duration=2',
        '-map','0:v','-map','1:a','-map','2:a','-c:v','libx264','-c:a','aac',source])
    wav = tmp_path/'dub.wav'
    sf.write(wav, np.zeros((96000,2)), 48000)
    mp3 = tmp_path/'dub.mp3'
    encode_mp3(wav, mp3, cancel)
    info = inspect_video(source)
    project = {'video_file':source.name, 'media':info, 'audio_index':info['audio_tracks'][1]['index']}
    output = tmp_path/'output.mkv'
    mux_mkv(project,tmp_path,mp3,output,cancel)
    tracks = identify(output)['tracks']
    audios = [t for t in tracks if t['type']=='audio']
    assert len(audios) == 2
    assert [t['properties']['track_name'] for t in audios] == ['Original','Vietnamese Dub']
    assert not audios[0]['properties']['default_track']
    assert audios[1]['properties']['default_track']
    # Prove selected original is copied: decode it and compare with original output track.
    a, b = tmp_path/'a.wav',tmp_path/'b.wav'
    run('ffmpeg',['-v','error','-i',source,'-map','0:a:1',a])
    run('ffmpeg',['-v','error','-i',output,'-map','0:a:0',b])
    x, _ = sf.read(a); y, _ = sf.read(b)
    # AAC priming can differ across containers; inspect codec and steady-state samples.
    assert audios[0]['codec'] == 'AAC'
    assert abs(np.sqrt(np.mean(x*x))-np.sqrt(np.mean(y*y))) < 0.01
    def video_hash(path):
        output = run('ffmpeg', ['-v','error','-i',path,'-map','0:v:0','-f','framemd5','-'])
        return [line.split(',')[-1].strip() for line in output.splitlines() if line and not line.startswith('#')]
    assert video_hash(source) == video_hash(output)


def test_overlap_is_added_and_tail_preserved(tmp_path):
    cancel = threading.Event()
    wav = tmp_path/'voice.wav'
    sf.write(wav,np.full(48000,.2,dtype=np.float32),48000,subtype='FLOAT')
    p={'media':{'duration':1},'audio_index':None,'background':'off','video_file':'unused.mp4'}
    clips=[{'start':.5,'duration':1,'frames':48000,'path':wav}, {'start':.5,'duration':1,'frames':48000,'path':wav}]
    out=tmp_path/'mix.wav'
    mix(p,tmp_path,clips,out,cancel)
    values,sr=sf.read(out)
    assert len(values)==72000
    assert np.max(abs(values[:24000]))==0
    assert np.mean(values[30000:])==pytest.approx(.4,abs=1e-6)


@pytest.mark.parametrize('mode,base,speaking', [('duck',.3,.1),('original_duck',1,.22),('original',1,1),('quiet',.06,.06),('off',0,0)])
def test_four_background_modes_preserve_stereo(tmp_path, media_tools, mode, base, speaking):
    source = tmp_path/'base.wav'
    sf.write(source, np.tile([.1,.05], (144000,1)), 48000, subtype='FLOAT')
    voice = tmp_path/'voice.wav'
    sf.write(voice, np.full(48000,.2), 48000, subtype='FLOAT')
    project = {'media':{'duration':3,'video_start':0,'audio_tracks':[{'index':0,'start':0}]},
               'video_file':source.name, 'audio_index':0,'background':mode}
    output = tmp_path/'mix.wav'
    mix(project,tmp_path,[{'start':1,'duration':1,'frames':48000,'path':voice}],output,threading.Event())
    values, rate = sf.read(output)
    assert rate == 48000 and values.shape == (144000,2)
    assert values[24000] == pytest.approx([.1*base,.05*base],abs=1e-6)
    assert values[72000] == pytest.approx([.2+.1*speaking,.2+.05*speaking],abs=1e-6)
