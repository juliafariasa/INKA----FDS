# Documentação Contributing do INKA

## Bem-vindo ao INKA

Esse é o manual de contribuição do nosso projeto. Nesse documento vamos falar sobre:

- As regras de conduta do projeto.
- Como contribuir para o código do INKA.
- Como clonar o repositório principal.
- Como executar o conjunto de testes.

INKA é uma aplicação web desenvolvida para ajudar estúdios de tatuagem a colocar o ESG (Ambiental, Social e Governança) em prática no dia a dia, reunindo em um único ambiente diversas ferramentas essenciais para a gestão sustentável do estúdio. A plataforma foi criada com o objetivo de traduzir os pilares do ESG em critérios objetivos, como o diagnóstico ESG, o selo do estúdio, o controle de estoque, o cálculo de resíduos, o guia de descarte e as aulas, evitando que o estúdio precise utilizar vários aplicativos ou sites diferentes para organizar suas práticas e acompanhar sua evolução.

---

## Regras de conduta

Antes de tudo vamos falar sobre as regras de como contribuir para o código, impondo algumas limitações para controle e um bom estruturamento do nosso projeto.

**1. Não apague nenhuma funcionalidade implementada ou qualquer tipo de código complexo do projeto.**

(Apagar o código de outras pessoas é primeiramente desrespeitoso e prejudicará no desenvolvimento da nossa plataforma. Tudo foi pensado com muito carinho e foi feito com muito cuidado, se está implementado é porque é uma parte importante do projeto. Aceitamos mudanças no código para melhorias de funcionalidade e uma boa experiência do usuário. Faça suas modificações a partir do que já faz parte do projeto.)

**2. Crie uma Branch só sua para acompanhar seu progresso e não interferir no código base antes de estar tudo pronto.**

(Separar as modificações que ainda estão em construção do que já está tudo certo é muito importante para organização do código e evitar problemas. A branch `main` é a branch principal do projeto e é a partir dela que o deploy automático é feito, então nunca trabalhe diretamente nela.)

**3. Não suba suas modificações sem abrir um Pull Request e sem a análise dos contribuidores principais.**

(Isso pode levar a algum conflito no código principal ou até mesmo levar a implementar algo que está fora dos princípios do nosso projeto. Então, tenha cuidado antes de enviar seu código e sempre peça revisão de cada modificação, explicando o que foi feito e o seu propósito.)

**4. Teste modificações antes de abrir o Pull Request.**

(Código não testado pode introduzir problemas. Antes de enviar qualquer mudança, rode os testes para garantir que todos passam e execute manualmente a funcionalidade no navegador. Se você adicionar uma nova feature, crie testes para ela!)

**5. Documente modificações.**

(Se você adicionar uma nova funcionalidade, atualize a documentação como por exemplo: README, comentários no código e etc. Se corrigir um bug complexo, explique o motivo da correção em comentários. Código sem documentação é difícil de manter e entender. Lembre-se: você está escrevendo código para que outras pessoas possam entender e dar continuidade.)

**6. Divirta-se e sempre pense em formas de melhorar nossa plataforma. Isso vai ajudar muito os desenvolvedores e os estúdios que usam o INKA!**

E por último e não menos importante, siga os padrões de código do projeto e sempre comunique-se com a equipe antes de alguma grande alteração. Assim, todos ficam felizes e o projeto vai dar muito certo.

---

## Como contribuir para o código do INKA

Aqui está o passo a passo para rodar o projeto na sua máquina e começar a contribuir.

### 1. Pré-requisitos

Certifique-se de ter instalado:

- Python 3.12+: [Download Python](https://www.python.org/downloads/) (o projeto usa Django 6.1, que exige Python 3.12 ou mais novo)
- Git: [Download Git](https://git-scm.com/downloads/)
- pip: Gerenciador de pacotes Python (instalado com Python)
- Google Chrome: [Download Chrome](https://www.google.com/chrome/) (necessário apenas para rodar os testes E2E com Selenium)

### 2. Clone o repositório

No seu ambiente de versionamento dê o seguinte comando:

```bash
git clone https://github.com/juliafariasa/INKA----FDS.git
```

(Essa é a URL do nosso projeto)

Depois entre na pasta do projeto:

```bash
cd INKA----FDS
```

### 3. Crie um ambiente virtual

Em Windows:

Comando:

```bash
python -m venv venv
```

depois você faz:

Comando:

```bash
venv\Scripts\activate
```

(Em Linux ou macOS, o comando para ativar é `source venv/bin/activate`)

### 4. Instale as dependências

Comando:

```bash
pip install -r requirements.txt
```

Se você for rodar os testes E2E, instale também as dependências de desenvolvimento (inclui o Selenium):

Comando:

```bash
pip install -r requirements-dev.txt
```

### 5. Configure o banco de dados

Comando:

```bash
python manage.py migrate
```

(As migrações já criam o conteúdo inicial da plataforma, como as práticas ESG, os materiais e os conteúdos de descarte.)

### 6. Crie um superusuário (opcional)

Para acessar o admin do Django:

Comando:

```bash
python manage.py createsuperuser
```

### 7. Rode o servidor de desenvolvimento

Comando:

```bash
python manage.py runserver
```

e depois acesse o localhost (http://127.0.0.1:8000/) em algum navegador para visualizar.

(Em desenvolvimento local não é preciso configurar a variável de ambiente `SECRET_KEY`, o projeto já usa uma chave de desenvolvimento. Nunca coloque chaves secretas reais no código!)

### 8. Faça suas modificações

- Crie uma nova branch: `git checkout -b feature/nome-da-funcionalidade`
- Edite o código
- Teste localmente: `python manage.py test forum.tests`
- Commit: `git commit -m "Descrição clara da mudança"`
- Push: `git push origin feature/nome-da-funcionalidade`

### 9. Abra um Pull Request

Vá até o repositório no GitHub e clique em "Compare & pull request".

(Nunca esqueça de abrir um Pull Request antes de fazer uma modificação, isso faz parte das regras de conduta, ajudando na análise e no controle do código. Lembre-se que tudo que entra na `main` vai automaticamente para o deploy no Render.)

---

## Como rodar os testes automatizados

Os testes são muito importantes para garantir a qualidade e estabilidade do código. Sempre rode os testes antes de abrir um Pull Request, isso está nas regras de conduta!!

### Como executar todos os testes do projeto

Basta rodar o seguinte comando:

```bash
python manage.py test
```

(Esse comando roda os testes de unidade e também os testes E2E, então você precisa ter instalado o `requirements-dev.txt` e o Google Chrome.)

### Como executar testes de uma parte específica

Se acabou trabalhando apenas em uma parte do projeto, pode rodar só os testes dessa parte:

Aqui estão alguns exemplos de comando para os testes existentes:

```bash
python manage.py test forum.tests
python manage.py test forum.test_e2e
python manage.py test forum.tests.EstoqueTest
python manage.py test forum.test_e2e.test_descarte
```

- `forum.tests`: todos os testes de unidade (não precisa do Chrome).
- `forum.test_e2e`: todos os testes de sistema (E2E) com Selenium, que abrem o Chrome e testam a plataforma como um usuário.
- `forum.tests.EstoqueTest`: só os testes de uma funcionalidade (outros exemplos: `DiagnosticoTest`, `SeloTest`, `ResiduoTest`, `DescarteTest`, `AulasTest`).
- `forum.test_e2e.test_descarte`: só um arquivo de testes E2E (outros exemplos: `test_estoque`, `test_aulas`).

Os testes E2E fazem uma pausa entre os passos para dar tempo de ver (e gravar) o que está acontecendo. Para rodar rápido, zere a pausa antes do comando:

```bash
# PowerShell
$env:E2E_PAUSA="0"

# Linux ou macOS
export E2E_PAUSA=0
```

### O que verificar antes de enviar código

- Todos os testes passam sem erros
- Adicionou testes para novas funcionalidades
- Não quebrou testes existentes
- O código roda sem erros no servidor local (é só utilizar o comando: `python manage.py runserver`)

---

## Obrigada por querer contribuir!

Esse foi o manual de contribuição do INKA, obrigada por querer fazer parte desse projeto tão especial. Apenas preste atenção nas regras e requisitos do nosso projeto e aproveite bastante!
