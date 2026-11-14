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

    iniciarMenu();
    desenharTintaDecorativa();
    iniciarDesenho();
    iniciarAnimacaoCaneta();
    iniciarFormularioContato();
    iniciarRevelacaoEquipe();
    revelarSecoes();
});

function iniciarMenu() {
    var botao = document.querySelector('.menu-botao');
    var menu = document.getElementById('menu');
    var aberto = function () {
        return document.body.classList.contains('menu-aberto');
    };

    var alternar = function (abrir) {
        document.body.classList.toggle('menu-aberto', abrir);
        botao.setAttribute('aria-expanded', abrir);
        botao.setAttribute('aria-label', abrir ? 'Fechar menu' : 'Abrir menu');
        if (abrir) {
            menu.querySelector('a').focus({ preventScroll: true });
        }
    };

    botao.addEventListener('click', function () {
        alternar(!aberto());
    });

    // Clique fora da gaveta fecha; o fundo escurecido é o próprio body.
    document.addEventListener('click', function (evento) {
        if (aberto() && !menu.contains(evento.target) &&
                !botao.contains(evento.target)) {
            alternar(false);
        }
    });

    document.addEventListener('keydown', function (evento) {
        if (evento.key === 'Escape' && aberto()) {
            alternar(false);
            botao.focus();
        }
    });
}

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
    var corClara = corDaPaleta('--inka-verde-claro');
    var corMedia = corDaPaleta('--inka-verde');
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
                stroke: sortear() > 0.5 ? corClara : corMedia,
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
                fill: corClara,
            });
        }
    });
}

// Lê uma cor da paleta definida em :root no estilo.css.
function corDaPaleta(variavel) {
    return getComputedStyle(document.documentElement)
        .getPropertyValue(variavel).trim();
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
    var COR_TRACO = corDaPaleta('--inka-verde-claro');
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
        contexto.shadowColor = COR_TRACO;
        contexto.shadowBlur = 2;
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

// Anima a ilustração de "O que é o INKA": a tinta se espalha a partir da ponta
// enquanto a caneta faz pequenos movimentos de escrita. Toca quando a figura
// aparece na tela e de novo quando o ponteiro passa sobre ela.
function iniciarAnimacaoCaneta() {
    var figura = document.getElementById('animacao-caneta');
    if (!figura || !('IntersectionObserver' in window) ||
            window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    var DURACAO = 4200;
    var REVELADO_INICIAL = -0.15;
    var REVELADO_FINAL = 1.15;
    var animando = false;

    var aplicar = function (revelado, x, y, giro) {
        figura.style.setProperty('--revelado', revelado.toFixed(3));
        figura.style.setProperty('--caneta-x', x.toFixed(2) + 'px');
        figura.style.setProperty('--caneta-y', y.toFixed(2) + 'px');
        figura.style.setProperty('--caneta-giro', giro.toFixed(2) + 'deg');
    };

    var tocar = function () {
        if (animando) {
            return;
        }
        animando = true;
        var inicio = null;
        var amplitude = figura.clientWidth * 0.012;

        var quadro = function (agora) {
            if (inicio === null) {
                inicio = agora;
            }
            var t = Math.min((agora - inicio) / DURACAO, 1);
            var segundos = (agora - inicio) / 1000;
            // O movimento começa e termina parado, como alguém que encosta e
            // levanta a caneta. A tinta desacelera ao se espalhar.
            var forca = Math.sin(Math.PI * t);
            var espalhado = 1 - Math.pow(1 - t, 3);

            aplicar(
                REVELADO_INICIAL + espalhado * (REVELADO_FINAL - REVELADO_INICIAL),
                Math.sin(segundos * 7) * amplitude * forca,
                Math.sin(segundos * 14 + 1) * amplitude * 0.6 * forca,
                Math.sin(segundos * 5) * 1.6 * forca
            );

            if (t < 1) {
                requestAnimationFrame(quadro);
            } else {
                animando = false;
            }
        };

        aplicar(REVELADO_INICIAL, 0, 0, 0);
        requestAnimationFrame(quadro);
    };

    aplicar(REVELADO_INICIAL, 0, 0, 0);
    new IntersectionObserver(function (entradas, observador) {
        if (entradas[0].isIntersecting) {
            observador.disconnect();
            // Espera o PNG carregar para a tinta não se espalhar no vazio.
            var imagens = Array.prototype.map.call(
                figura.querySelectorAll('img'),
                function (imagem) {
                    return imagem.decode().catch(function () {});
                }
            );
            Promise.all(imagens).then(tocar);
        }
    }, { threshold: 0.35 }).observe(figura);
    figura.addEventListener('pointerenter', tocar);
}

// Fale Conosco: leva o foco ao primeiro campo com erro e evita envio duplo.
function iniciarFormularioContato() {
    var formulario = document.getElementById('formulario-contato');
    if (!formulario) {
        return;
    }

    var primeiroErro = formulario.querySelector('[aria-invalid="true"]');
    if (primeiroErro) {
        primeiroErro.focus();
    }

    var botao = formulario.querySelector('[type="submit"]');
    var textoBotao = botao.querySelector('.landing-botao-texto');
    var textoOriginal = textoBotao.textContent;

    formulario.addEventListener('submit', function () {
        botao.disabled = true;
        textoBotao.textContent = 'Enviando…';
    });

    // Ao voltar pelo histórico, o navegador pode restaurar o botão travado.
    window.addEventListener('pageshow', function () {
        botao.disabled = false;
        textoBotao.textContent = textoOriginal;
    });
}

// Quem Somos: cada integrante aparece suavemente ao entrar na tela. Sem
// JavaScript, ou com movimento reduzido, a equipe já aparece inteira.
function iniciarRevelacaoEquipe() {
    var grade = document.getElementById('equipe-grade');
    if (!grade || !('IntersectionObserver' in window) ||
            window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    var observador = new IntersectionObserver(function (entradas) {
        entradas.forEach(function (entrada) {
            if (entrada.isIntersecting) {
                entrada.target.classList.remove('equipe-oculto');
                observador.unobserve(entrada.target);
            }
        });
    }, { threshold: 0.15 });

    grade.querySelectorAll('.equipe-item').forEach(function (item, indice) {
        // Pequeno atraso em cascata entre vizinhos da mesma linha.
        item.style.transitionDelay = (indice % 4) * 90 + 'ms';
        item.classList.add('equipe-oculto');
        observador.observe(item);
    });
}

// Seções do tema escuro entram ao aparecer na tela. A primeira de cada página
// já está à vista e fica de fora; sem JavaScript tudo aparece normalmente.
function revelarSecoes() {
    var secoes = Array.prototype.slice.call(
        document.querySelectorAll('.landing-secao'), 1
    );
    if (!secoes.length || !('IntersectionObserver' in window) ||
            window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    var observador = new IntersectionObserver(function (entradas) {
        entradas.forEach(function (entrada) {
            if (entrada.isIntersecting) {
                entrada.target.classList.add('revelada');
                observador.unobserve(entrada.target);
            }
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    secoes.forEach(function (secao) {
        secao.classList.add('revelar');
        observador.observe(secao);
    });
}


/* ==========================================
   INKA - MÁQUINA DE ESCREVER
   ========================================== */

document.addEventListener("DOMContentLoaded", () => {
    const experiencia = document.querySelector("#type-experiencia");
    const botao = document.querySelector("#type-acionar");
    const textoBotao = document.querySelector("#type-acao-texto");
    const formulario = document.querySelector("#type-form-container");
    const fechar = document.querySelector("#type-fechar");
    const titulo = document.querySelector("#type-titulo");
    const subtitulo = document.querySelector("#type-subtitulo");
    const somMaquina = document.querySelector("#som-maquina-escrever");

    if (!experiencia || !botao || !formulario || !fechar) return;

    let aberto = false;
    let digitando = false;
    let temporizadores = [];

    const agendar = (funcao, tempo) => {
        const temporizador = setTimeout(funcao, tempo);
        temporizadores.push(temporizador);
    };

    const limparTemporizadores = () => {
        temporizadores.forEach(clearTimeout);
        temporizadores = [];
    };

    const iniciarSom = () => {
        if (!somMaquina) return;

        somMaquina.pause();
        somMaquina.currentTime = 0;

        const reproducao = somMaquina.play();

        if (reproducao) {
            reproducao.catch(() => {
                console.warn("Não foi possível reproduzir o áudio da máquina.");
            });
        }
    };

    const pararSom = () => {
        if (!somMaquina) return;

        somMaquina.pause();
        somMaquina.currentTime = 0;
    };

    const abrirMaquina = () => {
        if (aberto || digitando) return;

        limparTemporizadores();

        digitando = true;
        experiencia.classList.add("type-digitando");
        textoBotao.textContent = "DIGITANDO...";

        iniciarSom();

        const tituloFinal = "Toda conversa\ncomeça com uma ideia.";
        const subtituloFinal = "Escreva para a gente.";

        titulo.textContent = "";
        subtitulo.textContent = "";

        let i = 0;

        const escrever = () => {
            if (i < tituloFinal.length) {
                titulo.textContent += tituloFinal[i];
                i++;

                agendar(escrever, 65);
            } else {
                let j = 0;

                const escreverSubtitulo = () => {
                    if (j < subtituloFinal.length) {
                        subtitulo.textContent += subtituloFinal[j];
                        j++;

                        agendar(escreverSubtitulo, 45);
                    } else {
                        finalizar();
                    }
                };

                escreverSubtitulo();
            }
        };

        const finalizar = () => {
            pararSom();

            experiencia.classList.remove("type-digitando");
            experiencia.classList.add("type-aberto");

            formulario.hidden = false;
            textoBotao.textContent = "MÁQUINA ACIONADA";

            aberto = true;
            digitando = false;

            agendar(() => {
                if (window.innerWidth <= 850) {
                    formulario.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                }

                const primeiroCampo = formulario.querySelector("input");

                if (primeiroCampo) {
                    primeiroCampo.focus({ preventScroll: true });
                }
            }, 300);
        };

        escrever();
    };

    const fecharMaquina = () => {
        limparTemporizadores();
        pararSom();

        experiencia.classList.remove("type-aberto", "type-digitando");
        formulario.hidden = true;

        titulo.textContent = "Toda conversa\ncomeça com uma ideia.";
        subtitulo.textContent = "Escreva para a gente.";

        textoBotao.textContent = "ACIONAR A MÁQUINA";

        aberto = false;
        digitando = false;

        botao.focus();
    };

    botao.addEventListener("click", abrirMaquina);
    fechar.addEventListener("click", fecharMaquina);

    document.addEventListener("keydown", (evento) => {
        if (evento.key === "Escape" && aberto) {
            fecharMaquina();
        }
    });
});


/* =========================================
   INKA VAULT / INTERAÇÕES 3D
========================================= */

document.addEventListener("DOMContentLoaded", () => {
    const page = document.querySelector("#inka-vault");

    if (!page) return;

    const scene = page.querySelector("#vault-scene");
    const control = page.querySelector("#vault-control");
    const status = page.querySelector("#vault-status-text");
    const drawers = page.querySelectorAll(".vault-drawer");

    if (!scene || !control) return;

    let vaultState = "closed";
    let transitionTimer = null;

    const setStatus = (message) => {
        if (status) status.textContent = message;
    };

    const updateControl = () => {
        const isOpen = vaultState === "open";

        control.querySelector(".vault-control-text").textContent =
            isOpen ? "FECHAR COFRE" : "ABRIR COFRE";

        control.setAttribute(
            "aria-label",
            isOpen ? "Fechar cofre" : "Abrir cofre"
        );
    };

    const openVault = () => {
        if (vaultState === "open" || vaultState === "opening") return;

        clearTimeout(transitionTimer);
        vaultState = "opening";

        scene.classList.remove("is-closing");
        scene.classList.remove("is-open");
        scene.classList.add("is-opening");

        setStatus("DESTRAVANDO MECANISMO...");
        updateControl();

        transitionTimer = setTimeout(() => {
            scene.classList.remove("is-opening");
            scene.classList.add("is-open");

            vaultState = "open";
            setStatus("COFRE ABERTO / SISTEMA ATIVO");
            updateControl();
        }, 2050);
    };

    const closeVault = () => {
        if (vaultState === "closed" || vaultState === "closing") return;

        clearTimeout(transitionTimer);
        vaultState = "closing";

        scene.classList.remove("is-opening");
        scene.classList.remove("is-open");
        scene.classList.add("is-closing");

        setStatus("TRAVANDO COFRE...");
        updateControl();

        transitionTimer = setTimeout(() => {
            scene.classList.remove("is-closing");

            vaultState = "closed";
            setStatus("COFRE FECHADO / AGUARDANDO");
            updateControl();
        }, 1850);
    };

    control.addEventListener("click", () => {
        if (vaultState === "opening" || vaultState === "closing") return;

        if (vaultState === "open") {
            closeVault();
        } else {
            openVault();
        }
    });

    // Abertura cinematográfica ao entrar na página
    updateControl();

    setTimeout(() => {
        openVault();
    }, 650);

    // Interação individual das gavetas
    drawers.forEach((drawer) => {
        const trigger = drawer.querySelector(".vault-drawer-pull");
        const info = drawer.querySelector(".vault-drawer-info");

        if (!trigger || !info) return;

        trigger.addEventListener("click", () => {
            const wasOpen = drawer.classList.contains("is-open");

            drawers.forEach((other) => {
                other.classList.remove("is-open");

                const otherTrigger = other.querySelector(
                    ".vault-drawer-pull"
                );

                const otherInfo = other.querySelector(
                    ".vault-drawer-info"
                );

                if (otherTrigger) {
                    otherTrigger.setAttribute("aria-expanded", "false");
                }

                if (otherInfo) {
                    otherInfo.setAttribute("aria-hidden", "true");
                }
            });

            if (wasOpen) return;

            drawer.classList.add("is-open");
            trigger.setAttribute("aria-expanded", "true");
            info.setAttribute("aria-hidden", "false");
        });
    });

    // Fecha gavetas abertas com Escape
    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;

        drawers.forEach((drawer) => {
            drawer.classList.remove("is-open");

            const trigger = drawer.querySelector(".vault-drawer-pull");
            const info = drawer.querySelector(".vault-drawer-info");

            if (trigger) {
                trigger.setAttribute("aria-expanded", "false");
            }

            if (info) {
                info.setAttribute("aria-hidden", "true");
            }
        });
    });

    // Perspectiva e iluminação que acompanham o mouse
    const canHover = window.matchMedia("(hover: hover: fine)").matches;
    const reduceMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    if (canHover && !reduceMotion) {
        scene.addEventListener("pointermove", (event) => {
            const bounds = scene.getBoundingClientRect();

            const x = (event.clientX - bounds.left) / bounds.width;
            const y = (event.clientY - bounds.top) / bounds.height;

            const rotateY = (x - 0.5) * 2.8;
            const rotateX = (0.5 - y) * 2.2;

            scene.style.setProperty("--mouse-x", `${x * 100}%`);
            scene.style.setProperty("--mouse-y", `${y * 100}%`);
            scene.style.setProperty(
                "--scene-rotate-x",
                `${rotateX}deg`
            );
            scene.style.setProperty(
                "--scene-rotate-y",
                `${rotateY}deg`
            );
        });

        scene.addEventListener("pointerleave", () => {
            scene.style.setProperty("--mouse-x", "50%");
            scene.style.setProperty("--mouse-y", "35%");
            scene.style.setProperty("--scene-rotate-x", "0deg");
            scene.style.setProperty("--scene-rotate-y", "0deg");
        });
    }
});
