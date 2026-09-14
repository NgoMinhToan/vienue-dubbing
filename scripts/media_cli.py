"""Browse/import media visible to the local server, including Docker mounts."""
import argparse
import json
import httpx

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--server',default='http://127.0.0.1:7861')
sub=parser.add_subparsers(dest='command',required=True)
listing=sub.add_parser('list')
listing.add_argument('path',nargs='?',default='')
listing.add_argument('--offset',type=int,default=0)
importer=sub.add_parser('import')
importer.add_argument('video')
importer.add_argument('srt')
importer.add_argument('--name',default='Lồng tiếng mới')
args=parser.parse_args()
with httpx.Client(base_url=args.server,timeout=600) as client:
    response=(client.get('/api/media',params={'path':args.path,'offset':args.offset}) if args.command=='list'
              else client.post('/api/media/import',json={'video':args.video,'srt':args.srt,'name':args.name}))
    if not response.is_success:
        raise SystemExit(f'{response.status_code}: {response.text}')
    print(json.dumps(response.json(),ensure_ascii=False,indent=2))
