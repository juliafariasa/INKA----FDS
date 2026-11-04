document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.aviso-success').forEach(function (aviso) {
        setTimeout(function () {
            aviso.classList.add('sumindo');
            setTimeout(function () {
                aviso.remove();
            }, 500);
        }, 5000);
    });

    var mensagem = document.getElementById('mensagem');
    if (mensagem) {
        var minimo = 20;
        var contador = document.createElement('p');
        contador.className = 'contador';
        mensagem.insertAdjacentElement('afterend', contador);

        var atualizar = function () {
            var total = mensagem.value.trim().length;
            if (total < minimo) {
                contador.textContent = total + ' caracteres (faltam ' +
                    (minimo - total) + ')';
                contador.classList.remove('ok');
            } else {
                contador.textContent = total + ' caracteres';
                contador.classList.add('ok');
            }
        };

        mensagem.addEventListener('input', atualizar);
        atualizar();
    }

    var botaoModo = document.createElement('button');
    botaoModo.type = 'button';
    botaoModo.className = 'botao-modo';
    document.querySelector('nav').appendChild(botaoModo);

    var aplicarModo = function (noturno) {
        document.body.classList.toggle('modo-noturno', noturno);
        botaoModo.textContent = noturno ? 'Modo claro' : 'Modo noturno';
        botaoModo.setAttribute('aria-pressed', noturno);
    };

    aplicarModo(localStorage.getItem('modo') === 'noturno');

    botaoModo.addEventListener('click', function () {
        var noturno = !document.body.classList.contains('modo-noturno');
        localStorage.setItem('modo', noturno ? 'noturno' : 'claro');
        aplicarModo(noturno);
    });

    var botaoTopo = document.createElement('button');
    botaoTopo.type = 'button';
    botaoTopo.className = 'voltar-topo';
    botaoTopo.textContent = '↑';
    botaoTopo.setAttribute('aria-label', 'Voltar ao topo');
    document.body.appendChild(botaoTopo);

    botaoTopo.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    window.addEventListener('scroll', function () {
        botaoTopo.classList.toggle('visivel', window.scrollY > 300);
    });

    desenharTintaDecorativa();
    iniciarDesenho();
});

// Gera a mancha de tinta do hero em SVG. Cada faixa segue uma linha-guia e é
// formada por vários fios finos. Os valores usam o viewBox 1280x806.
function desenharTintaDecorativa() {
    var svg = document.getElementById('tinta-decorativa');
    if (!svg) {
        return;
    }

    var faixas = [
        {
            largura: 3, fios: 3,
            guia: [[985, 378], [952, 394], [905, 402], [886, 420], [908, 428],
                [900, 452], [862, 490], [800, 506], [742, 520], [712, 545]],
        },
        {
            largura: 30, fios: 13,
            guia: [[322, 524], [395, 492], [468, 508], [535, 558], [604, 598],
                [676, 590], [742, 556], [812, 540], [868, 566], [886, 618],
                [852, 656], [786, 682], [716, 668]],
        },
        {
            largura: 24, fios: 11,
            guia: [[395, 560], [452, 572], [506, 622], [566, 650], [640, 642],
                [706, 616], [770, 600], [828, 612], [832, 640], [782, 652]],
        },
        {
            largura: 26, fios: 11,
            guia: [[604, 598], [566, 626], [548, 668], [578, 706], [600, 742],
                [606, 792]],
        },
        {
            largura: 22, fios: 10,
            guia: [[424, 640], [474, 664], [536, 678], [598, 672], [652, 694],
                [716, 682], [760, 668]],
        },
        {
            largura: 12, fios: 6,
            guia: [[536, 690], [540, 722], [566, 738], [552, 762]],
        },
        {
            largura: 15, fios: 7,
            guia: [[712, 545], [690, 566], [712, 592], [760, 590], [800, 570]],
        },
    ];

    
    var semente = 7;
    var sortear = function () {
        semente = (semente * 16807) % 2147483647;
        return semente / 2147483647;
    };

    var criar = function (tag, atributos) {
        var elemento = document.createElementNS(svg.namespaceURI, tag);
        Object.keys(atributos).forEach(function (nome) {
            elemento.setAttribute(nome, atributos[nome]);
        });
        svg.appendChild(elemento);
    };

    faixas.forEach(function (faixa) {
        var pontos = suavizarGuia(faixa.guia, 14);
        for (var fio = 0; fio < faixa.fios; fio++) {
            var deslocamento = faixa.fios === 1 ? 0 :
                fio / (faixa.fios - 1) * 2 - 1;
            var fase = sortear() * 6;
            var ondas = 3 + sortear() * 5;
            // Cada fio cobre só parte da faixa, o que desfia as pontas.
            var inicio = faixa.fios > 3 ? sortear() * 0.22 : 0;
            var fim = faixa.fios > 3 ? 1 - sortear() * 0.22 : 1;
            var trecho = pontos.slice(
                Math.round(inicio * (pontos.length - 1)),
                Math.round(fim * (pontos.length - 1)) + 1
            );
            var caminho = trecho.map(function (ponto, i) {
                var t = inicio + i / (trecho.length - 1) * (fim - inicio);
                var anterior = trecho[Math.max(i - 1, 0)];
                var proximo = trecho[Math.min(i + 1, trecho.length - 1)];
                var dx = proximo[0] - anterior[0];
                var dy = proximo[1] - anterior[1];
                var tamanho = Math.hypot(dx, dy) || 1;
                var abertura = faixa.largura * Math.sin(Math.PI * t);
                var afastamento = deslocamento * abertura +
                    Math.sin(t * ondas + fase) * abertura * 0.4;
                return (i ? 'L' : 'M') +
                    (ponto[0] - dy / tamanho * afastamento).toFixed(1) + ' ' +
                    (ponto[1] + dx / tamanho * afastamento).toFixed(1);
            }).join('');

            criar('path', {
                d: caminho,
                stroke: sortear() > 0.5 ? '#74dc6e' : '#2f8f3a',
                'stroke-width': (0.45 + sortear() * 0.75).toFixed(2),
                'stroke-dasharray': sortear() > 0.45 ?
                    Math.round(40 + sortear() * 110) + ' ' +
                    Math.round(4 + sortear() * 14) : 'none',
                opacity: (0.5 + sortear() * 0.5).toFixed(2),
            });
        }
    });

    // Respingos ao redor das pontas da mancha.
    [[330, 524], [420, 640], [600, 780], [850, 655], [900, 440]].forEach(function (centro) {
        for (var i = 0; i < 9; i++) {
            criar('circle', {
                cx: (centro[0] + (sortear() - 0.5) * 70).toFixed(1),
                cy: (centro[1] + (sortear() - 0.5) * 50).toFixed(1),
                r: (0.4 + sortear() * 1.2).toFixed(1),
                fill: '#7fe878',
            });
        }
    });
}

// Passa uma curva Catmull-Rom pelos pontos da guia.
function suavizarGuia(guia, passos) {
    var pontos = [];
    for (var i = 0; i < guia.length - 1; i++) {
        var p0 = guia[Math.max(i - 1, 0)];
        var p1 = guia[i];
        var p2 = guia[i + 1];
        var p3 = guia[Math.min(i + 2, guia.length - 1)];
        for (var passo = 0; passo < passos; passo++) {
            var t = passo / passos;
            pontos.push([0, 1].map(function (eixo) {
                return 0.5 * (2 * p1[eixo] + (p2[eixo] - p0[eixo]) * t +
                    (2 * p0[eixo] - 5 * p1[eixo] + 4 * p2[eixo] - p3[eixo]) * t * t +
                    (3 * p1[eixo] - p0[eixo] - 3 * p2[eixo] + p3[eixo]) * t * t * t);
            }));
        }
    }
    pontos.push(guia[guia.length - 1]);
    return pontos;
}

function iniciarDesenho() {
    var canvas = document.getElementById('canvas-desenho');
    if (!canvas) {
        return;
    }

    // Ponta da agulha dentro do PNG original, em proporção do arquivo.
    var PONTA_CANETA_X = 768 / 3000;
    var PONTA_CANETA_Y = 2069 / 3508;
    var COR_TRACO = '#6dff6d';
    var ESPESSURA_TRACO = 3;

    var hero = document.getElementById('hero-desenho');
    var area = document.getElementById('area-desenho');
    var cursor = document.getElementById('cursor-caneta');
    var botaoDesenhar = document.getElementById('iniciar-desenho');
    var controles = document.getElementById('controles-desenho');
    var botoes = {};
    controles.querySelectorAll('button').forEach(function (botao) {
        botoes[botao.dataset.acao] = botao;
    });

    var contexto = canvas.getContext('2d');
    var tracos = [];
    var desfeitos = [];
    var tracoAtual = null;
    var ponteiroAtivo = null;
    var somMaquina = new Audio('/static/audio/maquina-tatuagem.mp3');
    somMaquina.loop = true;
    somMaquina.volume = 0.4;
    var iniciarSom = function () {
        console.log('INICIAR SOM FOI CHAMADO!');

    if (somMaquina.paused) {
        somMaquina.currentTime = 0;
        somMaquina.play().catch(function (erro) {
            console.warn('Não foi possível reproduzir o áudio:', erro);
        });
    }
};
    

    var pararSom = function () {
    somMaquina.pause();
    somMaquina.currentTime = 0;
};

    // Os pontos ficam em coordenadas fixas da área onde o desenho começou.
    // Assim, redimensionar só muda uma escala uniforme e nada se deforma.
    var base = null;
    var vista = { largura: 0, altura: 0, escala: 1, x: 0, y: 0 };

    var atualizarVista = function () {
        vista.largura = area.clientWidth;
        vista.altura = area.clientHeight;
        var referencia = base || { largura: vista.largura, altura: vista.altura };
        vista.escala = Math.min(
            vista.largura / referencia.largura,
            vista.altura / referencia.altura
        );
        vista.x = (vista.largura - referencia.largura * vista.escala) / 2;
        vista.y = (vista.altura - referencia.altura * vista.escala) / 2;
    };

    var pontoNaTela = function (ponto) {
        return {
            x: ponto.x * vista.escala + vista.x,
            y: ponto.y * vista.escala + vista.y,
        };
    };

    var prepararPincel = function () {
        contexto.strokeStyle = COR_TRACO;
        contexto.fillStyle = COR_TRACO;
        contexto.lineCap = 'round';
        contexto.lineJoin = 'round';
        contexto.lineWidth = Math.max(ESPESSURA_TRACO * vista.escala, 1.5);
        contexto.shadowColor = 'rgba(109, 255, 109, 0.75)';
        contexto.shadowBlur = 8;
    };

    // Desenha um trecho curvo entre os pontos médios, o que evita quinas.
    var desenharTrecho = function (pontos, indice) {
        var anterior = pontoNaTela(pontos[indice - 1]);
        var meio = pontoNaTela(pontos[indice]);
        var proximo = pontos[indice + 1] ? pontoNaTela(pontos[indice + 1]) : meio;
        var inicio = indice === 1 ? anterior : {
            x: (anterior.x + meio.x) / 2,
            y: (anterior.y + meio.y) / 2,
        };

        contexto.beginPath();
        contexto.moveTo(inicio.x, inicio.y);
        contexto.quadraticCurveTo(
            meio.x, meio.y, (meio.x + proximo.x) / 2, (meio.y + proximo.y) / 2
        );
        contexto.stroke();
    };

    var desenharPonto = function (ponto) {
        var tela = pontoNaTela(ponto);
        contexto.beginPath();
        contexto.arc(tela.x, tela.y, contexto.lineWidth / 2, 0, Math.PI * 2);
        contexto.fill();
    };

    var redesenhar = function () {
        contexto.clearRect(0, 0, vista.largura, vista.altura);
        prepararPincel();
        tracos.forEach(function (traco) {
            desenharPonto(traco[0]);
            for (var i = 1; i < traco.length; i++) {
                desenharTrecho(traco, i);
            }
        });
    };

    var ajustarCanvas = function () {
        var densidade = window.devicePixelRatio || 1;
        atualizarVista();
        canvas.width = Math.round(vista.largura * densidade);
        canvas.height = Math.round(vista.altura * densidade);
        contexto.setTransform(densidade, 0, 0, densidade, 0, 0);
        redesenhar();
    };

    var atualizarControles = function () {
        botoes.desfazer.disabled = tracos.length === 0;
        botoes.refazer.disabled = desfeitos.length === 0;
        botoes.limpar.disabled = tracos.length === 0;
    };

    var posicaoNoCanvas = function (evento) {
        var limites = canvas.getBoundingClientRect();
        return {
            x: (evento.clientX - limites.left - vista.x) / vista.escala,
            y: (evento.clientY - limites.top - vista.y) / vista.escala,
        };
    };

    // Encaixa a ponta da agulha, e não o canto da imagem, no ponteiro.
    var moverCursor = function (evento) {
        if (evento.pointerType === 'touch') {
            cursor.classList.remove('visivel');
            return;
        }
        var limites = area.getBoundingClientRect();
        var x = evento.clientX - limites.left - cursor.offsetWidth * PONTA_CANETA_X;
        var y = evento.clientY - limites.top - cursor.offsetHeight * PONTA_CANETA_Y;
        cursor.style.transform = 'translate(' + x + 'px, ' + y + 'px)';
        cursor.classList.add('visivel');
    };

    var encerrarTraco = function (evento) {
        if (evento.pointerId !== ponteiroAtivo) {
            return;
        }
        // Os trechos param no meio do último par de pontos: falta fechar o fim.
        if (tracoAtual.length > 1) {
            desenharTrecho(tracoAtual, tracoAtual.length - 1);
        }
        ponteiroAtivo = null;
        tracoAtual = null;
        pararSom();
        atualizarControles();
    };

    canvas.addEventListener('pointerdown', function (evento) {
        if (!evento.isPrimary || evento.button !== 0) {
            return;
        }
        evento.preventDefault();
        canvas.setPointerCapture(evento.pointerId);
        ponteiroAtivo = evento.pointerId;
        iniciarSom();

        if (!base) {
            base = { largura: vista.largura, altura: vista.altura };
            atualizarVista();
        }

        tracoAtual = [posicaoNoCanvas(evento)];
        tracos.push(tracoAtual);
        desfeitos = [];
        prepararPincel();
        desenharPonto(tracoAtual[0]);
        moverCursor(evento);
        atualizarControles();
    });

    canvas.addEventListener('pointermove', function (evento) {
        moverCursor(evento);
        if (evento.pointerId !== ponteiroAtivo) {
            return;
        }

        
        var eventos = evento.getCoalescedEvents ? evento.getCoalescedEvents() : [];
        (eventos.length ? eventos : [evento]).forEach(function (item) {
            tracoAtual.push(posicaoNoCanvas(item));
            if (tracoAtual.length > 2) {
                desenharTrecho(tracoAtual, tracoAtual.length - 2);
            }
        });
    });

    canvas.addEventListener('pointerup', encerrarTraco);
    canvas.addEventListener('pointercancel', encerrarTraco);
    canvas.addEventListener('pointerleave', function () {
        cursor.classList.remove('visivel');
    });

    var alternarModo = function (ativo) {
        hero.classList.toggle('desenhando', ativo);
        controles.hidden = !ativo;
        if (!ativo) {
            pararSom();
            cursor.classList.remove('visivel');
        }
        (ativo ? botoes.finalizar : botaoDesenhar).focus();
    };

    var acoes = {
        desfazer: function () {
            desfeitos.push(tracos.pop());
        },
        refazer: function () {
            tracos.push(desfeitos.pop());
        },
        // Os traços vão para a pilha de refazer: um clique acidental tem volta.
        limpar: function () {
            desfeitos = desfeitos.concat(tracos.reverse());
            tracos = [];
        },
        finalizar: function () {
            alternarModo(false);
        },
    };

    controles.addEventListener('click', function (evento) {
        var acao = evento.target.dataset.acao;
        if (acoes[acao]) {
            acoes[acao]();
            redesenhar();
            atualizarControles();
        }
    });

    botaoDesenhar.addEventListener('click', function () {
        alternarModo(true);
    });

    new ResizeObserver(ajustarCanvas).observe(area);
    atualizarControles();
}
