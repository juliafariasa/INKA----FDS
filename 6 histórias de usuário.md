### História 1 — Selo "Estúdio Consciente"

**Como** cliente que procura um estúdio de tatuagem,
**quero** ver o selo ESG do estúdio no perfil e pelo QR Code na recepção,
**para** verificar o compromisso social e ambiental do local antes de agendar.

**Cenário 1 (positivo): visualizar o selo no perfil**

**Dado que** o estúdio tem vertentes ESG ativas registradas,
**Quando** acesso o perfil do estúdio,
**Então** a plataforma deve exibir o selo correspondente (Ouro = 3 vertentes, Prata = 2, Bronze = 1, sem selo = 0),
**E** mostrar quais vertentes estão ativas.

**Cenário 2 (negativo): Estúdio sem vertentes ESG ativas**

**Dado que** um estúdio possui 0 vertentes ESG ativas
**Quando** o cliente acessa o perfil do estúdio
**Então** nenhum selo é exibido
**E** é exibida a mensagem “Este estúdio ainda não possui o selo Estúdio Consciente”.

**Cenário 3 (positivo): escanear o QR Code**

**Dado que** o estúdio gerou seu QR Code,
**Quando** escaneio o código na recepção,
**Então** a plataforma deve abrir a página de verificação de selos,
**E** exibir o índice de sustentabilidade do estúdio.

**Cenário 4 (negativo): QR Code inválido**

**Dado que** o QR Code escaneado pertence a um estúdio que foi removido da plataforma
**Quando** o cliente escaneia o QR Code
**Então** a página de verificação NÃO exibe nenhum selo
**E** é exibida a mensagem “Selo não encontrado ou inválido!”.

### História 2 — Diagnóstico de maturidade ESG

**Como** dono de estúdio recém-cadastrado,
**quero** responder um questionário rápido sobre minhas práticas,
**para** receber uma nota inicial e um plano de ação personalizado.

**Cenário 1 (positivo): responder o diagnóstico no cadastro**

**Dado que** acabei de criar a conta do meu estúdio,
**Quando** respondo o questionário de maturidade ESG,
**Então** a plataforma deve calcular minha nota inicial,
**E** gerar um plano de ação com as práticas que preciso melhorar.

**Cenário 2 (negativo): Tentar responder o diagnóstico pela segunda vez**

**Dado que** o estúdio “Tinta Verde” já respondeu o diagnóstico e recebeu nota 62
**Quando** o dono tenta responder o questionário novamente
**Então** um novo diagnóstico NÃO é registrado
**E** é exibida a mensagem “Seu estúdio já realizou o diagnóstico inicial. Acompanhe sua evolução pelo painel!”.

### História 3 — Gerenciamento de estoque e equipamentos

**Como** dono de estúdio,
**quero** cadastrar e controlar meu estoque de materiais e equipamentos,
**para** saber o que tenho e o que uso.

**Cenário 1 (positivo): cadastrar material**

**Dado que** estou logado no painel do estúdio,
**Quando** cadastro um material ou equipamento com quantidade e fornecedor,
**Então** a plataforma deve adicioná-lo ao meu estoque,
**E** permitir editar ou remover o item depois.

**Cenário 2 (negativo): Material já cadastrado**

**Dado que** o estoque do estúdio “Tinta Verde” já possui o material “Copinho de tinta” do fornecedor “EcoTattoo”
**Quando** o dono tenta cadastrar novamente “Copinho de tinta” do mesmo fornecedor
**Então** um novo item NÃO é criado
**E** é exibida a mensagem “Este material já está no seu estoque. Edite a quantidade do item existente!”.

### História 4 — Calculadora de resíduos

**Como** tatuador,
**quero** informar quantos atendimentos faço por mês e quais materiais uso,
**para** saber quanto resíduo gero e como melhorar.

**Cenário 1 (positivo): calcular resíduos do mês**

**Dado que** informei o número de atendimentos e os materiais utilizados,
**Quando** solicito o cálculo,
**Então** a plataforma deve estimar a quantidade de resíduos por tipo,
**E** recomendar melhorias com base nas boas práticas ESG.

**Cenário 2 (negativo): Nenhum material selecionado**

**Dado que** o tatuador está logado e informou 40 atendimentos no mês
**Quando** ele solicita o cálculo sem selecionar nenhum material
**Então** o cálculo NÃO é realizado
**E** é exibida a mensagem “Selecione pelo menos um material utilizado!”.

### História 5 — Conteúdo sobre descarte de resíduos

**Como** dono de estúdio,
**quero** acessar vídeos, podcasts e slides sobre descarte de resíduos e as empresas que fazem esse serviço,
**para** descartar meus resíduos da forma adequada.

**Cenário 1 (positivo): acessar conteúdo**

**Dado que** existem conteúdos cadastrados na plataforma,
**Quando** acesso a área de descarte,
**Então** a plataforma deve listar os conteúdos por formato (vídeo, podcast, slides),
**E** exibir as empresas de descarte com seus contatos.

**Cenário 2 (negativo): Conteúdo com link indisponível**

**Dado que** o vídeo “Como descartar agulhas corretamente” está com o link fora do ar
**Quando** o dono do estúdio tenta abrir esse vídeo
**Então** o vídeo NÃO é reproduzido
**E** é exibida a mensagem “Este conteúdo está indisponível no momento. Tente outro conteúdo da lista!”.

### História 6 — Aulas de inclusão e acessibilidade

**Como** tatuador,
**quero** assistir aulas sobre inclusão e acessibilidade,
**para** atender melhor pessoas com deficiência e outros grupos minoritários.

**Cenário 1 (positivo): assistir uma aula**

**Dado que** existem aulas cadastradas,
**Quando** acesso a área de aulas sociais,
**Então** a plataforma deve listar as aulas disponíveis,
**E** permitir assistir ao conteúdo escolhido.

**Cenário 2 (negativo): Marcar aula como concluída sem assistir**

**Dado que** o tatuador assistiu apenas 10 dos 15 minutos da aula “Acolhimento de pessoas LGBTQIA+”
**Quando** ele clica em “Marcar como concluída”
**Então** a aula NÃO é marcada como concluída
**E** é exibida a mensagem “Assista à aula até o final para concluí-la!”.

---
