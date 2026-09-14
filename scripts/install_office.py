"""LibreOffice de Debian, extraído sin privilegios en el directorio de build.

No cambia el sistema ni escribe sobre el disco de materiales. Apt verifica las
firmas e integridad usando sus fuentes oficiales ya configuradas en Render.
"""
from pathlib import Path
import os
import re
import subprocess
import shutil

root = Path(os.getenv('EDIFOS_OFFICE_BUILD_ROOT', str(Path(__file__).resolve().parents[1]))).resolve()
work = root / '.office-build'
dest = root / '.office'
for path in [work / 'lists/partial', work / 'cache/archives/partial', work / 'packages', dest]:
    path.mkdir(parents=True, exist_ok=True)
opts = ['-o', f'Dir::State::lists={work / "lists"}', '-o', f'Dir::Cache={work / "cache"}',
        '-o', f'APT::Sandbox::User={os.getenv("USER", "render")}']
subprocess.run(['apt-get', *opts, 'update'], check=True)
plan = subprocess.run(['apt-get', *opts, '-s', 'install', '--no-install-recommends',
                      'libreoffice-writer', 'libreoffice-impress'], capture_output=True, text=True, check=True).stdout
packages = []
for line in plan.splitlines():
    if line.startswith('Inst '):
        match = re.match(r'Inst ([a-z0-9+.:\-]+) (?:\[[^]]+\] )?\(([^ ]+)', line)
        if not match:
            raise RuntimeError('No se pudo interpretar la lista de dependencias de apt.')
        packages.append(f'{match[1]}={match[2]}')
if packages:
    subprocess.run(['apt-get', *opts, 'download', *packages], cwd=work / 'packages', check=True)
for package in (work / 'packages').glob('*.deb'):
    subprocess.run(['dpkg-deb', '-x', str(package), str(dest)], check=True)
# Mantener los enlaces dentro del árbol extraído (los paquetes apuntan a /etc).
for path in dest.rglob('*'):
    if path.is_symlink():
        target = os.readlink(path)
        if target.startswith('/') and (dest / target.lstrip('/')).exists():
            path.unlink()
            path.symlink_to(os.path.relpath(dest / target.lstrip('/'), path.parent))
shutil.copytree(dest / 'usr/lib/libreoffice/share/.registry', dest / 'etc/libreoffice/registry', dirs_exist_ok=True)
fundamental = dest / 'usr/lib/libreoffice/program/fundamentalrc'
text = fundamental.read_text()
text = text.replace('file:///usr/lib/libreoffice', (dest / 'usr/lib/libreoffice').as_uri())
text = text.replace('file:///etc/libreoffice', (dest / 'etc/libreoffice').as_uri())
fundamental.write_text(text)
env = os.environ.copy()
env['LD_LIBRARY_PATH'] = ':'.join(str(dest / p) for p in ['usr/lib/libreoffice/program', 'usr/lib/x86_64-linux-gnu', 'lib/x86_64-linux-gnu'])
subprocess.run([str(dest / 'usr/lib/libreoffice/program/soffice'), '--headless', '--version'], env=env, check=True)
print('Conversor de documentos preparado.')
