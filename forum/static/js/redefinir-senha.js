// Telas do "esqueci minha senha": e-mail -> código -> senha nova.
//
// Cada tela tem um formulário com data-etapa. Este script envia os dados em
// JSON para /api/auth/password-reset/ e leva para a tela seguinte. O e-mail e
// o reset_token ficam no sessionStorage, que some quando a aba é fechada.
document.addEventListener('DOMContentLoaded', function () {
    var formulario = document.getElementById('form-redefinir');
    if (!formulario) {
        return;
    }

    var ESPERA_REENVIO = 60;
    var CHAVE_EMAIL = 'inka-redefinir-email';
    var CHAVE_ENVIO = 'inka-redefinir-envio';
    var CHAVE_TOKEN = 'inka-redefinir-token';
    var ERRO_CONEXAO = 'Não foi possível conectar. Tente de novo.';

    var etapa = formulario.dataset.etapa;
    var caixaErro = document.getElementById('redefinir-erro');
    var botaoEnviar = formulario.querySelector('[type=submit]');
    var token = formulario.querySelector('[name=csrfmiddlewaretoken]').value;

    var guardar = function (chave, valor) {
        try {
            sessionStorage.setItem(chave, valor);
        } catch (erro) {
            // Navegador sem sessionStorage: a tela seguinte volta ao início.
        }
    };

    var ler = function (chave) {
        try {
            return sessionStorage.getItem(chave) || '';
        } catch (erro) {
            return '';
        }
    };

    var limpar = function () {
        try {
            sessionStorage.removeItem(CHAVE_EMAIL);
            sessionStorage.removeItem(CHAVE_ENVIO);
            sessionStorage.removeItem(CHAVE_TOKEN);
        } catch (erro) {
            // Nada guardado, nada a limpar.
        }
    };

    var mostrarErro = function (mensagem) {
        caixaErro.textContent = mensagem;
        caixaErro.hidden = !mensagem;
    };

    // Envia em JSON e devolve { ok, dados }. O token CSRF vai no cabeçalho.
    var enviar = function (url, dados) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token,
            },
            body: JSON.stringify(dados),
        }).then(function (resposta) {
            return resposta.json().catch(function () {
                return {};
            }).then(function (corpo) {
                return { ok: resposta.ok, dados: corpo };
            });
        });
    };

    // Trava o botão durante o envio, para um clique duplo não mandar dois.
    var aoEnviar = function (acao) {
        formulario.addEventListener('submit', function (evento) {
            evento.preventDefault();
            mostrarErro('');
            var pedido = acao();
            if (!pedido) {
                return;
            }
            botaoEnviar.disabled = true;
            pedido.catch(function () {
                mostrarErro(ERRO_CONEXAO);
            }).then(function () {
                botaoEnviar.disabled = false;
            });
        });
    };

    if (etapa === 'email') {
        var campoEmail = document.getElementById('email');
        campoEmail.value = ler(CHAVE_EMAIL);

        aoEnviar(function () {
            var email = campoEmail.value.trim();
            if (!email) {
                mostrarErro('Informe o e-mail.');
                return null;
            }
            return enviar(formulario.dataset.url, { email: email })
                .then(function (resultado) {
                    if (!resultado.ok) {
                        mostrarErro(resultado.dados.erro || ERRO_CONEXAO);
                        return;
                    }
                    limpar();
                    guardar(CHAVE_EMAIL, email);
                    guardar(CHAVE_ENVIO, String(Date.now()));
                    window.location.assign(formulario.dataset.proxima);
                });
        });
    }

    if (etapa === 'codigo') {
        var emailGuardado = ler(CHAVE_EMAIL);
        if (!emailGuardado) {
            window.location.replace(formulario.dataset.inicio);
            return;
        }
        document.getElementById('redefinir-email').textContent = emailGuardado;

        var campoCodigo = document.getElementById('codigo');
        var botaoReenviar = document.getElementById('botao-reenviar');
        var contador = document.getElementById('reenviar-contador');
        var relogio = null;

        // O "reenviar" só libera 60 s depois do último envio. O horário fica
        // guardado, então recarregar a página não zera a espera.
        var atualizarContador = function () {
            var envio = Number(ler(CHAVE_ENVIO)) || 0;
            var passados = Math.floor((Date.now() - envio) / 1000);
            var faltam = ESPERA_REENVIO - passados;
            if (faltam > 0) {
                botaoReenviar.disabled = true;
                contador.textContent = '(disponível em ' + faltam + ' s)';
                return;
            }
            botaoReenviar.disabled = false;
            contador.textContent = '';
            clearInterval(relogio);
            relogio = null;
        };

        var iniciarContador = function () {
            clearInterval(relogio);
            relogio = setInterval(atualizarContador, 1000);
            atualizarContador();
        };

        // Só números no campo do código, mesmo colando um texto.
        campoCodigo.addEventListener('input', function () {
            campoCodigo.value = campoCodigo.value.replace(/\D/g, '').slice(0, 6);
        });

        botaoReenviar.addEventListener('click', function () {
            mostrarErro('');
            botaoReenviar.disabled = true;
            enviar(formulario.dataset.urlReenviar, { email: emailGuardado })
                .then(function (resultado) {
                    if (!resultado.ok) {
                        mostrarErro(resultado.dados.erro || ERRO_CONEXAO);
                        botaoReenviar.disabled = false;
                        return;
                    }
                    guardar(CHAVE_ENVIO, String(Date.now()));
                    campoCodigo.value = '';
                    campoCodigo.focus();
                    iniciarContador();
                })
                .catch(function () {
                    mostrarErro(ERRO_CONEXAO);
                    botaoReenviar.disabled = false;
                });
        });

        aoEnviar(function () {
            var codigo = campoCodigo.value;
            if (codigo.length !== 6) {
                mostrarErro('Digite os 6 dígitos do código.');
                return null;
            }
            return enviar(formulario.dataset.url,
                          { email: emailGuardado, code: codigo })
                .then(function (resultado) {
                    if (!resultado.ok || !resultado.dados.reset_token) {
                        mostrarErro(resultado.dados.erro || ERRO_CONEXAO);
                        campoCodigo.value = '';
                        campoCodigo.focus();
                        return;
                    }
                    guardar(CHAVE_TOKEN, resultado.dados.reset_token);
                    window.location.assign(formulario.dataset.proxima);
                });
        });

        iniciarContador();
        campoCodigo.focus();
    }

    if (etapa === 'senha') {
        var tokenRedefinicao = ler(CHAVE_TOKEN);
        if (!tokenRedefinicao) {
            window.location.replace(formulario.dataset.inicio);
            return;
        }
        var campoSenha = document.getElementById('senha');
        var campoSenha2 = document.getElementById('senha2');

        aoEnviar(function () {
            if (!campoSenha.value) {
                mostrarErro('Crie uma senha.');
                return null;
            }
            if (campoSenha.value !== campoSenha2.value) {
                mostrarErro('As senhas não são iguais.');
                return null;
            }
            return enviar(formulario.dataset.url, {
                reset_token: tokenRedefinicao,
                new_password: campoSenha.value,
            }).then(function (resultado) {
                if (resultado.ok) {
                    limpar();
                    window.location.assign(formulario.dataset.proxima);
                    return;
                }
                mostrarErro(resultado.dados.erro || ERRO_CONEXAO);
                if (resultado.dados.token_invalido) {
                    // O token não vale mais: só resta pedir outro código.
                    limpar();
                }
            });
        });
    }
});
