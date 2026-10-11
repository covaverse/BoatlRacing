"""Tune/check the existing Niagara spray clone through the running Editor MCP."""
import json
import urllib.request
import sys

headers = {'Content-Type': 'application/json'}


def rpc(method, params):
    request = urllib.request.Request('http://127.0.0.1:8000/mcp',
        json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode(), headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.headers.get('Mcp-Session-Id'):
            headers['Mcp-Session-Id'] = response.headers['Mcp-Session-Id']
        result = json.load(response)
    assert 'error' not in result, result
    return result['result']


rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                   'clientInfo': {'name': 'bow-spray', 'version': '1'}})


def call(name, arguments, toolset='NiagaraToolsets.NiagaraToolset_System'):
    result = rpc('tools/call', {'name': 'call_tool', 'arguments': {
        'toolset_name': toolset, 'tool_name': name, 'arguments': arguments}})
    assert not result.get('isError'), result
    return json.loads(result['content'][0]['text'])['returnValue']


system = {'refPath': '/Game/Boats/ThaiLongtail/FX/NS_LongtailBowSplash.NS_LongtailBowSplash'}
ref = dict(system=system, emitterName='Fountain', scriptName='ParticleSpawnScript',
           moduleName='', rendererIndex=0, inputNameStack=[])
float_type = {'refPath': '/Script/Niagara.NiagaraFloat'}
variables = []
for name, value in [('SpraySpeed', 60), ('SpraySpread', 25)]:
    variables.append(dict(name='User.' + name, description='Driven by bow contact and hull speed.',
        type={'classStructOrEnum': float_type},
        defaultValue={'struct': float_type, 'value': {'value': value}}))
call('AddUserVariables', dict(system=system, variablesToAdd=variables))
summary = call('GetSystemSummary', dict(system=system))
if not any(e['emitterName'] == 'Starboard' for e in summary['emitters']):
    call('AddEmitter', dict(system=system, emitterName='Starboard',
        templateEmitter={'refPath': '/Niagara/DefaultAssets/Templates/Emitters/Fountain.Fountain'}))


def set_input(module, name, struct, value, script='ParticleSpawnScript', emitter='Fountain'):
    call('SetStackInputData', dict(stackInputRef=dict(ref, moduleName=module,
        scriptName=script, emitterName=emitter, inputNameStack=[name]),
        inputData={'struct': {'refPath': struct}, 'value': value}))


if '--prop' in sys.argv:
    system = {'refPath': '/Game/Boats/ThaiLongtail/FX/NS_LongtailPropSpray.NS_LongtailPropSpray'}
    ref['system'] = system
    variables = [dict(name='User.' + name, description='Driven by immersed propeller RPM.',
        type={'classStructOrEnum': float_type}, defaultValue={'struct': float_type, 'value': {'value': value}})
        for name, value in [('JetSpeed', 120), ('JetSpread', 15)]]
    call('AddUserVariables', dict(system=system, variablesToAdd=variables))
    for name, value in [('Lifetime Min', .2), ('Lifetime Max', .65),
                        ('Uniform Sprite Size Min', 3), ('Uniform Sprite Size Max', 8)]:
        set_input('InitializeParticle', name, float_type['refPath'], {'value': value})
    set_input('InitializeParticle', 'Color', '/Script/CoreUObject.LinearColor',
              {'r': .88, 'g': .96, 'b': 1, 'a': .8})
    set_input('AddVelocity', 'Cone Axis', '/Script/CoreUObject.Vector3f', {'x': .94, 'y': 0, 'z': .35})
    for name, variable in [('Velocity Speed', 'JetSpeed'), ('Cone Angle', 'JetSpread')]:
        set_input('AddVelocity', name, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked',
            {'linkedVariable': {'name': 'User.' + variable, 'type': {'classStructOrEnum': float_type}}})
    set_input('GravityForce', 'Gravity', '/Script/CoreUObject.Vector3f',
              {'x': 0, 'y': 0, 'z': -980}, script='ParticleUpdateScript')
    values = call('GetScriptStackInputValues', dict(scriptRef=ref))
    inputs = {(m['moduleName'], i['name']): i['value'] for m in values for i in m['inputs']}
    assert inputs['AddVelocity', 'Cone Axis']['value']['x'] > 0
    assert inputs['AddVelocity', 'Velocity Speed']['value']['linkedVariable']['name'] == 'User.JetSpeed'
    call('save_assets', {'asset_paths': [system['refPath']]}, 'editor_toolset.toolsets.asset.AssetTools')
    print('BOAT_PROPELLER_JET_INPUTS_PASS')
    sys.exit(0)


for emitter, side in [('Fountain', 1), ('Starboard', -1)]:
    enum = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
    for name, asset, member in [
        ('Lifetime Mode', '/Niagara/Enums/ENiagara_LifetimeMode.ENiagara_LifetimeMode', 'ENiagara_LifetimeMode::NewEnumerator1'),
        ('Sprite Size Mode', '/Niagara/Enums/ENiagara_SizeScaleMode.ENiagara_SizeScaleMode', 'ENiagara_SizeScaleMode::NewEnumerator1')]:
        set_input('InitializeParticle', name, enum, {'enum': {'refPath': asset}, 'enumName': member}, emitter=emitter)
    for name, value in [('Lifetime Min', .22), ('Lifetime Max', .65),
                        ('Uniform Sprite Size Min', 2), ('Uniform Sprite Size Max', 7)]:
        set_input('InitializeParticle', name, float_type['refPath'], {'value': value}, emitter=emitter)
    set_input('InitializeParticle', 'Color', '/Script/CoreUObject.LinearColor',
              {'r': .84, 'g': .94, 'b': 1, 'a': .65}, emitter=emitter)
    set_input('InitializeParticle', 'UsePositionOffset', '/Script/Niagara.NiagaraBool', {'value': -1}, emitter=emitter)
    set_input('InitializeParticle', 'Position Offset Coordinate Space', enum,
        {'enum': {'refPath': '/Script/Niagara.ENiagaraCoordinateSpace'},
         'enumName': 'ENiagaraCoordinateSpace::Local'}, emitter=emitter)
    set_input('InitializeParticle', 'Position Offset', '/Script/CoreUObject.Vector3f',
              {'x': 0, 'y': 32 * side, 'z': 0}, emitter=emitter)
    set_input('ShapeLocation', 'Sphere Radius', float_type['refPath'], {'value': 4}, emitter=emitter)
    set_input('AddVelocity', 'Velocity Mode', enum,
        {'enum': {'refPath': '/Niagara/Enums/Utility/ENiagara_VelocityMode.ENiagara_VelocityMode'},
         'enumName': 'ENiagara_VelocityMode::NewEnumerator2'}, emitter=emitter)
    set_input('AddVelocity', 'Cone Axis', '/Script/CoreUObject.Vector3f', {'x': .2, 'y': .9 * side, 'z': .6}, emitter=emitter)
    for module, name, variable, script in [
        ('AddVelocity', 'Velocity Speed', 'SpraySpeed', 'ParticleSpawnScript'),
        ('AddVelocity', 'Cone Angle', 'SpraySpread', 'ParticleSpawnScript'),
        ('SpawnRate', 'SpawnRate', 'SpawnRate', 'EmitterUpdateScript')]:
        set_input(module, name, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked',
            {'linkedVariable': {'name': 'User.' + variable, 'type': {'classStructOrEnum': float_type}}},
            script=script, emitter=emitter)
    set_input('GravityForce', 'Gravity', '/Script/CoreUObject.Vector3f',
              {'x': 0, 'y': 0, 'z': -980}, script='ParticleUpdateScript', emitter=emitter)
inputs = call('GetScriptStackInputValues', dict(scriptRef=ref))
values = {(m['moduleName'], i['name']): i['value'] for m in inputs for i in m['inputs']}
assert values['AddVelocity', 'Velocity Speed']['value']['linkedVariable']['name'] == 'User.SpraySpeed'
assert values['AddVelocity', 'Cone Angle']['value']['linkedVariable']['name'] == 'User.SpraySpread'
assert values['InitializeParticle', 'Uniform Sprite Size Max']['value']['value'] == 7
other = call('GetScriptStackInputValues', dict(scriptRef=dict(ref, emitterName='Starboard')))
other_values = {(m['moduleName'], i['name']): i['value'] for m in other for i in m['inputs']}
assert other_values['InitializeParticle', 'Position Offset']['value']['y'] == -32
assert other_values['AddVelocity', 'Cone Axis']['value']['y'] < 0
call('save_assets', {'asset_paths': [system['refPath']]}, 'editor_toolset.toolsets.asset.AssetTools')
print('BOAT_BOW_SPRAY_INPUTS_PASS')
