"""Grava o screencast dos testes E2E com narração, sem nenhum programa extra.

1. Começa a gravar a tela com o ffmpeg.
2. Roda os testes Selenium com E2E_NARRAR=arquivo: a cada passo o narrador
   gera um MP3 da frase (gTTS), mostra a legenda e anota o horário.
3. Para a gravação e junta as falas ao vídeo, cada uma no seu momento.

Uso (na raiz do projeto, com o venv ativo):

    python screencast/gravar_screencast.py
    python screencast/gravar_screencast.py --testes forum.tests_e2e.EstoqueE2ETest

O resultado fica em screencast/saida/screencast_final.mp4.
Requisitos: pip install -r requirements-dev.txt e o ffmpeg instalado (ou o
pacote imageio-ffmpeg, que já traz um ffmpeg).
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / 'screencast' / 'saida'
PASTA_AUDIO = SAIDA / 'audio'
VIDEO_TELA = SAIDA / 'tela.mp4'
VIDEO_FINAL = SAIDA / 'screencast_final.mp4'


def achar_ffmpeg():
    caminho = shutil.which('ffmpeg')
    if caminho:
        return caminho
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit('ffmpeg não encontrado. Instale o ffmpeg ou rode '
                 '"pip install imageio-ffmpeg".')


def entrada_da_tela(args):
    """Argumentos do ffmpeg para capturar a tela inteira em cada sistema."""
    sistema = platform.system()
    if sistema == 'Windows':
        return ['-f', 'gdigrab', '-framerate', str(args.fps), '-i', 'desktop']
    if sistema == 'Darwin':
        # Liste as telas com: ffmpeg -f avfoundation -list_devices true -i ""
        return ['-f', 'avfoundation', '-framerate', str(args.fps),
                '-capture_cursor', '1', '-i', f'{args.tela_mac}:none']
    display = os.environ.get('DISPLAY', ':0')
    return ['-f', 'x11grab', '-framerate', str(args.fps), '-i', display]


def comecar_gravacao(ffmpeg, args):
    comando = [
        ffmpeg, '-y', '-loglevel', 'error', *entrada_da_tela(args),
        # Altura e largura pares, exigência do H.264.
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
        str(VIDEO_TELA),
    ]
    processo = subprocess.Popen(comando, stdin=subprocess.PIPE)
    # Espera o ffmpeg começar a escrever o arquivo para marcar o início.
    limite = time.time() + 15
    while not (VIDEO_TELA.exists() and VIDEO_TELA.stat().st_size > 0):
        if processo.poll() is not None or time.time() > limite:
            sys.exit('O ffmpeg não conseguiu gravar a tela.')
        time.sleep(0.05)
    return processo, time.time()


def parar_gravacao(processo):
    try:
        processo.communicate(b'q', timeout=30)  # "q" encerra e fecha o MP4
    except subprocess.TimeoutExpired:
        processo.kill()


def rodar_testes(args):
    ambiente = dict(os.environ, E2E_NARRAR='arquivo',
                    E2E_PASTA_AUDIO=str(PASTA_AUDIO))
    ambiente.pop('HEADLESS', None)  # o navegador precisa aparecer na tela
    comando = [sys.executable, 'manage.py', 'test', *args.testes]
    return subprocess.run(comando, cwd=RAIZ, env=ambiente).returncode


def juntar_audio(ffmpeg, inicio_video, ajuste):
    linha_do_tempo = PASTA_AUDIO / 'linha_do_tempo.jsonl'
    if not linha_do_tempo.exists():
        print('Nenhuma fala gravada; o vídeo fica sem áudio.')
        shutil.copy(VIDEO_TELA, VIDEO_FINAL)
        return

    falas = [json.loads(linha) for linha in
             linha_do_tempo.read_text(encoding='utf-8').splitlines() if linha]
    comando = [ffmpeg, '-y', '-loglevel', 'error', '-i', str(VIDEO_TELA)]
    filtros = []
    for numero, fala in enumerate(falas, start=1):
        comando += ['-i', str(PASTA_AUDIO / fala['arquivo'])]
        atraso = max(0, int((fala['inicio'] - inicio_video + ajuste) * 1000))
        filtros.append(f'[{numero}:a]adelay={atraso}|{atraso}[a{numero}]')
    entradas = ''.join(f'[a{n}]' for n in range(1, len(falas) + 1))
    filtros.append(f'{entradas}amix=inputs={len(falas)}:normalize=0[audio]')

    comando += [
        '-filter_complex', ';'.join(filtros),
        '-map', '0:v', '-map', '[audio]',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
        str(VIDEO_FINAL),
    ]
    subprocess.run(comando, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--testes', nargs='+', default=['forum.tests_e2e'],
                        help='testes a rodar (padrão: forum.tests_e2e)')
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--tela-mac', default='1',
                        help='número da tela no avfoundation (só macOS)')
    parser.add_argument('--ajuste', type=float, default=0.0,
                        help='segundos para adiantar (-) ou atrasar (+) o áudio')
    args = parser.parse_args()

    ffmpeg = achar_ffmpeg()
    shutil.rmtree(SAIDA, ignore_errors=True)
    PASTA_AUDIO.mkdir(parents=True)

    print('Gravando a tela... não mexa no mouse até os testes terminarem.')
    processo, inicio_video = comecar_gravacao(ffmpeg, args)
    try:
        codigo = rodar_testes(args)
    finally:
        parar_gravacao(processo)

    print('Juntando a narração ao vídeo...')
    juntar_audio(ffmpeg, inicio_video, args.ajuste)
    print(f'Pronto: {VIDEO_FINAL}')
    sys.exit(codigo)


if __name__ == '__main__':
    main()
