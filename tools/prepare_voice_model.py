"""Bundle the upstream multilingual tiny model in the Windows build, not in git."""
from pathlib import Path
from faster_whisper.utils import download_model
from urllib.request import urlopen

path = Path('build-assets/voice-model')
download_model('tiny', output_dir=str(path))
for name in ('model.bin', 'config.json', 'tokenizer.json'):
    if not (path / name).is_file():
        raise RuntimeError('Voice model incomplete: ' + name)
print('Voice model downloaded and checked for the EXE bundle.')

for name, url in [
    ('OPENAI-LICENSE.txt', 'https://raw.githubusercontent.com/openai/whisper/main/LICENSE'),
    ('SYSTRAN-LICENSE.txt', 'https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/LICENSE'),
]:
    with urlopen(url, timeout=30) as response:
        (path / name).write_bytes(response.read(50000))
