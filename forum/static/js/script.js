document.addEventListener('DOMContentLoaded', function () {
    iniciarAvisos();

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

    // Minha Área e Evolução têm o próprio botão de voltar ao topo; nelas o
    // botão global não é criado, para não aparecerem dois.
    if (!document.querySelector('.db-back-top, .ifs-backtop')) {
        var botaoTopo = document.createElement('button');
        botaoTopo.type = 'button';
        botaoTopo.className = 'voltar-topo';
        botaoTopo.textContent = '↑';
        botaoTopo.setAttribute('aria-label', 'Voltar ao topo');
        document.body.appendChild(botaoTopo);

        botaoTopo.addEventListener('click', function () {
            var suave = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            window.scrollTo({ top: 0, behavior: suave ? 'smooth' : 'auto' });
        });

        window.addEventListener('scroll', function () {
            botaoTopo.classList.toggle('visivel', window.scrollY > 300);
        }, { passive: true });
    }

    iniciarMenu();
    iniciarEnvioDeFormularios();
    iniciarCoreografia();
    iniciarLuzDoCursor();
    desenharTintaDecorativa();
    iniciarDesenho();
    iniciarAnimacaoCaneta();
    iniciarFormularioContato();
    iniciarRevelacaoEquipe();
    revelarSecoes();
});

// Avisos do Django ("Item cadastrado", "Senha alterada"...). Todos ganham
// um botão de fechar. Os de sucesso somem sozinhos depois de alguns segundos,
// com uma linha que mostra o tempo restante; passar o mouse ou focar o aviso
// pausa a contagem (WCAG 2.2.1). Os de erro ficam até a pessoa fechar.
function iniciarAvisos() {
    var DURACAO = 6000;

    document.querySelectorAll('p.aviso').forEach(function (aviso) {
        var fechar = document.createElement('button');
        fechar.type = 'button';
        fechar.className = 'aviso-fechar';
        fechar.setAttribute('aria-label', 'Fechar aviso');
        fechar.textContent = '×';
        aviso.appendChild(fechar);

        var sair = function () {
            if (aviso.classList.contains('sumindo')) {
                return;
            }
            aviso.classList.add('sumindo');
            setTimeout(function () {
                aviso.remove();
            }, 500);
        };
        fechar.addEventListener('click', sair);

        if (!aviso.classList.contains('aviso-success')) {
            return;
        }

        var restante = DURACAO;
        var inicio = 0;
        var relogio = null;
        var rodar = function () {
            inicio = Date.now();
            relogio = setTimeout(sair, restante);
            aviso.classList.remove('pausado');
        };
        var pausar = function () {
            if (relogio === null) {
                return;
            }
            clearTimeout(relogio);
            relogio = null;
            restante = Math.max(0, restante - (Date.now() - inicio));
            aviso.classList.add('pausado');
        };
        var retomar = function () {
            if (relogio === null && !aviso.matches(':hover, :focus-within')) {
                rodar();
            }
        };

        aviso.style.setProperty('--aviso-duracao', DURACAO + 'ms');
        aviso.classList.add('aviso-temporizado');
        aviso.addEventListener('pointerenter', pausar);
        aviso.addEventListener('pointerleave', retomar);
        aviso.addEventListener('focusin', pausar);
        aviso.addEventListener('focusout', function () {
            setTimeout(retomar, 0);
        });
        rodar();
    });
}

function iniciarMenu() {
    var botao = document.querySelector('.menu-botao');
    var menu = document.getElementById('menu');
    if (!botao || !menu) {
        return;
    }
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
            return;
        }

        // Com a gaveta aberta, o Tab circula entre o botão e os links dela
        // em vez de escapar para a página escurecida por trás.
        if (evento.key === 'Tab' && aberto()) {
            var focaveis = [botao].concat(Array.prototype.slice.call(
                menu.querySelectorAll('a[href], button:not([disabled])')
            ));
            var primeiro = focaveis[0];
            var ultimo = focaveis[focaveis.length - 1];
            if (evento.shiftKey && document.activeElement === primeiro) {
                evento.preventDefault();
                ultimo.focus();
            } else if (!evento.shiftKey && document.activeElement === ultimo) {
                evento.preventDefault();
                primeiro.focus();
            }
        }
    });

    // O link da página atual é anunciado como tal pelo leitor de tela.
    menu.querySelectorAll('a.ativo').forEach(function (link) {
        link.setAttribute('aria-current', 'page');
    });
}

// Entrada das páginas internas: o texto do topo de cada experiência entra em
// sequência (rótulo, título, texto, botão) e os blocos seguintes aparecem
// conforme a rolagem. Usa só opacity e "translate" (não mexe no transform que
// os componentes 3D já usam) e as classes saem quando a entrada termina.
// Fica de fora com movimento reduzido, nas páginas públicas (que já têm a
// própria revelação) e sob automação de testes.
function iniciarCoreografia() {
    var main = document.getElementById('conteudo');
    // O dossiê de documentos e o cadastro de aula já têm a própria abertura.
    if (!main || document.body.classList.contains('tema-inka') ||
            main.querySelector('#dossie-inka, #inka-director') ||
            navigator.webdriver || !('IntersectionObserver' in window) ||
            window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    var ignorar = function (el) {
        if (/^(SCRIPT|AUDIO|TEMPLATE|STYLE|DIALOG)$/.test(el.tagName) ||
                el.classList.contains('aviso') || el.hidden) {
            return true;
        }
        var estilo = getComputedStyle(el);
        return estilo.position === 'fixed' || estilo.position === 'sticky' ||
            estilo.position === 'absolute' || estilo.display === 'none' ||
            el.offsetHeight === 0;
    };
    var filhosVisiveis = function (el) {
        return Array.prototype.filter.call(el.children, function (filho) {
            return !ignorar(filho);
        });
    };

    // Tira as classes temporárias quando a entrada acaba (atraso + duração).
    var terminar = function (el) {
        var atraso = parseFloat(el.style.getPropertyValue('--inka-atraso')) || 0;
        setTimeout(function () {
            el.classList.remove('inka-entra', 'inka-entrou');
            el.style.removeProperty('--inka-atraso');
        }, atraso + 1000);
    };
    var revelar = function (el) {
        void el.offsetWidth; // garante que o estado inicial foi aplicado
        el.classList.add('inka-entrou');
        terminar(el);
    };

    // 1. Texto do topo da experiência: entra em sequência logo ao abrir.
    var copia = main.querySelector('.db-hero-copy, .ifs-hero-copy, .da-hero-copy, .aulas-hero-texto');
    if (copia) {
        var itens = filhosVisiveis(copia);
        itens.forEach(function (el, indice) {
            el.classList.add('inka-entra');
            el.style.setProperty('--inka-atraso', (90 + indice * 85) + 'ms');
        });
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                itens.forEach(revelar);
            });
        });
    }

    // 2. Blocos da página: desce enquanto houver um único invólucro e
    //    revela cada bloco ao entrar na tela.
    var no = main;
    for (var nivel = 0; nivel < 3; nivel++) {
        var filhos = filhosVisiveis(no);
        if (filhos.length !== 1) {
            break;
        }
        no = filhos[0];
    }
    var blocos = filhosVisiveis(no).filter(function (bloco) {
        return !(copia && bloco.contains(copia));
    });
    if (blocos.length < 2) {
        return;
    }

    var naTela = 0;
    var observador = new IntersectionObserver(function (entradas) {
        entradas.forEach(function (entrada) {
            if (!entrada.isIntersecting) {
                return;
            }
            var el = entrada.target;
            // Os que já estão na tela ao abrir entram em cascata curta.
            if (entrada.boundingClientRect.top < window.innerHeight) {
                el.style.setProperty('--inka-atraso', Math.min(naTela, 4) * 90 + 'ms');
                naTela++;
            }
            observador.unobserve(el);
            revelar(el);
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -6% 0px' });

    blocos.forEach(function (bloco) {
        bloco.classList.add('inka-entra');
        observador.observe(bloco);
    });
}

// Luz que acompanha o ponteiro nos painéis de abertura das experiências:
// um halo verde muito sutil, como luz rasante sobre papel. Só com mouse.
function iniciarLuzDoCursor() {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches ||
            window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    var paineis = document.querySelectorAll(
        '.db-hero, .ifs-hero, .da-hero, .aulas-hero, .inka-descarte-hero, .diagnostico-painel'
    );
    paineis.forEach(function (painel) {
        if (getComputedStyle(painel).position === 'static') {
            painel.style.position = 'relative';
        }
        var luz = document.createElement('span');
        luz.className = 'inka-luz';
        luz.setAttribute('aria-hidden', 'true');
        painel.appendChild(luz);

        var quadro = 0;
        var x = 0;
        var y = 0;
        painel.addEventListener('pointermove', function (evento) {
            var caixa = painel.getBoundingClientRect();
            x = evento.clientX - caixa.left;
            y = evento.clientY - caixa.top;
            if (!quadro) {
                quadro = requestAnimationFrame(function () {
                    quadro = 0;
                    luz.style.setProperty('--luz-x', x + 'px');
                    luz.style.setProperty('--luz-y', y + 'px');
                });
            }
        });
        painel.addEventListener('pointerenter', function () {
            luz.classList.add('acesa');
        });
        painel.addEventListener('pointerleave', function () {
            luz.classList.remove('acesa');
        });
    });
}

// Traço de tinta no topo da tela: mostra que o sistema está trabalhando
// enquanto um formulário é enviado ou a próxima página carrega. Só aparece
// se a espera passar de 150 ms, para não piscar em respostas rápidas.
function criarTracoDeProgresso() {
    var traco = document.createElement('div');
    traco.className = 'inka-progresso';
    traco.setAttribute('aria-hidden', 'true');
    document.body.appendChild(traco);

    var espera = null;
    return {
        iniciar: function () {
            clearTimeout(espera);
            espera = setTimeout(function () {
                traco.classList.add('ativo');
            }, 150);
        },
        parar: function () {
            clearTimeout(espera);
            traco.classList.remove('ativo');
        }
    };
}

// Envio único para todos os formulários POST: o segundo clique é ignorado
// enquanto o primeiro está em andamento. O botão não recebe "disabled" (isso
// tiraria o name/value dele do POST); fica com aria-disabled e o formulário
// com aria-busy. Formulários com fluxo próprio (dossiê de documentos e
// cadastro de aula) já cuidam disso e ficam de fora.
function iniciarEnvioDeFormularios() {
    var traco = criarTracoDeProgresso();
    var PROPRIOS = '#dossie-inka, #inka-director, [data-envio-proprio]';

    document.addEventListener('submit', function (evento) {
        var formulario = evento.target;
        if (evento.defaultPrevented || formulario.closest(PROPRIOS) ||
                (formulario.getAttribute('method') || '').toLowerCase() !== 'post') {
            return;
        }
        if (formulario.dataset.enviando === '1') {
            evento.preventDefault();
            return;
        }
        formulario.dataset.enviando = '1';
        formulario.setAttribute('aria-busy', 'true');
        var botao = evento.submitter;
        if (botao) {
            botao.setAttribute('aria-disabled', 'true');
            botao.classList.add('is-enviando');
        }
        traco.iniciar();
    });

    // Links internos: o mesmo traço indica que a próxima página está vindo.
    document.addEventListener('click', function (evento) {
        var link = evento.target.closest('a[href]');
        if (!link || evento.defaultPrevented || evento.button !== 0 ||
                evento.metaKey || evento.ctrlKey || evento.shiftKey ||
                evento.altKey || link.target === '_blank' ||
                link.hasAttribute('download')) {
            return;
        }
        var destino = new URL(link.href, location.href);
        var mesmaPagina = destino.pathname === location.pathname &&
            destino.search === location.search;
        if (destino.origin === location.origin && !mesmaPagina) {
            traco.iniciar();
        }
    });

    // Voltando pelo histórico, a página pode ser restaurada da memória com o
    // formulário ainda marcado como "enviando".
    window.addEventListener('pageshow', function () {
        traco.parar();
        document.querySelectorAll('form[data-enviando]').forEach(function (formulario) {
            delete formulario.dataset.enviando;
            formulario.removeAttribute('aria-busy');
            formulario.querySelectorAll('.is-enviando').forEach(function (botao) {
                botao.removeAttribute('aria-disabled');
                botao.classList.remove('is-enviando');
            });
        });
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

// Fale Conosco: leva o foco ao primeiro campo com erro.
function iniciarFormularioContato() {
    var formulario = document.getElementById('formulario-contato');
    if (!formulario) {
        return;
    }

    var primeiroErro = formulario.querySelector('[aria-invalid="true"]');
    if (primeiroErro) {
        primeiroErro.focus();
    }

    // O envio único e o estado "Enviando…" ficam com iniciarEnvioDeFormularios,
    // que vale para todos os formulários do site.
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

    // Quando o servidor devolve erros, o template já entrega o formulário
    // aberto; o estado inicial acompanha.
    let aberto = !formulario.hidden;
    let digitando = false;
    if (aberto && textoBotao) textoBotao.textContent = "MÁQUINA ACIONADA";
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

    // Abertura cinematográfica só na primeira visita da sessão. Ao voltar
    // depois de cadastrar ou editar um item, o cofre já está aberto e o
    // resultado aparece na hora; o mesmo vale para quem pede menos movimento.
    const CHAVE_COFRE = "inka-cofre-aberto";
    const lembrar = (valor) => {
        try { sessionStorage.setItem(CHAVE_COFRE, valor); } catch (erro) { /* modo privado */ }
    };
    let jaAbriuNaSessao = false;
    try { jaAbriuNaSessao = sessionStorage.getItem(CHAVE_COFRE) === "1"; } catch (erro) { /* modo privado */ }
    const semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    control.addEventListener("click", () => {
        // Depois do clique, o estado escolhido vale para a próxima visita.
        lembrar(vaultState === "open" || vaultState === "opening" ? "0" : "1");
    });

    updateControl();

    if (jaAbriuNaSessao || semMovimento) {
        scene.classList.add("sem-transicao", "is-open");
        vaultState = "open";
        setStatus("COFRE ABERTO / SISTEMA ATIVO");
        updateControl();
        requestAnimationFrame(() => requestAnimationFrame(() => {
            scene.classList.remove("sem-transicao");
        }));
    } else {
        setTimeout(() => {
            openVault();
            lembrar("1");
        }, 650);
    }

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
    const value = copy.dataset.copiar;
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

(() => {
  "use strict";

  const root = document.getElementById("inka-document-archive");
  if (!root) return;

  const gallery = root.querySelector("[data-da-gallery]");
  if (!gallery) return;

  const cards = Array.from(
    gallery.querySelectorAll("[data-da-file]")
  );

  const search = root.querySelector("[data-da-search]");
  const filters = Array.from(
    root.querySelectorAll("[data-da-filter]")
  );
  const sort = root.querySelector("[data-da-sort]");
  const visible = root.querySelector("[data-da-visible]");
  const empty = root.querySelector("[data-da-empty]");

  let active = "all";

  function statusGroup(value) {
    const status = (value || "")
      .toLocaleLowerCase("pt-BR")
      .trim();

    // Os códigos de situação vêm do Django.
    if (/vencid|expir|atrasad|invalid|fora.do.prazo/.test(status)) {
      return "expired";
    }

    if (/vencer|proxim|alert|penden|atenc|breve/.test(status)) {
      return "warning";
    }

    if (/dia|valid|regular|vigent|ok/.test(status)) {
      return "valid";
    }

    return "other";
  }

  function update() {
    const term = (search?.value || "")
      .trim()
      .toLocaleLowerCase("pt-BR");

    const ordered = [...cards].sort((a, b) => {
      if (sort?.value === "name") {
        return (a.dataset.name || "").localeCompare(
          b.dataset.name || "",
          "pt-BR"
        );
      }

      if (sort?.value === "expiry") {
        return (a.dataset.expiry || "9999").localeCompare(
          b.dataset.expiry || "9999"
        );
      }

      return Number(a.dataset.order) - Number(b.dataset.order);
    });

    let count = 0;

    ordered.forEach(card => {
      const matchesTerm =
        !term || (card.dataset.name || "").includes(term);

      const matchesStatus =
        active === "all" ||
        statusGroup(card.dataset.status) === active;

      const show = matchesTerm && matchesStatus;

      card.hidden = !show;

      if (show) count++;

      gallery.appendChild(card);
    });

    if (visible) {
      visible.textContent = String(count);
    }

    if (empty) {
      empty.hidden = count !== 0;
    }
  }

  search?.addEventListener("input", update);
  sort?.addEventListener("change", update);

  filters.forEach(button => {
    button.addEventListener("click", () => {
      active = button.dataset.daFilter;

      filters.forEach(item => {
        const selected = item === button;

        item.classList.toggle("is-active", selected);
        item.setAttribute("aria-pressed", String(selected));
      });

      update();
    });
  });

  update();
})();

document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  const root = document.getElementById("dossie-inka");
  if (!root) return;

  const openButton = root.querySelector("#dossie-open");
  const content = root.querySelector("#dossie-content");
  const form = root.querySelector("#dossie-form");
  const sheets = [...root.querySelectorAll("[data-dossie-step]")];
  const points = [...root.querySelectorAll("[data-step-target]")];
  const wire = root.querySelector("#dossie-wire");
  const timeline = root.querySelector(".dossie-timeline");
  const saveButton = root.querySelector("#dossie-save");
  const protocol = root.querySelector("#dossie-protocol");

  if (!openButton || !content || !form) return;

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  );

  const inputs = {
    tipo: root.querySelector("#tipo"),
    descricao: root.querySelector("#descricao"),
    emitido: root.querySelector("#emitido_em"),
    validade: root.querySelector("#validade"),
    link: root.querySelector("#link")
  };

  let current = 0;
  let opened = false;
  let opening = false;
  let submitting = false;

  function dateBR(value) {
    if (!value) return "";
    const parts = value.split("-");
    return parts.length === 3
      ? `${parts[2]}/${parts[1]}/${parts[0]}`
      : value;
  }

  function updateReview() {
    const selected = inputs.tipo.selectedOptions[0];
    root.querySelector("#dossie-review-type").textContent =
      inputs.tipo.value ? selected.textContent.trim() : "Não informado";

    root.querySelector("#dossie-review-date").textContent =
      dateBR(inputs.emitido.value) || "Não informada";

    root.querySelector("#dossie-review-expiry").textContent =
      dateBR(inputs.validade.value) || "Sem validade definida";
  }

  function fieldStep(field) {
    const sheet = field?.closest("[data-dossie-step]");
    return sheet ? Number(sheet.dataset.dossieStep) : 0;
  }

  function firstInvalidField() {
    return [...form.querySelectorAll("input,select")]
      .find(field => !field.checkValidity()) || null;
  }

  function checkStep(index) {
    const sheet = sheets[index];
    if (!sheet) return false;

    const invalid = [...sheet.querySelectorAll("input,select")]
      .find(field => !field.checkValidity());

    if (invalid) {
      invalid.reportValidity();
      invalid.focus();
      return false;
    }

    return true;
  }

  /* FIO SVG ENTRE OS TRÊS ALFINETES */

  function drawWire() {
    if (!wire || !timeline || points.length !== 3) return;

    const rect = timeline.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const positions = points.map(point => {
      const pinRect = point.querySelector("i").getBoundingClientRect();
      return {
        x: pinRect.left + pinRect.width / 2 - rect.left,
        y: pinRect.top + pinRect.height / 2 - rect.top
      };
    });

    wire.setAttribute("viewBox", `0 0 ${rect.width} ${rect.height}`);
    wire.replaceChildren();

    const ns = "http://www.w3.org/2000/svg";

    const path = (a, b) =>
      `M ${a.x} ${a.y} L ${b.x} ${b.y}`;

    // Linha completa, discreta.
    const base = document.createElementNS(ns, "path");
    base.setAttribute("d", path(positions[0], positions[2]));
    base.setAttribute("fill", "none");
    base.setAttribute("stroke", "#5F7B44");
    base.setAttribute("stroke-width", "2");
    base.setAttribute("opacity", ".55");
    wire.appendChild(base);

    // Fio ativo, desenhado conforme o progresso.
    const active = document.createElementNS(ns, "path");
    active.setAttribute("d", path(positions[0], positions[2]));
    active.setAttribute("fill", "none");
    active.setAttribute("stroke", "#B9D188");
    active.setAttribute("stroke-width", "2.5");
    active.setAttribute("stroke-linecap", "round");

    const length = active.getTotalLength();
    active.style.strokeDasharray = `${length}`;
    active.style.strokeDashoffset = `${
      length * (1 - current / 2)
    }`;
    active.style.transition = prefersReducedMotion.matches
      ? "none"
      : "stroke-dashoffset .65s cubic-bezier(.2,.8,.2,1)";

    wire.appendChild(active);
  }

  function advanceWire() {
    const active = wire?.querySelectorAll("path")[1];
    if (!active) return;

    const length = active.getTotalLength();

    active.style.strokeDashoffset =
      `${length * (1 - current / 2)}`;
  }

  function showStep(index, scroll = true) {
    current = Math.max(0, Math.min(index, sheets.length - 1));

    sheets.forEach((sheet, i) => {
      const active = i === current;
      sheet.classList.toggle("is-active", active);
      sheet.hidden = !active;
    });

    points.forEach((point, i) => {
      const active = i === current;

      point.classList.toggle("is-current", active);
      point.classList.toggle("is-complete", i < current);

      if (active) {
        point.setAttribute("aria-current", "step");
      } else {
        point.removeAttribute("aria-current");
      }
    });

    updateReview();
    advanceWire();

    if (scroll) {
      content.scrollIntoView({
        behavior: prefersReducedMotion.matches ? "auto" : "smooth",
        block: "start"
      });
    }
  }

  function finishOpening(scroll = true) {
    opened = true;
    opening = false;

    root.classList.remove("is-opening");
    root.classList.add("is-open");

    openButton.setAttribute("aria-expanded", "true");

    drawWire();

    if (scroll) {
      content.scrollIntoView({
        behavior: prefersReducedMotion.matches ? "auto" : "smooth",
        block: "start"
      });
    }
  }

  function openDossier() {
    if (opened || opening) return;

    opening = true;
    root.classList.add("is-opening");
    openButton.disabled = true;

    window.setTimeout(
      () => finishOpening(),
      prefersReducedMotion.matches ? 0 : 1150
    );
  }

  openButton.addEventListener("click", openDossier);

  /* ATIVAR A EXPERIÊNCIA SEM PREJUDICAR O HTML */

  root.classList.add("is-enhanced");

  // Esconde as folhas inativas somente com JS funcionando.
  sheets.forEach((sheet, i) => {
    sheet.hidden = i !== 0;
  });

  /* ERROS DO DJANGO: ABRE NA ETAPA CERTA */

  const errorElement = form.querySelector(".dossie-error");

  if (root.dataset.errors === "1" || errorElement) {
    finishOpening(false);

    const sheet = errorElement?.closest("[data-dossie-step]");
    showStep(sheet ? Number(sheet.dataset.dossieStep) : 0, false);
  } else {
    showStep(0, false);
  }

  /* AVANÇAR E VOLTAR */

  root.querySelectorAll("[data-next]").forEach(button => {
    button.addEventListener("click", () => {
      if (!checkStep(current)) return;
      showStep(current + 1);
    });
  });

  root.querySelectorAll("[data-back]").forEach(button => {
    button.addEventListener("click", () => {
      showStep(current - 1);
    });
  });

  // Permite voltar livremente; para avançar,
  // valida todas as etapas anteriores.
  points.forEach(point => {
    point.addEventListener("click", () => {
      if (!opened) return;

      const target = Number(point.dataset.stepTarget);

      if (target > current) {
        for (let i = 0; i < target; i++) {
          showStep(i, false);

          if (!checkStep(i)) return;
        }
      }

      showStep(target);
    });
  });

  Object.values(inputs).forEach(input => {
    input?.addEventListener("input", updateReview);
    input?.addEventListener("change", updateReview);
  });

  updateReview();

  /* VALIDAR ANTES DO ENVIO */

  saveButton?.addEventListener("click", event => {
    if (submitting) {
      event.preventDefault();
      return;
    }

    const invalid = firstInvalidField();

    if (invalid) {
      event.preventDefault();
      showStep(fieldStep(invalid), false);
      invalid.reportValidity();
      invalid.focus();
    }
  });

  /* ENVIO COM ANIMAÇÃO */
  form.addEventListener("submit", event => {
    if (submitting) return;

    const invalid = firstInvalidField();

    if (invalid) {
      event.preventDefault();
      showStep(fieldStep(invalid), false);
      invalid.reportValidity();
      return;
    }

    // O HTML original continua enviando os dados ao Django.
    // A animação apenas antecede o POST.
    if (prefersReducedMotion.matches) return;

    event.preventDefault();
    submitting = true;

    protocol.hidden = false;
    saveButton.disabled = true;

    window.setTimeout(() => {
      // Preserva o input hidden "salvar" no POST.
      HTMLFormElement.prototype.submit.call(form);
    }, 650);
  });

  window.addEventListener("resize", drawWire, { passive: true });

  if (document.fonts?.ready) {
    document.fonts.ready.then(drawWire);
  }
});
