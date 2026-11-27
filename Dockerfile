FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN cat terra_v5.part1 terra_v5.part2 > /app/terra-public.zip \
    && echo '05ff8bbda7569cc4dbe9eed7ed5f530ac925c887f5282c50bcfbe9664f99337f  /app/terra-public.zip' | sha256sum -c - \
    && rm terra_v5.part1 terra_v5.part2 \
    && chmod +x scripts/start_public.sh
EXPOSE 8501
CMD ["sh","scripts/start_public.sh"]
