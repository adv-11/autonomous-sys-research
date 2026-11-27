"""GPT Sol: exact request-identity wrapper around the installed official Colab CLI.

The CLI normally generates its UUID internally. Persisting it first lets the
independent guard resolve and release only this request if creation stalls.
Uses the CLI's existing authentication; never emits proxy tokens/credentials.
"""
import json
from pathlib import Path
import sys
import uuid

from colab_cli.client import Accelerator, Assignment, Variant
from colab_cli.common import state
from colab_cli.state import SessionState

OUT = Path('C:/Users/Advait/autonomous-sys-research/outputs/rtdetr_transfer_20261123')
request = json.loads((OUT / 'allocation_request.json').read_text())
nbh = uuid.UUID(request['notebook_uuid'])
name = request['session']
mode = sys.argv[1]

if mode == 'allocate':
    response = state.client.assign(nbh, variant=Variant.GPU, accelerator=Accelerator.L4)
else:
    response = state.client._get_assignment(nbh, variant=Variant.GPU, accelerator=Accelerator.L4)

if mode != 'allocate' and not isinstance(response, Assignment):
    print(json.dumps({'session': name, 'assigned': False}))
else:
    endpoint = response.endpoint
    assert endpoint != request['protected_user_endpoint'], 'Protected user runtime cannot be owned'
    record = {'session': name, 'endpoint': endpoint, 'notebook_uuid': str(nbh),
              'ownership': 'Resolved by exact persisted notebook UUID, not by timing/account enumeration'}
    if mode == 'release':
        state.client.unassign(endpoint)
        state.store.remove(name)
        print(json.dumps({**record, 'released': True}))
    else:
        proxy = response.runtime_proxy_info
        state.store.add(SessionState(name=name, endpoint=endpoint, token=proxy.token,
                                     url=proxy.url, token_expires_at=proxy.expires_at(),
                                     variant='GPU', accelerator='L4', machine_shape='STANDARD'))
        (OUT / 'ownership.json').write_text(json.dumps(record, indent=2))
        print(json.dumps({**record, 'assigned': True}))
