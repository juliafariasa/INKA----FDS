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
});
