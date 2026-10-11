"""Read-only check against the running Editor's MCP server: python Tools/verify_wake_realism.py."""
import json
import urllib.request

headers = {'Content-Type': 'application/json'}


def rpc(method, params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    request = urllib.request.Request('http://127.0.0.1:8000/mcp', body, headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        session = response.headers.get('Mcp-Session-Id')
        if session:
            headers['Mcp-Session-Id'] = session
        result = json.load(response)
    assert 'error' not in result, result
    return result['result']


rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                   'clientInfo': {'name': 'wake-check', 'version': '1'}})


def call(name, arguments):
    result = rpc('tools/call', {'name': 'call_tool', 'arguments': {
        'toolset_name': 'NiagaraToolsets.NiagaraToolset_System',
        'tool_name': name, 'arguments': arguments}})
    assert not result.get('isError'), result
    return json.loads(result['content'][0]['text'])['returnValue']


system = {'refPath': '/Game/Boats/ThaiLongtail/FX/NS_LongtailWake.NS_LongtailWake'}
ref = dict(system=system, emitterName='Fountain', scriptName='ParticleSpawnScript',
           moduleName='', rendererIndex=0, inputNameStack=[])
renderer = json.loads(call('GetRendererData', {'rendererRef': ref})['propertyValues'])
assert renderer['FacingMode'] == 'CustomFacingVector'
assert renderer['Alignment'] == 'CustomAlignment'
assert 'M_LongtailWakeSurface' in renderer['Material']['refPath']
modules = call('GetScriptStackTopology', {'scriptRef': ref})['modules']
assert not next(m for m in modules if m['moduleName'] == 'AddVelocity')['enabled']
values = call('GetScriptStackInputValues', {'scriptRef': ref})
inputs = {i['name']: i['value']['value'] for m in values for i in m['inputs']}
assert inputs['Particles.SpriteFacing'] == dict(x=0, y=0, z=1)
assert inputs['Sphere Radius']['value'] == 0
assert inputs['Lifetime Min']['value'] == 3
assert inputs['Lifetime Max']['value'] == 4
assert inputs['Uniform Sprite Size Min']['value'] == 160
assert inputs['Uniform Sprite Size Max']['value'] == 240
state = call('GetSystemCompileState', {'system': system})
assert not state['bHasErrors'] and not state['bIsStale'] and not state['bIsCompiling'], state
wash_system = {'refPath': '/Game/Boats/ThaiLongtail/FX/NS_LongtailPropWash.NS_LongtailPropWash'}
wash_ref = dict(ref, system=wash_system)
wash_renderer = json.loads(call('GetRendererData', {'rendererRef': wash_ref})['propertyValues'])
assert 'M_LongtailPropWash' in wash_renderer['Material']['refPath']
assert wash_renderer['FacingMode'] == 'CustomFacingVector'
wash_state = call('GetSystemCompileState', {'system': wash_system})
assert not wash_state['bHasErrors'] and not wash_state['bIsStale'], wash_state
print('BOAT_WAKE_REALISM_PASS')
