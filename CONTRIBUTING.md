# Guia de Contribuição do INKA

## Olá, que bom ter você por aqui!

Este guia reúne tudo o que você precisa saber para colaborar com o INKA. Ao longo dele você vai encontrar:

- Os combinados da equipe para contribuir com o projeto.
- O passo a passo para preparar o ambiente e rodar a aplicação.
- Como baixar o repositório para a sua máquina.
- Como rodar os testes automatizados.

O INKA é uma plataforma web pensada para estúdios de tatuagem que querem levar o ESG (Ambiental, Social e Governança) para a rotina do negócio. Em vez de espalhar a gestão sustentável por planilhas, anotações e sites diferentes, o estúdio encontra tudo em um só lugar: diagnóstico ESG, selo do estúdio, controle de estoque, cálculo de resíduos, guia de descarte e aulas. A ideia é transformar conceitos que parecem distantes em critérios concretos, que o estúdio consegue acompanhar e melhorar com o tempo.

---

## Combinados da equipe

Para que o projeto continue organizado e todo mundo consiga trabalhar sem atrapalhar o outro, pedimos que você siga alguns combinados.

**1. Preserve o que já existe.**

Cada funcionalidade do INKA foi discutida, planejada e construída pela equipe. Por isso, não remova telas, funções ou trechos de código que já estão funcionando. Melhorias são sempre bem-vindas, mas elas devem partir do que já foi feito, evoluindo o código em vez de substituí-lo.

**2. Trabalhe na sua própria branch.**

Nunca desenvolva direto na `main`. Ela guarda a versão estável do projeto e é dela que sai o deploy automático no Render, então qualquer erro ali chega direto na versão publicada. Crie uma branch para cada tarefa e só leve suas mudanças para a `main` quando elas estiverem prontas.

**3. Toda mudança passa por um Pull Request.**

Nenhum código entra na `main` sem revisão. Abra um Pull Request, descreva o que você alterou e por que, e espere que alguém da equipe revise. Assim evitamos conflitos e garantimos que as mudanças seguem a proposta do INKA.

**4. Teste antes de pedir revisão.**

Antes de abrir o Pull Request, rode a suíte de testes e confira se tudo continua passando. Também vale abrir a aplicação no navegador e usar a funcionalidade que você mexeu. Criou algo novo? Escreva testes para cobrir essa parte também.

**5. Deixe registrado o que você fez.**

Funcionalidade nova pede documentação nova: atualize o README e comente os trechos de código que não são óbvios. Se a correção de um bug exigiu uma solução fora do comum, explique o raciocínio em um comentário. Quem vier depois de você vai agradecer.

**6. Contribua com vontade!**

Fique à vontade para propor ideias e melhorias. Quanto mais o INKA evoluir, mais ele ajuda os estúdios que usam a plataforma.

Por fim, mantenha o estilo de código que já é usado no projeto e converse com a equipe antes de começar uma mudança grande. Alinhar antes evita retrabalho depois.

---

## Preparando o ambiente

Siga as etapas abaixo para ter o INKA rodando no seu computador.

### Etapa 1: O que você precisa ter instalado

- [Python](https://www.python.org/downloads/) na versão 3.12 ou superior (exigida pelo Django 6.1, usado no projeto)
- [Git](https://git-scm.com/downloads/), para versionar o código
- pip, que já vem junto com o Python
- [Google Chrome](https://www.google.com/chrome/), necessário só para os testes E2E com Selenium

### Etapa 2: Baixe o projeto

Copie o repositório para a sua máquina e entre na pasta dele:

```bash
git clone https://github.com/juliafariasa/INKA----FDS.git
cd INKA----FDS
```

### Etapa 3: Prepare um ambiente virtual

O ambiente virtual mantém as bibliotecas do INKA separadas das outras do seu computador.

```bash
python -m venv venv
```

Para ativá-lo no Windows:

```bash
venv\Scripts\activate
```

No Linux ou no macOS:

```bash
source venv/bin/activate
```

### Etapa 4: Instale as bibliotecas do projeto

```bash
pip install -r requirements.txt
```

Para rodar também os testes E2E, instale as bibliotecas de desenvolvimento (entre elas o Selenium):

```bash
pip install -r requirements-dev.txt
```

### Etapa 5: Monte o banco de dados

```bash
python manage.py migrate
```

Além de criar as tabelas, as migrações já carregam o conteúdo inicial da plataforma, como as práticas ESG, os materiais e as informações de descarte.

### Etapa 6 (opcional): Crie um usuário administrador

Se quiser usar o painel de administração do Django:

```bash
python manage.py createsuperuser
```

### Etapa 7: Suba a aplicação

```bash
python manage.py runserver
```

Com o servidor rodando, abra http://127.0.0.1:8000/ no navegador.

Para rodar localmente você não precisa definir a variável de ambiente `SECRET_KEY`, pois o projeto usa uma chave própria para desenvolvimento. Chaves reais nunca devem ser colocadas no código.

### Etapa 8: Desenvolva a sua parte

1. Abra uma branch para a tarefa: `git checkout -b feature/nome-da-funcionalidade`
2. Faça as alterações no código.
3. Confira se nada quebrou: `python manage.py test forum.tests`
4. Salve as mudanças com uma mensagem que explique o que foi feito: `git commit -m "Adiciona filtro de materiais no estoque"`
5. Envie a branch para o GitHub: `git push origin feature/nome-da-funcionalidade`

### Etapa 9: Peça a revisão

No GitHub, abra a página do repositório e clique em "Compare & pull request". Explique na descrição o que mudou e por quê. Lembre-se: o que for aprovado e entrar na `main` é publicado automaticamente no Render.

---

## Testes automatizados

Os testes são a nossa garantia de que uma mudança nova não estragou algo que já funcionava. Por isso, rodar os testes antes do Pull Request faz parte dos combinados da equipe.

### Rodando a suíte completa

```bash
python manage.py test
```

Esse comando executa os testes de unidade e os testes E2E juntos. Para ele funcionar, você precisa ter instalado o `requirements-dev.txt` e o Google Chrome.

### Rodando só uma parte dos testes

Quando a sua mudança afeta só uma área do INKA, dá para rodar apenas os testes dela:

| Comando | O que roda |
|---|---|
| `python manage.py test forum.tests` | Todos os testes de unidade (não precisa do Chrome) |
| `python manage.py test forum.test_e2e` | Todos os testes de sistema (E2E), que abrem o Chrome e usam a plataforma como um usuário faria |
| `python manage.py test forum.tests.EstoqueTest` | Os testes de uma funcionalidade específica. Outras opções: `DiagnosticoTest`, `SeloTest`, `ResiduoTest`, `DescarteTest`, `AulasTest` |
| `python manage.py test forum.test_e2e.test_descarte` | Um único arquivo de testes E2E. Outras opções: `test_estoque`, `test_aulas` |

### Acelerando os testes E2E

Por padrão, os testes E2E esperam alguns segundos entre um passo e outro, para que dê para acompanhar (e gravar) o que está acontecendo na tela. Se quiser que eles rodem sem pausa, defina a variável `E2E_PAUSA` como zero antes de rodar:

```bash
# PowerShell
$env:E2E_PAUSA="0"

# Linux ou macOS
export E2E_PAUSA=0
```

### Checklist antes do Pull Request

- [ ] A suíte de testes roda sem nenhuma falha.
- [ ] A funcionalidade nova tem testes próprios.
- [ ] Os testes que já existiam continuam passando.
- [ ] A aplicação abre e funciona normalmente com `python manage.py runserver`.

---

## Valeu pela ajuda!

Obrigado por dedicar seu tempo ao INKA. Cada contribuição ajuda a mostrar que o ESG pode fazer parte da rotina de qualquer estúdio. Siga os combinados, tire suas dúvidas com a equipe e bom código!
