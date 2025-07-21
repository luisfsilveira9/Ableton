import xml.etree.ElementTree as ET
import os
from collections import OrderedDict


def collect_manuals(elem, path, result):
    for child in elem:
        if child.tag == 'Manual':
            param_name = '.'.join(path)
            result[param_name] = {'value': child.get('Value'), 'elem': child}
        else:
            collect_manuals(child, path + [child.tag], result)


def parse_device(dev_elem):
    dev_name = dev_elem.tag
    device_id = dev_elem.find('DeviceId')
    if device_id is not None and device_id.get('Name'):
        dev_name = device_id.get('Name')
    params = {}
    collect_manuals(dev_elem, [], params)
    return {'name': dev_name, 'element': dev_elem, 'parameters': params}


def parse_devices(parent):
    devices = []
    chain = parent.find('./DeviceChain')
    if chain is None:
        return devices
    for container in chain.findall('.//Devices'):
        for elem in container:
            if elem.find('.//DeviceId') is not None and elem.find('.//Manual') is not None:
                devices.append(parse_device(elem))
    return devices


def parse_track(track_elem):
    name_elem = track_elem.find('./Name/EffectiveName')
    name = name_elem.get('Value') if name_elem is not None else ''
    return {'name': name, 'element': track_elem, 'devices': parse_devices(track_elem)}


def parse_file(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    groups = OrderedDict()
    for g in root.findall('.//GroupTrack'):
        gid = g.get('Id') or g.find('Id')
        name_elem = g.find('./Name/EffectiveName')
        name = name_elem.get('Value') if name_elem is not None else ''
        groups[gid] = {
            'name': name,
            'element': g,
            'devices': parse_devices(g),
            'audio_tracks': [],
            'midi_tracks': []
        }
    for a in root.findall('.//AudioTrack'):
        gid_elem = a.find('./TrackGroupId')
        gid = gid_elem.get('Value') if gid_elem is not None else None
        tinfo = parse_track(a)
        if gid in groups:
            groups[gid]['audio_tracks'].append(tinfo)
    for m in root.findall('.//MidiTrack'):
        gid_elem = m.find('./TrackGroupId')
        gid = gid_elem.get('Value') if gid_elem is not None else None
        tinfo = parse_track(m)
        if gid in groups:
            groups[gid]['midi_tracks'].append(tinfo)
    return tree, groups


def edit_param(device):
    for pname, info in device['parameters'].items():
        current = info['value']
        new_val = input(f"{device['name']} - {pname} [{current}]: ").strip()
        if not new_val:
            print('Empty input, keeping original.')
            continue
        if current.lower() in ['true', 'false']:
            if new_val.lower() in ['true', 'false']:
                info['elem'].set('Value', new_val.lower())
                info['value'] = new_val.lower()
            else:
                print('Invalid boolean, using original.')
        else:
            try:
                float(new_val)
                info['elem'].set('Value', new_val)
                info['value'] = new_val
            except ValueError:
                print('Invalid number, using original.')


def handle_track(track):
    while True:
        print(f"Track: {track['name']}")
        for i, dev in enumerate(track['devices'], 1):
            print(f"  {i}) Device: {dev['name']}")
        choice = input('Select device number to edit (b to go back): ').strip()
        if choice.lower() == 'b':
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(track['devices']):
                edit_param(track['devices'][idx])
        except ValueError:
            pass


def handle_group(group):
    while True:
        print(f"Group: {group['name']}")
        options = []
        idx = 1
        for dev in group['devices']:
            print(f"  {idx}) Group Device: {dev['name']}")
            options.append(('device', dev))
            idx += 1
        for t in group['audio_tracks']:
            print(f"  {idx}) AudioTrack: {t['name']}")
            options.append(('track', t))
            idx += 1
        for t in group['midi_tracks']:
            print(f"  {idx}) MidiTrack: {t['name']}")
            options.append(('track', t))
            idx += 1
        choice = input('Select item to edit (b to go back): ').strip()
        if choice.lower() == 'b':
            break
        try:
            num = int(choice) - 1
            if 0 <= num < len(options):
                typ, obj = options[num]
                if typ == 'device':
                    edit_param(obj)
                else:
                    handle_track(obj)
        except ValueError:
            pass


def main():
    fname = input('XML file path: ').strip()
    tree, groups = parse_file(fname)
    keys = list(groups.keys())
    while True:
        print('\nGroups:')
        for i, k in enumerate(keys, 1):
            print(f"  {i}) {groups[k]['name']} (Id {k})")
        choice = input('Select group number to edit (q to quit): ').strip()
        if choice.lower() == 'q':
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                handle_group(groups[keys[idx]])
        except ValueError:
            pass
    out_name = os.path.splitext(fname)[0] + 'Edit.adg'
    tree.write(out_name, encoding='utf-8', xml_declaration=True)
    print(f'Saved edited file as {out_name}')


if __name__ == '__main__':
    main()
