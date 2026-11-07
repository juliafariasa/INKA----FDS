// Acompanha quanto da aula foi assistido e envia o progresso ao servidor, que
// é quem decide se a aula pode ser concluída.
//
// Só conta como assistido o trecho reproduzido em sequência a partir do que
// já tinha sido visto: arrastar a barra para a frente não aumenta o progresso.
document.addEventListener('DOMContentLoaded', function () {
    var area = document.getElementById('aula-player');
    var formulario = document.getElementById('form-concluir');
    var video = document.getElementById('aula-video');
    if (!area || !formulario || !video) {
        return;
    }

    // Folga para o player retomar um pouco antes ou depois do ponto pedido.
    var MARGEM_RETOMADA = 3;
    // Folga entre duas leituras, para arredondamentos do player.
    var MARGEM_PASSO = 1;
    var INTERVALO_ENVIO = 10000;

    var duracao = Number(area.dataset.duracao);
    var inicio = Number(area.dataset.inicio);
    var urlProgresso = area.dataset.urlProgresso;
    var token = formulario.querySelector('[name=csrfmiddlewaretoken]').value;
    var campoSegundos = document.getElementById('campo-segundos');
    var textoAssistido = document.getElementById('texto-assistido');

    var alcance = Number(area.dataset.assistidos);
    var enviado = alcance;
    var anterior = null;

    var formatarTempo = function (segundos) {
        segundos = Math.floor(segundos);
        var resto = segundos % 60;
        return Math.floor(segundos / 60) + ':' + (resto < 10 ? '0' : '') + resto;
    };

    // O vídeo avançou em sequência se andou no máximo o tempo real que passou
    // (vezes a velocidade). Um salto maior é a barra sendo arrastada. E só
    // conta se a leitura anterior estava dentro do trecho já assistido.
    var registrarPosicao = function (posicao, velocidade) {
        var agora = Date.now();
        if (anterior !== null) {
            var passo = posicao - anterior.posicao;
            var decorrido = (agora - anterior.momento) / 1000;
            var emSequencia = passo > 0 &&
                passo <= decorrido * velocidade + MARGEM_PASSO;
            var partiuDoAssistido = anterior.posicao <= alcance + MARGEM_RETOMADA;

            if (emSequencia && partiuDoAssistido) {
                alcance = Math.min(Math.max(alcance, posicao), duracao);
                campoSegundos.value = Math.floor(alcance);
                textoAssistido.textContent = formatarTempo(alcance);
            }
        }
        anterior = { posicao: posicao, momento: agora };
    };

    var enviar = function () {
        var segundos = Math.floor(alcance);
        if (segundos <= enviado) {
            return;
        }
        var dados = new FormData();
        dados.append('csrfmiddlewaretoken', token);
        dados.append('segundos', segundos);
        fetch(urlProgresso, {
            method: 'POST',
            body: dados,
            credentials: 'same-origin',
            keepalive: true,
        }).then(function (resposta) {
            if (resposta.ok) {
                enviado = Math.max(enviado, segundos);
            }
        }).catch(function () {
            // Sem conexão: o próximo envio manda o valor de novo.
        });
    };

    // Pausa, carregamento ou salto: a próxima leitura recomeça a contagem.
    var interromper = function () {
        anterior = null;
        enviar();
    };

    var iniciarYoutube = function () {
        var player = null;
        var relogio = null;

        var lerPosicao = function () {
            registrarPosicao(player.getCurrentTime(), player.getPlaybackRate());
        };

        var aoMudarEstado = function (evento) {
            if (evento.data === YT.PlayerState.PLAYING) {
                if (relogio === null) {
                    relogio = setInterval(lerPosicao, 500);
                }
                return;
            }
            clearInterval(relogio);
            relogio = null;
            if (evento.data === YT.PlayerState.ENDED) {
                lerPosicao();
            }
            interromper();
        };

        window.onYouTubeIframeAPIReady = function () {
            player = new YT.Player('aula-video', {
                events: { onStateChange: aoMudarEstado },
            });
        };

        var script = document.createElement('script');
        script.src = 'https://www.youtube.com/iframe_api';
        document.head.appendChild(script);
    };

    var iniciarArquivo = function () {
        var retomar = function () {
            if (inicio > 0 && inicio < video.duration) {
                video.currentTime = inicio;
            }
        };
        // Se os metadados carregaram antes deste script (vídeo em cache), o
        // evento loadedmetadata já passou e não vem mais.
        if (video.readyState >= 1) {
            retomar();
        } else {
            video.addEventListener('loadedmetadata', retomar);
        }
        video.addEventListener('timeupdate', function () {
            if (!video.paused && !video.seeking) {
                registrarPosicao(video.currentTime, video.playbackRate);
            }
        });
        video.addEventListener('seeking', function () {
            anterior = null;
        });
        video.addEventListener('pause', interromper);
    };

    if (area.dataset.tipo === 'youtube') {
        iniciarYoutube();
    } else if (area.dataset.tipo === 'arquivo') {
        iniciarArquivo();
    }

    setInterval(enviar, INTERVALO_ENVIO);
    window.addEventListener('pagehide', enviar);
});
