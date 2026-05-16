FROM python:3.10.9-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY --chown=user . $HOME/app

EXPOSE 7860

CMD ["python", "app.py"]