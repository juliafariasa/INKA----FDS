"""Narração dos testes E2E para o screencast.

Por padrão não faz nada: os testes rodam rápido e sem pausas. A variável de
ambiente E2E_NARRAR liga a narração:

    E2E_NARRAR=legenda  mostra a frase como legenda no navegador e espera o
                        tempo de leitura (bom para gravar com OBS/Loom/ShareX
                        e narrar com a sua própria voz).
    E2E_NARRAR=voz      legenda + fala a frase em voz alta com o pyttsx3
                        (offline). O OBS grava o áudio do computador.
    E2E_NARRAR=arquivo  legenda + gera um MP3 da frase com o gTTS e anota em
                        que momento ela foi dita. O script
                        screencast/gravar_screencast.py junta esses MP3 ao
                        vídeo da tela no final.

As pausas daqui são de propósito, para dar tempo de ouvir a narração. Elas não
servem para esperar a página: para isso os testes usam WebDriverWait.
"""

import json
import os
import time
from pathlib import Path

MODO = os.environ.get('E2E_NARRAR', '').strip().lower()
PASTA_AUDIO = Path(os.environ.get('E2E_PASTA_AUDIO', 'screencast/saida/audio'))
SEGUNDOS_POR_CARACTERE = 0.065
PAUSA_MINIMA = 1.5

SCRIPT_LEGENDA = """
var legenda = document.getElementById('e2e-legenda');
if (!legenda) {
    legenda = document.createElement('div');
    legenda.id = 'e2e-legenda';
    legenda.style.cssText = [
        'position:fixed', 'left:50%', 'bottom:24px',
        'transform:translateX(-50%)', 'max-width:80%', 'z-index:99999',
        'padding:12px 20px', 'border-radius:8px', 'font:600 20px sans-serif',
        'color:#fff', 'background:rgba(0,0,0,.8)', 'text-align:center',
        'pointer-events:none'
    ].join(';');
    document.body.appendChild(legenda);
}
legenda.textContent = arguments[0];
"""


class Narrador:
    def __init__(self):
        self.modo = MODO
        self.contador = 0
        self.voz = None
        self.linha_do_tempo = None

        if self.modo == 'voz':
            import pyttsx3
            self.voz = pyttsx3.init()
            self.voz.setProperty('rate', 175)
        elif self.modo == 'arquivo':
            PASTA_AUDIO.mkdir(parents=True, exist_ok=True)
            self.linha_do_tempo = PASTA_AUDIO / 'linha_do_tempo.jsonl'

    @property
    def ligado(self):
        return self.modo in ('legenda', 'voz', 'arquivo')

    def __call__(self, driver, texto):
        if not self.ligado:
            return
        self.mostrar_legenda(driver, texto)

        if self.modo == 'voz':
            self.voz.say(texto)
            self.voz.runAndWait()  # bloqueia até terminar de falar
            time.sleep(0.3)
        elif self.modo == 'arquivo':
            try:
                duracao = self.gerar_audio(texto)
            except Exception as erro:  # sem internet, por exemplo
                print(f'\n[narrador] áudio não gerado ({erro}); só legenda.')
                duracao = self.tempo_de_leitura(texto)
            time.sleep(duracao + 0.4)
        else:
            time.sleep(self.tempo_de_leitura(texto))

    def tempo_de_leitura(self, texto):
        return max(PAUSA_MINIMA, len(texto) * SEGUNDOS_POR_CARACTERE)

    def mostrar_legenda(self, driver, texto):
        try:
            driver.execute_script(SCRIPT_LEGENDA, texto)
        except Exception:
            pass  # a legenda é só enfeite: não pode derrubar o teste

    def gerar_audio(self, texto):
        """Gera o MP3, anota quando ele começa e devolve a duração."""
        from gtts import gTTS
        from mutagen.mp3 import MP3

        self.contador += 1
        caminho = PASTA_AUDIO / f'fala_{os.getpid()}_{self.contador:03d}.mp3'
        gTTS(texto, lang='pt', tld='com.br').save(str(caminho))
        duracao = MP3(str(caminho)).info.length

        with open(self.linha_do_tempo, 'a', encoding='utf-8') as arquivo:
            registro = {'inicio': time.time(), 'arquivo': caminho.name,
                        'duracao': duracao, 'texto': texto}
            arquivo.write(json.dumps(registro, ensure_ascii=False) + '\n')
        return duracao


narrar = Narrador()
