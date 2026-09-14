import copy
from fastapi.testclient import TestClient
from apps.dubbing_web.api import create_app
from apps.dubbing_web.config import Settings
from apps.dubbing_web.domain import voice_key, speech_text
from apps.dubbing_web.pronunciation import spoken_text


def test_rules_unicode_boundaries_order_and_no_recursive_replacement():
    rules=[{'source':'VieNeu','target':'Vi Nói'}, {'source':'Vi Nói','target':'sai'},
           {'source':'CPU','target':'xi pi iu','case_sensitive':True}]
    assert spoken_text('VieNeu vieneu VieNeux CPU cpu',rules)=='Vi Nói Vi Nói VieNeux xi pi iu cpu'
    assert spoken_text('á', [{'source':'á','target':'A','enabled':False}])=='á'


def test_dictionary_snapshot_revision_and_cache(tmp_path):
    app=create_app(Settings(tmp_path))
    store=app.state.store
    id,root=store.create()
    p={'id':id,'name':'Test','revision':1,'voice':'Kim Thanh','cues':[{'text':'VieNeu'},{'text':'Xin chào'}]}
    store.save(p)
    before=copy.deepcopy(p)
    with TestClient(app) as client:
        d=client.get('/api/dictionary').json()
        d['rules']=[{'source':'VieNeu','target':'Vi Nói'}]
        saved=client.put('/api/dictionary',json=d).json()
        assert saved['revision']==1
        assert client.put('/api/dictionary',json=d).status_code==409
        assert client.post('/api/projects/'+id+'/dictionary',json={'revision':1,'dictionary_revision':0}).status_code==409
        assert client.post('/api/projects/'+id+'/dictionary',json={'revision':1,'dictionary_revision':1}).status_code==200
        after=store.get(id)
        assert after['cues']==before['cues']
        assert speech_text(after['cues'][0],after)=='Vi Nói'
        assert voice_key(after['cues'][0],after)!=voice_key(before['cues'][0],before)
        assert voice_key(after['cues'][1],after)==voice_key(before['cues'][1],before)
        saved['rules']=[]
        client.put('/api/dictionary',json=saved)
        assert store.get(id)['pronunciation']['rules']
        app.state.jobs.items['busy']={'project':id,'status':'running'}
        assert client.post('/api/projects/'+id+'/dictionary',json={'revision':2,'dictionary_revision':2}).status_code==400
        app.state.jobs.items.clear()


def test_invalid_import_is_atomic(tmp_path):
    app=create_app(Settings(tmp_path))
    with TestClient(app) as client:
        assert client.put('/api/dictionary',json={'version':2,'rules':[]}).status_code==422
        assert client.put('/api/dictionary',json={'rules':[{'source':'','target':'x'}]}).status_code==422
        assert client.get('/api/dictionary').json()['revision']==0
