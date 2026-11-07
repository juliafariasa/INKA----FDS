# Testes E2E (Selenium) e screencast das histórias 3, 5 e 6

Os testes ficam em `forum/tests_e2e.py`, com dois cenários por história:

| História | Teste | Cenário |
|---|---|---|
| 3 - Estoque | `EstoqueE2ETest.test_cenario1_cadastrar_editar_e_remover_material` | positivo |
| 3 - Estoque | `EstoqueE2ETest.test_cenario2_material_ja_cadastrado_nao_e_duplicado` | negativo |
| 5 - Descarte | `DescarteE2ETest.test_cenario1_lista_conteudos_por_formato_e_empresas` | positivo |
| 5 - Descarte | `DescarteE2ETest.test_cenario2_conteudo_com_link_indisponivel` | negativo |
| 6 - Aulas | `AulasE2ETest.test_cenario1_lista_as_aulas_e_assiste_a_escolhida` | positivo |
| 6 - Aulas | `AulasE2ETest.test_cenario2_nao_conclui_aula_sem_assistir_ate_o_final` | negativo |

## 1. Preparar o ambiente (uma vez só)

Você precisa do **Google Chrome** instalado. O Selenium baixa o ChromeDriver
certo sozinho.

```bash
# na raiz do projeto
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt -r requirements-dev.txt
```

## 2. Rodar os testes

```bash
python manage.py test forum.tests_e2e              # só os E2E, com o Chrome aparecendo
python manage.py test forum.tests_e2e.EstoqueE2ETest   # só uma história
python manage.py test --exclude-tag e2e            # só os testes unitários
python manage.py test                              # tudo
```

Sem abrir a janela do navegador (mais rápido):

```bash
set HEADLESS=1 && python manage.py test forum.tests_e2e      # Windows (cmd)
$env:HEADLESS=1; python manage.py test forum.tests_e2e        # Windows (PowerShell)
HEADLESS=1 python manage.py test forum.tests_e2e              # macOS / Linux
```

Variáveis que ajudam quando algo dá errado: `E2E_ESPERA=20` (aumenta o tempo
máximo de espera de cada elemento), `CHROMEDRIVER=caminho` (usa um driver
específico) e `CHROME_BIN=caminho` (usa outro Chrome).

## 3. Screencast com narração

A variável `E2E_NARRAR` liga a narração. Sem ela os testes rodam rápidos e sem
pausas. Em qualquer modo aparece uma **legenda** na parte de baixo do
navegador com o que está acontecendo.

| `E2E_NARRAR` | O que faz | Use com |
|---|---|---|
| `legenda` | mostra a legenda e pausa o tempo de leitura | OBS/Loom/ShareX e a sua própria voz no microfone |
| `voz` | legenda + fala em voz alta (pyttsx3, offline) | OBS/Loom/ShareX gravando o som do computador |
| `arquivo` | legenda + gera MP3 com o gTTS (precisa de internet) | o script automático abaixo |

### Opção 1: automática, por script (recomendada)

```bash
python screencast/gravar_screencast.py
```

O script grava a tela inteira com o ffmpeg, roda os 6 testes com a narração do
gTTS e no final junta cada fala ao vídeo no momento certo. O resultado fica em
`screencast/saida/screencast_final.mp4`.

* Não mexa no mouse nem troque de janela até aparecer "Pronto".
* Para gravar só uma história: `python screencast/gravar_screencast.py --testes forum.tests_e2e.AulasE2ETest`
* Se a voz estiver um pouco adiantada ou atrasada: `--ajuste 0.5` (atrasa meio segundo) ou `--ajuste -0.5`.
* No macOS, dê permissão de "Gravação de tela" ao Terminal. Se gravar a tela
  errada, liste as telas com `ffmpeg -f avfoundation -list_devices true -i ""`
  e use `--tela-mac NUMERO`.
* O ffmpeg vem pelo pacote `imageio-ffmpeg`. Se der erro ao gravar a tela,
  instale o ffmpeg completo (Windows: `winget install Gyan.FFmpeg`).

### Opção 2: manual, com OBS Studio

1. Instale o OBS Studio (obsproject.com) e abra.
2. Em **Cenas**, clique em `+` e crie a cena "Testes E2E".
3. Em **Fontes**, clique em `+` e escolha **Captura de tela** (Windows: "Captura de tela"; macOS: "Captura de tela do macOS"). Assim aparecem o terminal e o Chrome.
4. Áudio, em **Configurações > Áudio**:
   * **Áudio do desktop**: o dispositivo de saída padrão (grava a voz do `E2E_NARRAR=voz`).
   * **Microfone**: o seu microfone, se você mesma for narrar.
5. Em **Configurações > Saída**, formato de gravação **mp4** e a pasta onde salvar.
6. Deixe o terminal e o Chrome visíveis lado a lado. Clique em **Iniciar gravação** e rode:
   ```bash
   set E2E_NARRAR=voz && python manage.py test forum.tests_e2e -v 2      # Windows (cmd)
   $env:E2E_NARRAR="voz"; python manage.py test forum.tests_e2e -v 2      # PowerShell
   E2E_NARRAR=voz python manage.py test forum.tests_e2e -v 2              # macOS / Linux
   ```
   (Troque `voz` por `legenda` se você for narrar pelo microfone.)
7. Quando aparecer `OK` no terminal, clique em **Parar gravação**.

### Opção 2: com Loom ou ShareX

* **Loom**: escolha "Screen + Cam" ou "Screen only", selecione **Full screen**
  e ligue o microfone (e "Capture system audio", se for usar `E2E_NARRAR=voz`).
  Comece a gravar e rode o mesmo comando do passo 6.
* **ShareX**: em *Captura > Gravação de tela*, abra *Opções de gravação de
  tela* e escolha a fonte de áudio (microfone ou "virtual-audio-capturer" para
  o som do computador). Use *Gravar tela inteira* e rode o comando do passo 6.

`-v 2` faz o terminal mostrar o nome de cada teste e o `ok` dele, o que fica bom
no vídeo.
