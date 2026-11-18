# API de Atividades da Mergington High School

Uma aplicação FastAPI super simples que permite aos estudantes visualizar e se inscrever em atividades extracurriculares.

## Funcionalidades

- Visualizar todas as atividades extracurriculares disponíveis
- Professores autenticados podem inscrever e remover estudantes
- Estudantes sem login podem continuar vendo as atividades e participantes

## Primeiros Passos

1. Instale as dependências:

   ```
   pip install -r requirements.txt
   ```

2. Crie ou redefina uma conta de professor. A senha será solicitada sem aparecer no terminal:

   ```
   python -m src.manage_teachers set professor
   ```

   As credenciais ficam em `src/teachers.json`, que é ignorado pelo Git. Não adicione esse arquivo ao repositório.

3. Execute a aplicação:

   ```
   uvicorn src.app:app --reload
   ```

4. Abra seu navegador e vá para:
   - Documentação da API: http://localhost:8000/docs
   - Documentação alternativa: http://localhost:8000/redoc

## Endpoints da API

| Método | Endpoint | Descrição |
| ------ | -------- | --------- |
| GET | `/activities` | Obter atividades e participantes; não requer login |
| GET | `/auth/me` | Consultar o estado da sessão do professor |
| POST | `/auth/login` | Autenticar uma conta de professor |
| POST | `/auth/logout` | Encerrar a sessão do professor |
| POST | `/activities/{activity_name}/signup?email=student@mergington.edu` | Inscrever um estudante; requer login de professor |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Remover uma inscrição; requer login de professor |

As sessões expiram após oito horas e são mantidas em memória; reiniciar o servidor encerra as sessões ativas. Em produção com HTTPS, defina `COOKIE_SECURE=true` para marcar o cookie como `Secure`.

## Modelo de Dados

A aplicação usa um modelo de dados simples com identificadores significativos:

1. **Atividades** - Usa o nome da atividade como identificador:

   - Descrição
   - Cronograma
   - Número máximo de participantes permitidos
   - Lista de emails de estudantes que estão inscritos

2. **Estudantes** - Usa email como identificador:
   - Nome
   - Nível da série

Os dados de atividades e inscrições são armazenados na memória e serão reiniciados com o servidor. As credenciais dos professores são armazenadas separadamente em `src/teachers.json`, com senhas derivadas por PBKDF2.
