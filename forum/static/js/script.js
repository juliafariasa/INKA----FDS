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
    const canHover = window.matchMedia(
        "(hover: hover) and (pointer: fine)"
    ).matches;
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

document.addEventListener("DOMContentLoaded", () => {
    const livro = document.querySelector("#aula-livro");
    const botaoAbrir = document.querySelector("#aula-abrir-livro");
    const instrucao = document.querySelector("#aula-livro-instrucao");

    if (!livro || !botaoAbrir) return;

    botaoAbrir.addEventListener("click", () => {
        livro.classList.add("aula-livro-aberto");

        botaoAbrir.disabled = true;

        if (instrucao) {
            instrucao.textContent = "LIVRO ABERTO · NOVO REGISTRO";
        }

        setTimeout(() => {
            const primeiroCampo = document.querySelector("#titulo");

            if (primeiroCampo) {
                primeiroCampo.focus({ preventScroll: true });
            }
        }, 1900);
    });
});

document.addEventListener("DOMContentLoaded", () => {

    const livro = document.querySelector("#aula-livro");
    const botaoAbrir = document.querySelector("#aula-abrir-livro");
    const instrucao = document.querySelector("#aula-livro-instrucao");
    const folha = document.querySelector("#aula-folha-surpresa");

    if (!livro || !botaoAbrir || !folha) return;

    let livroAberto = false;

    botaoAbrir.addEventListener("click", () => {

        if (livroAberto) return;

        livroAberto = true;
        botaoAbrir.disabled = true;

        // ETAPA 1: ABRIR A CAPA
        livro.classList.add("aula-livro-aberto");

        if (instrucao) {
            instrucao.textContent = "ABRINDO O REGISTRO...";
        }

        // ETAPA 2: ARRANCAR A FOLHA
        setTimeout(() => {

            if (instrucao) {
                instrucao.textContent = "REVELANDO O CONTEÚDO...";
            }

            // Prepara a revelação antes de iniciar a animação
            const revelarFormulario = () => {

                livro.classList.add("aula-conteudo-revelado");

                if (instrucao) {
                    instrucao.textContent = "NOVO REGISTRO DISPONÍVEL";
                }

                // Foca no primeiro campo depois da entrada
                setTimeout(() => {

                    const primeiroCampo = document.querySelector("#titulo");

                    if (primeiroCampo) {
                        primeiroCampo.focus({ preventScroll: true });
                    }

                }, 600);

            };

            folha.addEventListener(
                "animationend",
                revelarFormulario,
                { once: true }
            );

            livro.classList.add("aula-folha-arrancando");

        }, 1500);

    });

});

document.addEventListener("DOMContentLoaded", () => {

    const livro = document.querySelector("#aula-livro");
    const botaoAbrir = document.querySelector("#aula-abrir-livro");
    const instrucao = document.querySelector("#aula-livro-instrucao");
    const folha = document.querySelector("#aula-folha-surpresa");

    if (!livro || !botaoAbrir || !folha) return;

    let livroAberto = false;

    botaoAbrir.addEventListener("click", () => {

        if (livroAberto) return;

        livroAberto = true;
        botaoAbrir.disabled = true;

        livro.classList.add("aula-livro-aberto");

        if (instrucao) {
            instrucao.textContent = "ABRINDO O LIVRO...";
        }

        setTimeout(() => {

            if (instrucao) {
                instrucao.textContent = "REVELANDO O CONTEÚDO...";
            }

            folha.addEventListener("animationend", () => {

                livro.classList.add("aula-conteudo-revelado");

                if (instrucao) {
                    instrucao.textContent = "NOVO REGISTRO DISPONÍVEL";
                }

                setTimeout(() => {
                    const primeiroCampo = document.querySelector("#titulo");

                    if (primeiroCampo) {
                        primeiroCampo.focus({ preventScroll: true });
                    }
                }, 700);

            }, { once: true });

            livro.classList.add("aula-folha-arrancando");

        }, 1500);

    });

});

/* =========================================
   MINHA ÁREA / COPIAR LINK DO PERFIL
   O link continua visível na página para quem não puder copiar pelo botão
   (navegador sem permissão para a área de transferência, por exemplo).
========================================= */

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-copiar]").forEach((botao) => {
        const aviso = botao.parentElement.querySelector(".ma-copiado");

        const avisar = (texto) => {
            if (aviso) aviso.textContent = texto;
        };

        botao.addEventListener("click", () => {
            if (!navigator.clipboard) {
                avisar("Copie o link logo abaixo.");
                return;
            }
            navigator.clipboard.writeText(botao.dataset.copiar).then(
                () => avisar("Link copiado!"),
                () => avisar("Não deu para copiar. Use o link logo abaixo.")
            );
        });
    });
});

/* ==============================================
   INKA / CONTROL ROOM · INTERAÇÕES
============================================== */

document.addEventListener("DOMContentLoaded", () => {

    const pagina = document.querySelector("#ma-atelier");
    if (!pagina) return;

    const reduzirMovimento = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    );

    const links = [...pagina.querySelectorAll(".ma-nav-link")];
    const progresso = pagina.querySelector("#ma-progresso-pagina");
    const voltar = pagina.querySelector(".ma-voltar-inicio");

    const secoes = links.map(link => ({
        link,
        elemento: document.querySelector(link.getAttribute("href"))
    })).filter(item => item.elemento);

    /* ==========================================
       01 / ROLAGEM ENTRE CAPÍTULOS
    ========================================== */

    links.forEach(link => {

        link.addEventListener("click", evento => {

            const destino = document.querySelector(
                link.getAttribute("href")
            );

            if (!destino) return;

            evento.preventDefault();

            destino.scrollIntoView({
                behavior: reduzirMovimento.matches ? "instant" : "smooth",
                block: "start"
            });

            links.forEach(item => {
                item.classList.remove("ativo");
                item.removeAttribute("aria-current");
            });

            link.classList.add("ativo");
            link.setAttribute("aria-current", "location");

        });

    });

    /* ==========================================
       02 / PROGRESSO E CAPÍTULO ATIVO
    ========================================== */

    let rolando = false;

    function atualizarNavegacao() {

        const posicao = window.scrollY;
        const altura = document.documentElement.scrollHeight
            - window.innerHeight;

        const percentual = altura > 0
            ? Math.min(100, Math.max(0, (posicao / altura) * 100))
            : 100;

        if (progresso) {
            progresso.style.width = percentual + "%";
        }

        if (voltar) {
            voltar.classList.toggle(
                "aparecer",
                posicao > 550
            );
        }

        const referencia = window.innerHeight * 0.36;
        let ativa = secoes[0];

        secoes.forEach(item => {
            if (
                item.elemento.getBoundingClientRect().top
                <= referencia
            ) {
                ativa = item;
            }
        });

        if (ativa) {
            links.forEach(link => {
                const selecionado = link === ativa.link;

                link.classList.toggle("ativo", selecionado);

                if (selecionado) {
                    link.setAttribute("aria-current", "location");
                } else {
                    link.removeAttribute("aria-current");
                }
            });
        }

        rolando = false;
    }

    window.addEventListener("scroll", () => {
        if (rolando) return;

        rolando = true;
        requestAnimationFrame(atualizarNavegacao);
    }, { passive: true });

    window.addEventListener("resize", atualizarNavegacao);

    atualizarNavegacao();

    /* ==========================================
       03 / ANIMAÇÃO DE ENTRADA
    ========================================== */

    const elementos = pagina.querySelectorAll(
        ".ma-acessos, .evo-bloco, .ma-rodape-atelier"
    );

    if ("IntersectionObserver" in window
        && !reduzirMovimento.matches) {

        const observador = new IntersectionObserver(
            entradas => {
                entradas.forEach(entrada => {

                    if (!entrada.isIntersecting) return;

                    entrada.target.classList.add("ma-visivel");
                    observador.unobserve(entrada.target);

                });
            },
            {
                threshold: 0.08,
                rootMargin: "0px 0px 50px 0px"
            }
        );

        elementos.forEach(elemento => {
            elemento.classList.add("ma-reveal");
            observador.observe(elemento);
        });

        pagina.classList.add("ma-animar");
    }

    /* ==========================================
       04 / ANIMAÇÃO DAS BARRAS DE PROGRESSO
    ========================================== */

    const indicadores = pagina.querySelectorAll(
        ".ma-indicador-diagnostico, .ma-indicador-checklist"
    );

    if ("IntersectionObserver" in window
        && !reduzirMovimento.matches) {

        const observadorIndicadores = new IntersectionObserver(
            entradas => {
                entradas.forEach(entrada => {

                    if (!entrada.isIntersecting) return;

                    entrada.target.classList.add("ma-valor-ativo");
                    observadorIndicadores.unobserve(entrada.target);

                });
            },
            { threshold: 0.3 }
        );

        indicadores.forEach(indicador => {
            observadorIndicadores.observe(indicador);
        });

    } else {
        indicadores.forEach(indicador => {
            indicador.classList.add("ma-valor-ativo");
        });
    }

    /* ==========================================
       05 / ILUMINAÇÃO NO CURSOR
    ========================================== */

    const aceitaHover = window.matchMedia(
        "(hover: hover) and (pointer: fine)"
    );

    if (aceitaHover.matches && !reduzirMovimento.matches) {

        pagina.querySelectorAll(".ma-grupo").forEach(grupo => {

            grupo.addEventListener("pointermove", evento => {

                const area = grupo.getBoundingClientRect();

                const x = evento.clientX - area.left;
                const y = evento.clientY - area.top;

                grupo.style.setProperty("--ma-luz-x", x + "px");
                grupo.style.setProperty("--ma-luz-y", y + "px");

            });

            grupo.addEventListener("pointerleave", () => {
                grupo.style.removeProperty("--ma-luz-x");
                grupo.style.removeProperty("--ma-luz-y");
            });

        });

    }

    /* ==========================================
       06 / VOLTAR PARA O INÍCIO
    ========================================== */

    if (voltar) {
        voltar.addEventListener("click", () => {

            window.scrollTo({
                top: 0,
                behavior: reduzirMovimento.matches ? "instant" : "smooth"
            });

        });
    }

});

/* INKA / MINHA ÁREA · EDIÇÃO 02
   JS exclusivo deste dashboard. Sem bibliotecas externas.
*/
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('inka-dashboard');
  if (!root) return;

  const prefersLessMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const canPoint = window.matchMedia('(hover: hover) and (pointer: fine)');
  const chapters = root.querySelector('.db-chapters');
  const navLinks = Array.from(root.querySelectorAll('.db-chapter'));
  const progress = root.querySelector('.db-chapters-progress > span');
  const backTop = root.querySelector('.db-back-top');
  const sections = navLinks.map((link) => {
    const selector = link.getAttribute('href');
    return { link, element: selector ? root.querySelector(selector) : null };
  }).filter((item) => item.element);

  const motion = () => prefersLessMotion.matches ? 'auto' : 'smooth';

  function navigateTo(element) {
    const stickyTop = chapters ? (Number.parseFloat(getComputedStyle(chapters).top) || 0) : 0;
    const stickyHeight = chapters ? chapters.getBoundingClientRect().height : 0;
    const target = window.scrollY + element.getBoundingClientRect().top - stickyTop - stickyHeight - 15;
    window.scrollTo({ top: Math.max(0, target), behavior: motion() });
  }

  root.querySelectorAll('a[href^="#db-"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      const id = link.getAttribute('href');
      const destination = id && root.querySelector(id);
      if (!destination) return;
      event.preventDefault();
      navigateTo(destination);
    });
  });

  let scrollFrame = null;
  function syncScroll() {
    const top = window.scrollY;
    const maximum = Math.max(0, document.documentElement.scrollHeight - innerHeight);
    if (progress) progress.style.width = (maximum ? Math.min(100, top / maximum * 100) : 100) + '%';
    if (backTop) backTop.classList.toggle('is-visible', top > 540);

    const stickyTop = chapters ? (Number.parseFloat(getComputedStyle(chapters).top) || 0) : 0;
    const chapterRect = chapters ? chapters.getBoundingClientRect() : null;
    const pinned = chapterRect && chapterRect.top <= stickyTop + 2;
    const reference = pinned ? chapterRect.bottom + 34 : stickyTop + (chapterRect ? chapterRect.height : 0) + 34;
    let active = sections[0];
    sections.forEach((item) => { if (item.element.getBoundingClientRect().top <= reference) active = item; });
    if (active) navLinks.forEach((link) => {
      const selected = link === active.link;
      link.classList.toggle('is-active', selected);
      if (selected) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    scrollFrame = null;
  }
  const scheduleScroll = () => {
    if (scrollFrame !== null) return;
    scrollFrame = requestAnimationFrame(syncScroll);
  };
  window.addEventListener('scroll', scheduleScroll, { passive: true });
  window.addEventListener('resize', scheduleScroll);
  syncScroll();

  if (backTop) backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: motion() }));

  // Barras numéricas só ganham movimento quando entram na área visível.
  const meters = root.querySelectorAll('[data-db-progress]');
  const setMeter = (meter) => {
    const parsed = Number.parseFloat(String(meter.dataset.dbProgress || 0).replace(',', '.'));
    meter.style.width = `${Number.isFinite(parsed) ? Math.min(100, Math.max(0, parsed)) : 0}%`;
  };
  if ('IntersectionObserver' in window && !prefersLessMotion.matches) {
    const meterObserver = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      setMeter(entry.target);
      meterObserver.unobserve(entry.target);
    }), { threshold: .1 });
    meters.forEach((meter) => meterObserver.observe(meter));
  } else meters.forEach(setMeter);

  // Nenhuma seção/card é ocultada por JS: conteúdo sempre visível.

  // Luz do cursor APENAS dentro dos módulos, nunca na página toda.
  if (canPoint.matches && !prefersLessMotion.matches) {
    root.querySelectorAll('.db-module').forEach((module) => {
      module.addEventListener('pointermove', (event) => {
        const rect = module.getBoundingClientRect();
        module.style.setProperty('--db-cx', `${event.clientX - rect.left}px`);
        module.style.setProperty('--db-cy', `${event.clientY - rect.top}px`);
      }, { passive: true });
      module.addEventListener('pointerleave', () => {
        module.style.removeProperty('--db-cx');
        module.style.removeProperty('--db-cy');
      });
    });
  }

  // Copiar link com fallback para ambientes locais não seguros.
  const copy = root.querySelector('.db-copy');
  const feedback = root.querySelector('.db-copy-feedback');
  if (copy) copy.addEventListener('click', async () => {
    const value = copy.dataset.dbCopy;
    if (!value) return;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value);
      } else {
        const input = document.createElement('textarea');
        input.value = value;
        input.setAttribute('readonly', '');
        input.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
        document.body.appendChild(input);
        input.select();
        let done;
        try { done = document.execCommand('copy'); }
        finally { input.remove(); }
        if (!done) throw new Error('clipboard blocked');
      }
      if (feedback) feedback.textContent = 'Link copiado com sucesso!';
    } catch (error) {
      if (feedback) feedback.textContent = 'Não foi possível copiar. Use o link exibido acima.';
    }
  });
});

/* INKA / EVOLUÇÃO LAB: cinco estilos, uma única fonte de dados e formulários Django. */
document.addEventListener('DOMContentLoaded', () => {
  const page = document.getElementById('evolucao-lab');
  if (!page) return;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = window.matchMedia('(hover:hover) and (pointer:fine)');
  const themes = {flash:'01 / THE LIVING FLASH SHEET',press:'02 / INK PRESS',blackbook:'03 / BLACKBOOK',needle:'04 / NEEDLEWORK',map:'05 / MARKS OF PROGRESS'};
  const buttons = [...page.querySelectorAll('[data-select-theme]')];
  const caption = page.querySelector('#el-theme-caption');
  const toast = page.querySelector('.el-toast');
  let toastTimer;
  function showToast(message){if(!toast)return;toast.textContent=message;toast.classList.add('is-visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.classList.remove('is-visible'),2300)}
  function setTheme(theme, notify=false){
    if(!(theme in themes))return;
    page.dataset.theme=theme;
    if(caption)caption.textContent=themes[theme];
    buttons.forEach(button=>{const active=button.dataset.selectTheme===theme;button.classList.toggle('is-current',active);button.setAttribute('aria-pressed',String(active))});
    try{sessionStorage.setItem('inka-evolucao-tema',theme)}catch(_){/* privacidade / storage restrito */}
    if(notify)showToast('Estética aplicada: '+themes[theme].split(' / ')[1]);
  }
  let saved='flash';try{saved=sessionStorage.getItem('inka-evolucao-tema')||'flash'}catch(_){}
  setTheme(saved);
  buttons.forEach(button=>button.addEventListener('click',()=>setTheme(button.dataset.selectTheme,true)));

  const nav=page.querySelector('.el-chapters');
  const chapterLinks=[...page.querySelectorAll('.el-chapter')];
  const chapters=chapterLinks.map(link=>({link,element:page.querySelector(link.getAttribute('href'))})).filter(item=>item.element);
  const bar=page.querySelector('.el-chapter-track span');
  const back=page.querySelector('.el-backtop');
  const offset=()=>((nav?.getBoundingClientRect().height||0)+(Number.parseFloat(getComputedStyle(nav).top)||0)+18);
  page.querySelectorAll('a[href^="#el-"]').forEach(link=>link.addEventListener('click',event=>{
    const target=page.querySelector(link.getAttribute('href'));if(!target)return;
    event.preventDefault();const y=window.scrollY+target.getBoundingClientRect().top-offset();
    window.scrollTo({top:Math.max(0,y),behavior:reduce.matches?'auto':'smooth'});
  }));
  let ticking=false;
  function updateNav(){
    const scrolled=window.scrollY;
    const max=document.documentElement.scrollHeight-window.innerHeight;
    if(bar)bar.style.width=(max>0?Math.min(100,100*scrolled/max):100)+'%';
    if(back)back.classList.toggle('is-visible',scrolled>500);
    const threshold=offset()+28;let current=chapters[0];
    chapters.forEach(item=>{if(item.element.getBoundingClientRect().top<=threshold)current=item});
    if(current)chapterLinks.forEach(link=>{const active=link===current.link;link.classList.toggle('is-active',active);if(active)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current')});
    ticking=false;
  }
  window.addEventListener('scroll',()=>{if(ticking)return;ticking=true;requestAnimationFrame(updateNav)},{passive:true});
  window.addEventListener('resize',updateNav);updateNav();
  if(back)back.addEventListener('click',()=>window.scrollTo({top:0,behavior:reduce.matches?'auto':'smooth'}));

  // Checklist: atualização visual local. O registro só é salvo pelo POST original.
  const form=page.querySelector('.el-check-form');
  if(form){
    const checks=[...form.querySelectorAll('input[type="checkbox"][name="itens"]')];
    const count=form.querySelector('[data-completed]');const total=form.querySelector('[data-total]');const progress=form.querySelector('.el-form-progress span');
    function updateChecklist(){const completed=checks.filter(check=>check.checked).length;if(count)count.textContent=completed;if(total)total.textContent=checks.length;if(progress)progress.style.width=(checks.length?100*completed/checks.length:0)+'%'}
    checks.forEach(check=>check.addEventListener('change',updateChecklist));updateChecklist();
  }

  // Valores Django que podem aparecer com vírgula decimal em pt-BR.
  function percent(str){const value=Number.parseFloat(String(str||'0').replace(',','.'));return Number.isFinite(value)?Math.max(0,Math.min(100,value)):0}
  const meters=[...page.querySelectorAll('[data-el-progress]')];
  const renderMeter=element=>{element.style.width=percent(element.dataset.elProgress)+'%'};
  if('IntersectionObserver' in window && !reduce.matches){
    const io=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){renderMeter(entry.target);io.unobserve(entry.target)}}),{threshold:.15});meters.forEach(element=>io.observe(element));
  }else meters.forEach(renderMeter);

  // Microinteração de tinta na flash sheet e luz local sem afetar eventos/campos.
  if(finePointer.matches&&!reduce.matches){
    page.querySelectorAll('.el-indicator').forEach(card=>card.addEventListener('pointermove',event=>{
      if(page.dataset.theme!=='flash'&&page.dataset.theme!=='map')return;
      const r=card.getBoundingClientRect();card.style.setProperty('--el-mx',(event.clientX-r.left)+'px');card.style.setProperty('--el-my',(event.clientY-r.top)+'px');
    },{passive:true}));
  }
});
/* ============================================================
   INKA / THE LIVING FLASH SHEET
   Isolado em #inka-flash-sheet; sem dependências externas.
   Interações visuais não alteram o envio dos formulários Django.
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('inka-flash-sheet');
  if (!root) return;

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const chapters = root.querySelector('.ifs-nav');
  const links = [...root.querySelectorAll('.ifs-nav-link')];
  const sections = links.map(link => ({
    link,
    element: root.querySelector(link.getAttribute('href'))
  })).filter(item => item.element);
  const progressBar = root.querySelector('.ifs-nav-progress span');
  const backTop = root.querySelector('.ifs-backtop');

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const number = value => {
    const parsed = Number.parseFloat(String(value ?? '0').replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : 0;
  };
  const motion = () => reduce.matches ? 'auto' : 'smooth';

  // O menu principal do INKA pode ser fixo ou estático. Ajustamos o
  // offset apenas quando ele está efetivamente ocupando o topo da tela.
  function mainHeaderBottom() {
    const header = document.querySelector('body > .topo, body > header.topo, .topo');
    if (!header || header.contains(root)) return 12;
    const style = window.getComputedStyle(header);
    if (style.position !== 'fixed' && style.position !== 'sticky') return 12;
    const rect = header.getBoundingClientRect();
    return rect.bottom > 0 ? clamp(rect.bottom + 8, 12, 170) : 12;
  }

  function navOffset() {
    const top = mainHeaderBottom();
    root.style.setProperty('--ifs-nav-top', `${top}px`);
    return top + (chapters?.offsetHeight || 0) + 18;
  }

  root.querySelectorAll('a[href^="#ifs-"]').forEach(link => {
    link.addEventListener('click', event => {
      const selector = link.getAttribute('href');
      const target = selector && root.querySelector(selector);
      if (!target) return;
      event.preventDefault();
      const y = window.scrollY + target.getBoundingClientRect().top - navOffset();
      window.scrollTo({ top: Math.max(0, y), behavior: motion() });
    });
  });

  if (backTop) {
    backTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: motion() });
    });
  }

  // Os cinco desenhos ganham uma segunda camada de tinta no hover.
  // Sem JS, o SVG original continua completamente visível.
  if (!reduce.matches) {
    root.querySelectorAll('.ifs-flash-drawing svg').forEach(svg => {
      svg.classList.add('ifs-ink-base');
      const tracing = svg.cloneNode(true);
      tracing.classList.remove('ifs-ink-base');
      tracing.classList.add('ifs-ink-trace');
      tracing.setAttribute('aria-hidden', 'true');
      svg.after(tracing);
    });
  }

  // Checklist: somente contador e marcação. O salvamento permanece no POST.
  const checklist = root.querySelector('.ifs-stencil');
  if (checklist) {
    const checks = [...checklist.querySelectorAll('input[type="checkbox"][name="itens"]')];
    const doneEl = checklist.querySelector('[data-ifs-done]');
    const totalEl = checklist.querySelector('[data-ifs-total]');
    const meter = checklist.querySelector('.ifs-stencil-meter span');
    const updateChecklist = () => {
      const done = checks.filter(input => input.checked).length;
      if (doneEl) doneEl.textContent = String(done);
      if (totalEl) totalEl.textContent = String(checks.length);
      if (meter) meter.style.width = `${checks.length ? done * 100 / checks.length : 0}%`;
    };
    checks.forEach(input => input.addEventListener('change', updateChecklist));
    updateChecklist();
  }

  // Cada meta é um ramo botânico. Os traços são revelados em sequência,
  // de acordo com o percentual enviado pelo Django (incluindo vírgula pt-BR).
  const goals = [...root.querySelectorAll('.ifs-goal[data-goal-progress]')];
  goals.forEach(goal => {
    const paths = [...goal.querySelectorAll('.ifs-growth-drawn path')];
    const lengths = paths.map(path => {
      const length = path.getTotalLength();
      path.style.strokeDasharray = `${length}`;
      path.style.strokeDashoffset = `${length}`;
      return length;
    });
    const totalLength = lengths.reduce((sum, value) => sum + value, 0);
    const percent = clamp(number(goal.dataset.goalProgress), 0, 100);
    goal._flashDraw = () => {
      let remaining = totalLength * percent / 100;
      paths.forEach((path, index) => {
        const revealed = clamp(remaining, 0, lengths[index]);
        path.style.transition = reduce.matches ? 'none' : 'stroke-dashoffset 1.4s cubic-bezier(.22,1,.36,1)';
        path.style.strokeDashoffset = String(lengths[index] - revealed);
        remaining -= lengths[index];
      });
      const bar = goal.querySelector('[data-ifs-bar]');
      if (bar) bar.style.width = `${percent}%`;
    };
  });

  if ('IntersectionObserver' in window && !reduce.matches) {
    const goalObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target._flashDraw?.();
        goalObserver.unobserve(entry.target);
      });
    }, { threshold: .12, rootMargin: '0px 0px 40px 0px' });
    goals.forEach(goal => goalObserver.observe(goal));
  } else {
    goals.forEach(goal => goal._flashDraw?.());
  }

  // Diário: a linha de tinta avança em função da rolagem, e cada
  // registro aparece como uma nova marca de arquivo.
  const timeline = root.querySelector('.ifs-timeline');
  if (timeline) {
    const events = [...timeline.querySelectorAll('.ifs-event')];
    if ('IntersectionObserver' in window) {
      const diaryObserver = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-seen');
            diaryObserver.unobserve(entry.target);
          }
        });
      }, { threshold: .1 });
      events.forEach(event => diaryObserver.observe(event));
    } else {
      events.forEach(event => event.classList.add('is-seen'));
    }
  }

  // Fio de tinta que conecta os quatro capítulos na margem esquerda.
  // É apenas decorativo e se desativa em telas menores.
  const threadSvg = root.querySelector('.ifs-page-thread');
  const threadTrack = threadSvg?.querySelector('.ifs-page-thread-track');
  const threadInk = threadSvg?.querySelector('.ifs-page-thread-ink');
  const threadTip = threadSvg?.querySelector('.ifs-page-thread-tip');
  let threadLength = 0;
  let threadStart = 0;
  let threadEnd = 0;

  function rebuildThread() {
    if (!threadSvg || !threadTrack || !threadInk || !threadTip) return;
    if (window.innerWidth <= 760 || sections.length < 2) return;

    const rootRect = root.getBoundingClientRect();
    const positions = sections.map(item =>
      item.element.getBoundingClientRect().top - rootRect.top + 34
    );
    const x = 12;
    let d = `M ${x} ${positions[0]}`;
    for (let i = 1; i < positions.length; i++) {
      const previous = positions[i - 1];
      const current = positions[i];
      d += ` C ${x - 9} ${previous + 55}, ${x + 9} ${current - 55}, ${x} ${current}`;
    }
    threadSvg.setAttribute('viewBox', `0 0 ${root.clientWidth} ${root.scrollHeight}`);
    threadTrack.setAttribute('d', d);
    threadInk.setAttribute('d', d);
    threadLength = threadInk.getTotalLength();
    threadInk.style.strokeDasharray = `${threadLength}`;
    threadStart = positions[0];
    threadEnd = positions[positions.length - 1];
    updateThread();
  }

  function updateThread() {
    if (!threadInk || !threadTip || !threadLength || window.innerWidth <= 760) return;
    const rect = root.getBoundingClientRect();
    const viewportCursor = window.innerHeight * .58 - rect.top;
    const fraction = clamp((viewportCursor - threadStart) / Math.max(1, threadEnd - threadStart), 0, 1);
    const drawn = threadLength * fraction;
    threadInk.style.strokeDashoffset = String(threadLength - drawn);
    const point = threadInk.getPointAtLength(drawn);
    threadTip.setAttribute('cx', String(point.x));
    threadTip.setAttribute('cy', String(point.y));
  }

  let framePending = false;
  function updateScroll() {
    const offset = navOffset();
    const scrollTop = window.scrollY;
    const maximum = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    if (progressBar) progressBar.style.width = `${maximum ? scrollTop / maximum * 100 : 100}%`;
    if (backTop) backTop.classList.toggle('is-visible', scrollTop > 550);

    let active = sections[0];
    sections.forEach(item => {
      if (item.element.getBoundingClientRect().top <= offset + 30) active = item;
    });
    if (active) {
      links.forEach(link => {
        const current = link === active.link;
        link.classList.toggle('is-current', current);
        if (current) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    }

    if (timeline) {
      const rect = timeline.getBoundingClientRect();
      const height = Math.max(0, rect.height - 54);
      const reached = clamp(window.innerHeight * .57 - rect.top - 24, 0, height);
      timeline.style.setProperty('--ifs-timeline-progress', `${reached}px`);
    }
    updateThread();
    framePending = false;
  }
  window.addEventListener('scroll', () => {
    if (framePending) return;
    framePending = true;
    window.requestAnimationFrame(updateScroll);
  }, { passive: true });
  window.addEventListener('resize', () => {
    rebuildThread();
    updateScroll();
  });
  rebuildThread();
  updateScroll();
});