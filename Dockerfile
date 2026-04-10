# Use a imagem base leve recomendada
FROM python:3.9-slim

# Evitar a geração de arquivos .pyc e garantir logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definir o diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema necessárias para algumas libs Python (se houver)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código da aplicação
COPY . .

# Criar um usuário não-root para segurança (Best Practice DevSecOps)
RUN useradd -m streamlit_user && \
    chown -R streamlit_user:streamlit_user /app
USER streamlit_user

# Expor a porta padrão do Streamlit
EXPOSE 8501

# Comando para rodar a aplicação
# --server.address=0.0.0.0 é necessário para rodar em containers
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
