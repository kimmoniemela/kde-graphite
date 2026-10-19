#!/usr/bin/env python3
"""Keep Super+Shift+number working with the active KDE keyboard layout."""
import ast
import configparser
import ctypes as C
import ctypes.util
import json
import os
from pathlib import Path
import subprocess
import sys


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=8)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Command failed: ' + args[0])
    return result.stdout.strip()


def shifted_symbols(layout, variant=''):
    """Read the shifted number row from XKB rather than assuming a US keyboard."""
    lib = C.CDLL(ctypes.util.find_library('xkbcommon') or 'libxkbcommon.so.0')
    class Names(C.Structure):
        _fields_ = [(name, C.c_char_p) for name in ['rules', 'model', 'layout', 'variant', 'options']]
    signatures = {
        'xkb_context_new': (C.c_void_p, [C.c_int]),
        'xkb_keymap_new_from_names': (C.c_void_p, [C.c_void_p, C.POINTER(Names), C.c_int]),
        'xkb_keymap_key_by_name': (C.c_uint32, [C.c_void_p, C.c_char_p]),
        'xkb_keymap_mod_get_index': (C.c_uint32, [C.c_void_p, C.c_char_p]),
        'xkb_state_new': (C.c_void_p, [C.c_void_p]),
        'xkb_state_update_mask': (C.c_uint32, [C.c_void_p] + [C.c_uint32] * 6),
        'xkb_state_key_get_utf32': (C.c_uint32, [C.c_void_p, C.c_uint32]),
        'xkb_context_unref': (None, [C.c_void_p]),
        'xkb_keymap_unref': (None, [C.c_void_p]),
        'xkb_state_unref': (None, [C.c_void_p]),
    }
    for name, (restype, argtypes) in signatures.items():
        function = getattr(lib, name)
        function.restype, function.argtypes = restype, argtypes
    context = lib.xkb_context_new(0)
    if not context:
        raise RuntimeError('Cannot create XKB context')
    keymap = state = None
    try:
        names = Names(None, b'pc105', layout.encode(), variant.encode(), b'')
        keymap = lib.xkb_keymap_new_from_names(context, C.byref(names), 0)
        if not keymap:
            raise RuntimeError('Cannot read XKB layout: ' + layout)
        state = lib.xkb_state_new(keymap)
        if not state:
            raise RuntimeError('Cannot create XKB state')
        shift = lib.xkb_keymap_mod_get_index(keymap, b'Shift')
        if shift == 0xffffffff:
            raise RuntimeError('XKB layout has no Shift modifier: ' + layout)
        lib.xkb_state_update_mask(state, 1 << shift, 0, 0, 0, 0, 0)
        result = {}
        for position in range(1, 11):
            key = lib.xkb_keymap_key_by_name(keymap, f'AE{position:02d}'.encode())
            code = lib.xkb_state_key_get_utf32(state, key)
            result[position] = chr(code) if code else ''
        return result
    finally:
        if state: lib.xkb_state_unref(state)
        if keymap: lib.xkb_keymap_unref(keymap)
        if context: lib.xkb_context_unref(context)


def sequences(number, symbol):
    result = [f'Meta+Shift+{number % 10}']
    if symbol and symbol.isprintable() and not symbol.isdigit():
        # KWin may consume Shift while translating the symbol. Retain both forms.
        result += ['Meta+' + symbol, 'Meta+Shift+' + symbol]
    return result


_last_symbols = None


def apply_layout(index):
    global _last_symbols
    from PySide6.QtGui import QKeySequence
    reply = run('gdbus', 'call', '--session', '--dest', 'org.kde.keyboard', '--object-path', '/Layouts',
                '--method', 'org.kde.KeyboardLayouts.getLayoutsList')
    layouts = ast.literal_eval(reply)[0]
    if not 0 <= index < len(layouts):
        return
    layout = layouts[index][0]
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.read(Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'kxkbrc')
    variants = config.get('Layout', 'VariantList', fallback='').split(',')
    variant = variants[index] if index < len(variants) else ''
    symbols = shifted_symbols(layout, variant)
    if symbols == _last_symbols:
        return
    def bind(number, keys):
        ids = ['kwin', f'KdeHyprSendDesktop{number}', 'KWin', f'Graphite: Send window to workspace {number}']
        codes = [QKeySequence(key)[0].toCombined() for key in keys]
        run('gdbus', 'call', '--session', '--dest', 'org.kde.kglobalaccel', '--object-path', '/kglobalaccel',
            '--method', 'org.kde.KGlobalAccel.setShortcut', json.dumps(ids), json.dumps(codes), '4')
    # Never steal an alias from another application's or KWin script's shortcut.
    actions = {f'KdeHyprSendDesktop{n}' for n in range(1, 11)}
    for number in range(1, 11):
        for sequence in sequences(number, symbols[number]):
            key = QKeySequence(sequence)[0].toCombined()
            reply = run('gdbus', 'call', '--session', '--dest', 'org.kde.kglobalaccel', '--object-path', '/kglobalaccel',
                        '--method', 'org.kde.KGlobalAccel.action', str(key))
            owner = ast.literal_eval(reply.replace('@as ', ''))[0]
            if owner and (owner[0] != 'kwin' or owner[1] not in actions):
                raise RuntimeError(sequence + ' belongs to ' + owner[1] + '; resolve the shortcut conflict in KDE settings.')
    # Release aliases from the previous layout before assigning symbols to new numbers.
    for number in range(1, 11):
        bind(number, sequences(number, ''))
    for number in range(1, 11):
        bind(number, sequences(number, symbols[number]))
    _last_symbols = symbols
    print('Graphite workspace move keys updated for ' + layout, flush=True)


def main():
    from PySide6.QtCore import QCoreApplication, QObject, QTimer, Slot, SLOT
    from PySide6.QtDBus import QDBusConnection, QDBusInterface
    app = QCoreApplication(sys.argv)
    bus = QDBusConnection.sessionBus()
    if not bus.registerService('org.kde.GraphiteWorkspaceKeys'):
        return 0  # Already running in this session.
    keyboard = QDBusInterface('org.kde.keyboard', '/Layouts', 'org.kde.KeyboardLayouts', bus)
    class Watcher(QObject):
        @Slot('uint')
        def changed(self, index):
            try:
                apply_layout(index)
            except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as error:
                print(str(error), file=sys.stderr, flush=True)
        @Slot()
        def refresh(self):
            reply = keyboard.call('getLayout')
            if reply.arguments(): self.changed(int(reply.arguments()[0]))
    watcher = Watcher()
    bus.connect('org.kde.keyboard', '/Layouts', 'org.kde.KeyboardLayouts', 'layoutChanged', watcher, SLOT('changed(uint)'))
    bus.connect('org.kde.keyboard', '/Layouts', 'org.kde.KeyboardLayouts', 'layoutListChanged', watcher, SLOT('refresh()'))
    QTimer.singleShot(0, watcher.refresh)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
