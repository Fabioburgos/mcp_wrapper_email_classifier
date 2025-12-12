# Dockerfile para AWS Lambda con Python 3.12
FROM public.ecr.aws/lambda/python:3.12

# Establecer directorio de trabajo
WORKDIR ${LAMBDA_TASK_ROOT}

# Copiar requirements.txt primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código fuente
COPY handler.py .
COPY tools/ ./tools/

# Verificar que los archivos se copiaron correctamente
RUN ls -la && \
    ls -la tools/

CMD [ "handler.lambda_handler" ]